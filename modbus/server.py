# modbus/server.py
from pymodbus.server.sync import StartTcpServer
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
import threading, random, time

# 10 variables = 0 à 9
store = ModbusSlaveContext(
    hr=ModbusSequentialDataBlock(0, [0]*10)
)
context = ModbusServerContext(slaves=store, single=True)

def update_data():
    while True:
        values = [
            int(random.uniform(100, 300)),  # pression
            int(random.uniform(50, 150)),   # débit
            int(random.uniform(40, 100)),   # température
            int(random.uniform(80, 200)),   # pression_pip
            int(random.uniform(60, 180)),   # pression_tete
            int(random.uniform(0, 100)), # GOR
            int(random.uniform(0, 100)), # GLR
            int(random.uniform(0, 100)),    # taux_eau
            0,
            0
        ]
        context[0].setValues(3, 0, values)
        time.sleep(2)  # Update every 2 seconds

threading.Thread(target=update_data, daemon=True).start()
StartTcpServer(context, address=("localhost", 5020))
