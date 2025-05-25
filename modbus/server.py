# modbus/server.py

from pymodbus.server.sync import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading
import random
import time
import pandas as pd

# Crée un espace mémoire pour 10 variables (adresses 0 à 9)
store = ModbusSlaveContext(
    hr=ModbusSequentialDataBlock(0, [0] * 10)
)
context = ModbusServerContext(slaves=store, single=True)

def generate_data():
    return [
        int(random.uniform(150, 260)),              # pression_puits (kg/cm²)
        int(random.uniform(110, 450)),             # débit (m³/h)
        int(random.uniform(50, 100)),               # température (°C)
        int(random.uniform(100, 250)),              # pression_pip (kg/cm²)
        int(random.uniform(80, 200)),               # pression_tete (kg/cm²)
        int(random.uniform(100, 800)),              # GOR (m³/m³)
        int(random.uniform(100, 1000)),             # GLR (m³/m³)
        int(random.uniform(0, 90)),                 # taux_eau (m³/h)
        int(random.uniform(10, 25)),                # diametre_duse (mm)
        0                                           # Réservé / Placeholder
    ]

def update_data():
    while True:
        values = generate_data()

        # Création d'un DataFrame temporaire pour traitement instantané
        df = pd.DataFrame([{
            'pression': values[0],
            'debit': values[1],
            'temperature': values[2],
            'pression_pip': values[3],
            'pression_tete': values[4],
            'gor': values[5],
            'glr': values[6],
            'taux_eau': values[7],
            'diametre_duse': values[8]
        }])

    
        context[0].setValues(3, 0, values)

# Lancer la mise à jour des données en tâche de fond
threading.Thread(target=update_data, daemon=True).start()

# Démarrage du serveur Modbus TCP sur le port 5020
StartTcpServer(context, address=("localhost", 5020))
