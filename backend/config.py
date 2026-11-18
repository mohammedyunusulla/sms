import os
from datetime import timedelta
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')

    # JWT Configuration
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = 'HS256'
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    JWT_BLACKLIST_ENABLED = True
    JWT_BLACKLIST_TOKEN_CHECKS = ['access', 'refresh']

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # PostgreSQL Configuration — single source of truth for all DB connections
    POSTGRES_HOST = os.environ.get('POSTGRES_HOST') or '127.0.0.1'
    POSTGRES_USER = os.environ.get('POSTGRES_USER') or 'postgres'
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD') or 'postgres'
    POSTGRES_PORT = int(os.environ.get('POSTGRES_PORT', 5432))

    # URL-encode password to survive special chars like @ ! $ :
    _PG_PWD_ENC = quote_plus(POSTGRES_PASSWORD)
    _PG_BASE = f'postgresql://{POSTGRES_USER}:{_PG_PWD_ENC}@{POSTGRES_HOST}:{POSTGRES_PORT}'

    # Super Admin Database (for managing schools/users in main DB)
    SUPER_ADMIN_DATABASE_URL = os.environ.get('SUPER_ADMIN_DATABASE_URL') or \
        f'{_PG_BASE}/sms_dev'

    # Template for school databases (use .format(skid=...) to substitute)
    SCHOOL_DATABASE_TEMPLATE = f'{_PG_BASE}/skool_{{skid}}'

    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'
    LOG_FILE = os.environ.get('LOG_FILE') or 'logs/app.log'

    # CORS: comma-separated list of allowed origins (e.g., "http://localhost:3000,https://app.example.com")
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*')

    # Set to True when behind a trusted reverse proxy (nginx, etc.)
    TRUSTED_PROXY = os.environ.get('TRUSTED_PROXY', 'false').lower() == 'true'


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = Config.SUPER_ADMIN_DATABASE_URL

    # Allow weak secrets in development only
    SECRET_KEY = Config.SECRET_KEY or 'dev-secret-key-change-in-production'
    JWT_SECRET_KEY = Config.JWT_SECRET_KEY or 'jwt-dev-secret-string'

    # Longer token for development
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = Config.SUPER_ADMIN_DATABASE_URL

    def __init__(self):
        # Fail loudly if secrets are not configured in production
        if not self.SECRET_KEY:
            raise RuntimeError("SECRET_KEY environment variable must be set in production")
        if not self.JWT_SECRET_KEY:
            raise RuntimeError("JWT_SECRET_KEY environment variable must be set in production")
        if self.CORS_ORIGINS == '*':
            import warnings
            warnings.warn("CORS_ORIGINS is set to '*' in production. Consider restricting to specific domains.")


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    SECRET_KEY = 'test-secret-key'
    JWT_SECRET_KEY = 'test-jwt-secret-key'


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}