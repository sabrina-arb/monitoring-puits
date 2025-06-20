from flask import request
from sqlalchemy import Column, Numeric
from database.db import db
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class Puit(db.Model):
    __tablename__ = 'puits'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), nullable=False) 
    p_min = db.Column(db.Float) 
    p_max = db.Column(db.Float)
    d_min = db.Column(db.Float)
    d_max = db.Column(db.Float)
    t_min = db.Column(db.Float)
    t_max = db.Column(db.Float)

    # Clé étrangère vers Region (obligatoire pour la relation)
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=False)
    # Relation Many-to-One avec Region
    region = db.relationship('Region', back_populates='puits') 
    separateurs = db.relationship('Separateur', back_populates='puit')
    duse = db.relationship('Duse', back_populates='puit')
    jaugeages = db.relationship('Telejaugeage', back_populates='puit')



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
    puits = db.relationship ('Puit', back_populates='region', cascade="all, delete-orphan")

    # Méthode pour afficher le nom au lieu de <Region 1>
    def __repr__(self):
        return self.nom  # Affichera directement le nom dans Flask-Admin
    
class Duse(db.Model):
    __tablename__ = 'duse'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False,unique=True)
    type = db.Column(db.String(50), nullable=False)
    pression_max = db.Column(db.Float, nullable=False)
    
    puits_id = db.Column(db.Integer, db.ForeignKey('puits.id'), nullable=True)
    puit = db.relationship('Puit', back_populates='duse')


    # Méthode pour afficher le nom au lieu de <Duse 1>
    def __repr__(self):
        return self.nom  # Affichera directement le nom dans Flask-Admin

class Separateur(db.Model):
    __tablename__ = 'separateur'
    id = db.Column(db.Integer, primary_key=True)
    nom = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(50), nullable=False)
    capacite = db.Column(db.Float, nullable=False)

    puits_id = db.Column(db.Integer, db.ForeignKey('puits.id'), nullable=True)
    puit = db.relationship('Puit', back_populates='separateurs')

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
    email = db.Column(db.String(255), nullable=False)  
    last_login = db.Column(db.TIMESTAMP, default=datetime.utcnow, nullable=True)
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password, password)
    

class Telejaugeage(db.Model):
    __tablename__ = 'datajaug'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nom_puits = db.Column(db.String(100), nullable=False)
    pression_pip = db.Column(db.Float)
    pression_manifold = db.Column(db.Float)
    temperature_pipe = db.Column(db.Float)
    temperature_tete = db.Column(db.Float)
    pression_tete = db.Column(db.Float)
    debit_huile = db.Column(db.Float)
    gor = db.Column(db.Float)
    glr = db.Column(db.Float)
    taux_eau = db.Column(db.Float)
    date_debut = db.Column(db.Date)
    date_fin = db.Column(db.Date)
    eau_inj = db.Column(db.Float)
    

    puit = db.relationship('Puit', back_populates='jaugeages')
    puit_id = db.Column(db.Integer, db.ForeignKey('puits.id'), nullable=False)
    def __repr__(self):
     return f"<Telejaugeage {self.nom_puits} du {self.date_debut} au {self.date_fin}>"
    
class Rapport(db.Model):
    __tablename__ = 'rapport'

    id = db.Column(db.Integer, primary_key=True)
    date_rapport = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    type_rapport = db.Column(db.String(100), nullable=False)
    nom_rapport = db.Column(db.String(100), nullable=False ) 
    nom_puits = db.Column(db.String(100), nullable=False)
    id_puits = db.Column(db.String(50), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    region = db.Column(db.String(100), nullable=False)
    date_mise_en_service = db.Column(db.Date)
    pression = db.Column(db.Float)
    temperature = db.Column(db.Float)
    debit = db.Column(db.Float)
    etat_puits = db.Column(db.String(50), nullable=False)
    alertes = db.Column(db.Integer, default=0)
    operateur = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'date_rapport': self.date_rapport.strftime('%d/%m/%Y') if self.date_rapport else '',
            'nom_rapport': self.nom_rapport or '',
            'nom_puits': self.nom_puits or '',
            'id_puits': self.id_puits or '',
            'latitude': self.latitude or '',
            'longitude': self.longitude or '',
            'region': self.region or '',
            'date_mise_en_service': self.date_mise_en_service.strftime('%d/%m/%Y') if self.date_mise_en_service else '',
            'pression': self.pression or '',
            'temperature': self.temperature or '',
            'debit': self.debit or '',
            'etat_puits': self.etat_puits or '',
            'alertes': self.alertes or '',
            'operateur': self.operateur or '',
            'description': self.description or ''
        }

    def __repr__(self):
        return f'<Rapport {self.id} - {self.nom_puits}>'
