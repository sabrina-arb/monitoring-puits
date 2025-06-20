from pymodbus.server.sync import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading
import requests
import random
import time

# Contexte Modbus initial
store = ModbusSlaveContext(hr=ModbusSequentialDataBlock(0, [0] * 10))
context = ModbusServerContext(slaves=store, single=True)

# Obtenir la liste des puits disponibles
def get_puits_list():
    try:
        res = requests.get("http://localhost:5000/api/puits")
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print("Erreur récupération liste des puits:")
    return []

# Obtenir l'ID du puits actuellement sélectionné via l'API Flask
def get_current_puit_id():
    try:
        res = requests.get("http://localhost:5000/api/get_current_puit")
        if res.status_code == 200:
            return res.json().get("id")
    except Exception as e:
        print("Erreur récupération ID puits sélectionné:")
    return None

# Obtenir les seuils min/max pour un puits donné
def get_thresholds(puit_id):
    try:
        res = requests.get(f"http://localhost:5000/api/puit_details/{puit_id}")
        if res.status_code == 200:
            data = res.json()
            return {
                'p_min': data['p_min'], 'p_max': data['p_max'],
                'd_min': data['d_min'], 'd_max': data['d_max'],
                't_min': data['t_min'], 't_max': data['t_max'],
                'nom': data['nom']  # Ajout du nom pour les logs
            }
    except Exception as e:
        print(f"Erreur récupération seuils pour puits {puit_id}:")
    return None

# Générer des données simulées avec des alertes occasionnelles
def generate_data(thresholds, safe=False):
    def r(minv, maxv, alert_chance=0.1):  # 10% de chance d'alerte
        if safe:
            return int((minv + maxv) / 2)
        
        # Décider si on génère une alerte pour cette valeur
        if random.random() < alert_chance:
            # Choisir aléatoirement si on est en dessous ou au dessus du seuil
            if random.choice([True, False]):
                # Valeur en dessous du seuil min
                return int(random.uniform(minv * 0.7, minv * 0.95))
            else:
                # Valeur au dessus du seuil max
                return int(random.uniform(maxv * 1.05, maxv * 1.3))
        else:
            # Valeur normale dans les seuils
            return int(random.uniform(minv + 0.05 * (maxv - minv), maxv - 0.05 * (maxv - minv)))

    # Générer les données avec possibilité d'alertes
    data = [
        r(thresholds['p_min'], thresholds['p_max'], 0.1),  # Pression (10% chance d'alerte)
        r(thresholds['d_min'], thresholds['d_max'], 0.1),  # Débit (10% chance d'alerte)
        r(thresholds['t_min'], thresholds['t_max'], 0.1),  # Température (10% chance d'alerte)
        random.randint(100, 250),   # GOR
        random.randint(80, 200),    # GLR
        random.randint(100, 800),   # Pression pipeline
        random.randint(100, 1000),  # Pression tête
        random.randint(0, 30),      # Taux eau
        random.randint(10, 25),     # Diamètre duse
        0                           # Reserved
    ]
    
    # Journaliser si une alerte est générée
    if (data[0] < thresholds['p_min'] or data[0] > thresholds['p_max'] or
        data[1] < thresholds['d_min'] or data[1] > thresholds['d_max'] or
        data[2] < thresholds['t_min'] or data[2] > thresholds['t_max']):
        print(f"⚠️ ALERTE générée - Pression: {data[0]} (min:{thresholds['p_min']}, max:{thresholds['p_max']}), "
              f"Débit: {data[1]} (min:{thresholds['d_min']}, max:{thresholds['d_max']}), "
              f"Température: {data[2]} (min:{thresholds['t_min']}, max:{thresholds['t_max']})")
    
    return data

# Mise à jour en continu basée sur le puits sélectionné
def update_data():
    last_id = None
    thresholds = None
    current_status = None  # Ajout pour suivre le statut
    
    puits_list = get_puits_list()
    default_puit_id = puits_list[0]['id'] if puits_list else None
    
    while True:
        current_id = get_current_puit_id() or default_puit_id
        
        if current_id is None:
            print("⏳ Aucun puits disponible - en attente...")
            time.sleep(5)
            continue

        if current_id != last_id:
            try:
                res = requests.get(f"http://localhost:5000/api/puit_details/{current_id}")
                if res.status_code == 200:
                    data = res.json()
                    thresholds = {
                        'p_min': data['p_min'], 'p_max': data['p_max'],
                        'd_min': data['d_min'], 'd_max': data['d_max'],
                        't_min': data['t_min'], 't_max': data['t_max'],
                        'nom': data['nom'],
                        'status': data['status']  # Ajout du statut
                    }
                    current_status = data['status']
                    print(f"🔄 Puits sélectionné : {thresholds['nom']} (ID: {current_id}, Statut: {current_status})")
                    last_id = current_id
                else:
# print(f"⚠️ Impossible de charger les seuils pour le puits ID {current_id}")
                    time.sleep(2)
                    continue
            except Exception as e:
                # print(f"Erreur récupération détails puits {current_id}:", e)
                time.sleep(2)
                continue

        if thresholds:
            # Ne pas générer de données si inactif ou en maintenance
            if current_status in ['inactif', 'en maintenance']:
                print(f"⏸️ Puits {thresholds['nom']} est {current_status} - pas de simulation de données")
                # Envoyer des zéros ou valeurs nulles
                context[0].setValues(3, 0, [0] * 10)
            else:
                data = generate_data(thresholds)
                context[0].setValues(3, 0, data)
                print(f"📊 Données simulées - Pression: {data[0]}, Débit: {data[1]}, Température: {data[2]}")

        time.sleep(4)
# Lancement du thread de simulation et du serveur Modbus
if __name__ == "__main__":
    print("🚀 Démarrage du serveur Modbus...")
    threading.Thread(target=update_data, daemon=True).start()
    StartTcpServer(context, address=("localhost", 5020))