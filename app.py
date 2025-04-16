from flask import Flask, flash, redirect, url_for
from flask_login import LoginManager, current_user, UserMixin
from flask_admin import Admin, expose
from flask_admin.contrib.sqla import ModelView
from database.models import User, Puit , UserProfile, Region
from database.db import db
from config import Config
from routes.routes import routes  # Import du Blueprint
from flask_admin.base import AdminIndexView
from flask_admin.form import SecureForm
from wtforms import PasswordField, StringField, validators 
from flask_admin.form import ImageUploadField



app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Configuration de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'routes.login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Configuration de Flask-Admin
class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if not (current_user.is_authenticated and current_user.role == 'admin'):
            flash("Accès refusé. Vous devez être un administrateur.", "danger")
            return redirect(url_for('routes.login'))
        return self.render('admin/master.html')



from wtforms import StringField, SelectField, PasswordField
from flask_admin.form import SecureForm

class UserAdmin(ModelView):
    column_list = ['id', 'username', 'role']
    

class UserProfileAdmin(ModelView):
    column_list = ['id', 'nom', 'prenom', 'adresse']
    form_extra_fields = {
        'image_url': ImageUploadField(
            'Photo de profil',
            base_path='static/uploads',  # Dossier sur le disque
            url_relative_path='static/uploads',  # Pour affichage dans HTML
            allowed_extensions=['jpg', 'png', 'jpeg', 'gif','jfif'],
        )}

class PuitAdmin(ModelView):
    column_list = ('id', 'nom', 'latitude', 'longitude', 'status')
    column_searchable_list = ('nom',)
    column_filters = ('status',)
    form_columns = ('nom', 'latitude', 'longitude', 'status')

    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        flash("Accès refusé. Vous devez être un administrateur.", "danger")
        return redirect(url_for('routes.login'))
    

class RegionAdmin(ModelView):
    column_list = ('id', 'nom')
    form_columns = ('nom', 'geom')

    def is_accessible(self):
        return current_user.is_authenticated and current_user.role == 'admin'

    def inaccessible_callback(self, name, **kwargs):
        flash("Accès refusé. Vous devez être un administrateur.", "danger")
        return redirect(url_for('routes.login'))


admin = Admin(app, name='Sonatrach Admin', template_mode='bootstrap4', index_view=MyAdminIndexView())
admin.add_view(UserAdmin(User, db.session))
admin.add_view(PuitAdmin(Puit, db.session))
admin.add_view(UserProfileAdmin(UserProfile, db.session))
admin.add_view(RegionAdmin(Region, db.session))

# Enregistrement du Blueprint
app.register_blueprint(routes)

if __name__ == '__main__':
    app.run(debug=True)
