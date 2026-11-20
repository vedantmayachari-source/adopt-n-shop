from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

def utc_now():
    return datetime.now(timezone.utc)

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='customer', nullable=False)  # 'customer' or 'admin'
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    adoption_requests = db.relationship('AdoptionRequest', backref='user', lazy=True, cascade='all, delete-orphan')
    orders = db.relationship('Order', backref='user', lazy=True, cascade='all, delete-orphan')
    cart_items = db.relationship('CartItem', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        if password:
            self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash or not password:
            return False
        try:
            return check_password_hash(self.password_hash, password)
        except Exception:
            return False

    @property
    def is_admin(self):
        return (self.role or '').strip().lower() == 'admin'

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Pet(db.Model):
    __tablename__ = 'pets'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    name = db.Column(db.String(100), nullable=False)
    species = db.Column(db.String(50), nullable=False)  # Dog, Cat, Bird, Rabbit, Other
    breed = db.Column(db.String(100), nullable=False)
    age_years = db.Column(db.Integer, default=0)
    age_months = db.Column(db.Integer, default=0)
    gender = db.Column(db.String(20), nullable=False)  # Male, Female
    size = db.Column(db.String(20), default='Medium')  # Small, Medium, Large
    city = db.Column(db.String(100), default='Mumbai', nullable=False)
    state = db.Column(db.String(100), default='Maharashtra', nullable=False)
    contact_phone = db.Column(db.String(20), nullable=True)
    rehoming_fee = db.Column(db.Float, default=0.0, nullable=False)
    additional_images = db.Column(db.Text, nullable=True)  # Comma-separated list of image URLs
    approval_status = db.Column(db.String(20), default='approved', nullable=False)  # pending, approved, rejected
    approval_notes = db.Column(db.Text, nullable=True)
    health_status = db.Column(db.String(100), default='Healthy')
    vaccinated = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, nullable=True)
    image_url = db.Column(db.String(255), default='/static/images/default_pet.svg')
    status = db.Column(db.String(20), default='available', nullable=False)  # available, pending, adopted
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    owner = db.relationship('User', backref=db.backref('listed_pets', lazy=True, cascade='all, delete-orphan'))
    adoption_requests = db.relationship('AdoptionRequest', backref='pet', lazy=True, cascade='all, delete-orphan')

    @property
    def is_user_listed(self):
        return self.owner_id is not None

    @property
    def is_approved(self):
        return (self.approval_status or 'approved').strip().lower() == 'approved'

    @property
    def is_pending(self):
        return (self.approval_status or '').strip().lower() == 'pending'

    @property
    def is_rejected(self):
        return (self.approval_status or '').strip().lower() == 'rejected'

    @property
    def all_images(self):
        images = []
        if self.image_url and self.image_url != '/static/images/default_pet.svg':
            images.append(self.image_url)
        elif not self.additional_images:
            images.append(self.image_url or '/static/images/default_pet.svg')

        if self.additional_images:
            for img in self.additional_images.split(','):
                img = img.strip()
                if img and img not in images:
                    images.append(img)
        if not images:
            images.append('/static/images/default_pet.svg')
        return images

    @property
    def age_display(self):
        parts = []
        if self.age_years > 0:
            parts.append(f"{self.age_years} yr{'s' if self.age_years > 1 else ''}")
        if self.age_months > 0 or not parts:
            parts.append(f"{self.age_months} mo{'s' if self.age_months > 1 else ''}")
        return ' '.join(parts)

    def __repr__(self):
        return f'<Pet {self.name} - {self.species} ({self.approval_status})>'


class AdoptionRequest(db.Model):
    __tablename__ = 'adoption_requests'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    pet_id = db.Column(db.Integer, db.ForeignKey('pets.id', ondelete='CASCADE'), nullable=False)
    
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    living_situation = db.Column(db.String(50), nullable=False)  # Own House, Apartment, Rented, Farm
    has_other_pets = db.Column(db.Boolean, default=False)
    previous_experience = db.Column(db.Text, nullable=True)
    reason = db.Column(db.Text, nullable=False)
    
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, approved, rejected
    admin_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    def __repr__(self):
        return f'<AdoptionRequest #{self.id} User:{self.user_id} Pet:{self.pet_id} Status:{self.status}>'


class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Food, Toys, Accessories, Healthcare
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0, nullable=False)
    image_url = db.Column(db.String(255), default='/static/images/default_product.jpg')
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    cart_items = db.relationship('CartItem', backref='product', lazy=True, cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

    def in_stock(self):
        return self.stock > 0

    def __repr__(self):
        return f'<Product {self.name} (${self.price})>'


class CartItem(db.Model):
    __tablename__ = 'cart_items'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    @property
    def subtotal(self):
        return round(self.quantity * self.product.price, 2)

    def __repr__(self):
        return f'<CartItem User:{self.user_id} Prod:{self.product_id} Qty:{self.quantity}>'


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    order_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    subtotal_amount = db.Column(db.Float, nullable=False, default=0.0)
    shipping_fee = db.Column(db.Float, nullable=False, default=0.0)
    tax_amount = db.Column(db.Float, nullable=False, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    
    status = db.Column(db.String(30), default='Pending', nullable=False)  # Pending, Processing, Shipped, Delivered, Cancelled
    payment_method = db.Column(db.String(50), default='Card', nullable=False)  # Card, UPI, Cash on Delivery
    payment_status = db.Column(db.String(30), default='Paid', nullable=False)  # Paid, Pending
    
    shipping_name = db.Column(db.String(100), nullable=False)
    shipping_phone = db.Column(db.String(20), nullable=False)
    shipping_address = db.Column(db.Text, nullable=False)
    shipping_city = db.Column(db.String(50), nullable=True)
    shipping_pincode = db.Column(db.String(20), nullable=True)
    
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True, cascade='all, delete-orphan')

    @property
    def total_items_count(self):
        return sum(item.quantity for item in self.items)

    def __repr__(self):
        return f'<Order {self.order_number} (${self.total_amount})>'


class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    
    product_name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    subtotal = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<OrderItem {self.product_name} x {self.quantity}>'
