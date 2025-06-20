from datetime import datetime, time
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
import os
import re
from flask import Blueprint, app, current_app, json, jsonify, make_response, render_template, request, redirect, session, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
import folium
from fpdf import FPDF
import requests
from sqlalchemy import Numeric, null
from weasyprint import HTML
from database.models import  Puit, Region,Test,Telejaugeage, Rapport
from database.db import db 
from werkzeug.utils import secure_filename
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import re
from email.utils import formataddr
from folium.plugins import MarkerCluster
from config import mail  # adapte selon ton projet
from flask import jsonify
from modbus.data_service import data_modbus
from typing import Dict, Tuple
from datetime import datetime
from flask import jsonify, request
from database.models import Telejaugeage  # Importez votre modèle Telejaugeage



# Création du Blueprint
routes = Blueprint('routes', __name__, url_prefix='/')

# Puits actuellement sélectionné pour la simulation
current_selected_puit = {"id": None}

@routes.route('/get_telegougage_data', methods=['GET'])
def get_telegougage_data():
    try:
        # Option : Filtrer par puit_id si fourni dans les query params
        puit_id = request.args.get('puit_id')
        
        query = Telejaugeage.query
        
        if puit_id:
            query = query.filter_by(puit_id=puit_id)
            
        # Trier par date décroissante et limiter à 100 entrées
        jaugeages = query.order_by(Telejaugeage.date_debut.desc()).limit(100).all()
        
        # Formatage des données
        jaugeage_data = [{
            'id': j.id,
            'nom_puits': j.nom_puits,
            'date_debut': j.date_debut.isoformat() if j.date_debut else None,
            'date_fin': j.date_fin.isoformat() if j.date_fin else None,
            'pression_pip': j.pression_pip,
            'pression_manifold': j.pression_manifold,
            'temperature_pipe': j.temperature_pipe,
            'temperature_tete': j.temperature_tete,
            'pression_tete': j.pression_tete,
            'debit_huile': j.debit_huile,  # Champ clé pour le graphique
            'gor': j.gor,
            'glr': j.glr,
            'taux_eau': j.taux_eau,
            'eau_inj': j.eau_inj,
            'puit_id': j.puit_id
        } for j in jaugeages]
        
        return jsonify(jaugeage_data)
    
    except Exception as e:
        return jsonify({'error': str(e), 'status': 'failed'}), 500

@routes.route('/api/update_puit_status/<int:puit_id>', methods=['POST'])
@login_required
def update_puit_status(puit_id):
    if not current_user.is_authenticated or current_user.role != 'Administrateur':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    new_status = data.get('status')
    
    if not new_status:
        return jsonify({'error': 'Status is required'}), 400
    
    puit = Puit.query.get_or_404(puit_id)
    puit.status = new_status
    db.session.commit()
    
    # Envoyer un email d'alerte si le statut est 'urgence'
    if new_status == 'en urgence':
        msg = Message(
            subject=f"URGENCE: Changement de statut du puits {puit.nom}",
            recipients=['regaiaalaa@gmail.com','clusterlicence@gmail.com'],  # Liste des destinataires
            body=f"Le puits {puit.nom} (ID: {puit.id}) a été marqué comme 'en urgence'.\n\n"
                 f"Région: {puit.region.nom if puit.region else 'Non spécifiée'}\n"
                 f"Coordonnées: {puit.latitude}, {puit.longitude}\n\n"
                 f"Veuillez prendre les mesures nécessaires."
        )
        mail.send(msg)
    
    return jsonify({
        'id': puit.id,
        'nom': puit.nom,
        'status': puit.status
    })

@routes.route('/api/set_current_puit/<int:puit_id>', methods=['POST'])
def set_current_puit(puit_id):
    current_selected_puit['id'] = puit_id
    return jsonify({"message": f"Puits sélectionné mis à jour : {puit_id}"}), 200

@routes.route('/api/get_current_puit', methods=['GET'])
def get_current_puit():
    return jsonify(current_selected_puit)


@routes.route("/api/modbus_data")
def api_modbus_data():
    return jsonify(data_modbus)

@routes.route('/api/puits', methods=['GET'])
def api_puits():
    try:
        puits_list = Puit.query.all()
        result = [{'id': puit.id, 'nom': puit.nom} for puit in puits_list]
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la récupération des puits: {e}")
        return jsonify({"error": "Erreur serveur lors de la récupération des données des puits"}), 500

@routes.route('/api/puit_details/<int:puit_id>', methods=['GET'])
def api_puit_details(puit_id):
    try:
        puit = Puit.query.get(puit_id)
        if puit:
            details = {
                'id': puit.id,
                'nom': puit.nom,
                'latitude': puit.latitude,
                'longitude': puit.longitude,
                'status': puit.status,
                'p_min': puit.p_min,
                'p_max': puit.p_max,
                'd_min': puit.d_min,
                'd_max': puit.d_max,
                't_min': puit.t_min,
                't_max': puit.t_max,
                'region_id': puit.region_id
            }
            return jsonify(details)
        else:
            return jsonify({"error": "Puit non trouvé"}), 404
    except Exception as e:
        current_app.logger.error(f"Erreur lors de la récupération des détails du puit {puit_id}: {e}")
        return jsonify({"error": "Erreur serveur lors de la récupération des détails du puit"}), 500

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
            # ✅ Mise à jour de la dernière connexion
            user.last_login = datetime.utcnow()
            db.session.commit()
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

@routes.route('/sysalerte', methods=['GET', 'POST'])
def sysalerte():
    if request.method == 'POST':
        puits_id = request.form.get('id')
        action = request.form.get('action')

        try:
            # Conversion des valeurs
            new_values = {
                'p_min': float(request.form['p_min']),
                'p_max': float(request.form['p_max']),
                'd_min': float(request.form['d_min']),
                'd_max': float(request.form['d_max']),
                't_min': float(request.form['t_min']),
                't_max': float(request.form['t_max'])
            }
        except (TypeError, ValueError):
            flash("Erreur : Tous les seuils doivent être des nombres valides", "danger")
            return redirect(url_for('routes.sysalerte'))

        puits = db.session.query(Puit).get(puits_id)
        if not puits:
            flash("Erreur : Puits non trouvé", "danger")
            return redirect(url_for('routes.sysalerte'))

        # Vérification des contraintes métier
        errors = []

        
        # 1. Vérification des min < max pour chaque paramètre
        if new_values['p_min'] >= new_values['p_max']:
            errors.append("Pression min doit être < Pression max")
        if new_values['d_min'] >= new_values['d_max']:
            errors.append("Débit min doit être < Débit max")
        if new_values['t_min'] >= new_values['t_max']:
            errors.append("Température min doit être < Température max")

        # 2. Pour l'action 'modifier', vérifier qu'aucun seuil n'est augmenté
        if action == 'modifier':
            if new_values['p_min'] > puits.p_min:
                errors.append("Impossible d'augmenter la Pression min")
            if new_values['p_max'] > puits.p_max:
                errors.append("Impossible d'augmenter la Pression max")
            if new_values['d_min'] > puits.d_min:
                errors.append("Impossible d'augmenter le Débit min")
            if new_values['d_max'] > puits.d_max:
                errors.append("Impossible d'augmenter le Débit max")
            if new_values['t_min'] > puits.t_min:
                errors.append("Impossible d'augmenter la Température min")
            if new_values['t_max'] > puits.t_max:
                errors.append("Impossible d'augmenter la Température max")

        if errors:
             for error in errors:
               flash(error, "danger")
             return redirect(url_for('routes.sysalerte', error_id=puits_id))


        # Mise à jour des valeurs si toutes les validations passent
        puits.p_min = new_values['p_min']
        puits.p_max = new_values['p_max']
        puits.d_min = new_values['d_min']
        puits.d_max = new_values['d_max']
        puits.t_min = new_values['t_min']
        puits.t_max = new_values['t_max']

        db.session.commit()
        flash(" Les seuils ont été mis à jour avec succès", "success")

    tous_les_puits = db.session.query(Puit).all()
    return render_template("director/sysalerte.html", puits=tous_les_puits, error_id=request.args.get("error_id")
)


@routes.route('/carte', methods=['GET', 'POST'])
@login_required
def carte():
    search_query = request.form.get('search', '')

    # Initialisation de la carte
    m = folium.Map(location=[28.0339, 1.6596], zoom_start=5, control_scale=True)
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
                    'fillOpacity': 0.2
                },
                tooltip=folium.GeoJsonTooltip(fields=['nom'], aliases=["Région:"]),
                popup=folium.GeoJsonPopup(fields=['nom', 'nb_puits'], aliases=["Région:", "Nombre de puits:"])
            ).add_to(regions_layer)

    regions_layer.add_to(m)

    # Couche des puits (avec cluster)
    puits_layer = folium.FeatureGroup(name="Puits", show=True)

    marker_cluster = MarkerCluster().add_to(puits_layer)

    # Récupération des puits
    puits = Puit.query.filter(Puit.nom.ilike(f'%{search_query}%')).all() if search_query else Puit.query.all()

    for puit in puits:
        popup_text = folium.Popup(f"""
            <div style="font-size: 14px;">
                <b>🛢️ {puit.nom}</b><br>
                <span>📍 Statut : {puit.status}</span><br>
                <span>🌍 Latitude : {puit.latitude}</span><br>
                <span>🌍 Longitude : {puit.longitude}</span>
            </div>
        """, max_width=250)

        # Définir couleur et icône selon le statut du puits
        if puit.status == 'actif':
            marker_color = "green"
            marker_icon = "tint"
        elif puit.status == 'inactif':
            marker_color = "lightgray"
            marker_icon = "ban"
        elif puit.status == 'en urgence':
            marker_color = "red"
            marker_color = "red"
            marker_icon = "fire"
        else :  # 'en maintenance' 
            marker_color = "orange"
            marker_icon = "wrench"
        

        folium.Marker(
            location=[puit.latitude, puit.longitude],
            popup=popup_text,
            tooltip=puit.nom,
            icon=folium.Icon(
            color=marker_color,
            icon=marker_icon,
            prefix='fa'
            )
        ).add_to(marker_cluster)

    puits_layer.add_to(m)

    # Couche des frontières de l'Algérie
    geojson_url = "https://raw.githubusercontent.com/johan/world.geo.json/master/countries/DZA.geo.json"
    try:
        geojson_data = requests.get(geojson_url).json()
    except:
        geojson_data = {}

    geojson_path = os.path.join("static", "custom.geo.json")
    if os.path.exists(geojson_path):
        with open(geojson_path, encoding='utf-8') as f:
            geojson_data = json.load(f)

    folium.GeoJson(
        geojson_data,
        name="Frontières",
        style_function=lambda x: {'color': 'orange', 'weight': 1.5, 'fillOpacity': 0}
    ).add_to(m)

    # Contrôle des couches
    folium.LayerControl(position='topright', collapsed=True).add_to(m)
    
    
    
    # Appliquer une taille de police personnalisée aux couches de la carte (LayerControl)
    m.get_root().html.add_child(folium.Element("""
    <style>
    .leaflet-control-layers label {
        font-size: 16px !important;
    }
    </style>
    """))

    return render_template(
        'user/carte.html',
        map_html=m._repr_html_(),
        search_query=search_query,
    )


@routes.route('/dashboard_user')
@login_required
def dashboard_user():
    return render_template('user/dashboard.html')

@routes.route('/rapport', methods=['GET', 'POST'], endpoint='rapport')
@login_required
def rapport():
    if request.method == 'POST':
        nom_rapport = request.form.get('nom_rapport', '').strip()

        try:
            # Vérification d'unicité du nom_rapport
            if Rapport.query.filter_by(nom_rapport=nom_rapport).first():
                flash('Ce nom de rapport existe déjà. Veuillez en choisir un autre.', 'error')
                return redirect(url_for('routes.rapport'))

            # Création du rapport
            nouveau_rapport = Rapport(
                date_rapport=datetime.now(),
                nom_rapport=nom_rapport,
                type_rapport=request.form['type_rapport'],
                nom_puits=request.form['nom_puits'],
                id_puits=request.form['id_puits'],
                latitude=float(request.form['latitude']),
                longitude=float(request.form['longitude']),
                region=request.form['region'],
                date_mise_en_service=datetime.strptime(request.form['date_mise_en_service'], '%Y-%m-%d').date(),
                pression=float(request.form['pression']),
                temperature=float(request.form['temperature']),
                debit=float(request.form['debit']) if request.form['debit'] else 0.0,
                etat_puits=request.form['etat_puits'],
                alertes=int(request.form['alertes']),
                operateur=request.form['operateur'],
                description=request.form.get('description', '')
            )
            
        # Stockage dans la session pour le PDF
            session['rapport_data'] = nouveau_rapport.to_dict()
            chemin_rapport = generer_pdf(
                   data=nouveau_rapport.to_dict(),
                nom_fichier='rapport_technique.pdf',
                   logo_path='chemin/alternatif/logo.png'
            )


            db.session.add(nouveau_rapport)
            db.session.commit()

            flash('Rapport enregistré avec succès!', 'success')
            return redirect(url_for('routes.rapport'))

        except ValueError as e:
            db.session.rollback()
            flash(f"Erreur de conversion des données : {str(e)}", 'error')
            return redirect(url_for('routes.rapport'))

        except Exception as e:
            db.session.rollback()
            flash(f"Erreur lors de l\'enregistrement : {str(e)}", 'error')
            return redirect(url_for('routes.rapport'))

    # GET method : afficher tous les rapports
    rapports = Rapport.query.order_by(Rapport.date_rapport.desc()).all()
    puits_objs = Puit.query.all()

# Convertir chaque objet en dictionnaire
    puits = [
    {
        "id": p.id,
        "nom": p.nom,
        "latitude": p.latitude,
        "longitude": p.longitude,
        "region": p.region.nom ,
        'etat_puits': p.status

    }
         for p in puits_objs
]
    return render_template('engineer/rapport.html',
                           datetime=datetime,
                           rapports=rapports,
                           submitted=False, puits=puits)



@routes.route('/get_all_reports')
def get_all_reports():
    try:
        rapports = Rapport.query.order_by(Rapport.date_rapport.desc()).all()
        return jsonify([{
            'id': r.id,
            'nom_rapport': r.nom_rapport,
            'date_rapport': r.date_rapport.isoformat()
        } for r in rapports])
    except Exception as e:
        print(f"Erreur base de données: {str(e)}")
        return jsonify({'error': 'Database error'}), 500
    
@routes.route('/get_rapport/<int:id>')
def get_rapport(id):
    rapport = Rapport.query.get_or_404(id)
    return jsonify({
        'id': rapport.id,
        'nom_rapport': rapport.nom_rapport,
        'date_rapport': rapport.date_rapport.isoformat(),
        'nom_puits': rapport.nom_puits,
        'id_puits': rapport.id_puits,
        'region': rapport.region,
        'latitude': rapport.latitude,
        'longitude': rapport.longitude,
        'date_mise_en_service': rapport.date_mise_en_service.strftime('%Y-%m-%d'),

        'description': rapport.description,
        'pression': rapport.pression,
        'temperature': rapport.temperature,
        'debit': rapport.debit,
        'etat_puits': rapport.etat_puits,
        'alertes': rapport.alertes,
        'operateur': rapport.operateur
    })


@routes.route('/supprimer_rapport/<int:id>', methods=['DELETE'])
def supprimer_rapport(id):
    rapport = Rapport.query.get_or_404(id)
    db.session.delete(rapport)
    db.session.commit()
    return jsonify({'message': 'Rapport supprimé avec succès'}), 200

@routes.route('/download_pdf/<int:rapport_id>', methods=['GET'])
def download_pdf(rapport_id):
    rapport = Rapport.query.get_or_404(rapport_id)

    data = {
        'nom_rapport': rapport.nom_rapport,
        'date_rapport': rapport.date_rapport.strftime('%d/%m/%Y'),
        'nom_puits': rapport.nom_puits,
        'id_puits': rapport.id_puits,
        'region': rapport.region,
        'latitude': rapport.latitude,
        'longitude': rapport.longitude,
        'date_mise_en_service': rapport.date_mise_en_service.strftime('%d/%m/%Y'),
        'pression': rapport.pression,
        'temperature': rapport.temperature,
        'debit': rapport.debit,
        'etat_puits': rapport.etat_puits,
        'alertes': rapport.alertes,
        'operateur': rapport.operateur,
        'description': rapport.description or 'Aucune description fournie',
    }

    html = render_template('engineer/export_pdf.html', data=data)
    pdf = HTML(string=html).write_pdf()

    filename = f"rapport_{rapport.nom_puits}_{rapport.date_rapport.strftime('%Y%m%d')}.pdf"
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename={filename}'
    return response


    
def generate_pdf(data):
    # Votre logique existante de génération PDF
    html = render_template('export_pdf.html', data=data)
    return HTML(string=html).write_pdf()

@routes.route('/profile')
@login_required
def profile():
    return render_template('user/profile-carte.html')

@routes.route('/settings')
@login_required
def settings():
    return render_template('user/settings.html')

@routes.route('/get_email_form_partial')
def get_email_form_partial():
    return render_template('engineer/partials/email_form.html')

# Dashboard Ingénieur de production
@routes.route('/dashboard_engineer')
@login_required
def dashboard_engineer():
    if current_user.role not in ['Administrateur', 'Ingénieur de production']:
        flash("Accès réservé aux ingénieurs de production", "danger")
        return redirect(url_for('routes.login'))
    return render_template('user/dashboard.html')

# Dashboard Directeur de production
@routes.route('/dashboard_director')
@login_required
def dashboard_director():
    if current_user.role not in ['Administrateur', 'Directeur de production']:
        flash("Accès réservé aux directeurs de production", "danger")
        return redirect(url_for('routes.login'))
    return render_template('user/dashboard.html')

# Dashboard Opérateur de terrain
@routes.route('/dashboard_operator')
@login_required
def dashboard_operator():
    if current_user.role not in ['Administrateur', 'Opérateur de terrain']:
        flash("Accès réservé aux opérateurs de terrain", "danger")
        return redirect(url_for('routes.login'))
    return render_template('user/dashboard.html')

@routes.route('/switch_to_engineer_view')
@login_required
def switch_to_engineer_view():
    if current_user.role != 'Administrateur':
        flash("Accès réservé aux administrateurs", "danger")
        return redirect(url_for('routes.login'))
    session['view_as'] = 'engineer'  # Stocke le mode de vue
    return redirect(url_for('routes.dashboard_engineer'))

@routes.route('/switch_to_director_view')
@login_required
def switch_to_director_view():
    if current_user.role != 'Administrateur':
        flash("Accès réservé aux administrateurs", "danger")
        return redirect(url_for('routes.login'))
    session['view_as'] = 'director'  # Stocke le mode de vue
    return redirect(url_for('routes.dashboard_director'))

@routes.route('/switch_to_operator_view')
@login_required
def switch_to_operator_view():
    if current_user.role != 'Administrateur':
        flash("Accès réservé aux administrateurs", "danger")
        return redirect(url_for('routes.login'))
    session['view_as'] = 'operator'  # Stocke le mode de vue
    return redirect(url_for('routes.dashboard_operator'))

# Ajoutez une route pour revenir à la vue admin
@routes.route('/switch_to_admin_view')
@login_required
def switch_to_admin_view():
    if current_user.role != 'Administrateur':
        flash("Accès réservé aux administrateurs", "danger")
        return redirect(url_for('routes.login'))
    session.pop('view_as', None)  # Retire le mode de vue
    return redirect(url_for('admin.index'))

@routes.route('/jaugeage')
@login_required
def datajaugeage(): 

    return render_template('operator/datajaugeage.html')

@routes.route('/enregistrer_donnees', methods=['POST'])
def enregistrer_donnees():
    data = request.get_json()

    try:
        entry = Telejaugeage(
            nom_puits=data['nom_puits'],
            pression_pip=data['pression_pip'],
            pression_manifold=data['pression_manifold'],
            temperature_pipe=data['temperature_pipe'],
            temperature_tete=data['temperature_tete'],
            pression_tete=data['pression_tete'],
            debit_huile=data['debit_huile'],
            gor=data['gor'],
            glr=data['glr'],
            taux_eau=data['taux_eau'],
            date_debut=data['date_debut'],
            date_fin=data['date_fin'],            
            eau_inj=data['eau_inj'],
            puit_id=data['puit_id']

        )
        db.session.add(entry)
        db.session.commit()
        return jsonify({'message': 'Enregistrement réussi'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Erreur : {str(e)}'}), 500
    

@routes.route('/api/puits')
def search_puits():
    search_term = request.args.get('q', '').strip()
    if len(search_term) < 2:
        return jsonify([])
    
    # Recherche des puits qui contiennent le terme recherché (insensible à la casse)
    puits = Puit.query.filter(Puit.nom.ilike(f'%{search_term}%')).limit(10).all()
    
    results = [{'id': p.id, 'nom': p.nom} for p in puits]
    return jsonify(results)

@routes.route('/supprimer_telegougage/<int:id>', methods=['DELETE'])
def supprimer_telegougage(id):
    try:
        entry = Telejaugeage.query.get_or_404(id)
        db.session.delete(entry)
        db.session.commit()
        return jsonify({'message': 'Suppression réussie'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
    
@routes.route('/send_email', methods=['POST'])
def send_email():
    destinataire = request.form.get('destinataire')
    data = session.get('rapport_data')

    if not data:
        flash("❌ Aucune donnée de rapport trouvée. Veuillez soumettre un rapport d'abord.", 'danger')
        return redirect(url_for('routes.rapport'))

    nom_rapport = data.get('nom_rapport', 'rapport.pdf')
    if not nom_rapport.endswith('.pdf'):
        nom_rapport += '.pdf'

    try:
        chemin_pdf = generer_pdf(data, nom_rapport)

        msg = Message(f'Rapport PDF - {nom_rapport}', recipients=[destinataire])
        message_personnalise = request.form.get('message', '')
        msg.body = message_personnalise

        with open(chemin_pdf, 'rb') as fp:
         msg.attach(nom_rapport, 'application/pdf', fp.read())

        mail.send(msg)
        flash('📧 Email envoyé avec succès !', 'success')
        return redirect(url_for('routes.rapport'))

    except Exception as e:
        print("Erreur lors de l'envoi de l'email :", e)
        flash('❌ Erreur d\'envoi de l\'email.', 'danger')

    return redirect(url_for('routes.rapport'))


class PDFStyleConfig:
    """Configuration des styles et couleurs"""
    COLORS = {
 'title': (0, 0, 0),        
   'section_title': (51, 51, 51),
        'text': (60, 60, 60),
        'footer': (100, 100, 100),
        'status_active': (0, 128, 0),
        'status_inactive': (87, 86, 85),
        'status_maintenance': (199, 93, 7),
        'status_urgence': (255, 0, 0),
        'background': (248, 248, 248)
    }
    
    FONTS = {
        'title': ('Arial', 'B', 16),
        'section': ('Arial', 'B', 12),
        'body': ('Arial', '', 10),
        'table_header': ('Arial', 'B', 10),
        'footer': ('Arial', '', 8)
    }

class PDFGenerator(FPDF):
    def __init__(self, data: Dict):
        super().__init__()
        self.data = data
        self.page_width = 210  # Largeur A4 en mm
        self.set_auto_page_break(auto=True, margin=25)
    
    def header(self):
        pass  # Pas d'en-tête
    
    def footer(self):
        if self.page_no() > 1:  # Pas de footer sur la page de garde
            self.set_y(-30)
            self.set_font(*PDFStyleConfig.FONTS['footer'])
            self.set_text_color(*PDFStyleConfig.COLORS['footer'])
            self.multi_cell(0, 4, 
                "Direction Générale\n"
                "Djenane El Malik, Hydra, Alger, Algérie\n"
                "Tél : +213 23 48 30 30\n"
                "www.sonatrach.dz", 
                align='C'
            )
            self.set_y(-15)
            self.cell(0, 10, f'Page {self.page_no()-1}', 0, 0, 'C')

    def add_cover_page(self, logo_path: str):
        self.add_page()
        if os.path.exists(logo_path):
            self.image(logo_path, x=(self.w - 50)/2, y=30, w=50)
        
        self.set_font(*PDFStyleConfig.FONTS['title'])
        self.set_text_color(*PDFStyleConfig.COLORS['title'])
        self.ln(100)
        self.cell(0, 10, "Rapport Technique de Surveillance de Puits", 0, 1, 'C')
        
        self.set_font(*PDFStyleConfig.FONTS['body'])
        self.set_text_color(*PDFStyleConfig.COLORS['text'])
        self.ln(10)
        self.cell(0, 6, f"Date du rapport : {self.data['date_rapport']}", 0, 1, 'C')
        self.cell(0, 6, f"Nom du puits : {self.data['nom_puits']}", 0, 1, 'C')

    def add_section_title(self, title: str):
        self.set_font(*PDFStyleConfig.FONTS['section'])
        self.set_text_color(*PDFStyleConfig.COLORS['section_title'])
        self.ln(10)
        self.cell(0, 8, title, 0, 1)
        self.ln(2)

    def add_data_row(self, label: str, value: str, indent: int = 5):
        self.set_font(*PDFStyleConfig.FONTS['body'])
        self.set_text_color(*PDFStyleConfig.COLORS['text'])
        
        # Label
        self.cell(indent)
        self.cell(50, 6, f"{label}: ")
        
        # Valeur
        self.set_x(60)
        self.multi_cell(0, 6, value)
        self.ln(4)

    def add_technical_table(self, headers: Tuple, data: Dict):
        col_widths = [60, 30, 25, 50]
        self.set_font(*PDFStyleConfig.FONTS['table_header'])
        
        # En-têtes
        self.set_fill_color(240, 240, 240)
        for i, header in enumerate(headers):
            self.cell(col_widths[i], 8, header, 1, 0, 'C', 1)
        self.ln()
        
        # Données
        self.set_font(*PDFStyleConfig.FONTS['body'])
        for row in data:
            for i, item in enumerate(row):
                self.cell(col_widths[i], 8, str(item), 1)
            self.ln()

    def add_status_indicator(self, status: str):
        status_colors = {
            'actif': 'status_active',
            'inactif': 'status_inactive',
            'maintenance': 'status_maintenance'
        }
        color = PDFStyleConfig.COLORS[status_colors.get(status, 'status_urgence')]
        
        # Ajouter le point coloré
        self.set_fill_color(*color)
        self.cell(5, 6, ' ', 0, 0, 'C', 1)
        self.cell(2)  # Espacement

    def add_observations(self, text: str):
        self.set_fill_color(*PDFStyleConfig.COLORS['background'])
        self.rect(self.x, self.y, self.page_width - 20, 30, 'F')
        self.multi_cell(0, 6, text)

    def add_signature_blocks(self):
        self.ln(26)
        self.set_line_width(0.3)
        self.set_draw_color(51, 51, 51)
        
        # Responsable exploitation
        self.cell(80, 10, "Responsable exploitation", 0, 0)
        self.cell(30)  # Espacement
        # Chef de district
        self.cell(80, 10, "Chef de district", 0, 1)
        
        # Lignes de signature
        self.line(self.x, self.y, self.x + 80, self.y)
        self.line(self.x + 110, self.y, self.x + 190, self.y)
        self.ln(100)

def generer_pdf(data: Dict, nom_fichier: str, logo_path: str = "static/images/sonatrach.png"):
    pdf = PDFGenerator(data)
    if not nom_fichier:
        nom_fichier = f"rapport_technique_{int(time.time())}.pdf"
    pdf.add_page()
    if os.path.exists(logo_path):
        # Logo centré et redimensionné
        logo_width = 20  # Taille réduite à 20mm
        pdf.image(logo_path, x=(pdf.w - logo_width)/2, y=20, w=logo_width)
    
    # Espacement ajusté après le logo
    pdf.ln(70)
    
   # Titre principal
    pdf.set_font(*PDFStyleConfig.FONTS['title'])
    pdf.set_text_color(0, 0, 0)  # Noir pur (R, G, B)
    pdf.cell(0, 10, "Rapport Technique de Surveillance de Puits", 0, 1, 'C')
    # Métadonnées
    pdf.set_font(*PDFStyleConfig.FONTS['body'])
    pdf.set_text_color(*PDFStyleConfig.COLORS['text'])
    pdf.ln(8)
    pdf.cell(0, 6, f"Date du rapport : {data['date_rapport']}", 0, 1, 'C')
    pdf.cell(0, 6, f"Nom du puits : {data['nom_puits']}", 0, 1, 'C')



    pdf.ln(10)  
    
    # Contenu principal
    pdf.add_page()
    
    # Section 1: Identification
    pdf.add_section_title("1. IDENTIFICATION DU PUITS")
    pdf.add_data_row("Code puits", data['id_puits'])
    pdf.add_data_row("Nom du puits", data['nom_puits'])
    pdf.add_data_row("Localisation", 
        f"Région: {data['region']}\n"
        f"Coord. GPS: {data['latitude']}°N, {data['longitude']}°E"
    )
    pdf.add_data_row("Date mise en service", data['date_mise_en_service'])
    
    # Section 2: Paramètres techniques
    pdf.add_section_title("2. PARAMÈTRES TECHNIQUES")
    headers = ("Paramètre", "Valeur", "Unité", "Seuil normal")
    table_data = [
        ("Pression de fond", data['pression'], "bar", "50-150"),
        ("Température", data['temperature'], "°C", "60-120"),
        ("Débit journalier", data.get('debit', 'N/A'), "m³/h", "Selon contrat")
    ]
    pdf.add_technical_table(headers, table_data)
    
    # Section 3: État opérationnel
    pdf.add_section_title("3. ÉTAT OPÉRATIONNEL")
    pdf.add_data_row("Statut du puits", "")
    pdf.set_x(40)
    pdf.add_status_indicator(data['etat_puits'])
    pdf.cell(0, 6, {
        'actif': 'Actif - Production normale',
        'inactif': 'Inactif - En attente',
        'maintenance': 'Maintenance'
    }.get(data['etat_puits'], 'Urgence'))
    pdf.ln(8)
    pdf.add_data_row("Alertes techniques", str(data['alertes']))
    pdf.add_data_row("Opérateur responsable", data['operateur'])
    
    # Section 4: Observations
    pdf.add_section_title("4. OBSERVATIONS TECHNIQUES")
    observations = data.get('description') or "Aucune observation particulière à signaler."
    pdf.add_observations(observations)
    
    # Signatures
    pdf.add_signature_blocks()
    
    # Génération du fichier
    dossier = "export_pdf"
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, nom_fichier)
    pdf.output(chemin)
    return chemin


@routes.route('/suggestions_puits')
def suggestions_puits():
    query = request.args.get('query', '')
    suggestions = []

    if query:
        results = Puit.query.filter(Puit.nom.ilike(f"{query}%")).limit(10).all()
        suggestions = [p.nom for p in results]

    return jsonify(suggestions)
