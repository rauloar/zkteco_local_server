import sqlite3
from sys import stdout
import time
import logging
from logging.handlers import RotatingFileHandler
from requests import request
from zk import ZK
import pickledb


class DB:
    def __init__(self, path="database.db"):
        self.conn = sqlite3.connect(path)
        try:
            self.conn.execute("SELECT * FROM logs")
        except Exception as ex:
            if "no such table" in str(ex):
                self.conn.execute("CREATE TABLE logs (identifier VARCHAR (80), log_date VARCHAR (80), user INTEGER, "
                                  "verified INTEGER (1) DEFAULT 0);")
        finally:
            self.conn.commit()

    def insert(self, device, date, user, Verified=False):
        print("INSERT INTO logs VALUES ('{}','{}', {}, {})".format(str(device), str(date), int(user), int(Verified)))
        self.conn.execute(
            "INSERT INTO logs VALUES ('{}','{}', {}, {})".format(str(device), str(date), int(user), int(Verified)))
        self.conn.commit()

    def exist(self, device, date, user):
        for r in self.conn.execute("SELECT * FROM logs WHERE identifier=? AND log_date=? AND user=?",
                                   (str(device), str(date), int(user))):
            return True
        return False

    def verify(self, device, date, user):
        self.conn.execute(
            "UPDATE logs SET verified = 1 WHERE identifier=? AND log_date=? AND user=?", (str(device), str(date),
                                                                                          int(user)))
        self.conn.commit()

    def get_all_verified(self):
        return self.conn.execute("SELECT * FROM logs WHERE verified=1")

    def get_all_unverified(self):
        return self.conn.execute("SELECT * FROM logs WHERE verified=0")


def setup_logger(name, log_file, level=logging.INFO, formatter=None):
    if not formatter:
        formatter = logging.Formatter('%(asctime)s\t%(levelname)s\t%(message)s')
    handler = RotatingFileHandler(log_file, maxBytes=10000000, backupCount=50)
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.hasHandlers():
        logger.addHandler(handler)
    return logger


config = pickledb.load("config.json", False)
PUSH_URL = config.get("PUSH_URL") if bool(config.get("PUSH_URL")) else "http://zkteco.test/push"
print(f"Push url -> {PUSH_URL}")
PUSH_KEY = config.get("PUSH_KEY") if bool(config.get("PUSH_KEY")) else "123456789abcdef"
print(f"Push Key -> {PUSH_KEY}")
PUSH_FREQUENCY = config.get("PUSH_FREQUENCY") if bool(config.get("PUSH_FREQUENCY")) else 5
print(f"Push Frequency -> {PUSH_FREQUENCY}")
DEVICES = config.get("DEVICES") if bool(config.get("DEVICES")) else []
database = DB()
error_logger = setup_logger('error_logger', 'error.log', logging.ERROR)
info_logger = setup_logger('info_logger', 'logs.log')


def get_attendances(ip, port=4370, timeout=30, device_serial=None, clear_from_device_on_fetch=False):
    zk = ZK(ip, port=port, timeout=timeout)
    conn = None
    returning_attendance = []
    try:
        conn = zk.connect()
        x = conn.disable_device()
        info_logger.info("\t".join((device_serial, "Device Disable Attempted. Result:", str(x))))
        logging.info("\t".join((device_serial, "Device Disable Attempted. Result:", str(x))))
        attendances = conn.get_attendance()
        info_logger.info("\t".join((device_serial, "Attendances Fetched:", str(len(attendances)))))
        logging.info("\t".join((device_serial, "Attendances Fetched:", str(len(attendances)))))
        if len(attendances):
            for at in attendances:
                try:
                    if not database.exist(device_serial, at.timestamp.strftime("%Y-%m-%d %H:%M:%S"), at.user_id):
                        database.insert(device_serial, at.timestamp.strftime("%Y-%m-%d %H:%M:%S"), at.user_id)
                        returning_attendance.append(at)
                except:
                    error_logger.exception(
                        str(device_serial) + ' -> ' + str(ip) + ' exception when fetching from device...')
                    logging.error(str(device_serial) + ' -> ' + str(ip) + ' exception when fetching from device...')
                    raise Exception('Database error')

            if clear_from_device_on_fetch:
                x = conn.clear_attendance()
                info_logger.info("\t".join((device_serial, "Attendance Clear Attempted. Result:", str(x))))
                logging.info("\t".join((device_serial, "Attendance Clear Attempted. Result:", str(x))))
        x = conn.enable_device()
        info_logger.info("\t".join((device_serial, "Device Enable Attempted. Result:", str(x))))
        logging.info("\t".join((device_serial, "Device Enable Attempted. Result:", str(x))))
    except:
        error_logger.exception(str(device_serial) + ' -> ' + str(ip) + ' exception when fetching from device...')
        logging.error(str(device_serial) + ' -> ' + str(ip) + ' exception when fetching from device...')
        # raise Exception('Device fetch failed.')
    finally:
        if conn:
            conn.disconnect()
    return returning_attendance


def push_to_server(device_serial, user_id, log_time):
    data = {
        'push_key': PUSH_KEY,
        'user': user_id,
        'date': log_time,
        'identifier': device_serial,
    }
    try:
        response = request("POST", PUSH_URL, data=data)
        if response.status_code == 200:
            if response.text != "accapted" and len(response.text) > 1:
                error_logger.error(
                    '\t'.join(
                        ['Error during API Call.', str(user_id), str(log_time), str(device_serial), response.text]))
                logging.error(
                    '\t'.join(
                        ['Error during API Call.', str(user_id), str(log_time), str(device_serial), response.text]))
            else:
                database.verify(device_serial, log_time, user_id)
        else:
            error_str = response.text
            error_logger.error(
                '\t'.join(['Error during API Call.', str(user_id), str(log_time), str(device_serial), error_str]))
            logging.error(
                '\t'.join(['Error during API Call.', str(user_id), str(log_time), str(device_serial), error_str]))
    except:
        error_logger.exception('Error during API Call')
        logging.error('Error during API Call')
        # raise Exception("Remote server error")


def get_serial(ip, port=4370, timeout=30):
    zk = ZK(ip, port=port, timeout=timeout)
    conn = None
    serial = None
    try:
        conn = zk.connect()
        serial = conn.get_serialnumber()
    except:
        error_logger.exception(str(ip) + ' exception when fetching serial from device...')
        logging.error(str(ip) + ' exception when fetching serial from device...')
        # raise Exception('Device serial fetch failed.')
    finally:
        if conn:
            conn.disconnect()
    return serial


def main():
    if DEVICES is None:
        return
    for index, device in enumerate(DEVICES):
        ip = device["ip"]
        keys = device.keys()
        port = int(device["port"]) if "port" in keys else 4370
        timeout = int(device["timeout"]) if "timeout" in keys else 30
        clear_from_device_on_fetch = bool(
            device["clear_from_device_on_fetch"]) if "clear_from_device_on_fetch" in keys else False

        device_serial = get_serial(ip, port, timeout)

        attendances = get_attendances(ip, port, timeout, device_serial, clear_from_device_on_fetch)
        for attendance in attendances:
            push_to_server(device_serial, user_id=attendance.user_id,
                           log_time=attendance.timestamp.strftime("%Y-%m-%d %H:%M:%S"), )


def push_unverified():
    for at in database.get_all_unverified():
        push_to_server(device_serial=at[0], log_time=at[1], user_id=at[2])


def start():
    try:
        f = open("last.txt")
        LAST = int(f.readline())
        f.close()
    except:
        LAST = int(time.time())

    while True:
        if LAST + (PUSH_FREQUENCY * 60) <= int(time.time()):
            print('\r')
            main()
            push_unverified()
            LAST = int(time.time())
            try:
                f = open("last.txt", "w")
                f.write(str(LAST))
                f.close()
            except:
                error_logger.exception("saving last sync error")
                logging.error("saving last sync error")

        else:
            second = (LAST + (PUSH_FREQUENCY * 60)) - int(time.time())
            munite = second // 60
            second = second - (munite * 60)
            stdout.write('\r' + f"Next Sync remaining {munite}m {second}s  ")
        time.sleep(1)

try:
    start()
except:
    error_logger.exception("Main error")
