import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, '../db_directory/testsb.sqlite3')

class LocalDevelopmentConfig:
    DEBUG=  True
    SECRET_KEY ="dev"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH}"
    SQLALCHEMY_TRACK_MODIFICATIONS= False