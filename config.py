# config.py
from flask_mail import Mail

mail = Mail()
class Config:
    SECRET_KEY = "your_secret_key_here"  # Changez cette valeur par une clé sécurisée
    SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://postgres:binabina@localhost:5432/monitoring_db?client_encoding=utf8"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    
