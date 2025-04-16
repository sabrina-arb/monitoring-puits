from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
import folium
from database.models import User, Puit, UserProfile, Region

# Création du Blueprint
routes = Blueprint('routes', __name__)

@routes.route('/')
def index():
    return render_template('index.html')

@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password= request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.verify_password(password):
            login_user(user)
            return redirect(url_for('admin.index') if user.role == 'admin' else url_for('routes.dashboard_user'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@routes.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('routes.login'))

@routes.route('/carte', methods=['GET', 'POST'])
@login_required
def carte():
    search_query = request.form.get('search', '')
    map_center = [28.0339, 1.6596]
    m = folium.Map(location=map_center, zoom_start=5.45)
    folium.GeoJson('https://raw.githubusercontent.com/johan/world.geo.json/master/countries/DZA.geo.json', name='geojson').add_to(m)
    puits = Puit.query.filter(Puit.nom.ilike(f'%{search_query}%')).all() if search_query else Puit.query.all()
    for puit in puits:
        folium.Marker(
            location=[puit.latitude, puit.longitude],
            popup=f"{puit.nom} - {puit.status}",
            icon=folium.Icon(color='blue' if puit.status == 'Actif' else 'red')
        ).add_to(m)
    return render_template('user/carte.html', map_html=m._repr_html_(), search_query=search_query)

@routes.route('/dashboard_user')
@login_required
def dashboard_user():
    return render_template('user/dashboard.html')

@routes.route('/profile')
@login_required
def profile():
    return render_template('user/profile.html')

@routes.route('/settings')
@login_required
def settings():
    return render_template('user/settings.html')
