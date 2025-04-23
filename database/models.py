from database.db import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

"""
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='engineer')

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password, password) 
    
    
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
"""


class Puit(db.Model):
    __tablename__ = 'puits'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False) 
    # Clé étrangère vers Region (obligatoire pour la relation)
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=False)
    
    # Relation Many-to-One avec Region
    region = db.relationship('Region', back_populates='puits') 

    # Méthode pour afficher le nom au lieu de <Puit 1>
    def __repr__(self):
        return self.nom  # Affichera directement le nom dans Flask-Admin     

class Region(db.Model):
    __tablename__ = 'regions'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(255), nullable=False)
    lat_min = db.Column(db.Float)  # Latitude coin sud-ouest
    lon_min = db.Column(db.Float)  # Longitude coin sud-ouest
    lat_max = db.Column(db.Float)  # Latitude coin nord-est
    lon_max = db.Column(db.Float)  # Longitude coin nord-est


     # Relation One-to-Many avec Puit
    puits = db.relationship('Puit', back_populates='region', cascade="all, delete-orphan")

    # Méthode pour afficher le nom au lieu de <Region 1>
    def __repr__(self):
        return self.nom  # Affichera directement le nom dans Flask-Admin
    
class Duse(db.Model):
    __tablename__ = 'duse'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    pression_max = db.Column(db.Float, nullable=False)

    # Méthode pour afficher le nom au lieu de <Duse 1>
    def __repr__(self):
        return self.nom  # Affichera directement le nom dans Flask-Admin

class Separateur(db.Model):
    __tablename__ = 'separateur'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    capacite = db.Column(db.Float, nullable=False)

    # Méthode pour afficher le nom au lieu de <Separateur 1>
    def __repr__(self):
        return self.nom  # Affichera directement le nom dans Flask-Admin
 
class Test(db.Model, UserMixin):
    __tablename__ = 'test'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255),nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=True)
    nom = db.Column(db.String(100), nullable=True)
    prenom = db.Column(db.String(100), nullable=True)
    adresse = db.Column(db.String(255), nullable=True)
    image_url = db.Column(db.String(255), nullable=True)

    

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password, password)