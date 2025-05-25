# modbus/client.py
import pandas as pd
from pymodbus.client.sync import ModbusTcpClient
from datetime import datetime

client = ModbusTcpClient('localhost', port=5020)

def get_modbus_data():
    client.connect()
    result = client.read_holding_registers(0, 9)  # Lecture de 9 registres
    client.close()

    if result.isError():
        return None

    vals = result.registers
    data = {
        'timestamp': datetime.now().isoformat(),
        'pression': vals[0],
        'debit': vals[1],
        'temperature': vals[2],
        'pression_pip': vals[3],
        'pression_tete': vals[4],
        'gor': vals[5],
        'glr': vals[6],
        'taux_eau': vals[7],
        'diametre_duse': vals[8]
    }
    return data

def get_modbus_data_df():
    data = get_modbus_data()
    if data is None:
        return None
    return pd.DataFrame([data])