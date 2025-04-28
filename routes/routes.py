from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
import folium
from database.models import  Puit, Region,Test

# Création du Blueprint
routes = Blueprint('routes', __name__)

@routes.route('/')
def index():
    return render_template('index.html')

@routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Test.query.filter_by(username=username).first()
        
        if user and user.verify_password(password): 
            login_user(user)
            if user.role == 'Administrateur':
                return redirect(url_for('admin.index'))
            elif user.role == 'Ingénieur de production':
                return redirect(url_for('routes.dashboard_engineer'))
            elif user.role == 'Directeur de production':
                return redirect(url_for('routes.dashboard_director'))
            elif user.role == 'Opérateur de terrain':
                return redirect(url_for('routes.dashboard_operator'))
        else:
            flash('Identifiant ou mot de passe incorrect', 'danger')
    return render_template('login.html')

@routes.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('routes.login'))


@routes.route('/carte', methods=['GET', 'POST'])
@login_required
def carte():
    # Configuration initiale
    search_query = request.form.get('search', '')
    map_center = [28.0339, 1.6596]

    # Création de la carte sans la couche par défaut
    m = folium.Map(
        location=map_center,
        zoom_start=5.45,
        tiles=None,
        control_scale=True
    )

    # Couche de base
    folium.TileLayer(name='Carte de base').add_to(m)

    # Couche des régions
    regions_layer = folium.FeatureGroup(name="Régions", show=True)
    regions = Region.query.all()

    for region in regions:
        if region.lat_min and region.lon_min:
            geojson = {
                "type": "Feature",
                "properties": {
                    "nom": region.nom,
                    "nb_puits": len(region.puits)
                },
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [region.lon_min, region.lat_min],
                        [region.lon_max, region.lat_min],
                        [region.lon_max, region.lat_max],
                        [region.lon_min, region.lat_max],
                        [region.lon_min, region.lat_min]
                    ]]
                }
            }

            folium.GeoJson(
                geojson,
                name=region.nom,
                style_function=lambda x: {
                    'fillColor': '#3388ff',
                    'color': '#3388ff',
                    'weight': 2,
                    'fillOpacity': 0.3
                },
                tooltip=folium.GeoJsonTooltip(fields=['nom'], aliases=["Région:"]),
                popup=folium.GeoJsonPopup(fields=['nom', 'nb_puits'], aliases=["Région:", "Nombre de puits:"])
            ).add_to(regions_layer)

    regions_layer.add_to(m)

    # Couche des puits
    puits_layer = folium.FeatureGroup(name="Puits", show=True)
    puits = Puit.query.filter(Puit.nom.ilike(f'%{search_query}%')).all() if search_query else Puit.query.all()

    for puit in puits:
        folium.Marker(
            location=[puit.latitude, puit.longitude],
            popup=f"""
            <b>{puit.nom}</b><br>
            Statut: {puit.status}<br>
            Région: {puit.region.nom if puit.region else 'N/A'}
            """,
           
            icon=folium.Icon(
                 color='orange' if puit.status == 'en maintenance' else 'green' if puit.status == 'actif' else 'red',
                 icon='wrench' if puit.status == 'en maintenance' else 'tint' if puit.status == 'actif' else 'remove',
                 prefix='fa'
)
        ).add_to(puits_layer)

    puits_layer.add_to(m)

    # Couche des frontières algériennes
    folium.GeoJson(
        'https://raw.githubusercontent.com/johan/world.geo.json/master/countries/DZA.geo.json',
        name="Frontières",
        style_function=lambda x: {'color': 'orange', 'weight': 1.5, 'fillOpacity': 0}
    ).add_to(m)

    # Contrôle des calques
    folium.LayerControl(position='topright', collapsed=True).add_to(m)

    return render_template(
        'user/carte.html',
        map_html=m._repr_html_(),
        search_query=search_query,
    )


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



# Dashboard Ingénieur de production
@routes.route('/dashboard_engineer')
@login_required
def dashboard_engineer():
    if current_user.role not in ['Administrateur', 'Ingénieur de production']:
        flash("Accès réservé aux ingénieurs de production", "danger")
        return redirect(url_for('routes.login'))
    return render_template('engineer/dashboard.html')

# Dashboard Directeur de production
@routes.route('/dashboard_director')
@login_required
def dashboard_director():
    if current_user.role not in ['Administrateur', 'Directeur de production']:
        flash("Accès réservé aux directeurs de production", "danger")
        return redirect(url_for('routes.login'))
    return render_template('director/dashboard.html')

# Dashboard Opérateur de terrain
@routes.route('/dashboard_operator')
@login_required
def dashboard_operator():
    if current_user.role not in ['Administrateur', 'Opérateur de terrain']:
        flash("Accès réservé aux opérateurs de terrain", "danger")
        return redirect(url_for('routes.login'))
    return render_template('operator/dashboard.html')

@routes.route('/switch_to_engineer_view')
@login_required
def switch_to_engineer_view():  # Nom unique
    if current_user.role != 'Administrateur':
        flash("Accès réservé aux administrateurs", "danger")
        return redirect(url_for('routes.login'))
    return redirect(url_for('routes.dashboard_engineer'))

@routes.route('/switch_to_director_view')
@login_required
def switch_to_director_view():  # Nom unique
    if current_user.role != 'Administrateur':
        flash("Accès réservé aux administrateurs", "danger")
        return redirect(url_for('routes.login'))
    return redirect(url_for('routes.dashboard_director'))

@routes.route('/switch_to_operator_view')
@login_required
def switch_to_operator_view():  # Nom unique
    if current_user.role != 'Administrateur':
        flash("Accès réservé aux administrateurs", "danger")
        return redirect(url_for('routes.login'))
    return redirect(url_for('routes.dashboard_operator'))


@routes.route('/jaugeage')
@login_required
def datajaugeage(): 
    return render_template('operator/datajaugeage.html')


@routes.route('/système_d/alerte')
@login_required
def sysalerte(): 
    return render_template('director/sysalerte.html')


@routes.route('/Rapport')
@login_required
def rapport(): 
    return render_template('engineer/rapport.html')