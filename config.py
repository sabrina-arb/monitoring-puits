# config.py
import os

class Config:
    SECRET_KEY = "your_secret_key_here"  # Changez cette valeur par une clé sécurisée
    SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://postgres:binabina@localhost:5432/monitoring_puits?client_encoding=utf8"
    SQLALCHEMY_TRACK_MODIFICATIONS = False