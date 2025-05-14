# modbus/client.py
from pymodbus.client.sync import ModbusTcpClient
from datetime import datetime

client = ModbusTcpClient('localhost', port=5020)

def get_modbus_data():
    client.connect()
    result = client.read_holding_registers(0, 8)
    client.close()

    if result.isError():
        return None

    vals = result.registers
    return {
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'pression': vals[0],
        'debit': vals[1],
        'temperature': vals[2],
        'pression_pip': vals[3],
        'pression_tete': vals[4],
        'gor': vals[5],
        'glr': vals[6],
        'taux_eau': vals[7]
    }
