from database.db import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from geoalchemy2 import Geometry

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password) 
    
class Puit(db.Model):
    __tablename__ = 'puits'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False)  # New column for status
    # Clé étrangère vers Region
    region_id = db.Column(db.Integer, db.ForeignKey('region.id'), nullable=True)

    # Relation vers la classe Region
    region = db.relationship('Region', back_populates='puits')


class Region(db.Model):
    __tablename__ = 'region'

    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(255), nullable=False, unique=True)
    geom = db.Column(Geometry('POLYGON'))

    puits = db.relationship('Puit', back_populates='region', cascade="all, delete-orphan")


    

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)  # Clé étrangère vers User
    nom = db.Column(db.String(100), nullable=False)
    prenom = db.Column(db.String(100), nullable=False)
    adresse = db.Column(db.String(255), nullable=True)
    image_url = db.Column(db.String(255), nullable=True)  # New column for image URL

    # Relation One-to-One avec User
    user = db.relationship('User', backref=db.backref('profile', uselist=False, cascade="all, delete-orphan"))
