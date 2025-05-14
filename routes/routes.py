from datetime import datetime
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
from database.models import  Puit, Region,Test,Telejaugeage
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




# Création du Blueprint
routes = Blueprint('routes', __name__, url_prefix='/')



@routes.route("/api/modbus_data")
def api_modbus_data():
    return jsonify(data_modbus)



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
            return redirect(url_for('routes.sysalerte'))

        # Mise à jour des valeurs si toutes les validations passent
        puits.p_min = new_values['p_min']
        puits.p_max = new_values['p_max']
        puits.d_min = new_values['d_min']
        puits.d_max = new_values['d_max']
        puits.t_min = new_values['t_min']
        puits.t_max = new_values['t_max']

        db.session.commit()
        flash("Tous les seuils ont été mis à jour avec succès", "success")

    tous_les_puits = db.session.query(Puit).all()
    return render_template("director/sysalerte.html", puits=tous_les_puits)

@routes.route('/carte', methods=['GET', 'POST'])
@login_required
def carte():
    search_query = request.form.get('search', '')

    # Initialisation de la carte
    m = folium.Map(location=[28.0339, 1.6596], zoom_start=6, control_scale=True)
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

        folium.Marker(
            location=[puit.latitude, puit.longitude],
            popup=popup_text,
            tooltip=puit.nom,
            icon=folium.Icon(color="orange" if puit.status == 'en maintenance'
                             else "green" if puit.status == 'actif'
                             else "red",
                             icon="wrench" if puit.status == 'en maintenance'
                             else "tint" if puit.status == 'actif'
                             else "remove",
                             prefix='fa')
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

    return render_template(
        'user/carte.html',
        map_html=m._repr_html_(),
        search_query=search_query,
    )



@routes.route('/dashboard_user')
@login_required
def dashboard_user():
    return render_template('user/dashboard.html')

@routes.route('/rapport', methods=['GET', 'POST'],endpoint='rapport')
@login_required
def rapport():
    if request.method == 'POST':
        etat_puits = request.form['etat_puits']
        data = {
            'nom_rapport': request.form.get('nom_rapport', 'Rapport de Puits'),  
            'date_rapport': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'nom_puits': request.form['nom_puits'],
            'id_puits': request.form['id_puits'],
            'latitude': request.form['latitude'],
            'longitude': request.form['longitude'],
            'region': request.form['region'],
            'date_mise_en_service': request.form['date_mise_en_service'],
            'pression': request.form['pression'],
            'temperature': request.form['temperature'],
            'etat_puits': request.form['etat_puits'],
            'alertes': request.form['alertes'],
            'operateur': request.form['operateur'],
            'description': request.form.get('description', '')  # Ajout de la description

            
        }
        session['rapport_data'] = data  # ✅ On stocke dans la session


        # Stocker temporairement les données dans la session ou un fichier si nécessaire
        request.session_data = data  # alternatif temporaire pour démonstration

        return render_template('engineer/rapport.html',
                         
                            datetime=datetime, submitted=True, data=data)

    return render_template('engineer/rapport.html',
                         datetime=datetime, submitted=False)

@routes.route('/download_pdf', methods=['GET'])
def download_pdf():

    # Récupération des données depuis la session
    data = session.get('rapport_data', {})
    
    # Assurez-vous que la description est incluse dans les données
    if 'description' not in data:
        data['description'] = 'Aucune description fournie'
    
    # Ajoutez également la description sous le nom 'comptrendu' pour votre template
    data['comptrendu'] = data.get('description', '')
    
    # Rendu du template HTML
    html = render_template('engineer/export_pdf.html', data=data)
    
    # Conversion en PDF
    pdf = HTML(string=html).write_pdf()
    
    # Préparation de la réponse
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'inline; filename=rapport_puits.pdf'
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
            eau_inj=data['eau_inj']

        )
        db.session.add(entry)
        db.session.commit()
        return jsonify({'message': 'Enregistrement réussi'}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Erreur : {str(e)}'}), 500
    

@routes.route('/get_telegougage_data')
def get_telegougage_data():
    try:
        data = Telejaugeage.query.all()
        result = []
        for item in data:
            result.append({
                'id': item.id,
                'nom_puits': item.nom_puits,
                'date_debut': item.date_debut.isoformat() if item.date_debut else None,
                'date_fin': item.date_fin.isoformat() if item.date_fin else None,
                'pression_pip': item.pression_pip,
                'pression_manifold': item.pression_manifold,
                'temperature_pipe': item.temperature_pipe,
                'temperature_tete': item.temperature_tete,
                'pression_tete': item.pression_tete,
                'debit_huile': item.debit_huile,
                'gor': item.gor,
                'glr': item.glr,
                'taux_eau': item.taux_eau,
                'eau_inj':item.eau_inj
            })
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

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
    destinataire = request.form['destinataire']
    
    # Récupérer les données du rapport depuis la session
    data = session.get('rapport_data')

    if not data:
        flash("❌ Aucune donnée de rapport trouvée. Veuillez soumettre un rapport d'abord.", 'danger')
        return redirect(url_for('routes.rapport'))
    
    nom_rapport = data.get('nom_rapport', 'rapport.pdf')

    if not nom_rapport.endswith('.pdf'):
        nom_rapport += '.pdf'

    
        chemin_pdf = generer_pdf(data, nom_rapport)

        # Envoi du mail avec le PDF en pièce jointe
        msg = Message(f'Rapport PDF - {nom_rapport}', recipients=[destinataire])
        message_personnalise = request.form['message']  # Récupère le message saisi
        msg.body = f"{message_personnalise}."


        with open(chemin_pdf, 'rb') as fp:
            msg.attach(nom_rapport, 'application/pdf', fp.read())

        mail.send(msg)
        flash('📧 Email envoyé avec succès !')

    

    return redirect(url_for('routes.rapport'))  # Retourner à la page de création du rapport


def generer_pdf(data, nom_fichier):
    pdf = FPDF()
    pdf.add_page()
    
    # Définir la police pour le document
    pdf.set_font("Arial", size=12)

    def nettoyer_texte(texte):
        remplacements = {
            '’': "'",
            '“': '"',
            '”': '"',
            '–': '-',
            '—': '-',
            '…': '...',
            'é': 'e',
            'è': 'e',
            'à': 'a',
            'ç': 'c',
        }
        for ancien, nouveau in remplacements.items():
            texte = texte.replace(ancien, nouveau)
        return texte

    # Titre du rapport
    pdf.set_text_color(26, 82, 118)  # Couleur #1a5276
    pdf.cell(200, 10, txt="Rapport Technique de Surveillance de Puits", ln=True, align='C')
    pdf.ln(10)  # Espacement

    # Date du rapport
    pdf.set_text_color(0, 0, 0)  # Noir
    pdf.cell(200, 10, txt=f"Date du rapport : {data['date_rapport']}", ln=True)
    pdf.ln(5)

    # Liste des sections
    sections = [
        ("Nom du puits", data['nom_puits']),
        ("ID du puits", data['id_puits']),
        ("Localisation GPS", f"Latitude {data['latitude']}, Longitude {data['longitude']}"),
        ("Région", data['region']),
        ("Date de mise en service", data['date_mise_en_service']),
        ("Pression (bar)", data['pression']),
        ("Température (°C)", data['temperature']),
        ("État du puits", data['etat_puits']),
        ("Nombre d'alertes", data['alertes']),
        ("Opérateur responsable", data['operateur']),
    ]

    for titre, valeur in sections:
      titre_nettoye = nettoyer_texte(titre)
      valeur_nettoyee = nettoyer_texte(str(valeur))
      pdf.set_font("Arial", size=12, style='B')
      pdf.cell(200, 10, txt=f"{titre_nettoye} :", ln=True)
      pdf.set_font("Arial", size=12, style='')
      pdf.multi_cell(0, 10, txt=valeur_nettoyee)


    # Section description détaillée
    pdf.set_font("Arial", size=12, style='B')
    pdf.cell(200, 10, txt="Compte-rendu Technique Détaillé", ln=True)
    pdf.set_font("Arial", size=12)
    description = data.get('description', "Aucun compte-rendu détaillé n'a été fourni pour ce puits.")
    pdf.multi_cell(0, 10, txt=nettoyer_texte(description))

    # Créer le dossier pour les rapports si nécessaire
    dossier = "rapport_exports"
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, nom_fichier)

    # Sauvegarder le fichier PDF
    pdf.output(chemin)
    return chemin

