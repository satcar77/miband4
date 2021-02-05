import sys,os,time,random
import logging
from bluepy.btle import Peripheral, DefaultDelegate, ADDR_TYPE_RANDOM,ADDR_TYPE_PUBLIC, BTLEException
from constants import UUIDS, AUTH_STATES, ALERT_TYPES, QUEUE_TYPES, MUSICSTATE, BYTEPATTERNS
import struct
from datetime import datetime, timedelta
from Crypto.Cipher import AES
from datetime import datetime
try:
    import zlib
except ImportError:
    print("zlib module not found. Updating watchface/firmware requires zlib")
try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty
try:
    xrange
except NameError:
    xrange = range


class Delegate(DefaultDelegate):
    def __init__(self, device):
        DefaultDelegate.__init__(self)
        self.device = device
        self.pkg = 0


    def handleNotification(self, hnd, data):
        if hnd == self.device._char_auth.getHandle():
            if data[:3] == b'\x10\x01\x01':
                self.device._req_rdn()
            elif data[:3] == b'\x10\x01\x04':
                self.device.state = AUTH_STATES.KEY_SENDING_FAILED
            elif data[:3] == b'\x10\x02\x01':
                # 16 bytes
                random_nr = data[3:]
                self.device._send_enc_rdn(random_nr)
            elif data[:3] == b'\x10\x02\x04':
                self.device.state = AUTH_STATES.REQUEST_RN_ERROR
            elif data[:3] == b'\x10\x03\x01':
                self.device.state = AUTH_STATES.AUTH_OK
            elif data[:3] == b'\x10\x03\x04':
                self.device.status = AUTH_STATES.ENCRIPTION_KEY_FAILED
                self.device._send_key()
            else:
                self.device.state = AUTH_STATES.AUTH_FAILED
        elif hnd == self.device._char_heart_measure.getHandle():
            self.device.queue.put((QUEUE_TYPES.HEART, data))
        elif hnd == 0x38:
            if len(data) == 20 and struct.unpack('b', data[0:1])[0] == 1:
                # This may no longer be valid
                self.device.queue.put((QUEUE_TYPES.RAW_GYRO, data))
            elif len(data) == 16:
                self.device.queue.put((QUEUE_TYPES.RAW_HEART, data))
        elif hnd == self.device._char_hz.getHandle():
            if len(data) == 20 and struct.unpack('b', data[0:1])[0] == 1:
                self.device.queue.put((QUEUE_TYPES.RAW_GYRO, data))
            elif len(data) == 11:
                #print("Unknown data: {}".format(bytes.hex(data, " ")))
                # Seems to be a counter of the time the gyro is enabled.
                ...
            elif len(data) == 8:
                self.device.queue.put((QUEUE_TYPES.AVG_GYRO, data))
        # The fetch characteristic controls the communication with the activity characteristic.
        elif hnd == self.device._char_fetch.getHandle():
            if data[:3] == b'\x10\x01\x01':
                # get timestamp from what date the data actually is received
                year = struct.unpack("<H", data[7:9])[0]
                month = struct.unpack("b", data[9:10])[0]
                day = struct.unpack("b", data[10:11])[0]
                hour = struct.unpack("b", data[11:12])[0]
                minute = struct.unpack("b", data[12:13])[0]
                self.device.first_timestamp = datetime(year, month, day, hour, minute)
                print("Fetch data from {}-{}-{} {}:{}".format(year, month, day, hour, minute))
                self.pkg = 0 #reset the packing index
                self.device._char_fetch.write(b'\x02', False)
            elif data[:3] == b'\x10\x02\x01':
                if self.device.last_timestamp > self.device.end_timestamp - timedelta(minutes=1):
                    print("Finished fetching")
                    return
                print("Trigger more communication")
                time.sleep(1)
                t = self.device.last_timestamp + timedelta(minutes=1)
                self.device.start_get_previews_data(t)

            elif data[:3] == b'\x10\x02\x04':
                print("No more activity fetch possible")
                return
            else:
                print("Unexpected data on handle " + str(hnd) + ": " + str(data))
                return
        elif hnd == self.device._char_activity.getHandle():
            if len(data) % 4 == 1:
                self.pkg += 1
                i = 1
                while i < len(data):
                    index = int(self.pkg) * 4 + (i - 1) / 4
                    timestamp = self.device.first_timestamp + timedelta(minutes=index)
                    self.device.last_timestamp = timestamp
                    category = struct.unpack("<B", data[i:i + 1])[0]
                    intensity = struct.unpack("B", data[i + 1:i + 2])[0]
                    steps = struct.unpack("B", data[i + 2:i + 3])[0]
                    heart_rate = struct.unpack("B", data[i + 3:i + 4])[0]
                    if timestamp < self.device.end_timestamp:
                        self.device.activity_callback(timestamp,category,intensity,steps,heart_rate)
                    i += 4

        #music controls
        elif(hnd == 74):
            if(data[1:] == b'\xe0'):
                self.device.setMusic()
                if(self.device._default_music_focus_in):
                    self.device._default_music_focus_in()
            elif(data[1:]==b'\xe1'):
                if(self.device._default_music_focus_out):
                    self.device._default_music_focus_out()
            elif(data[1:]==b'\x00'):
                if(self.device._default_music_play):
                    self.device._default_music_play()
            elif(data[1:]==b'\x01'):
                if(self.device._default_music_pause):
                    self.device._default_music_pause()
            elif(data[1:]==b'\x03'):
                if(self.device._default_music_forward):
                    self.device._default_music_forward()
            elif(data[1:]==b'\x04'):
                if(self.device._default_music_back):
                    self.device._default_music_back()
            elif(data[1:]==b'\x05'):
                if(self.device._default_music_vup):
                    self.device._default_music_vup()
            elif(data[1:]==b'\x06'):
                if(self.device._default_music_vdown):
                    self.device._default_music_vdown()


class miband(Peripheral):
    _send_rnd_cmd = struct.pack('<2s', b'\x02\x00')
    _send_enc_key = struct.pack('<2s', b'\x03\x00')
    def __init__(self, mac_address,key=None, timeout=0.5, debug=False):
        FORMAT = '%(asctime)-15s %(name)s (%(levelname)s) > %(message)s'
        logging.basicConfig(format=FORMAT)
        log_level = logging.WARNING if not debug else logging.DEBUG
        self._log = logging.getLogger(self.__class__.__name__)
        self._log.setLevel(log_level)


        self._log.info('Connecting to ' + mac_address)
        Peripheral.__init__(self, mac_address, addrType=ADDR_TYPE_PUBLIC)
        self._log.info('Connected')
        if not key:
            self.setSecurityLevel(level = "medium")
        self.timeout = timeout
        self.mac_address = mac_address
        self.state = None
        self.heart_measure_callback = None
        self.heart_raw_callback = None
        self.gyro_raw_callback = None
        self.gyro_avg_callback = None
        self.gyro_started_flag = False

        self.auth_key = key
        self.queue = Queue()
        self.write_queue = Queue()
        self.svc_1 = self.getServiceByUUID(UUIDS.SERVICE_MIBAND1)
        self.svc_2 = self.getServiceByUUID(UUIDS.SERVICE_MIBAND2)
        self.svc_heart = self.getServiceByUUID(UUIDS.SERVICE_HEART_RATE)
        self.svc_alert = self.getServiceByUUID(UUIDS.SERVICE_ALERT)

        self._char_auth = self.svc_2.getCharacteristics(UUIDS.CHARACTERISTIC_AUTH)[0]
        self._desc_auth = self._char_auth.getDescriptors(forUUID=UUIDS.NOTIFICATION_DESCRIPTOR)[0]

        self._char_heart_ctrl = self.svc_heart.getCharacteristics(UUIDS.CHARACTERISTIC_HEART_RATE_CONTROL)[0]
        self._char_heart_measure = self.svc_heart.getCharacteristics(UUIDS.CHARACTERISTIC_HEART_RATE_MEASURE)[0]
        self._heart_measure_handle = self._char_heart_measure.getHandle() + 1

        self._char_alert = self.svc_alert.getCharacteristics(UUIDS.CHARACTERISTIC_ALERT)[0]

        # Recorded information
        self._char_fetch = self.getCharacteristics(uuid=UUIDS.CHARACTERISTIC_FETCH)[0]
        self._desc_fetch = self._char_fetch.getDescriptors(forUUID=UUIDS.NOTIFICATION_DESCRIPTOR)[0]
        self._char_activity = self.getCharacteristics(uuid=UUIDS.CHARACTERISTIC_ACTIVITY_DATA)[0]
        self._desc_activity = self._char_activity.getDescriptors(forUUID=UUIDS.NOTIFICATION_DESCRIPTOR)[0]

        #chunked transfer and music
        self._char_chunked = self.svc_1.getCharacteristics(UUIDS.CHARACTERISTIC_CHUNKED_TRANSFER)[0]
        self._char_music_notif= self.svc_1.getCharacteristics(UUIDS.CHARACTERISTIC_MUSIC_NOTIFICATION)[0]
        self._desc_music_notif = self._char_music_notif.getDescriptors(forUUID=UUIDS.NOTIFICATION_DESCRIPTOR)[0]

        # Sensor characteristics and handles/descriptors
        self._char_hz = self.svc_1.getCharacteristics(UUIDS.CHARACTERISTIC_HZ)[0]
        self._hz_handle = self._char_hz.getHandle() + 1

        self._char_sensor = self.svc_1.getCharacteristics(UUIDS.CHARACTERISTIC_SENSOR)[0]
        self._sensor_handle = self._char_sensor.getHandle() + 1

        self._char_steps = self.svc_1.getCharacteristics(UUIDS.CHARACTERISTIC_STEPS)[0]
        self._steps_handle = self._char_steps.getHandle() + 1


        self._auth_notif(True)
        self.enable_music()
        self.activity_notif_enabled = False
        self.waitForNotifications(0.1)
        self.setDelegate( Delegate(self) )


    def generateAuthKey(self):
        if(self.authKey):
            return struct.pack('<18s',b'\x01\x00'+ self.auth_key)


    def _send_key(self):
        self._log.info("Sending Key...")
        self._char_auth.write(self._send_my_key)
        self.waitForNotifications(self.timeout)


    def _auth_notif(self, enabled):
        if enabled:
            self._log.info("Enabling Auth Service notifications status...")
            self._desc_auth.write(b"\x01\x00", True)
        elif not enabled:
            self._log.info("Disabling Auth Service notifications status...")
            self._desc_auth.write(b"\x00\x00", True)
        else:
            self._log.error("Something went wrong while changing the Auth Service notifications status...")


    def _auth_previews_data_notif(self, enabled):
        if enabled:
            self._log.info("Enabling Fetch Char notifications status...")
            self._desc_fetch.write(b"\x01\x00", True)
            self._log.info("Enabling Activity Char notifications status...")
            self._desc_activity.write(b"\x01\x00", True)
            self.activity_notif_enabled = True
        else:
            self._log.info("Disabling Fetch Char notifications status...")
            self._desc_fetch.write(b"\x00\x00", True)
            self._log.info("Disabling Activity Char notifications status...")
            self._desc_activity.write(b"\x00\x00", True)
            self.activity_notif_enabled = False


    def initialize(self):
        self._req_rdn()

        while True:
            self.waitForNotifications(0.1)
            if self.state == AUTH_STATES.AUTH_OK:
                self._log.info('Initialized')
                self._auth_notif(False)
                return True
            elif self.state is None:
                continue

            self._log.error(self.state)
            return False


    def _req_rdn(self):
        self._log.info("Requesting random number...")
        self._char_auth.write(self._send_rnd_cmd)
        self.waitForNotifications(self.timeout)


    def _send_enc_rdn(self, data):
        self._log.info("Sending encrypted random number")
        cmd = self._send_enc_key + self._encrypt(data)
        send_cmd = struct.pack('<18s', cmd)
        self._char_auth.write(send_cmd)
        self.waitForNotifications(self.timeout)


    def _encrypt(self, message):
        aes = AES.new(self.auth_key, AES.MODE_ECB)
        return aes.encrypt(message)


    def _get_from_queue(self, _type):
        try:
            res = self.queue.get(False)
        except Empty:
            return None
        if res[0] != _type:
            self.queue.put(res)
            return None
        return res[1]


    def _parse_queue(self):
        while True:
            try:
                res = self.queue.get(False)
                _type = res[0]
                if self.heart_measure_callback and _type == QUEUE_TYPES.HEART:
                    self.heart_measure_callback(struct.unpack('bb', res[1])[1])
                elif self.heart_raw_callback and _type == QUEUE_TYPES.RAW_HEART:
                    self.heart_raw_callback(self._parse_raw_heart(res[1]))
                elif self.gyro_raw_callback and _type == QUEUE_TYPES.RAW_GYRO:
                    self.gyro_raw_callback(self._parse_raw_gyro(res[1]))
                elif self.gyro_avg_callback and _type == QUEUE_TYPES.AVG_GYRO:
                    self.gyro_avg_callback(self._parse_avg_gyro(res[1]))
            except Empty:
                break


    def send_custom_alert(self, type, phone, msg):
        if type == 5:
            base_value = '\x05\x01'
        elif type == 4:
            base_value = '\x04\x01'
        elif type == 3:
                base_value = '\x03\x01'
        elif type == 1:
            base_value = '\x01\x01'
        svc = self.getServiceByUUID(UUIDS.SERVICE_ALERT_NOTIFICATION)
        char = svc.getCharacteristics(UUIDS.CHARACTERISTIC_CUSTOM_ALERT)[0]
        # 3 new lines: space for the icon, two spaces for the time HH:MM
        text = base_value+phone+'\x0a\x0a\x0a'+msg.replace('\\n','\n')
        char.write(bytes(text,'utf-8'), withResponse=True)


    def get_steps(self):
        char = self.svc_1.getCharacteristics(UUIDS.CHARACTERISTIC_STEPS)[0]
        a = char.read()
        steps = struct.unpack('h', a[1:3])[0] if len(a) >= 3 else None
        meters = struct.unpack('h', a[5:7])[0] if len(a) >= 7 else None
        fat_burned = struct.unpack('h', a[2:4])[0] if len(a) >= 4 else None
        # why only 1 byte??
        calories = struct.unpack('b', a[9:10])[0] if len(a) >= 10 else None
        return {
            "steps": steps,
            "meters": meters,
            "fat_burned": fat_burned,
            "calories": calories
        }


    def _parse_raw_gyro(self, bytes):
        gyro_raw_data_list = []
        for i in range(2, 20, 6):
            gyro_raw_data = struct.unpack("3h", bytes[i:(i+6)])
            gyro_dict = {
                'gyro_raw_x': gyro_raw_data[0],
                'gyro_raw_y': gyro_raw_data[1],
                'gyro_raw_z': gyro_raw_data[2]
            }
            gyro_raw_data_list.append(gyro_dict)
        return gyro_raw_data_list


    def _parse_avg_gyro(self, bytes):
        gyro_avg_data = struct.unpack('<b3h', bytes[1:])
        gyro_dict = {
            'gyro_time': gyro_avg_data[0],
            'gyro_avg_x': gyro_avg_data[1],
            'gyro_avg_y': gyro_avg_data[2],
            'gyro_avg_z': gyro_avg_data[3]
        }
        return gyro_dict


    def _parse_raw_heart(self, bytes):
        res = struct.unpack('HHHHHHH', bytes[2:])
        return res


    @staticmethod
    def _parse_date(bytes):
        year = struct.unpack('h', bytes[0:2])[0] if len(bytes) >= 2 else None
        month = struct.unpack('b', bytes[2:3])[0] if len(bytes) >= 3 else None
        day = struct.unpack('b', bytes[3:4])[0] if len(bytes) >= 4 else None
        hours = struct.unpack('b', bytes[4:5])[0] if len(bytes) >= 5 else None
        minutes = struct.unpack('b', bytes[5:6])[0] if len(bytes) >= 6 else None
        seconds = struct.unpack('b', bytes[6:7])[0] if len(bytes) >= 7 else None
        day_of_week = struct.unpack('b', bytes[7:8])[0] if len(bytes) >= 8 else None
        fractions256 = struct.unpack('b', bytes[8:9])[0] if len(bytes) >= 9 else None

        return {"date": datetime(*(year, month, day, hours, minutes, seconds)), "day_of_week": day_of_week, "fractions256": fractions256}


    @staticmethod
    def create_date_data(date):
        data = struct.pack( 'hbbbbbbbxx', date.year, date.month, date.day, date.hour, date.minute, date.second, date.weekday(), 0 )
        return data


    def _parse_battery_response(self, bytes):
        level = struct.unpack('b', bytes[1:2])[0] if len(bytes) >= 2 else None
        last_level = struct.unpack('b', bytes[19:20])[0] if len(bytes) >= 20 else None
        status = 'normal' if struct.unpack('b', bytes[2:3])[0] == b'0' else "charging"
        datetime_last_charge = self._parse_date(bytes[11:18])
        datetime_last_off = self._parse_date(bytes[3:10])

        res = {
            "status": status,
            "level": level,
            "last_level": last_level,
            "last_level": last_level,
            "last_charge": datetime_last_charge,
            "last_off": datetime_last_off
        }
        return res


    def get_battery_info(self):
        char = self.svc_1.getCharacteristics(UUIDS.CHARACTERISTIC_BATTERY)[0]
        return self._parse_battery_response(char.read())


    def get_current_time(self):
        char = self.svc_1.getCharacteristics(UUIDS.CHARACTERISTIC_CURRENT_TIME)[0]
        return self._parse_date(char.read()[0:9])


    def get_revision(self):
        svc = self.getServiceByUUID(UUIDS.SERVICE_DEVICE_INFO)
        char = svc.getCharacteristics(UUIDS.CHARACTERISTIC_REVISION)[0]
        data = char.read()
        return data.decode('utf-8')


    def get_hrdw_revision(self):
        svc = self.getServiceByUUID(UUIDS.SERVICE_DEVICE_INFO)
        char = svc.getCharacteristics(UUIDS.CHARACTERISTIC_HRDW_REVISION)[0]
        data = char.read()
        return data.decode('utf-8')


    def set_encoding(self, encoding="en_US"):
        char = self.svc_1.getCharacteristics(UUIDS.CHARACTERISTIC_CONFIGURATION)[0]
        packet = struct.pack('5s', encoding)
        packet = b'\x06\x17\x00' + packet
        return char.write(packet)


    def set_heart_monitor_sleep_support(self, enabled=True, measure_minute_interval=1):
        char_m = self.svc_heart.getCharacteristics(UUIDS.CHARACTERISTIC_HEART_RATE_MEASURE)[0]
        char_d = char_m.getDescriptors(forUUID=UUIDS.NOTIFICATION_DESCRIPTOR)[0]
        char_d.write(b'\x01\x00', True)
        self._char_heart_ctrl.write(b'\x15\x00\x00', True)
        # measure interval set to off
        self._char_heart_ctrl.write(b'\x14\x00', True)
        if enabled:
            self._char_heart_ctrl.write(b'\x15\x00\x01', True)
            # measure interval set
            self._char_heart_ctrl.write(b'\x14' + str(measure_minute_interval).encode(), True)
        char_d.write(b'\x00\x00', True)


    def _enable_fw_notification(self):
        svc = self.getServiceByUUID(UUIDS.SERVICE_DFU_FIRMWARE)
        char = svc.getCharacteristics(UUIDS.CHARACTERISTIC_DFU_FIRMWARE)[0]
        des = char.getDescriptors(forUUID = UUIDS.NOTIFICATION_DESCRIPTOR)[0]
        des.write(b"\x01\x00", True)


    def get_serial(self):
        svc = self.getServiceByUUID(UUIDS.SERVICE_DEVICE_INFO)
        char = svc.getCharacteristics(UUIDS.CHARACTERISTIC_SERIAL)[0]
        data = char.read()
        serial = struct.unpack('12s', data[-12:])[0] if len(data) == 12 else None
        return serial.decode('utf-8')


    def send_alert(self, _type):
        svc = self.getServiceByUUID(UUIDS.SERVICE_ALERT)
        char = svc.getCharacteristics(UUIDS.CHARACTERISTIC_ALERT)[0]
        char.write(_type)


    def set_current_time(self, date):
        char = self.svc_1.getCharacteristics(UUIDS.CHARACTERISTIC_CURRENT_TIME)[0]
        return char.write(self.create_date_data(date), True)


    def set_heart_monitor_sleep_support(self, enabled=True, measure_minute_interval=1):
        char_m = self.svc_heart.getCharacteristics(UUIDS.CHARACTERISTIC_HEART_RATE_MEASURE)[0]
        char_d = char_m.getDescriptors(forUUID=UUIDS.NOTIFICATION_DESCRIPTOR)[0]
        char_d.write(b'\x01\x00', True)
        self._char_heart_ctrl.write(b'\x15\x00\x00', True)
        # measure interval set to off
        self._char_heart_ctrl.write(b'\x14\x00', True)
        if enabled:
            self._char_heart_ctrl.write(b'\x15\x00\x01', True)
            # measure interval set
            self._char_heart_ctrl.write(b'\x14' + str(measure_minute_interval).encode(), True)
        char_d.write(b'\x00\x00', True)


    def dfuUpdate(self,fileName):
        print('Update Watchface/Firmware')
        svc = self.getServiceByUUID(UUIDS.SERVICE_DFU_FIRMWARE)
        char = svc.getCharacteristics(UUIDS.CHARACTERISTIC_DFU_FIRMWARE)[0]
        char_write = svc.getCharacteristics(UUIDS.CHARACTERISTIC_DFU_FIRMWARE_WRITE)[0]
        # self._enable_fw_notification()
        # self.setDelegate(TestDelegate(self))
        extension = os.path.splitext(fileName)[1][1:]
        fileSize = os.path.getsize(fileName)
        # calculating crc checksum of firmware
        #crc32
        crc=0xFFFF
        with open(fileName,"rb") as f:
            crc = zlib.crc32(f.read())
        print('CRC32 Value is-->', crc)
        # input('Press Enter to Continue')
        payload = b'\x01\x08'+struct.pack("<I",fileSize)[:-1]+b'\x00'+struct.pack("<I",crc)
        char.write(payload,withResponse=True)
        self.waitForNotifications(2)
        char.write(b'\x03\x01',withResponse=True)
        with open(fileName,"rb") as f:
            while True:
                c = f.read(20) #takes 20 bytes 
                if not c:
                    print ("Bytes written successfully. Wait till sync finishes")
                    break
                char_write.write(c)
        # # after update is done send these values
        char.write(b'\x00', withResponse=True)
        self.waitForNotifications(2)
        char.write(b'\x04', withResponse=True)
        self.waitForNotifications(2)
        if extension.lower() == "fw":
            self.waitForNotifications(0.5)
            char.write(b'\x05', withResponse=True)
        print('Update Complete')
        input('Press Enter to Continue')


    def get_heart_rate_one_time(self):
        # stop continous
        self._char_heart_ctrl.write(b'\x15\x01\x00', True)
        # stop manual
        self._char_heart_ctrl.write(b'\x15\x02\x00', True)
        # start manual
        self._char_heart_ctrl.write(b'\x15\x02\x01', True)
        res = None
        while not res:
            self.waitForNotifications(self.timeout)
            res = self._get_from_queue(QUEUE_TYPES.HEART)

        rate = struct.unpack('bb', res)[1]
        return rate


    def start_heart_rate_realtime(self, heart_measure_callback):
        self.heart_measure_callback = heart_measure_callback
        self.send_heart_measure_start()
        heartbeat_time = time.time()
        while True:
            self.wait_for_notifications_with_queued_writes(0.5)
            self._parse_queue()
            if (time.time() - heartbeat_time) >= 12:
                heartbeat_time = time.time()
                self.send_heart_measure_keepalive()


    def stop_realtime(self):
        char_m = self.svc_heart.getCharacteristics(UUIDS.CHARACTERISTIC_HEART_RATE_MEASURE)[0]
        char_d = char_m.getDescriptors(forUUID=UUIDS.NOTIFICATION_DESCRIPTOR)[0]
        char_ctrl = self.svc_heart.getCharacteristics(UUIDS.CHARACTERISTIC_HEART_RATE_CONTROL)[0]

        char_sensor1 = self.svc_1.getCharacteristics(UUIDS.CHARACTERISTIC_HZ)[0]
        char_sens_d1 = char_sensor1.getDescriptors(forUUID=UUIDS.NOTIFICATION_DESCRIPTOR)[0]

        char_sensor2 = self.svc_1.getCharacteristics(UUIDS.CHARACTERISTIC_SENSOR)[0]

        # stop heart monitor continues
        char_ctrl.write(b'\x15\x01\x00', True)
        char_ctrl.write(b'\x15\x01\x00', True)
        # IMO: stop heart monitor notifications
        char_d.write(b'\x00\x00', True)
        # WTF
        char_sensor2.write(b'\x03')
        # IMO: stop notifications from sensors
        char_sens_d1.write(b'\x00\x00', True)

        self.heart_measure_callback = None
        self.heart_raw_callback = None
        self.gyro_raw_callback = None


    def start_get_previews_data(self, start_timestamp):
        if not self.activity_notif_enabled:
            self._auth_previews_data_notif(True)
            self.waitForNotifications(0.1)
        print("Trigger activity communication")
        year = struct.pack("<H", start_timestamp.year)
        month = struct.pack("b", start_timestamp.month)
        day = struct.pack("b", start_timestamp.day)
        hour = struct.pack("b", start_timestamp.hour)
        minute = struct.pack("b", start_timestamp.minute)
        ts = year + month + day + hour + minute
        char = self.svc_1.getCharacteristics(UUIDS.CHARACTERISTIC_CURRENT_TIME)[0]
        utc_offset = char.read()[9:11]
        trigger = b'\x01\x01' + ts + utc_offset
        self._char_fetch.write(trigger, False)
        self.active = True
    

    def get_activity_betwn_intervals(self,start_timestamp, end_timestamp, callback ):
        self.end_timestamp = end_timestamp
        self.start_get_previews_data(start_timestamp)
        self.activity_callback = callback


    def enable_music(self):
        self._desc_music_notif.write(b'\x01\x00')


    def writeChunked(self,type,data):
        MAX_CHUNKLENGTH = 17
        remaining = len(data)
        count =0
        while(remaining > 0):
            copybytes = min(remaining,MAX_CHUNKLENGTH)
            chunk=b''
            flag = 0
            if(remaining <= MAX_CHUNKLENGTH):
                flag |= 0x80
                if(count == 0):
                    flag |= 0x40
            elif(count>0):
                flag |= 0x40

            chunk+=b'\x00'
            chunk+= bytes([flag|type])
            chunk+= bytes([count & 0xff])
            chunk+= data[(count * MAX_CHUNKLENGTH):(count * MAX_CHUNKLENGTH)+copybytes]
            count+=1
            self._char_chunked.write(chunk)
            remaining-=copybytes


    def setTrack(self,track,state):
        self.track = track
        self.pp_state = state
        self.setMusic()


    def setMusicCallback(self,play=None,pause=None,forward=None,backward=None,volumeup=None,volumedown=None,focusin=None,focusout=None):
        if play is not None:
            self._default_music_play = play
        if pause is not None:
            self._default_music_pause = pause
        if forward is not None:
            self._default_music_forward = forward
        if backward is not None:
            self._default_music_back = backward
        if volumedown is not None:
            self._default_music_vdown = volumedown
        if volumeup is not None:
            self._default_music_vup = volumeup
        if focusin is not None:
            self._default_music_focus_in = focusin
        if focusout is not None:
            self._default_music_focus_out = focusout


    def setMusic(self):
        track = self.track
        state = self.pp_state
        # st=b"\x01\x00\x01\x00\x00\x00\x01\x00"
        #self.writeChunked(3,st)
        flag = 0x00
        flag |=0x01
        length =8
        if(len(track)>0):
            length+=len(track.encode('utf-8'))
            flag |=0x0e
        buf = bytes([flag])+bytes([state])+bytes([1,0,0,0])+bytes([1,0])
        if(len(track)>0):
            buf+=bytes(track,'utf-8')
            buf+=bytes([0])
        self.writeChunked(3,buf)


    def write_cmd(self, characteristic, data, response=False, queued=False):
        if queued:
            self.write_queue.put(['write_cmd', [characteristic, data, response]])
        else:
            characteristic.write(data, withResponse=response)


    def write_req(self, handle, data, response=True, queued=False):
        if queued:
            self.write_queue.put(['write_req', [handle, data, response]])
        else:
            self.writeCharacteristic(handle, data, withResponse=response)


    def process_write_queue(self):
        while True:
            try:
                res = self.write_queue.get(False)
                _type = res[0]
                _payload = res[1]
                if _type == 'write_cmd':
                    self.write_cmd(_payload[0], _payload[1], response=_payload[2])
                elif _type == 'write_req':
                    self.write_req(_payload[0], _payload[1], response=_payload[2])
            except Empty:
                break


    def wait_for_notifications_with_queued_writes(self, wait):
        self.process_write_queue()
        self.waitForNotifications(wait)


    def vibrate(self, value):
        # Set queued to True when multithreading
        #  Otherwise waitForNotifications will received an invalid 'wr' response

        if value == 255 or value == 0:
            # '255' means 'continuous vibration' 
            #   I've arbitrarily assigned the otherwise pointless value of '0' to indicate 'stop_vibration'
            #   These modes do not require pulse timing to avoid strange behavior
            self.write_cmd(self._char_alert, BYTEPATTERNS.vibration(value), queued=True)
        else:
            # A value of '150' will vibrate for ~200ms, hence vibration_scaler.
            #   This isn't exact however, but does leave a ~5ms gap between pulses.
            #   A scaler any lower causes the pulses to be indistinguishable from each other to a human
            #   I considered making this function accept a desired amount of vibration time in ms, 
            #   however it was fiddly and I couldn't get it right.  More work could be done here.
            vibration_scaler = 0.75  
            ms = round(value / vibration_scaler)
            vibration_duration = ms / 1000
            self.write_cmd(self._char_alert, BYTEPATTERNS.vibration(value), queued=False)
            time.sleep(vibration_duration)


    def generate_random_vibration_pattern(self, pulse_count):
        #pulse_duration_range and pulse_interval_range_ms are arbitrary
        pulse_duration_range = {
                                    'low': 60, 
                                    'high': 100
                                }  
        pulse_interval_range_ms = {
                                    'low': 100, 
                                    'high': 800
                                }

        output_pulse_pattern = []
        for _ in range(pulse_count):
            pulse_duration = random.randrange(pulse_duration_range['low'], pulse_duration_range['high'])
            pulse_interval = random.randrange(pulse_interval_range_ms['low'], pulse_interval_range_ms['high'])/1000
            output_pulse_pattern.append([pulse_duration, pulse_interval])
        return output_pulse_pattern


    def vibrate_random(self, duration_seconds):
        print("Sending random vibration...")
        duration_start = time.time()

        pattern_length = 20  #This value is arbitrary

        pulse_pattern = self.generate_random_vibration_pattern(pattern_length)

        while True:
            if (time.time() - duration_start) >= duration_seconds:
                print ("Stopping vibration")
                self.vibrate(0)
                break
            else:
                for pattern in pulse_pattern:
                    if (time.time() - duration_start) >= duration_seconds:
                        break
                    vibrate_ms = pattern[0]
                    vibro_delay = pattern[1]
                    self.vibrate(vibrate_ms)
                    time.sleep(vibro_delay)


    def vibrate_pattern(self, duration_seconds):
        print("Sending vibration...")
        duration_start = time.time()

        #This pattern is an example.
        pulse_pattern = [[30, 0.01], [60, 0.01], [90, 0.01], [120, 0.01], [150, 0.01], [180, 0.01]]

        while True:
            if (time.time() - duration_start) >= duration_seconds:
                print ("Stopping vibration")
                self.vibrate(0)
                break
            else:
                for pattern in pulse_pattern:
                    if (time.time() - duration_start) >= duration_seconds:
                        break
                    vibrate_ms = pattern[0]
                    vibro_delay = pattern[1]
                    self.vibrate(vibrate_ms)
                    time.sleep(vibro_delay)


    def vibrate_rolling(self, duration_seconds):
        print("Sending rolling vibration...")

        duration_start = time.time()
        
        while True:
            if (time.time() - duration_start) >= duration_seconds:
                print ("Stopping vibration")
                self.vibrate(0)
                break
            else:
                for x in range(10):
                    for x in range(20, 40, 1):
                        self.vibrate(x)
                    for x in range(40, 20, -1):
                        self.vibrate(x)


    def send_gyro_start(self, sensitivity):
        if not self.gyro_started_flag:
            self._log.info("Starting gyro...")
            self.write_req(self._sensor_handle, BYTEPATTERNS.start)
            self.write_req(self._steps_handle, BYTEPATTERNS.start)
            self.write_req(self._hz_handle, BYTEPATTERNS.start)
            self.gyro_started_flag = True
        self.write_cmd(self._char_sensor, BYTEPATTERNS.gyro_start(sensitivity))
        self.write_req(self._sensor_handle, BYTEPATTERNS.stop)
        self.write_cmd(self._char_sensor, b'\x02')


    def send_heart_measure_start(self):
        self._log.info("Starting heart measure...")
        self.write_cmd(self._char_heart_ctrl, BYTEPATTERNS.stop_heart_measure_manual, response=True)
        self.write_cmd(self._char_heart_ctrl, BYTEPATTERNS.stop_heart_measure_continues, response=True)
        self.write_req(self._heart_measure_handle, BYTEPATTERNS.start)
        self.write_cmd(self._char_heart_ctrl, BYTEPATTERNS.start_heart_measure_continues, response=True)


    def send_heart_measure_keepalive(self):
        self.write_cmd(self._char_heart_ctrl, BYTEPATTERNS.heart_measure_keepalive, response=True)


    def start_heart_and_gyro_realtime(self, sensitivity, callback):
        self.heart_measure_callback = callback
        self.gyro_raw_callback = callback

        self.send_gyro_start(sensitivity)
        self.send_heart_measure_start()

        heartbeat_time = time.time()
        while True:
            self.wait_for_notifications_with_queued_writes(0.5)
            self._parse_queue()
            if (time.time() - heartbeat_time) >= 12:
                heartbeat_time = time.time()
                self.send_heart_measure_keepalive()
                self.send_gyro_start(sensitivity)

    def start_gyro_realtime(self, sensitivity, callback, avg=False):
        if avg:
            self.gyro_avg_callback = callback
        else:
            self.gyro_raw_callback = callback

        self.send_gyro_start(sensitivity)

        heartbeat_time = time.time()
        while True:
            self.wait_for_notifications_with_queued_writes(0.5)
            self._parse_queue()
            if (time.time() - heartbeat_time) >= 60:
                heartbeat_time = time.time()
                self.send_gyro_start(sensitivity)

