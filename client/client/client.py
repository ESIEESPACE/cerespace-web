import json
import os
import sys
import threading
import time
import traceback
import sqlite3

import paho.mqtt.client as mqtt

from client import run

mqtt_client = mqtt.Client("farm_client")

MQTT_SERVER = "mqtt"
HTTP_SERVER = "web"

db = sqlite3.connect(os.path.dirname(os.path.abspath(__file__)) + "/data.db")
db_curs = db.cursor()


def on_connect(client: mqtt.Client, userdata, flags, rc: int):
    print("Connected with result code " + str(rc))
    client.subscribe("farm/farm1")
    client.subscribe("farm/farm1/instants")
    client.subscribe("farm/farm1/ping")


def on_disconnect(client, userdata, rc: int):
    print("Disconnected with result code " + str(rc))


def on_message(client: mqtt.Client, userdata, msg: mqtt.MQTTMessage):
    try:
        data = msg.payload.decode("utf-8")
        if msg.topic == "farm/farm1/instants":
            try:
                commands = json.loads(data)
                for command in commands:
                    run.run_command(command)
            except Exception:
                print(data)
                traceback.print_exc()
        elif msg.topic == "farm/farm1/ping" and data == "ping":
            client.publish("farm/farm1/ping", "pong")
        else:
            print(data)
    except Exception:
        traceback.print_exc()


def send_logs(message):
    mqtt_client.publish("/farm/farm1/logs", message)


def connect():
    try:
        run.connect()
    except:
        print("Can't connect to serial port")
        traceback.print_exc()
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.on_disconnect = on_disconnect

    global MQTT_SERVER
    global HTTP_SERVER

    if len(sys.argv) > 1:
        MQTT_SERVER = sys.argv[1]
        HTTP_SERVER = sys.argv[1]

    mqtt_client.connect(MQTT_SERVER, 1883, 60)


def main_loop():
    while True:
        try:
            line = run.ser.readline()
            if line is not None or line is not "":
                run.gcode_interpreter(line)
            else:
                time.sleep(1)
            if run.parameters_change:
                update_db()
                run.parameters_change = False
        except Exception:
            time.sleep(1)


def init_db():
    try:
        db_curs.execute('''CREATE TABLE settings (param INT UNIQUE, value TEXT)''')
        for param in run.parameters:
            db_curs.execute('''INSERT INTO settings VALUES (?, ?)''',
                            (int(param), str(run.parameters[param])))
        db.commit()
    except:
        ""

    try:
        db_curs.execute('''CREATE TABLE event (id INT UNIQUE, name TEXT, cond TEXT, data TEXT)''')
    except:
        ""


def update_db():
    for param in run.parameters:
        db_curs.execute('''UPDATE settings SET value = ? WHERE param = ?''', (str(run.parameters[param]), int(param)))
    db.commit()


def main():
    print("Starting CERESPACE Client")
    connect()
    init_db()

    mqtt_client.loop_start()

    try:
        main_loop()
    except KeyboardInterrupt:
        print("Shutdown requested...exiting")
    except Exception:
        traceback.print_exc(file=sys.stdout)

    mqtt_client.loop_stop()
    db.close()
    sys.exit(0)


if __name__ == '__main__':
    main()
