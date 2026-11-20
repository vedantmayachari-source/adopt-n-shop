import sys
from sqlalchemy import inspect, text
from app import app
from models import db

def run_migration():
    with app.app_context():
        # Ensure base tables exist
        db.create_all()
        
        inspector = inspect(db.engine)
        if not inspector.has_table('pets'):
            print("[MIGRATE] Table 'pets' does not exist yet.")
            return

        columns = [c['name'] for c in inspector.get_columns('pets')]
        print('[MIGRATE] Existing columns in pets:', columns)

        new_cols = [
            ('state', "VARCHAR(100) DEFAULT 'Maharashtra'"),
            ('contact_phone', "VARCHAR(20)"),
            ('rehoming_fee', "FLOAT DEFAULT 0.0"),
            ('additional_images', "TEXT"),
            ('approval_status', "VARCHAR(20) DEFAULT 'approved'"),
            ('approval_notes', "TEXT")
        ]

        with db.engine.connect() as conn:
            for col_name, col_def in new_cols:
                if col_name not in columns:
                    print(f"[MIGRATE] Adding column {col_name}...")
                    try:
                        conn.execute(text(f"ALTER TABLE pets ADD COLUMN {col_name} {col_def}"))
                        conn.commit()
                    except Exception as e:
                        print(f"[MIGRATE] Notice adding column {col_name}: {e}")

            # Fix legacy null values safely
            try:
                conn.execute(text("UPDATE pets SET approval_status = 'approved' WHERE approval_status IS NULL OR approval_status = ''"))
                conn.execute(text("UPDATE pets SET state = 'Maharashtra' WHERE state IS NULL OR state = ''"))
                conn.execute(text("UPDATE pets SET rehoming_fee = 0.0 WHERE rehoming_fee IS NULL"))
                conn.commit()
            except Exception as e:
                print(f"[MIGRATE] Notice updating legacy values: {e}")

        updated_inspector = inspect(db.engine)
        updated_cols = [c['name'] for c in updated_inspector.get_columns('pets')]
        print('[MIGRATE] Migration complete. Current columns in pets:', updated_cols)

if __name__ == '__main__':
    run_migration()
