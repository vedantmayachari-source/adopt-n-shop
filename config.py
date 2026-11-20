import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Security Configuration: Use environment variable in production, fallback for development only
    SECRET_KEY = os.environ.get('SECRET_KEY', 'adopt-n-shop-dev-secret-key-change-in-production')
    
    # Database Configuration: SQLite by default, override via DATABASE_URL
    _database_url = os.environ.get('DATABASE_URL')
    if _database_url:
        # Render / Heroku compatibility: SQLAlchemy requires postgresql:// instead of postgres://
        if _database_url.startswith('postgres://'):
            _database_url = _database_url.replace('postgres://', 'postgresql://', 1)
        SQLALCHEMY_DATABASE_URI = _database_url
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'adoptnshop.db')
        
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Administrator Account Configuration (overridable via environment variables in production)
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@adoptnshop.com').strip().lower()
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    ADMIN_NAME = os.environ.get('ADMIN_NAME', 'Aarav Sharma').strip()
    
    # File Upload Configuration
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max upload size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
