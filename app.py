import os
from wtforms.validators import InputRequired, Optional, Length
from flask import Flask, flash, redirect, url_for, request
from flask_login import LoginManager, current_user, login_required
from flask_admin import Admin, expose
from flask_admin.contrib.sqla import ModelView
from flask_mail import Mail, Message
from database.models import  Puit , Region,Duse,Separateur,Test
from database.db import db
from config import Config
from routes.routes import routes 
from flask_admin.base import AdminIndexView
from flask_admin.form import ImageUploadField
from wtforms import SelectField, PasswordField, StringField
from wtforms.validators import InputRequired
from werkzeug.security import generate_password_hash
from flask_admin.form.fields import Select2Field
from flask_admin.form import Select2Field 
from config import mail 
from flask_apscheduler import APScheduler
from modbus.client import get_modbus_data
from modbus.data_service import data_modbus
from email_validator import validate_email, EmailNotValidError



app = Flask(__name__)
app.config.from_object(Config)

def read_from_modbus():
    data = get_modbus_data()
    if data:
        data_modbus.append(data)
        if len(data_modbus) > 50:
            data_modbus.pop(0)

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
scheduler.add_job(id='modbus_reader', func=read_from_modbus, trigger='interval', seconds=2)



app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'regaiaalaa@gmail.com' 
app.config['MAIL_PASSWORD'] = 'eymq cqnh mpuu ozse'
app.config['MAIL_DEFAULT_SENDER'] ='regaiaalaa@gmail.com'


mail = Mail(app)


db.init_app(app)

# Configuration de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'routes.login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Test, int(user_id))

# Configuration de Flask-Admin
# Dans app.py, modifiez la méthode index de MyAdminIndexView comme suit :

class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        try:
            # 1. Statistiques de base existantes
            stats = {
                'user_count': Test.query.count(),
                'well_count': Puit.query.count(),
                'region_count': Region.query.count(),
                'duse_count': Duse.query.count(),
                'separateur_count': Separateur.query.count(),
                'active_wells': Puit.query.filter_by(status='actif').count(),
                'inactive_wells': Puit.query.filter_by(status='inactif').count(),
                'maintenance_wells': Puit.query.filter_by(status='en maintenance').count(),
                'urgent_wells': Puit.query.filter_by(status='en urgence').count()
            }

            # 2. Statistiques par rôle
            role_stats = db.session.query(
                Test.role,
                db.func.count(Test.id)
            ).group_by(Test.role).all()
            
            role_counts = {role: count for role, count in role_stats}

            # 3. Calcul des pourcentages
            total_wells = stats['well_count'] or 1
            percentages = {
                'active_percent': (stats['active_wells'] / total_wells) * 100,
                'inactive_percent': (stats['inactive_wells'] / total_wells) * 100,
                'maintenance_percent': (stats['maintenance_wells'] / total_wells) * 100,
                'urgent_percent': (stats['urgent_wells'] / total_wells) * 100
            }

            # 4. Récupération des dernières activités
            def get_recent_activities():
                activities = []
                
                # Derniers puits
                for puit in Puit.query.order_by(Puit.id.desc()).limit(3):
                    activities.append({
                        'icon': 'oil-well',
                        'title': f"Puit {puit.nom}",
                        'details': f"Région: {puit.region.nom if puit.region else 'N/A'} • Statut: {puit.status}",
                        'sort_key': -puit.id
                    })

                # Derniers utilisateurs
                for user in Test.query.order_by(Test.id.desc()).limit(3):
                    activities.append({
                        'icon': 'user',
                        'title': f"Utilisateur {user.username}",
                        'details': f"Rôle: {user.role}",
                        'sort_key': -user.id
                    })

                # Dernières régions
                for region in Region.query.order_by(Region.id.desc()).limit(2):
                    activities.append({
                        'icon': 'map-marked-alt',
                        'title': f"Région {region.nom}",
                        'details': f"{len(region.puits)} puits",
                        'sort_key': -region.id
                    })

                activities.sort(key=lambda x: x['sort_key'])
                return activities[:5]

            last_activities = get_recent_activities()

            return self.render(
                'admin/dashboard.html',
                last_activities=last_activities,
                **stats,
                **role_counts,
                **percentages,
                admin_count=role_counts.get('Administrateur', 0),
                engineer_count=role_counts.get('Ingénieur de production', 0),
                director_count=role_counts.get('Directeur de production', 0),
                operator_count=role_counts.get('Opérateur de terrain', 0)
            )

        except Exception as e:
            flash(f"Erreur lors de la récupération des données: {str(e)}", "danger")
            return self.render('admin/dashboard.html')

    @expose('/refresh_well_stats')
    def refresh_well_stats(self):
        try:
            stats = {
                'active_wells': Puit.query.filter_by(status='actif').count(),
                'inactive_wells': Puit.query.filter_by(status='inactif').count(),
                'maintenance_wells': Puit.query.filter_by(status='en maintenance').count(),
                'urgent_wells': Puit.query.filter_by(status='en urgence').count(),
                'well_count': Puit.query.count()
            }
            
            return {
                'success': True,
                'data': stats,
                'percentages': {
                    'active': (stats['active_wells'] / stats['well_count']) * 100,
                    'inactive': (stats['inactive_wells'] / stats['well_count']) * 100,
                    'maintenance': (stats['maintenance_wells'] / stats['well_count']) * 100,
                    'urgent': (stats['urgent_wells'] / stats['well_count']) * 100
                }
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}     

class PuitAdmin(ModelView):
    column_list = ('nom', 'region.nom', 'latitude', 'longitude', 'status')
    column_labels = {
        'nom': 'Nom du puits',
        'region.nom': 'Nom de la région',
        'status': 'Statut'
    }
    column_searchable_list = ('nom', 'region.nom')
    column_filters = ('status', 'region.nom')
    form_columns = ('nom', 'latitude', 'longitude', 'status', 'region')

    
    form_overrides = {
        'status': SelectField
    }

    
    form_args = {
        'status': {
            'choices': [
                ('actif', 'Actif'),
                ('inactif', 'Inactif'),
                ('en maintenance', 'En maintenance'),
                ('en urgence', 'En urgence')

            ],
            'label': 'Statut'
        }
    }

    form_ajax_refs = {
        'region': {
            'fields': ['nom'],
            'minimum_input_length': 1,
            'placeholder': 'Rechercher une région par nom',
            'page_size': 10,
        }
    }

    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'Administrateur'

    def inaccessible_callback(self, *_):
        flash("Accès refusé. Vous devez être un administrateur.", "danger")
        return redirect(url_for('routes.login'))

class RegionAdmin(ModelView):
    column_list = ['nom', 'puits_count', 'puits_list']
    form_columns = ['nom', 'puits', 'lat_min', 'lon_min', 'lat_max', 'lon_max']
    column_searchable_list = ['nom']

    column_labels = {
        'nom': 'Nom de la région',
        'lat_min': 'Latitude Sud-Ouest',
        'lon_min': 'Longitude Sud-Ouest',
        'lat_max': 'Latitude Nord-Est',
        'lon_max': 'Longitude Nord-Est'
    } 
    
    # Exemple de valeurs par défaut pour le placeholder
    form_args = {
        'lat_min': {'label': 'Latitude Sud-Ouest', 'render_kw': {'placeholder': 'ex: 31.68'}},
        'lon_min': {'label': 'Longitude Sud-Ouest', 'render_kw': {'placeholder': 'ex: 5.50'}},
        'lat_max': {'label': 'Latitude Nord-Est', 'render_kw': {'placeholder': 'ex: 31.80'}},
        'lon_max': {'label': 'Longitude Nord-Est', 'render_kw': {'placeholder': 'ex: 5.70'}},
    }
    
    form_ajax_refs = {
        'puits': {
            'fields': ['nom'],
            'page_size': 10,
            'minimum_input_length': 1,
            'placeholder': 'Rechercher un puits',
        }
    }

    

    # Colonne calculée pour le nombre de puits
    def puits_count(self, context, model, name):
        return len(model.puits)
    
    # Colonne calculée pour la liste des noms de puits
    def puits_list(self, context, model, name):
        return ", ".join([p.nom for p in model.puits]) or "Aucun puits"
    
    # Configuration des colonnes calculées
    column_formatters = {
        'puits_count': puits_count,
        'puits_list': puits_list
    }
    
    # Labels des colonnes
    column_labels = {
        'puits_count': 'Nombre de puits',
        'puits_list': 'Puits associés'
    }
    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'Administrateur'

    def inaccessible_callback(self, name, **kwargs):
        flash("Accès refusé. Vous devez être un administrateur.", "danger")
        return redirect(url_for('routes.login'))
 
class SeparateurAdmin(ModelView):
    column_list = ['nom', 'type', 'capacite', 'puit.nom']
    column_labels = {
    'nom': 'Nom du séparateur',
    'type': 'Type de séparateur',
    'capacite': 'Capacité (m³)',
    'puit.nom': 'Nom du puits'
}

    column_searchable_list = [ 'nom']
    column_filters = ['type']
    
    form_columns = ['nom', 'type', 'capacite', 'puit']
    
    form_overrides = {
        'type': SelectField
    }
    
    form_args = {
        'type': {
            'choices': [
                ('vertical', 'Vertical'),
                ('horizontal', 'Horizontal'),
                ('spherique', 'Sphérique')
            ],
            'validators': [InputRequired()]
        },
        'capacite': {
            'label': 'Capacité (m³)',
            'validators': [InputRequired()],
            'render_kw': {'placeholder': 'ex: 1500.50'}
        },
        'puit': {
            'label': 'Nom du puits',
            'validators': [InputRequired()]
        }
    }
    form_ajax_refs = {
        'puit': {
            'fields': ['nom'],
            'page_size': 10,
            'minimum_input_length': 1,
            'placeholder': 'Rechercher un puits',
        }
    }

    # Méthode pour afficher la liste des puits associés
    def puits_list(self, context, model, name):
        return ", ".join([p.nom for p in model.puits]) if model.puits else "Aucun puits"
    column_formatters = {
        'puits_list': puits_list
    }


    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'Administrateur'

    def inaccessible_callback(self, name, **kwargs):
        flash("Accès refusé. Vous devez être un administrateur.", "danger")
        return redirect(url_for('routes.login'))

class DuseAdmin(ModelView):
    column_list = ['nom', 'type', 'pression_max','puit.nom']
    column_labels = {
        'nom': 'Nom de la Düse',
        'type': 'Type de Düse',
        'pression_max': 'Pression maximale (bar)',
        'puit.nom': 'Nom du puits'

    }
    column_searchable_list = ['nom', 'type']
    column_filters = ['type']
    
    form_columns = ['nom', 'type', 'pression_max','puit']
    
    form_overrides = {
        'type': SelectField
    }
    
    form_args = {
        'type': {
            'choices': [
                ('réglable', 'Düse à étranglement réglable'),
                ('fixe', 'Düse à étranglement fixe'),
                ('automatique', 'Düse automatique')
            ],
            'validators': [InputRequired()],
            'label': 'Type de Düse'
        },
        'pression_max': {
            'label': 'Pression maximale (bar)',
            'validators': [InputRequired()],
            'render_kw': {'placeholder': 'ex: 150.50'}
        },
        'puit': {
            'label': 'Nom du puits',
            'validators': [InputRequired()]
        }
    }
    form_ajax_refs = {
        'puit': {
            'fields': ['nom'],
            'page_size': 10,
            'minimum_input_length': 1,
            'placeholder': 'Rechercher un puits',
        }
    }


    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'Administrateur'

    def inaccessible_callback(self, name, **kwargs):
        flash("Accès refusé. Vous devez être un administrateur.", "danger")
        return redirect(url_for('routes.login'))


from flask_admin.contrib.sqla import ModelView
from flask_admin.form import ImageUploadField
from wtforms import PasswordField, SelectField
from wtforms.validators import InputRequired, Email, Optional, Length, ValidationError
from werkzeug.security import generate_password_hash

class TestAdmin(ModelView):
    column_list = ['username', 'role', 'nom', 'prenom', 'adresse']
    form_columns = ['username','role', 'password','nom', 'prenom', 'adresse','email', 'image_url']
    column_searchable_list = ['role','nom']

    form_args = {
        'role': {
            'choices': [
                ('Administrateur', 'Administrateur'),
                ('Ingénieur de production', 'Ingénieur de production'),
                ('Directeur de production', 'Directeur de production'),
                ('Opérateur de terrain', 'Opérateur de terrain')
            ],
            'label': 'Role',
            'validators': [InputRequired()]
        },
        'email': {
            'label': 'Adresse email',
            'validators': [InputRequired(), Email(message='Adresse email invalide')]
        }
    }

    form_overrides = {
        'role': SelectField
    }

    form_extra_fields = {
        'image_url': ImageUploadField(
            'Photo de profil',
            base_path='static/uploads',
            url_relative_path='uploads/',  # Modifier si besoin
            allowed_extensions=['jpg', 'png', 'jpeg', 'gif', 'jfif'],
        )
    }

    def scaffold_form(self):
        form_class = super().scaffold_form()
        form_class.password = PasswordField(
            'Mot de passe',
            validators=[Optional(), Length(min=6)],
            description='',  # sera ajusté dynamiquement
            render_kw={'autocomplete': 'new-password'}
        )
        return form_class

    def create_form(self, obj=None):
        form = super().create_form(obj)
        form.password.description = "Laissez vide pour utiliser le mot de passe par défaut"
        form.password.render_kw = {
            'placeholder': "Définir le mot de passe initial (si vide, 'password123' sera utilisé par défaut)",
            'autocomplete': 'new-password'
        }
        return form

    def edit_form(self, obj=None):
        form = super().edit_form(obj)
        form.password.description = "Laissez vide pour ne pas modifier le mot de passe actuel"
        form.password.render_kw = {
            'placeholder': 'Nouveau mot de passe (min 6 caractères)',
            'autocomplete': 'new-password'
        }
        # Stocke l'ancien mot de passe dans le formulaire (pas dans le modèle, ni dans self)
        if obj is not None:
            form._original_password = obj.password
        return form

    def validate_email(self, form, field):
        existing = self.session.query(self.model).filter_by(email=field.data).first()
        if existing and (not form.id.data or existing.id != int(form.id.data)):
            raise ValidationError("Cet email est déjà utilisé par un autre utilisateur.")

    def on_model_change(self, form, model, is_created):
        # Création
        if is_created:
            if not form.password.data:
                model.password = generate_password_hash("password123")
            else:
                model.password = generate_password_hash(form.password.data)
        # Modification
        else:
            if form.password.data:
                model.password = generate_password_hash(form.password.data)
            else:
                # Restaurer l'ancien mot de passe stocké lors de l'édition
                model.password = getattr(form, '_original_password', model.password)        

admin = Admin(app, name='Sonatrach Admin', template_mode='bootstrap4', index_view=MyAdminIndexView())
admin.add_view(PuitAdmin(Puit, db.session))
admin.add_view(RegionAdmin(Region, db.session))
admin.add_view(DuseAdmin(Duse, db.session))
admin.add_view(SeparateurAdmin(Separateur, db.session))
admin.add_view(TestAdmin(Test, db.session))  


# Enregistrement du Blueprint
app.register_blueprint(routes)

if __name__ == '__main__':
    app.run(debug=True)
