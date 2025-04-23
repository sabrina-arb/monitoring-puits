from flask import Flask, flash, redirect, url_for, request
from flask_login import LoginManager, current_user, login_required
from flask_admin import Admin, expose
from flask_admin.contrib.sqla import ModelView
from database.models import  Puit , Region,Duse,Separateur,Test
from database.db import db
from config import Config
from routes.routes import routes 
from flask_admin.base import AdminIndexView
from flask_admin.form import ImageUploadField
from wtforms import SelectField, PasswordField
from wtforms.validators import InputRequired
from werkzeug.security import generate_password_hash
from flask_admin.form.fields import Select2Field
from flask_admin.form import Select2Field 





app = Flask(__name__)
app.config.from_object(Config)

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
        if not (current_user.is_authenticated and current_user.role == 'Administrateur'):
            flash("Accès refusé. Vous devez être un administrateur.", "danger")
            return redirect(url_for('routes.login'))

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
                'maintenance_wells': Puit.query.filter_by(status='en maintenance').count()
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
                'maintenance_percent': (stats['maintenance_wells'] / total_wells) * 100
            }

            # 4. Récupération des dernières activités (nouveau)
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
                return activities[:5]  # Retourne les 5 plus récentes

            last_activities = get_recent_activities()

            # 5. Rendu du template avec toutes les données
            return self.render(
                'admin/dashboard.html',
                last_activities=last_activities,
                **stats,
                **role_counts,
                **percentages,
                # Conservez vos autres variables existantes si nécessaire
                admin_count=role_counts.get('Administrateur', 0),
                engineer_count=role_counts.get('Ingénieur de production', 0),
                director_count=role_counts.get('Directeur de production', 0),
                operator_count=role_counts.get('Opérateur de terrain', 0)
            )

        except Exception as e:
            flash(f"Erreur lors de la récupération des données: {str(e)}", "danger")
            return self.render('admin/dashboard.html')
        
        """
class UserAdmin(ModelView):
    column_list = ['id', 'username', 'role']
    
class UserProfileAdmin(ModelView):
    column_list = ['id', 'nom', 'prenom', 'adresse']
    form_columns = ['nom', 'prenom', 'adresse', 'image_url']  # Explicitement définir les champs
    
    form_extra_fields = {
        'image_url': ImageUploadField(
            'Photo de profil',
            base_path='static/uploads',
            url_relative_path='uploads/',  # Modifier ce chemin
            allowed_extensions=['jpg', 'png', 'jpeg', 'gif', 'jfif'],
        )
    }
"""

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
                ('en maintenance', 'En maintenance')
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
    column_list = ['nom', 'type', 'capacite']
    column_labels = {
        'nom': 'Nom du séparateur',
        'type': 'Type de séparateur',
        'capacite': 'Capacité (m³)'
    }
    column_searchable_list = [ 'nom']
    column_filters = ['type']
    
    form_columns = ['nom', 'type', 'capacite']
    
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
        }
    }

    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'Administrateur'

    def inaccessible_callback(self, name, **kwargs):
        flash("Accès refusé. Vous devez être un administrateur.", "danger")
        return redirect(url_for('routes.login'))

class DuseAdmin(ModelView):
    column_list = ['nom', 'type', 'pression_max']
    column_labels = {
        'nom': 'Nom de la Düse',
        'type': 'Type de Düse',
        'pression_max': 'Pression maximale (bar)'
    }
    column_searchable_list = ['nom', 'type']
    column_filters = ['type']
    
    form_columns = ['nom', 'type', 'pression_max']
    
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
        }
    }

    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'Administrateur'

    def inaccessible_callback(self, name, **kwargs):
        flash("Accès refusé. Vous devez être un administrateur.", "danger")
        return redirect(url_for('routes.login'))

class TestAdmin(ModelView):
    column_list = ['username', 'role', 'nom', 'prenom', 'adresse']
    form_columns = ['username','role', 'password','nom', 'prenom', 'adresse', 'image_url']
    
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
        }

    }

    form_overrides = {
        'role': SelectField
    }
    
    form_extra_fields = {
    'image_url': ImageUploadField(
        'Photo de profil',
        base_path='static/uploads',
        url_relative_path='uploads/',  # Modifier ce chemin si nécessaire
        allowed_extensions=['jpg', 'png', 'jpeg', 'gif', 'jfif'],
    ),

    'password': PasswordField(
        'Mot de passe',
        validators=[],
        render_kw={'placeholder': 'Saisissez un mot de passe (laisser vide pour ne pas modifier)'}
    )
}
    
    def on_model_change(self, form, model, is_created):
        # Si c'est une création et qu'aucun mot de passe n'est fourni
        if is_created and not form.password.data:
            # Générer un mot de passe par défaut (par exemple "password123")
            model.password = generate_password_hash("password123")
        # Si un mot de passe est fourni (création ou modification)
        elif form.password.data:
            model.password = generate_password_hash(form.password.data)

admin = Admin(app, name='Sonatrach Admin', template_mode='bootstrap4', index_view=MyAdminIndexView())
"""
admin.add_view(UserAdmin(User, db.session))
admin.add_view(UserProfileAdmin(UserProfile, db.session))
"""
admin.add_view(PuitAdmin(Puit, db.session))
admin.add_view(RegionAdmin(Region, db.session))
admin.add_view(DuseAdmin(Duse, db.session))
admin.add_view(SeparateurAdmin(Separateur, db.session))
admin.add_view(TestAdmin(Test, db.session))  


# Enregistrement du Blueprint
app.register_blueprint(routes)

if __name__ == '__main__':
    app.run(debug=True)
