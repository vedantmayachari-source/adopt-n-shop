import os
import sys
from datetime import datetime, timedelta, timezone
from sqlalchemy import func

from config import Config
from models import db, User, Pet, Product, AdoptionRequest, Order, OrderItem

def utc_now():
    return datetime.now(timezone.utc)

def seed_database(safe_mode=True, app_instance=None):
    if app_instance is None:
        from app import app
        target_app = app
    else:
        target_app = app_instance

    with target_app.app_context():
        # Ensure database tables exist safely without dropping
        db.create_all()

        print("[SEED] Verifying demo users and administrator...")
        admin_email = Config.ADMIN_EMAIL.lower()
        admin_pass = Config.ADMIN_PASSWORD
        admin_name = Config.ADMIN_NAME

        # 1. Admin User
        admin = User.query.filter(func.lower(User.email) == admin_email).first()
        if not admin:
            admin = User(
                name=admin_name,
                email=admin_email,
                role="admin",
                phone="+91 98200 12345",
                address="Adopt n Shop Shelter HQ, Bandra Kurla Complex (BKC), Mumbai, Maharashtra - 400051"
            )
            admin.set_password(admin_pass)
            db.session.add(admin)
            print(f"[SEED] Created administrator: {admin_email}")
        else:
            if admin.role != "admin":
                admin.role = "admin"
            if os.environ.get('ADMIN_PASSWORD'):
                admin.set_password(os.environ.get('ADMIN_PASSWORD'))
            print(f"[SEED] Administrator verified: {admin_email}")

        # 2. Demo Customers
        demo_users = [
            ("Rohan Verma", "rohan@example.com", "+91 98765 43210", "Flat 402, Shanti Heights, Bandra West, Mumbai, Maharashtra - 400050", "user123"),
            ("Priya Patel", "priya@example.com", "+91 98234 56789", "12, Gokuldham Society, Satellite Road, Ahmedabad, Gujarat - 380015", "user123"),
            ("Ananya Iyer", "ananya@example.com", "+91 97123 45678", "88, 12th Main, Indiranagar, Bengaluru, Karnataka - 560038", "user123")
        ]

        for name, email, phone, addr, pwd in demo_users:
            u_clean = email.lower()
            existing = User.query.filter(func.lower(User.email) == u_clean).first()
            if not existing:
                u = User(name=name, email=u_clean, role="customer", phone=phone, address=addr)
                u.set_password(pwd)
                db.session.add(u)
                print(f"[SEED] Created demo customer: {u_clean}")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[SEED] Warning during user commit: {e}")

        # Fetch fresh user references
        rohan = User.query.filter(func.lower(User.email) == "rohan@example.com").first()
        priya = User.query.filter(func.lower(User.email) == "priya@example.com").first()
        ananya = User.query.filter(func.lower(User.email) == "ananya@example.com").first()

        print("Seeding Pets across Indian cities...")
        pets = [
            Pet(
                name="Bruno",
                species="Dog",
                breed="Indian Pariah (Desi)",
                age_years=1,
                age_months=6,
                gender="Male",
                size="Medium",
                city="Mumbai",
                state="Maharashtra",
                contact_phone="+91 98200 12345",
                rehoming_fee=0.0,
                approval_status="approved",
                health_status="Fully Vaccinated, Dewormed & Microchipped",
                vaccinated=True,
                description="Bruno is a resilient and affectionate Indian Indie dog rescued from Marine Drive promenade. Highly alert, friendly, extremely low-maintenance, and great with society apartments.",
                image_url="https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=600&q=80",
                status="available"
            ),
            Pet(
                name="Simba",
                species="Cat",
                breed="Persian Longhair",
                age_years=1,
                age_months=2,
                gender="Female",
                size="Small",
                city="Bengaluru",
                state="Karnataka",
                contact_phone="+91 98200 12345",
                rehoming_fee=0.0,
                approval_status="approved",
                health_status="Vaccinated & Spayed",
                vaccinated=True,
                description="Simba is a gentle cream-white Persian beauty with amber eyes. She enjoys quiet balconies, afternoon naps in the Bangalore breeze, and soft chin scratches.",
                image_url="https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=600&q=80",
                status="available"
            ),
            Pet(
                name="Sheru",
                species="Dog",
                breed="Golden Retriever",
                age_years=2,
                age_months=4,
                gender="Male",
                size="Large",
                city="Delhi NCR",
                state="Delhi NCR",
                contact_phone="+91 98200 12345",
                rehoming_fee=0.0,
                approval_status="approved",
                health_status="Up-to-date on 7-in-1 Vaccine & Anti-Rabies",
                vaccinated=True,
                description="Sheru is a magnificent, playful Golden Retriever who loves morning park runs in Lodhi Gardens. Very gentle with kids and loves ball games.",
                image_url="https://images.unsplash.com/photo-1552053831-71594a27632d?auto=format&fit=crop&w=600&q=80",
                status="available"
            ),
            Pet(
                owner_id=rohan.id if rohan else None,
                name="Bella",
                species="Dog",
                breed="Beagle",
                age_years=0,
                age_months=9,
                gender="Female",
                size="Medium",
                city="Mumbai",
                state="Maharashtra",
                contact_phone="+91 98765 43210",
                rehoming_fee=500.0,
                approval_status="approved",
                health_status="Vaccinated & Health Checked",
                vaccinated=True,
                description="Bella is a curious, energetic Beagle pup listed for rehoming as our family is relocating abroad. She is house-trained, friendly, and loves treat puzzles.",
                image_url="https://images.unsplash.com/photo-1537151625747-768eb6cf92b2?auto=format&fit=crop&w=600&q=80",
                status="pending"
            ),
            Pet(
                owner_id=priya.id if priya else None,
                name="Milo",
                species="Cat",
                breed="Indian Indie Cat",
                age_years=1,
                age_months=0,
                gender="Male",
                size="Small",
                city="Ahmedabad",
                state="Gujarat",
                contact_phone="+91 98234 56789",
                rehoming_fee=0.0,
                approval_status="approved",
                health_status="Vaccinated & Neutered",
                vaccinated=True,
                description="Rescued as a stray kitten, Milo has blossomed into a clean, playful indoor cat. He is litter-trained, loves chasing feather toys, and purrs non-stop.",
                image_url="https://images.unsplash.com/photo-1573865526739-10659fec78a5?auto=format&fit=crop&w=600&q=80",
                status="available"
            ),
            Pet(
                name="Mithu",
                species="Bird",
                breed="Indian Ringneck Parakeet",
                age_years=2,
                age_months=0,
                gender="Male",
                size="Small",
                city="Pune",
                state="Maharashtra",
                contact_phone="+91 98200 12345",
                rehoming_fee=0.0,
                approval_status="approved",
                health_status="Avian Vet Inspected & Healthy",
                vaccinated=True,
                description="Mithu is a lively green parrot who loves fresh guava slices and almonds. He whistles tunes and greets family members with cheerful chirps.",
                image_url="https://images.unsplash.com/photo-1552728089-57bdde30beb3?auto=format&fit=crop&w=600&q=80",
                status="available"
            ),
            Pet(
                name="Clover",
                species="Rabbit",
                breed="Holland Lop",
                age_years=0,
                age_months=8,
                gender="Female",
                size="Small",
                city="Hyderabad",
                state="Telangana",
                contact_phone="+91 98200 12345",
                rehoming_fee=0.0,
                approval_status="approved",
                health_status="Vaccinated & Vet Checked",
                vaccinated=True,
                description="Clover is a sweet bunny with floppy ears and a calm temperament. She loves fresh coriander, spinach, and gentle ear rubs.",
                image_url="https://images.unsplash.com/photo-1585110396000-c9ffd4e4b308?auto=format&fit=crop&w=600&q=80",
                status="available"
            ),
            Pet(
                name="Rocky",
                species="Dog",
                breed="Labrador Retriever",
                age_years=2,
                age_months=0,
                gender="Male",
                size="Large",
                city="Bengaluru",
                state="Karnataka",
                contact_phone="+91 98200 12345",
                rehoming_fee=0.0,
                approval_status="approved",
                health_status="Vaccinated & Dewormed",
                vaccinated=True,
                description="Rocky is an energetic chocolate Labrador who loves playing fetch in Cubbon Park. Perfect companion for an active family.",
                image_url="https://images.unsplash.com/photo-1583511655857-d19b40a7a54e?auto=format&fit=crop&w=600&q=80",
                status="available"
            ),
            Pet(
                name="Cleo",
                species="Cat",
                breed="Siamese Mix",
                age_years=1,
                age_months=8,
                gender="Female",
                size="Small",
                city="Pune",
                state="Maharashtra",
                contact_phone="+91 98200 12345",
                rehoming_fee=0.0,
                approval_status="approved",
                health_status="Vaccinated & Spayed",
                vaccinated=True,
                description="Cleo is a blue-eyed Siamese mix who loves curling up on the sofa during monsoons. She gets along well with calm dogs and other cats.",
                image_url="https://images.unsplash.com/photo-1513360309081-38f076278f1e?auto=format&fit=crop&w=600&q=80",
                status="available"
            ),
            Pet(
                name="Moti",
                species="Dog",
                breed="Desi Indie Hound",
                age_years=3,
                age_months=0,
                gender="Male",
                size="Medium",
                city="Jaipur",
                state="Rajasthan",
                contact_phone="+91 98200 12345",
                rehoming_fee=0.0,
                approval_status="approved",
                health_status="Vaccinated & Neutered",
                vaccinated=True,
                description="Moti is a proud, intelligent desi dog who was adopted by Ananya through Adopt n Shop. He is now living his happiest life!",
                image_url="https://images.unsplash.com/photo-1591769225440-811ad7d6eab2?auto=format&fit=crop&w=600&q=80",
                status="adopted"
            )
        ]

        for p in pets:
            existing_pet = Pet.query.filter_by(name=p.name, species=p.species).first()
            if not existing_pet:
                db.session.add(p)
                print(f"[SEED] Added pet: {p.name}")
            else:
                if (not existing_pet.approval_status or existing_pet.approval_status != "approved") and existing_pet.owner_id is None:
                    existing_pet.approval_status = "approved"
                if existing_pet.state != p.state and p.state:
                    existing_pet.state = p.state

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[SEED] Warning during pet commit: {e}")

        print("Seeding Products with Indian Rupee (INR) Pricing...")
        products = [
            # Food
            Product(
                name="Royal Canin Maxi Adult Dry Dog Food (15kg)",
                category="Food",
                description="Complete nutritional feed tailored for large adult dogs. Enriched with EPA & DHA omega fatty acids for bone health and radiant shiny coat.",
                price=5499.00,
                stock=25,
                image_url="https://images.unsplash.com/photo-1589924691995-400dc9ecc119?auto=format&fit=crop&w=600&q=80",
                is_active=True
            ),
            Product(
                name="Whiskas Ocean Fish & Tuna Wet Cat Food (12-Pouch Multipack)",
                category="Food",
                description="Delicious tender fish chunks in savory gravy formulated for adult cats. Packed with essential Taurine, Vitamin E, and Zinc for eye and coat health.",
                price=899.00,
                stock=40,
                image_url="https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=600&q=80",
                is_active=True
            ),
            Product(
                name="Drools Absolute Calcium Bone Supplement for Dogs (50 Pcs)",
                category="Food",
                description="Essential calcium-phosphorus ratio supplement strengthening teeth and joint development in active puppies and adult dogs.",
                price=450.00,
                stock=50,
                image_url="https://images.unsplash.com/photo-1548767797-d8c844163c4c?auto=format&fit=crop&w=600&q=80",
                is_active=True
            ),
            Product(
                name="Kaytee Forti-Diet Healthy Grain & Seed Blend for Birds (2kg)",
                category="Food",
                description="Wholesome seed, millets, and nut blend enriched with DHA and prebiotics to support immunity and vibrant plumage in parakeets and lovebirds.",
                price=799.00,
                stock=30,
                image_url="https://images.unsplash.com/photo-1555685812-4b943f1cb0eb?auto=format&fit=crop&w=600&q=80",
                is_active=True
            ),
            Product(
                name="Oxbow Western Timothy High-Fiber Grass Hay (1kg)",
                category="Food",
                description="Hand-sorted fragrant grass hay essential for the digestion and dental health of rabbits and guinea pigs. 100% natural and pesticide free.",
                price=850.00,
                stock=35,
                image_url="https://images.unsplash.com/photo-1585110396000-c9ffd4e4b308?auto=format&fit=crop&w=600&q=80",
                is_active=True
            ),
            # Toys
            Product(
                name="KONG Classic Durable Natural Rubber Dog Chew Toy (Large)",
                category="Toys",
                description="Ultra-durable natural red rubber toy with erratic bounce for fetch. Excellent for stuffing with peanut butter or kibble to keep dogs mentally stimulated.",
                price=999.00,
                stock=45,
                image_url="https://images.unsplash.com/photo-1601758228041-f3b2795255f1?auto=format&fit=crop&w=600&q=80",
                is_active=True
            ),
            Product(
                name="Interactive Feather Wand & LED Laser Pointer Cat Toy Combo",
                category="Toys",
                description="Stimulate your indoor cat's natural hunting instinct. Includes a flexible telescopic wand with organic feathers and a USB rechargeable laser light.",
                price=499.00,
                stock=40,
                image_url="https://images.unsplash.com/photo-1545249390-6bdfa286032f?auto=format&fit=crop&w=600&q=80",
                is_active=True
            ),
            Product(
                name="Heavy-Duty Braided Pure Cotton Tug Rope with Squeaker",
                category="Toys",
                description="100% natural washable cotton rope designed for intense tug-of-war. Helps remove tartar and plaque during play.",
                price=349.00,
                stock=30,
                image_url="https://images.unsplash.com/photo-1576201836106-db1758fd1c97?auto=format&fit=crop&w=600&q=80",
                is_active=True
            ),
            Product(
                name="Handcrafted Wooden Hanging Swing & Bell Toy for Birds",
                category="Toys",
                description="Natural non-toxic wooden perches with colorful wooden beads and copper bells providing hours of exercise inside bird cages.",
                price=399.00,
                stock=25,
                image_url="https://images.unsplash.com/photo-1552728089-57bdde30beb3?auto=format&fit=crop&w=600&q=80",
                is_active=True
            ),
            # Accessories
            Product(
                name="Adjustable Ergonomic Reflective No-Pull Dog Harness",
                category="Accessories",
                description="Breathable air-mesh padding with dual leash attachment rings. Front D-ring discourages pulling, with 3M reflective trims for night walk safety.",
                price=899.00,
                stock=35,
                image_url="https://images.unsplash.com/photo-1608096299210-db7e38487075?auto=format&fit=crop&w=600&q=80",
                is_active=True
            ),
            Product(
                name="Orthopedic Memory Foam Ultra-Soft Velvet Pet Lounge Bed",
                category="Accessories",
                description="High-density therapeutic orthopedic foam relieving joint and hip pressure. Removable water-resistant, machine-washable soft velvet cover.",
                price=2499.00,
                stock=18,
                image_url="https://images.unsplash.com/photo-1541599540903-216a46ca1dc0?auto=format&fit=crop&w=600&q=80",
                is_active=True
            ),
            Product(
                name="Non-Skid Stainless Steel Double Feeding & Water Bowls",
                category="Accessories",
                description="Rust-proof food grade stainless steel bowls fitted inside an anti-spill non-skid silicone base keeping feeding areas clean.",
                price=699.00,
                stock=40,
                image_url="https://images.unsplash.com/photo-1548767797-d8c844163c4c?auto=format&fit=crop&w=600&q=80",
                is_active=True
            ),
            Product(
                name="One-Click Self-Cleaning Deshedding Pet Grooming Brush",
                category="Accessories",
                description="Gently removes shedding undercoat, mats, and knots with fine bent wire bristles. One-click button retracts bristles for effortless hair disposal.",
                price=549.00,
                stock=40,
                image_url="https://images.unsplash.com/photo-1516734212186-a967f81ad0d7?auto=format&fit=crop&w=600&q=80",
                is_active=True
            ),
            # Healthcare
            Product(
                name="Frontline Plus Flea & Tick Spot-On Treatment (3 Pipettes)",
                category="Healthcare",
                description="Fast-acting veterinary formula that kills adult fleas, ticks, and flea eggs on contact for a full 30 days per pipette application.",
                price=1499.00,
                stock=22,
                image_url="https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&w=600&q=80",
                is_active=True
            ),
            Product(
                name="Himalaya Herbal Erina-EP Anti-Tick Pet Shampoo (400ml)",
                category="Healthcare",
                description="Enriched with natural Neem and Eucalyptus oil. Prevents ectoparasites, relieves skin itching, and leaves a pleasant herbal aroma.",
                price=380.00,
                stock=30,
                image_url="https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=600&q=80",
                is_active=True
            )
        ]
        for pr in products:
            existing_product = Product.query.filter_by(name=pr.name).first()
            if not existing_product:
                db.session.add(pr)
                print(f"[SEED] Added product: {pr.name}")
            else:
                if not existing_product.is_active:
                    existing_product.is_active = True

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[SEED] Warning during product commit: {e}")

        print("Seeding Adoption Requests (idempotent)...")
        moti = Pet.query.filter_by(name="Moti").first()
        bruno = Pet.query.filter_by(name="Bruno").first()

        # Ananya's approved request for Moti
        if ananya and moti:
            existing_req1 = AdoptionRequest.query.filter_by(user_id=ananya.id, pet_id=moti.id).first()
            if not existing_req1:
                req1 = AdoptionRequest(
                    user_id=ananya.id,
                    pet_id=moti.id,
                    full_name="Ananya Iyer",
                    phone="+91 97123 45678",
                    address="88, 12th Main, Indiranagar, Bengaluru, Karnataka - 560038",
                    living_situation="Own House with Fenced Yard",
                    has_other_pets=False,
                    previous_experience="Grew up with indie dogs in Bengaluru. Knowledgeable about regular vet checkups and daily exercise.",
                    reason="Looking for a loyal and affectionate companion for our home.",
                    status="approved",
                    admin_notes="Home verification complete. Ananya is a wonderful pet parent. Moti is happily adopted!",
                    created_at=utc_now() - timedelta(days=12),
                    updated_at=utc_now() - timedelta(days=10)
                )
                db.session.add(req1)
                print("[SEED] Added adoption request: Ananya -> Moti")

        # Priya's pending request for Bruno
        if priya and bruno:
            existing_req2 = AdoptionRequest.query.filter_by(user_id=priya.id, pet_id=bruno.id).first()
            if not existing_req2:
                req2 = AdoptionRequest(
                    user_id=priya.id,
                    pet_id=bruno.id,
                    full_name="Priya Patel",
                    phone="+91 98234 56789",
                    address="12, Gokuldham Society, Satellite Road, Ahmedabad, Gujarat - 380015",
                    living_situation="Own House with Fenced Yard",
                    has_other_pets=True,
                    previous_experience="Have experience caring for rescued indie dogs and cats.",
                    reason="We love Bruno's calm nature and have plenty of time for daily evening walks.",
                    status="pending",
                    admin_notes="Application under initial review. Scheduling phone verification with applicant.",
                    created_at=utc_now() - timedelta(days=2),
                    updated_at=utc_now() - timedelta(days=2)
                )
                db.session.add(req2)
                print("[SEED] Added adoption request: Priya -> Bruno")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"[SEED] Warning during adoption requests commit: {e}")

        print("Seeding Sample Orders with Indian Rupee (INR)...")
        p_royal = Product.query.filter_by(name="Royal Canin Maxi Adult Dry Dog Food (15kg)").first()
        p_kong = Product.query.filter_by(name="KONG Classic Durable Natural Rubber Dog Chew Toy (Large)").first()
        p_whiskas = Product.query.filter_by(name="Whiskas Ocean Fish & Tuna Wet Cat Food (12-Pouch Multipack)").first()
        p_bed = Product.query.filter_by(name="Orthopedic Memory Foam Ultra-Soft Velvet Pet Lounge Bed").first()

        # Order 1: Rohan's delivered order
        if rohan:
            existing_order1 = Order.query.filter_by(order_number="ANS-IN-20261110-A98F21").first()
            if not existing_order1:
                order1 = Order(
                    user_id=rohan.id,
                    order_number="ANS-IN-20261110-A98F21",
                    subtotal_amount=6498.00,
                    shipping_fee=0.0,
                    tax_amount=324.90,
                    total_amount=6822.90,
                    status="Delivered",
                    payment_method="UPI / QR (Google Pay)",
                    payment_status="Paid",
                    shipping_name="Rohan Verma",
                    shipping_phone="+91 98765 43210",
                    shipping_address="Flat 402, Shanti Heights, Bandra West",
                    shipping_city="Mumbai",
                    shipping_pincode="400050",
                    created_at=utc_now() - timedelta(days=8)
                )
                db.session.add(order1)
                db.session.flush()

                if p_royal:
                    db.session.add(OrderItem(
                        order_id=order1.id,
                        product_id=p_royal.id,
                        product_name=p_royal.name,
                        price=p_royal.price,
                        quantity=1,
                        subtotal=p_royal.price
                    ))
                if p_kong:
                    db.session.add(OrderItem(
                        order_id=order1.id,
                        product_id=p_kong.id,
                        product_name=p_kong.name,
                        price=p_kong.price,
                        quantity=1,
                        subtotal=p_kong.price
                    ))
                print("[SEED] Added order: Rohan (Delivered)")

        # Order 2: Priya's processing order
        if priya:
            existing_order2 = Order.query.filter_by(order_number="ANS-IN-20261118-B47C56").first()
            if not existing_order2:
                order2 = Order(
                    user_id=priya.id,
                    order_number="ANS-IN-20261118-B47C56",
                    subtotal_amount=3398.00,
                    shipping_fee=0.0,
                    tax_amount=169.90,
                    total_amount=3567.90,
                    status="Processing",
                    payment_method="UPI / QR (PhonePe)",
                    payment_status="Paid",
                    shipping_name="Priya Patel",
                    shipping_phone="+91 98234 56789",
                    shipping_address="12, Gokuldham Society, Satellite Road",
                    shipping_city="Ahmedabad",
                    shipping_pincode="380015",
                    created_at=utc_now() - timedelta(days=1)
                )
                db.session.add(order2)
                db.session.flush()

                if p_whiskas:
                    db.session.add(OrderItem(
                        order_id=order2.id,
                        product_id=p_whiskas.id,
                        product_name=p_whiskas.name,
                        price=p_whiskas.price,
                        quantity=1,
                        subtotal=p_whiskas.price
                    ))
                if p_bed:
                    db.session.add(OrderItem(
                        order_id=order2.id,
                        product_id=p_bed.id,
                        product_name=p_bed.name,
                        price=p_bed.price,
                        quantity=1,
                        subtotal=p_bed.price
                    ))
                print("[SEED] Added order: Priya (Processing)")

        try:
            db.session.commit()
            print("[SEED] Database seeding complete (safe & idempotent).")
        except Exception as e:
            db.session.rollback()
            print(f"[SEED] Warning during order commit: {e}")

if __name__ == '__main__':
    seed_database(safe_mode=True)
