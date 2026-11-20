import os
import uuid
from datetime import datetime, timezone
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, flash, 
    abort, jsonify, session
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from werkzeug.utils import secure_filename
from sqlalchemy import func

from config import Config
from models import (
    db, User, Pet, AdoptionRequest, Product, CartItem, Order, OrderItem
)

# Initialize Flask App
app = Flask(__name__)
app.config.from_object(Config)

# Initialize Extensions
db.init_app(app)

def init_app_db(app_instance):
    """
    Safely initialize database schema and ensure required demo data exists.
    Compatible with SQLite, Render PostgreSQL, and Gunicorn workers.
    Never drops existing tables or overwrites production records.
    """
    with app_instance.app_context():
        try:
            # 1. Create tables if not existing
            db.create_all()

            # 2. Check if database needs initial seeding or repair
            from seed_data import seed_database
            
            pet_count = Pet.query.count()
            prod_count = Product.query.count()
            admin_user = User.query.filter(User.role == 'admin').first()

            # If empty database or missing essential data, run safe idempotent seed
            if pet_count == 0 or prod_count == 0 or admin_user is None:
                app_instance.logger.info("[INIT] Auto-seeding database with Indian demo records and administrator account...")
                seed_database(safe_mode=True, app_instance=app_instance)
            else:
                # Ensure administrator account exists and is valid
                admin_email = app_instance.config.get('ADMIN_EMAIL', 'admin@adoptnshop.com').lower()
                admin = User.query.filter(func.lower(User.email) == admin_email).first()
                if not admin:
                    app_instance.logger.info("[INIT] Admin account missing; creating administrator account...")
                    seed_database(safe_mode=True, app_instance=app_instance)
                else:
                    if admin.role != 'admin':
                        admin.role = 'admin'
                        db.session.commit()
                    if os.environ.get('ADMIN_PASSWORD'):
                        admin.set_password(os.environ.get('ADMIN_PASSWORD'))
                        db.session.commit()

                # Ensure any legacy pets with approval_status IS NULL are approved
                from sqlalchemy import text
                try:
                    db.session.execute(text("UPDATE pets SET approval_status = 'approved' WHERE approval_status IS NULL OR approval_status = ''"))
                    db.session.commit()
                except Exception:
                    db.session.rollback()

        except Exception as e:
            app_instance.logger.warning(f"[INIT] Database initialization notice: {e}")

init_app_db(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'warning'

def utc_now():
    return datetime.now(timezone.utc)

# Ensure upload folders exist
PETS_UPLOAD_DIR = os.path.join(app.config['UPLOAD_FOLDER'], 'pets')
PRODUCTS_UPLOAD_DIR = os.path.join(app.config['UPLOAD_FOLDER'], 'products')
os.makedirs(PETS_UPLOAD_DIR, exist_ok=True)
os.makedirs(PRODUCTS_UPLOAD_DIR, exist_ok=True)


# ==========================================
# AUTHENTICATION & ACCESS CONTROL HELPERS
# ==========================================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in with administrator privileges to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        if not current_user.is_admin:
            flash('Access denied. Administrator privileges required.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def save_uploaded_file(file, subfolder):
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex[:12]}_{int(utc_now().timestamp())}.{ext}"
        destination = os.path.join(app.config['UPLOAD_FOLDER'], subfolder, filename)
        file.save(destination)
        return f"/static/uploads/{subfolder}/{filename}"
    return None


@app.template_filter('inr')
def format_inr(number):
    if number is None:
        return "₹0"
    try:
        val = float(number)
    except (ValueError, TypeError):
        return f"₹{number}"
    
    is_negative = val < 0
    val = abs(val)
    
    int_part = int(val)
    dec_part = round((val - int_part) * 100)
    
    s = str(int_part)
    if len(s) <= 3:
        formatted_int = s
    else:
        last3 = s[-3:]
        rem = s[:-3]
        parts = []
        while len(rem) > 2:
            parts.insert(0, rem[-2:])
            rem = rem[:-2]
        if rem:
            parts.insert(0, rem)
        formatted_int = ",".join(parts) + "," + last3
        
    sign = "-" if is_negative else ""
    if dec_part > 0:
        return f"{sign}₹{formatted_int}.{dec_part:02d}"
    else:
        return f"{sign}₹{formatted_int}"


@app.context_processor
def inject_global_data():
    cart_count = 0
    pending_adoptions_count = 0
    pending_listings_count = 0
    my_listed_pets_count = 0
    if current_user.is_authenticated:
        if not current_user.is_admin:
            cart_count = sum(item.quantity for item in current_user.cart_items)
            my_listed_pets_count = Pet.query.filter_by(owner_id=current_user.id).count()
        else:
            pending_adoptions_count = AdoptionRequest.query.filter_by(status='pending').count()
            pending_listings_count = Pet.query.filter(Pet.owner_id.isnot(None), Pet.approval_status == 'pending').count()
    return {
        'cart_count': cart_count,
        'pending_adoptions_count': pending_adoptions_count,
        'pending_listings_count': pending_listings_count,
        'my_listed_pets_count': my_listed_pets_count,
        'current_year': utc_now().year
    }


# ==========================================
# PUBLIC & GENERAL ROUTES
# ==========================================

@app.route('/')
def index():
    featured_pets = Pet.query.filter(Pet.status == 'available', (Pet.approval_status == 'approved') | (Pet.approval_status.is_(None))).order_by(Pet.created_at.desc()).limit(4).all()
    featured_products = Product.query.filter_by(is_active=True).filter(Product.stock > 0).order_by(Product.created_at.desc()).limit(4).all()
    
    total_pets_adopted = Pet.query.filter_by(status='adopted').count()
    total_available_pets = Pet.query.filter(Pet.status == 'available', (Pet.approval_status == 'approved') | (Pet.approval_status.is_(None))).count()
    total_products = Product.query.filter_by(is_active=True).count()
    total_customers = User.query.filter_by(role='customer').count()

    return render_template(
        'index.html',
        featured_pets=featured_pets,
        featured_products=featured_products,
        total_pets_adopted=total_pets_adopted,
        total_available_pets=total_available_pets,
        total_products=total_products,
        total_customers=total_customers
    )


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()
        if not name or not email or not message:
            flash('Please complete all fields before sending.', 'danger')
        else:
            flash(f'Thank you, {name}! Your message has been received. Our team will get back to you soon.', 'success')
            return redirect(url_for('contact'))
    return render_template('contact.html')


# ==========================================
# AUTHENTICATION ROUTES
# ==========================================

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()

        # Backend validations
        if not name or not email or not password:
            flash('Full Name, Email, and Password are required.', 'danger')
            return render_template('auth/register.html', name=name, email=email, phone=phone, address=address)

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('auth/register.html', name=name, email=email, phone=phone, address=address)

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html', name=name, email=email, phone=phone, address=address)

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('An account with this email address already exists. Please log in.', 'warning')
            return redirect(url_for('login'))

        new_user = User(
            name=name,
            email=email,
            phone=phone,
            address=address,
            role='customer'
        )
        new_user.set_password(password)

        db.session.add(new_user)
        db.session.commit()

        login_user(new_user)
        flash(f'Welcome to Adopt n Shop, {new_user.name}! Your account has been created successfully.', 'success')
        return redirect(url_for('index'))

    return render_template('auth/register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash('Invalid email address or password. Please try again.', 'danger')
            return render_template('auth/login.html', email=email)

        login_user(user, remember=remember)
        flash(f'Welcome back, {user.name}!', 'success')

        next_page = request.args.get('next')
        if next_page and next_page.startswith('/'):
            return redirect(next_page)
        
        if user.is_admin:
            return redirect(url_for('admin_dashboard'))
        return redirect(url_for('index'))

    return render_template('auth/login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out successfully. See you again soon!', 'info')
    return redirect(url_for('index'))


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')

        if not name:
            flash('Name cannot be empty.', 'danger')
            return redirect(url_for('profile'))

        current_user.name = name
        current_user.phone = phone
        current_user.address = address

        if new_password:
            if not current_password or not current_user.check_password(current_password):
                flash('Current password is incorrect. Profile details saved without password change.', 'warning')
            elif len(new_password) < 6:
                flash('New password must be at least 6 characters long.', 'danger')
            else:
                current_user.set_password(new_password)
                flash('Profile and password updated successfully!', 'success')
                db.session.commit()
                return redirect(url_for('profile'))

        db.session.commit()
        flash('Profile details updated successfully.', 'success')
        return redirect(url_for('profile'))

    recent_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).limit(3).all()
    recent_adoptions = AdoptionRequest.query.filter_by(user_id=current_user.id).order_by(AdoptionRequest.created_at.desc()).limit(3).all()
    
    return render_template(
        'auth/profile.html',
        recent_orders=recent_orders,
        recent_adoptions=recent_adoptions
    )


INDIAN_CITIES = ['Pune', 'Mumbai', 'Delhi', 'Bengaluru', 'Nashik', 'Solapur', 'Hyderabad', 'Ahmedabad', 'Chennai', 'Kolkata', 'Jaipur', 'Nagpur']
INDIAN_STATES = ['Maharashtra', 'Karnataka', 'Delhi NCR', 'Telangana', 'Gujarat', 'Tamil Nadu', 'West Bengal', 'Rajasthan']

# ==========================================
# PET ADOPTION MODULE ROUTES
# ==========================================

@app.route('/pets')
def pets_list():
    query_text = request.args.get('q', '').strip()
    species = request.args.get('species', 'all')
    gender = request.args.get('gender', 'all')
    status = request.args.get('status', 'all')
    city = request.args.get('city', 'all')
    state = request.args.get('state', 'all')

    # Only approved pets appear on the public storefront
    query = Pet.query.filter((Pet.approval_status == 'approved') | (Pet.approval_status.is_(None)))

    if query_text:
        query = query.filter(
            (Pet.name.ilike(f'%{query_text}%')) | 
            (Pet.breed.ilike(f'%{query_text}%')) |
            (Pet.description.ilike(f'%{query_text}%')) |
            (Pet.city.ilike(f'%{query_text}%')) |
            (Pet.state.ilike(f'%{query_text}%'))
        )

    if species != 'all' and species:
        query = query.filter_by(species=species)

    if gender != 'all' and gender:
        query = query.filter_by(gender=gender)

    if status != 'all' and status:
        query = query.filter_by(status=status)

    if city != 'all' and city:
        query = query.filter_by(city=city)

    if state != 'all' and state:
        query = query.filter_by(state=state)

    pets = query.order_by(
        Pet.status.asc(),
        Pet.created_at.desc()
    ).all()

    return render_template(
        'pets/list.html',
        pets=pets,
        selected_species=species,
        selected_gender=gender,
        selected_status=status,
        selected_city=city,
        selected_state=state,
        cities=INDIAN_CITIES,
        states=INDIAN_STATES,
        search_query=query_text
    )


@app.route('/pets/<int:pet_id>')
def pet_detail(pet_id):
    pet = db.session.get(Pet, pet_id)
    if not pet:
        abort(404)

    # Unapproved customer listings are only viewable by their owner or an administrator
    if pet.approval_status != 'approved':
        if not current_user.is_authenticated or (pet.owner_id != current_user.id and not current_user.is_admin):
            abort(404)

    user_has_applied = False
    if current_user.is_authenticated:
        existing_req = AdoptionRequest.query.filter_by(
            user_id=current_user.id,
            pet_id=pet.id
        ).first()
        if existing_req:
            user_has_applied = True

    similar_pets = Pet.query.filter(
        Pet.species == pet.species,
        Pet.id != pet.id,
        Pet.status == 'available',
        Pet.approval_status == 'approved'
    ).limit(3).all()

    return render_template(
        'pets/detail.html',
        pet=pet,
        user_has_applied=user_has_applied,
        similar_pets=similar_pets
    )


@app.route('/pets/<int:pet_id>/apply', methods=['GET', 'POST'])
@login_required
def pet_apply(pet_id):
    if current_user.is_admin:
        flash('Administrators cannot submit adoption applications.', 'warning')
        return redirect(url_for('pet_detail', pet_id=pet_id))

    pet = db.session.get(Pet, pet_id)
    if not pet:
        abort(404)

    if pet.owner_id == current_user.id:
        flash('You cannot apply to adopt your own listed pet.', 'warning')
        return redirect(url_for('pet_detail', pet_id=pet_id))

    if pet.status == 'adopted':
        flash('This pet has already found a loving forever home!', 'info')
        return redirect(url_for('pet_detail', pet_id=pet_id))

    existing_application = AdoptionRequest.query.filter_by(
        user_id=current_user.id,
        pet_id=pet.id
    ).first()

    if existing_application:
        flash('You have already submitted an adoption application for this pet. Track your application status below.', 'info')
        return redirect(url_for('my_adoptions'))

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        living_situation = request.form.get('living_situation', '').strip()
        has_other_pets = bool(request.form.get('has_other_pets'))
        previous_experience = request.form.get('previous_experience', '').strip()
        reason = request.form.get('reason', '').strip()

        if not full_name or not phone or not address or not living_situation or not reason:
            flash('Please complete all required fields on the application form.', 'danger')
            return render_template('pets/apply.html', pet=pet)

        adoption_req = AdoptionRequest(
            user_id=current_user.id,
            pet_id=pet.id,
            full_name=full_name,
            phone=phone,
            address=address,
            living_situation=living_situation,
            has_other_pets=has_other_pets,
            previous_experience=previous_experience,
            reason=reason,
            status='pending'
        )

        # Mark pet as pending if it's currently available
        if pet.status == 'available':
            pet.status = 'pending'

        db.session.add(adoption_req)
        db.session.commit()

        flash(f'Your adoption application for {pet.name} has been submitted successfully! The caregiver will review it.', 'success')
        return redirect(url_for('my_adoptions'))

    return render_template('pets/apply.html', pet=pet)


@app.route('/my-adoptions')
@login_required
def my_adoptions():
    applications = AdoptionRequest.query.filter_by(user_id=current_user.id).order_by(AdoptionRequest.created_at.desc()).all()
    return render_template('pets/my_requests.html', applications=applications)


# --- Customer Pet Rehoming / Listing Feature ---

# --- Customer Pet Rehoming / Listing Feature ---

@app.route('/pets/list-my-pet', methods=['GET', 'POST'])
@login_required
def list_my_pet():
    if current_user.is_admin:
        flash('Admins can list shelter pets directly via the Admin Dashboard.', 'info')
        return redirect(url_for('admin_pet_new'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        species = request.form.get('species', 'Dog')
        breed = request.form.get('breed', '').strip()
        age_years = int(request.form.get('age_years', 0))
        age_months = int(request.form.get('age_months', 0))
        gender = request.form.get('gender', 'Male')
        size = request.form.get('size', 'Medium')
        city = request.form.get('city', 'Mumbai').strip()
        state = request.form.get('state', 'Maharashtra').strip()
        contact_phone = request.form.get('contact_phone', current_user.phone or '').strip()
        try:
            rehoming_fee = float(request.form.get('rehoming_fee', 0.0) or 0.0)
            if rehoming_fee < 0:
                rehoming_fee = 0.0
        except ValueError:
            rehoming_fee = 0.0
        health_status = request.form.get('health_status', 'Healthy & Vaccinated').strip()
        vaccinated = bool(request.form.get('vaccinated'))
        description = request.form.get('description', '').strip()

        if not name or not breed or not description:
            flash('Pet Name, Breed, and Description are required.', 'danger')
            return render_template('pets/list_pet.html', cities=INDIAN_CITIES, states=INDIAN_STATES)

        image_file = request.files.get('image')
        image_url = None
        if image_file and image_file.filename != '':
            image_url = save_uploaded_file(image_file, 'pets')

        if not image_url:
            image_url = '/static/images/default_pet.svg'

        # Handle multiple photos
        additional_files = request.files.getlist('additional_images')
        extra_urls = []
        for extra_file in additional_files:
            if extra_file and extra_file.filename != '':
                saved_url = save_uploaded_file(extra_file, 'pets')
                if saved_url:
                    extra_urls.append(saved_url)
        additional_images_str = ','.join(extra_urls) if extra_urls else None

        new_pet = Pet(
            owner_id=current_user.id,
            name=name,
            species=species,
            breed=breed,
            age_years=age_years,
            age_months=age_months,
            gender=gender,
            size=size,
            city=city,
            state=state,
            contact_phone=contact_phone,
            rehoming_fee=rehoming_fee,
            additional_images=additional_images_str,
            health_status=health_status,
            vaccinated=vaccinated,
            description=description,
            image_url=image_url,
            status='available',
            approval_status='pending',
            approval_notes=None
        )

        db.session.add(new_pet)
        db.session.commit()

        flash(f'Thank you, {current_user.name}! Your pet listing for "{new_pet.name}" has been submitted and is currently Pending Approval by our team. You can view its status below.', 'success')
        return redirect(url_for('my_listed_pets'))

    return render_template('pets/list_pet.html', cities=INDIAN_CITIES, states=INDIAN_STATES)


@app.route('/my-listings')
@app.route('/my-listed-pets')
@login_required
def my_listed_pets():
    pets = Pet.query.filter_by(owner_id=current_user.id).order_by(Pet.created_at.desc()).all()
    return render_template('pets/my_listed_pets.html', pets=pets)


@app.route('/my-listings/<int:pet_id>/edit', methods=['GET', 'POST'])
@app.route('/my-listed-pets/<int:pet_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_listed_pet(pet_id):
    pet = db.session.get(Pet, pet_id)
    if not pet or (pet.owner_id != current_user.id and not current_user.is_admin):
        abort(403)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        species = request.form.get('species', pet.species)
        breed = request.form.get('breed', '').strip()
        age_years = int(request.form.get('age_years', pet.age_years))
        age_months = int(request.form.get('age_months', pet.age_months))
        gender = request.form.get('gender', pet.gender)
        size = request.form.get('size', pet.size)
        city = request.form.get('city', pet.city).strip()
        state = request.form.get('state', pet.state).strip()
        contact_phone = request.form.get('contact_phone', pet.contact_phone or '').strip()
        try:
            rehoming_fee = float(request.form.get('rehoming_fee', pet.rehoming_fee) or 0.0)
            if rehoming_fee < 0:
                rehoming_fee = 0.0
        except ValueError:
            rehoming_fee = 0.0
        health_status = request.form.get('health_status', pet.health_status).strip()
        vaccinated = bool(request.form.get('vaccinated'))
        description = request.form.get('description', '').strip()

        if not name or not breed or not description:
            flash('Pet Name, Breed, and Description are required.', 'danger')
            return render_template('pets/edit_pet.html', pet=pet, cities=INDIAN_CITIES, states=INDIAN_STATES)

        pet.name = name
        pet.species = species
        pet.breed = breed
        pet.age_years = age_years
        pet.age_months = age_months
        pet.gender = gender
        pet.size = size
        pet.city = city
        pet.state = state
        pet.contact_phone = contact_phone
        pet.rehoming_fee = rehoming_fee
        pet.health_status = health_status
        pet.vaccinated = vaccinated
        pet.description = description

        # If customer edits listing, reset to pending approval for re-verification
        if not current_user.is_admin:
            pet.approval_status = 'pending'
            pet.approval_notes = None

        image_file = request.files.get('image')
        if image_file and image_file.filename != '':
            new_image = save_uploaded_file(image_file, 'pets')
            if new_image:
                pet.image_url = new_image

        additional_files = request.files.getlist('additional_images')
        extra_urls = []
        for extra_file in additional_files:
            if extra_file and extra_file.filename != '':
                saved_url = save_uploaded_file(extra_file, 'pets')
                if saved_url:
                    extra_urls.append(saved_url)
        if extra_urls:
            existing = [u.strip() for u in pet.additional_images.split(',') if u.strip()] if pet.additional_images else []
            existing.extend(extra_urls)
            pet.additional_images = ','.join(existing)

        db.session.commit()
        flash(f'Your pet listing for "{pet.name}" has been updated and resubmitted for admin review.', 'success')
        return redirect(url_for('my_listed_pets'))

    return render_template('pets/edit_pet.html', pet=pet, cities=INDIAN_CITIES, states=INDIAN_STATES)


@app.route('/my-listings/<int:pet_id>/delete', methods=['POST'])
@app.route('/my-listed-pets/<int:pet_id>/delete', methods=['POST'])
@login_required
def delete_listed_pet(pet_id):
    pet = db.session.get(Pet, pet_id)
    if not pet or (pet.owner_id != current_user.id and not current_user.is_admin):
        abort(403)
    name = pet.name
    db.session.delete(pet)
    db.session.commit()
    flash(f'Your pet listing for "{name}" has been removed.', 'info')
    return redirect(url_for('my_listed_pets'))


@app.route('/my-listings/<int:pet_id>/mark-adopted', methods=['POST'])
@app.route('/my-listed-pets/<int:pet_id>/mark-adopted', methods=['POST'])
@login_required
def mark_pet_adopted(pet_id):
    pet = db.session.get(Pet, pet_id)
    if not pet or (pet.owner_id != current_user.id and not current_user.is_admin):
        abort(403)
    pet.status = 'adopted'
    db.session.commit()
    flash(f'Wonderful news! "{pet.name}" has been marked as adopted.', 'success')
    return redirect(url_for('my_listed_pets'))


@app.route('/my-listed-pets/<int:pet_id>/applications')
@login_required
def pet_applications(pet_id):
    pet = db.session.get(Pet, pet_id)
    if not pet or (pet.owner_id != current_user.id and not current_user.is_admin):
        abort(403)
    applications = AdoptionRequest.query.filter_by(pet_id=pet.id).order_by(AdoptionRequest.created_at.desc()).all()
    return render_template('pets/pet_applications.html', pet=pet, applications=applications)


# ==========================================
# PET SHOP MODULE ROUTES
# ==========================================

@app.route('/shop')
def shop_list():
    category = request.args.get('category', 'all')
    search_query = request.args.get('q', '').strip()
    sort_by = request.args.get('sort', 'featured')

    query = Product.query.filter_by(is_active=True)

    if category != 'all' and category:
        query = query.filter_by(category=category)

    if search_query:
        query = query.filter(
            (Product.name.ilike(f'%{search_query}%')) |
            (Product.description.ilike(f'%{search_query}%'))
        )

    if sort_by == 'price_low':
        query = query.order_by(Product.price.asc())
    elif sort_by == 'price_high':
        query = query.order_by(Product.price.desc())
    elif sort_by == 'name':
        query = query.order_by(Product.name.asc())
    else:
        query = query.order_by(Product.created_at.desc())

    products = query.all()
    categories = ['Food', 'Toys', 'Accessories', 'Healthcare']

    return render_template(
        'shop/list.html',
        products=products,
        categories=categories,
        selected_category=category,
        search_query=search_query,
        selected_sort=sort_by
    )


@app.route('/shop/<int:product_id>')
def product_detail(product_id):
    product = db.session.get(Product, product_id)
    if not product or not product.is_active:
        abort(404)

    related_products = Product.query.filter(
        Product.category == product.category,
        Product.id != product.id,
        Product.is_active == True
    ).limit(4).all()

    return render_template('shop/detail.html', product=product, related_products=related_products)


# ==========================================
# SHOPPING CART MODULE ROUTES
# ==========================================

@app.route('/cart')
@login_required
def view_cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    subtotal = sum(item.subtotal for item in cart_items)
    
    # Free delivery on orders over ₹999, else ₹99
    shipping_fee = 0.0 if (subtotal >= 999.0 or subtotal == 0) else 99.0
    tax_amount = round(subtotal * 0.05, 2)
    grand_total = round(subtotal + shipping_fee + tax_amount, 2)

    return render_template(
        'cart/view.html',
        cart_items=cart_items,
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        tax_amount=tax_amount,
        grand_total=grand_total
    )


@app.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    if current_user.is_admin:
        flash('Admins cannot make purchases. Please use a customer account.', 'warning')
        return redirect(url_for('product_detail', product_id=product_id))

    product = db.session.get(Product, product_id)
    if not product or not product.is_active:
        flash('Product not found or currently unavailable.', 'danger')
        return redirect(url_for('shop_list'))

    quantity = int(request.form.get('quantity', 1))
    if quantity < 1:
        quantity = 1

    if product.stock < quantity:
        flash(f'Only {product.stock} unit(s) of {product.name} are available.', 'warning')
        return redirect(url_for('product_detail', product_id=product_id))

    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product.id).first()

    if cart_item:
        if cart_item.quantity + quantity > product.stock:
            cart_item.quantity = product.stock
            flash(f'Cart updated to maximum available stock ({product.stock}).', 'info')
        else:
            cart_item.quantity += quantity
            flash(f'Added {quantity} more of "{product.name}" to your cart.', 'success')
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product.id, quantity=quantity)
        db.session.add(cart_item)
        flash(f'"{product.name}" added to your cart!', 'success')

    db.session.commit()
    
    redirect_target = request.form.get('next')
    if redirect_target:
        return redirect(redirect_target)
    return redirect(url_for('view_cart'))


@app.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart_item(item_id):
    cart_item = db.session.get(CartItem, item_id)
    if not cart_item or cart_item.user_id != current_user.id:
        flash('Cart item not found.', 'danger')
        return redirect(url_for('view_cart'))

    action = request.form.get('action')
    if action == 'increase':
        if cart_item.quantity < cart_item.product.stock:
            cart_item.quantity += 1
            db.session.commit()
        else:
            flash(f'Maximum stock ({cart_item.product.stock}) reached for this item.', 'warning')
    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            db.session.commit()
        else:
            db.session.delete(cart_item)
            db.session.commit()
            flash('Item removed from cart.', 'info')
    elif action == 'set':
        new_qty = int(request.form.get('quantity', 1))
        if new_qty <= 0:
            db.session.delete(cart_item)
            flash('Item removed from cart.', 'info')
        elif new_qty > cart_item.product.stock:
            cart_item.quantity = cart_item.product.stock
            flash(f'Quantity adjusted to maximum available stock ({cart_item.product.stock}).', 'warning')
        else:
            cart_item.quantity = new_qty
        db.session.commit()

    return redirect(url_for('view_cart'))


@app.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    cart_item = db.session.get(CartItem, item_id)
    if cart_item and cart_item.user_id == current_user.id:
        product_name = cart_item.product.name
        db.session.delete(cart_item)
        db.session.commit()
        flash(f'"{product_name}" removed from cart.', 'info')
    return redirect(url_for('view_cart'))


@app.route('/cart/clear', methods=['POST'])
@login_required
def clear_cart():
    CartItem.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()
    flash('Your shopping cart has been cleared.', 'info')
    return redirect(url_for('view_cart'))


# ==========================================
# CHECKOUT & ORDER MANAGEMENT ROUTES
# ==========================================

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if current_user.is_admin:
        flash('Admins cannot place orders.', 'warning')
        return redirect(url_for('index'))

    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not cart_items:
        flash('Your cart is empty. Please add items before proceeding to checkout.', 'warning')
        return redirect(url_for('shop_list'))

    # Verify inventory availability
    for item in cart_items:
        if item.quantity > item.product.stock:
            flash(f'Sorry, only {item.product.stock} of "{item.product.name}" are in stock. Please adjust quantity.', 'danger')
            return redirect(url_for('view_cart'))

    subtotal = sum(item.subtotal for item in cart_items)
    shipping_fee = 0.0 if subtotal >= 999.0 else 99.0
    tax_amount = round(subtotal * 0.05, 2)
    grand_total = round(subtotal + shipping_fee + tax_amount, 2)

    if request.method == 'POST':
        shipping_name = request.form.get('shipping_name', '').strip()
        shipping_phone = request.form.get('shipping_phone', '').strip()
        shipping_address = request.form.get('shipping_address', '').strip()
        shipping_city = request.form.get('shipping_city', 'Mumbai').strip()
        shipping_pincode = request.form.get('shipping_pincode', '400050').strip()
        payment_method = request.form.get('payment_method', 'UPI / QR (Google Pay, PhonePe, Paytm)')

        if not shipping_name or not shipping_phone or not shipping_address:
            flash('Please fill in complete delivery address and contact details.', 'danger')
            return render_template(
                'cart/checkout.html',
                cart_items=cart_items,
                subtotal=subtotal,
                shipping_fee=shipping_fee,
                tax_amount=tax_amount,
                grand_total=grand_total
            )

        # Generate unique Indian order number
        order_number = f"ANS-IN-{utc_now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        # Create Order
        new_order = Order(
            user_id=current_user.id,
            order_number=order_number,
            subtotal_amount=subtotal,
            shipping_fee=shipping_fee,
            tax_amount=tax_amount,
            total_amount=grand_total,
            status='Pending',
            payment_method=payment_method,
            payment_status='Paid' if payment_method != 'Cash on Delivery' else 'Pending',
            shipping_name=shipping_name,
            shipping_phone=shipping_phone,
            shipping_address=shipping_address,
            shipping_city=shipping_city,
            shipping_pincode=shipping_pincode
        )

        db.session.add(new_order)
        db.session.flush()  # assign new_order.id

        # Create OrderItems and decrease inventory stock
        for item in cart_items:
            order_item = OrderItem(
                order_id=new_order.id,
                product_id=item.product.id,
                product_name=item.product.name,
                price=item.product.price,
                quantity=item.quantity,
                subtotal=item.subtotal
            )
            db.session.add(order_item)
            item.product.stock -= item.quantity

        # Clear user cart
        CartItem.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        flash(f'Order placed successfully! Order Number: {order_number}', 'success')
        return redirect(url_for('order_confirmation', order_number=order_number))

    return render_template(
        'cart/checkout.html',
        cart_items=cart_items,
        subtotal=subtotal,
        shipping_fee=shipping_fee,
        tax_amount=tax_amount,
        grand_total=grand_total
    )


@app.route('/orders/<order_number>/confirmation')
@login_required
def order_confirmation(order_number):
    order = Order.query.filter_by(order_number=order_number).first()
    if not order or (order.user_id != current_user.id and not current_user.is_admin):
        abort(404)
    return render_template('orders/confirmation.html', order=order)


@app.route('/my-orders')
@login_required
def my_orders():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders/my_orders.html', orders=orders)


@app.route('/orders/<int:order_id>')
@login_required
def order_detail(order_id):
    order = db.session.get(Order, order_id)
    if not order or (order.user_id != current_user.id and not current_user.is_admin):
        abort(404)
    return render_template('orders/detail.html', order=order)


# ==========================================
# ADMIN DASHBOARD & MANAGEMENT MODULE
# ==========================================

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    total_users = User.query.filter_by(role='customer').count()
    total_pets = Pet.query.count()
    available_pets = Pet.query.filter_by(status='available').count()
    adopted_pets = Pet.query.filter_by(status='adopted').count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    pending_adoptions = AdoptionRequest.query.filter_by(status='pending').count()

    total_revenue = db.session.query(func.coalesce(func.sum(Order.total_amount), 0.0)).filter(Order.status != 'Cancelled').scalar()

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    recent_adoptions = AdoptionRequest.query.order_by(AdoptionRequest.created_at.desc()).limit(5).all()
    low_stock_products = Product.query.filter(Product.stock <= 5, Product.is_active == True).limit(5).all()

    return render_template(
        'admin/dashboard.html',
        total_users=total_users,
        total_pets=total_pets,
        available_pets=available_pets,
        adopted_pets=adopted_pets,
        total_products=total_products,
        total_orders=total_orders,
        pending_adoptions=pending_adoptions,
        total_revenue=round(total_revenue, 2),
        recent_orders=recent_orders,
        recent_adoptions=recent_adoptions,
        low_stock_products=low_stock_products
    )


@app.route('/admin/api/analytics')
@login_required
@admin_required
def admin_api_analytics():
    # Pets by species
    species_data = db.session.query(Pet.species, func.count(Pet.id)).group_by(Pet.species).all()
    species_labels = [s[0] for s in species_data]
    species_counts = [s[1] for s in species_data]

    # Products by category
    cat_data = db.session.query(Product.category, func.count(Product.id)).group_by(Product.category).all()
    cat_labels = [c[0] for c in cat_data]
    cat_counts = [c[1] for c in cat_data]

    # Order status breakdown
    order_status_data = db.session.query(Order.status, func.count(Order.id)).group_by(Order.status).all()
    order_status_labels = [o[0] for o in order_status_data]
    order_status_counts = [o[1] for o in order_status_data]

    return jsonify({
        'species': {'labels': species_labels, 'counts': species_counts},
        'categories': {'labels': cat_labels, 'counts': cat_counts},
        'order_statuses': {'labels': order_status_labels, 'counts': order_status_counts}
    })


# --- Admin: Pet Management ---

@app.route('/admin/pets')
@login_required
@admin_required
def admin_pets():
    search = request.args.get('q', '').strip()
    status = request.args.get('status', 'all')
    
    query = Pet.query
    if search:
        query = query.filter((Pet.name.ilike(f'%{search}%')) | (Pet.breed.ilike(f'%{search}%')))
    if status != 'all' and status:
        query = query.filter_by(status=status)

    pets = query.order_by(Pet.created_at.desc()).all()
    return render_template('admin/pets.html', pets=pets, search=search, selected_status=status)


@app.route('/admin/pets/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_pet_new():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        species = request.form.get('species', 'Dog')
        breed = request.form.get('breed', '').strip()
        age_years = int(request.form.get('age_years', 0))
        age_months = int(request.form.get('age_months', 0))
        gender = request.form.get('gender', 'Male')
        size = request.form.get('size', 'Medium')
        city = request.form.get('city', 'Mumbai').strip()
        state = request.form.get('state', 'Maharashtra').strip()
        contact_phone = request.form.get('contact_phone', '').strip()
        try:
            rehoming_fee = float(request.form.get('rehoming_fee', 0.0) or 0.0)
            if rehoming_fee < 0:
                rehoming_fee = 0.0
        except ValueError:
            rehoming_fee = 0.0
        health_status = request.form.get('health_status', 'Healthy').strip()
        vaccinated = bool(request.form.get('vaccinated'))
        description = request.form.get('description', '').strip()
        status = request.form.get('status', 'available')

        if not name or not breed:
            flash('Pet Name and Breed are required.', 'danger')
            return render_template('admin/pet_form.html', pet=None, cities=INDIAN_CITIES, states=INDIAN_STATES)

        image_file = request.files.get('image')
        image_url = None
        if image_file and image_file.filename != '':
            image_url = save_uploaded_file(image_file, 'pets')

        if not image_url:
            image_url = '/static/images/default_pet.svg'

        new_pet = Pet(
            name=name,
            species=species,
            breed=breed,
            age_years=age_years,
            age_months=age_months,
            gender=gender,
            size=size,
            city=city,
            state=state,
            contact_phone=contact_phone,
            rehoming_fee=rehoming_fee,
            health_status=health_status,
            vaccinated=vaccinated,
            description=description,
            image_url=image_url,
            status=status,
            approval_status='approved'
        )

        db.session.add(new_pet)
        db.session.commit()
        flash(f'Pet "{new_pet.name}" has been added to the system.', 'success')
        return redirect(url_for('admin_pets'))

    return render_template('admin/pet_form.html', pet=None, cities=INDIAN_CITIES, states=INDIAN_STATES)


@app.route('/admin/pets/<int:pet_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_pet_edit(pet_id):
    pet = db.session.get(Pet, pet_id)
    if not pet:
        abort(404)

    if request.method == 'POST':
        pet.name = request.form.get('name', '').strip()
        pet.species = request.form.get('species', pet.species)
        pet.breed = request.form.get('breed', '').strip()
        pet.age_years = int(request.form.get('age_years', pet.age_years))
        pet.age_months = int(request.form.get('age_months', pet.age_months))
        pet.gender = request.form.get('gender', pet.gender)
        pet.size = request.form.get('size', pet.size)
        pet.city = request.form.get('city', pet.city).strip()
        pet.state = request.form.get('state', pet.state).strip()
        pet.contact_phone = request.form.get('contact_phone', pet.contact_phone or '').strip()
        try:
            rehoming_fee = float(request.form.get('rehoming_fee', pet.rehoming_fee) or 0.0)
            if rehoming_fee < 0:
                rehoming_fee = 0.0
            pet.rehoming_fee = rehoming_fee
        except ValueError:
            pass
        pet.health_status = request.form.get('health_status', pet.health_status).strip()
        pet.vaccinated = bool(request.form.get('vaccinated'))
        pet.description = request.form.get('description', '').strip()
        pet.status = request.form.get('status', pet.status)

        image_file = request.files.get('image')
        if image_file and image_file.filename != '':
            new_image = save_uploaded_file(image_file, 'pets')
            if new_image:
                pet.image_url = new_image

        db.session.commit()
        flash(f'Pet "{pet.name}" details updated successfully.', 'success')
        return redirect(url_for('admin_pets'))

    return render_template('admin/pet_form.html', pet=pet, cities=INDIAN_CITIES, states=INDIAN_STATES)


@app.route('/admin/pets/<int:pet_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_pet_delete(pet_id):
    pet = db.session.get(Pet, pet_id)
    if pet:
        name = pet.name
        db.session.delete(pet)
        db.session.commit()
        flash(f'Pet "{name}" removed from the platform.', 'info')
    return redirect(url_for('admin_pets'))


# --- Admin: Customer Pet Listing Approvals ---

@app.route('/admin/listing-approvals')
@login_required
@admin_required
def admin_listing_approvals():
    tab = request.args.get('tab', 'pending')
    query = Pet.query.filter(Pet.owner_id.isnot(None))

    pending_count = Pet.query.filter(Pet.owner_id.isnot(None), Pet.approval_status == 'pending').count()
    approved_count = Pet.query.filter(Pet.owner_id.isnot(None), Pet.approval_status == 'approved').count()
    rejected_count = Pet.query.filter(Pet.owner_id.isnot(None), Pet.approval_status == 'rejected').count()
    total_count = Pet.query.filter(Pet.owner_id.isnot(None)).count()

    if tab == 'pending':
        query = query.filter_by(approval_status='pending')
    elif tab == 'approved':
        query = query.filter_by(approval_status='approved')
    elif tab == 'rejected':
        query = query.filter_by(approval_status='rejected')

    listings = query.order_by(Pet.created_at.desc()).all()

    return render_template(
        'admin/listing_approvals.html',
        listings=listings,
        active_tab=tab,
        pending_count=pending_count,
        approved_count=approved_count,
        rejected_count=rejected_count,
        total_count=total_count
    )


@app.route('/admin/listing-approvals/<int:pet_id>/action', methods=['POST'])
@login_required
@admin_required
def admin_listing_action(pet_id):
    pet = db.session.get(Pet, pet_id)
    if not pet:
        abort(404)

    action = request.form.get('action')
    notes = request.form.get('notes', '').strip()

    if action == 'approve':
        pet.approval_status = 'approved'
        pet.approval_notes = notes or 'Listing approved by shelter administrator.'
        owner_name = pet.owner.name if pet.owner else "User"
        flash(f'Pet listing "{pet.name}" submitted by {owner_name} has been APPROVED and is now live on the public adoption catalogue.', 'success')
    elif action == 'reject':
        pet.approval_status = 'rejected'
        pet.approval_notes = notes or 'Listing was rejected. Please review our shelter policy guidelines.'
        flash(f'Pet listing "{pet.name}" has been REJECTED. The pet owner will see your feedback in their portal.', 'warning')
    else:
        flash('Invalid action requested.', 'danger')

    db.session.commit()
    return redirect(url_for('admin_listing_approvals', tab=request.args.get('tab', 'pending')))


# --- Admin: Adoption Requests Management ---

@app.route('/admin/adoptions')
@login_required
@admin_required
def admin_adoptions():
    status = request.args.get('status', 'all')
    query = AdoptionRequest.query
    if status != 'all' and status:
        query = query.filter_by(status=status)
    adoptions = query.order_by(AdoptionRequest.created_at.desc()).all()
    return render_template('admin/adoptions.html', adoptions=adoptions, selected_status=status)


@app.route('/admin/adoptions/<int:request_id>/status', methods=['POST'])
@login_required
@admin_required
def admin_adoption_update_status(request_id):
    adoption_req = db.session.get(AdoptionRequest, request_id)
    if not adoption_req:
        abort(404)

    new_status = request.form.get('status')
    admin_notes = request.form.get('admin_notes', '').strip()

    if new_status in ['approved', 'rejected', 'pending']:
        adoption_req.status = new_status
        adoption_req.admin_notes = admin_notes

        # Synchronize pet status
        if new_status == 'approved':
            adoption_req.pet.status = 'adopted'
            # Reject any other pending applications for the same pet
            other_apps = AdoptionRequest.query.filter(
                AdoptionRequest.pet_id == adoption_req.pet_id,
                AdoptionRequest.id != adoption_req.id,
                AdoptionRequest.status == 'pending'
            ).all()
            for other_app in other_apps:
                other_app.status = 'rejected'
                other_app.admin_notes = f'Another applicant was approved for {adoption_req.pet.name}.'
        elif new_status == 'rejected':
            # Check if there are other pending requests
            other_pending = AdoptionRequest.query.filter(
                AdoptionRequest.pet_id == adoption_req.pet_id,
                AdoptionRequest.id != adoption_req.id,
                AdoptionRequest.status == 'pending'
            ).first()
            if not other_pending and adoption_req.pet.status == 'pending':
                adoption_req.pet.status = 'available'

        db.session.commit()
        flash(f'Adoption application #{adoption_req.id} status updated to {new_status.capitalize()}.', 'success')

    return redirect(url_for('admin_adoptions'))


# --- Admin: Product Management ---

@app.route('/admin/products')
@login_required
@admin_required
def admin_products():
    category = request.args.get('category', 'all')
    search = request.args.get('q', '').strip()

    query = Product.query
    if category != 'all' and category:
        query = query.filter_by(category=category)
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))

    products = query.order_by(Product.created_at.desc()).all()
    categories = ['Food', 'Toys', 'Accessories', 'Healthcare']
    return render_template('admin/products.html', products=products, categories=categories, selected_category=category, search=search)


@app.route('/admin/products/new', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_product_new():
    categories = ['Food', 'Toys', 'Accessories', 'Healthcare']
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category = request.form.get('category', 'Food')
        description = request.form.get('description', '').strip()
        price = float(request.form.get('price', 0.0))
        stock = int(request.form.get('stock', 0))
        is_active = bool(request.form.get('is_active'))

        if not name or price <= 0:
            flash('Product Name and valid positive Price are required.', 'danger')
            return render_template('admin/product_form.html', product=None, categories=categories)

        image_file = request.files.get('image')
        image_url = None
        if image_file and image_file.filename != '':
            image_url = save_uploaded_file(image_file, 'products')

        if not image_url:
            image_url = '/static/images/default_product.svg'

        new_product = Product(
            name=name,
            category=category,
            description=description,
            price=price,
            stock=stock,
            image_url=image_url,
            is_active=is_active
        )

        db.session.add(new_product)
        db.session.commit()
        flash(f'Product "{new_product.name}" added to catalogue.', 'success')
        return redirect(url_for('admin_products'))

    return render_template('admin/product_form.html', product=None, categories=categories)


@app.route('/admin/products/<int:product_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def admin_product_edit(product_id):
    product = db.session.get(Product, product_id)
    if not product:
        abort(404)

    categories = ['Food', 'Toys', 'Accessories', 'Healthcare']

    if request.method == 'POST':
        product.name = request.form.get('name', '').strip()
        product.category = request.form.get('category', product.category)
        product.description = request.form.get('description', '').strip()
        product.price = float(request.form.get('price', product.price))
        product.stock = int(request.form.get('stock', product.stock))
        product.is_active = bool(request.form.get('is_active'))

        image_file = request.files.get('image')
        if image_file and image_file.filename != '':
            new_image = save_uploaded_file(image_file, 'products')
            if new_image:
                product.image_url = new_image

        db.session.commit()
        flash(f'Product "{product.name}" updated successfully.', 'success')
        return redirect(url_for('admin_products'))

    return render_template('admin/product_form.html', product=product, categories=categories)


@app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
@login_required
@admin_required
def admin_product_delete(product_id):
    product = db.session.get(Product, product_id)
    if product:
        name = product.name
        # Soft delete (deactivate) or hard delete
        product.is_active = False
        db.session.commit()
        flash(f'Product "{name}" deactivated from storefront.', 'info')
    return redirect(url_for('admin_products'))


# --- Admin: Order Management ---

@app.route('/admin/orders')
@login_required
@admin_required
def admin_orders():
    status = request.args.get('status', 'all')
    search = request.args.get('q', '').strip()

    query = Order.query
    if status != 'all' and status:
        query = query.filter_by(status=status)
    if search:
        query = query.filter(
            (Order.order_number.ilike(f'%{search}%')) |
            (Order.shipping_name.ilike(f'%{search}%'))
        )

    orders = query.order_by(Order.created_at.desc()).all()
    statuses = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
    return render_template('admin/orders.html', orders=orders, statuses=statuses, selected_status=status, search=search)


@app.route('/admin/orders/<int:order_id>')
@login_required
@admin_required
def admin_order_detail(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)
    statuses = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
    return render_template('admin/order_detail.html', order=order, statuses=statuses)


@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
@login_required
@admin_required
def admin_order_update_status(order_id):
    order = db.session.get(Order, order_id)
    if not order:
        abort(404)

    new_status = request.form.get('status')
    valid_statuses = ['Pending', 'Processing', 'Shipped', 'Delivered', 'Cancelled']
    if new_status in valid_statuses:
        # If cancelled, restore stock
        if new_status == 'Cancelled' and order.status != 'Cancelled':
            for item in order.items:
                if item.product:
                    item.product.stock += item.quantity
        order.status = new_status
        db.session.commit()
        flash(f'Order {order.order_number} status updated to {new_status}.', 'success')

    return redirect(url_for('admin_order_detail', order_id=order.id))


# --- Admin: Customer Directory ---

@app.route('/admin/customers')
@login_required
@admin_required
def admin_customers():
    customers = User.query.filter_by(role='customer').order_by(User.created_at.desc()).all()
    return render_template('admin/customers.html', customers=customers)


# ==========================================
# ERROR HANDLERS
# ==========================================

@app.errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500


# Application Entry Point
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
