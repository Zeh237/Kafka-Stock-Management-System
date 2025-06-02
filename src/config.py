import os
from datetime import timedelta

basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

class Config:
    """Base configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-very-secret-string-that-you-should-change'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')

    SQLALCHEMY_TRACK_MODIFICATIONS = False 
    print("Resolved DB path:", os.path.join(basedir, 'app.db'))

    # Flask-Mail configuration (example)
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 25)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') is not None
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['your-admin-email@example.com']

    # Session configuration (example)
    PERMANENT_SESSION_LIFETIME = timedelta(days=7) # Sessions persist for 7 days

    # Example of a custom setting
    ITEMS_PER_PAGE = 20

class DevelopmentConfig(Config):
    """Development specific configuration."""
    DEBUG = True
    FLASK_ENV = 'development'

class TestingConfig(Config):
    """Testing specific configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    FLASK_ENV = 'testing'

class ProductionConfig(Config):
    """Production specific configuration."""
    DEBUG = False
    FLASK_ENV = 'production'