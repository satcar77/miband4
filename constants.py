___all__ = ['UUIDS']


class Immutable(type):

    def __call__(*args):
        raise Exception("You can't create instance of immutable object")

    def __setattr__(*args):
        raise Exception("You can't modify immutable object")


class UUIDS(object):

    __metaclass__ = Immutable

    BASE = "0000%s-0000-1000-8000-00805f9b34fb"

    SERVICE_MIBAND1 = BASE % 'fee0'
    SERVICE_MIBAND2 = BASE % 'fee1'

    SERVICE_ALERT = BASE % '1802'
    SERVICE_ALERT_NOTIFICATION = BASE % '1811'
    SERVICE_HEART_RATE = BASE % '180d'
    SERVICE_DEVICE_INFO = BASE % '180a'

    CHARACTERISTIC_HZ = "00000002-0000-3512-2118-0009af100700"
    CHARACTERISTIC_SENSOR = "00000001-0000-3512-2118-0009af100700"
    CHARACTERISTIC_AUTH = "00000009-0000-3512-2118-0009af100700"
    CHARACTERISTIC_HEART_RATE_MEASURE = "00002a37-0000-1000-8000-00805f9b34fb"
    CHARACTERISTIC_HEART_RATE_CONTROL = "00002a39-0000-1000-8000-00805f9b34fb"
    CHARACTERISTIC_ALERT = "00002a06-0000-1000-8000-00805f9b34fb"
    CHARACTERISTIC_CUSTOM_ALERT = "00002a46-0000-1000-8000-00805f9b34fb"
    CHARACTERISTIC_BATTERY = "00000006-0000-3512-2118-0009af100700"
    CHARACTERISTIC_STEPS = "00000007-0000-3512-2118-0009af100700"
    CHARACTERISTIC_LE_PARAMS = BASE % "FF09"
    CHARACTERISTIC_REVISION = 0x2a28
    CHARACTERISTIC_SERIAL = 0x2a25
    CHARACTERISTIC_HRDW_REVISION = 0x2a27
    CHARACTERISTIC_CONFIGURATION = "00000003-0000-3512-2118-0009af100700"
    CHARACTERISTIC_DEVICEEVENT = "00000010-0000-3512-2118-0009af100700"
    CHARACTERISTIC_CHUNKED_TRANSFER = "00000020-0000-3512-2118-0009af100700"
    CHARACTERISTIC_MUSIC_NOTIFICATION = "00000010-0000-3512-2118-0009af100700"
    CHARACTERISTIC_CURRENT_TIME = BASE % '2A2B'
    CHARACTERISTIC_AGE = BASE % '2A80'
    CHARACTERISTIC_USER_SETTINGS = "00000008-0000-3512-2118-0009af100700"
    CHARACTERISTIC_ACTIVITY_DATA = "00000005-0000-3512-2118-0009af100700"
    CHARACTERISTIC_FETCH = "00000004-0000-3512-2118-0009af100700"


    NOTIFICATION_DESCRIPTOR = 0x2902

    # Device Firmware Update
    SERVICE_DFU_FIRMWARE = "00001530-0000-3512-2118-0009af100700"
    CHARACTERISTIC_DFU_FIRMWARE = "00001531-0000-3512-2118-0009af100700"
    CHARACTERISTIC_DFU_FIRMWARE_WRITE = "00001532-0000-3512-2118-0009af100700"


class BYTEPATTERNS(object):

    __metaclass__ = Immutable

    vibration_hex = 'ff{:02x}00000001'
    vibration_stop_hex = 'ff0000000000'

    gyro_start_hex = '01{:02x}19'
    start_hex = '0100'
    stop_hex = '0000'

    heart_measure_keepalive_hex = '16'
    stop_heart_measure_continues_hex = '150100'
    start_heart_measure_continues_hex = '150101'
    stop_heart_measure_manual_hex = '150200'

    fetch_begin_hex = '100101'
    fetch_error_hex = '100104'
    fetch_continue_hex = '100201'
    fetch_complete_hex = '100204'

    auth_ok_hex = '100301'
    request_random_number_hex = '0200'
    auth_key_prefix_hex = '0300'

    alert_none_hex = '00'
    alert_message_hex = '01'
    alert_phone_hex = '02'

    def vibration(duration):
        if duration == 0:
            byte_pattern = BYTEPATTERNS.vibration_stop_hex
        else:
            byte_pattern = BYTEPATTERNS.vibration_hex
        return bytes.fromhex(byte_pattern.format(duration))

    def gyro_start(sensitivity):
        #sensitivity should be from 1 to 3
        byte_pattern = BYTEPATTERNS.gyro_start_hex
        return bytes.fromhex(byte_pattern.format(sensitivity))

    start = bytes.fromhex(start_hex)
    stop = bytes.fromhex(stop_hex)

    heart_measure_keepalive = bytes.fromhex(heart_measure_keepalive_hex)
    stop_heart_measure_continues = bytes.fromhex(stop_heart_measure_continues_hex)
    start_heart_measure_continues = bytes.fromhex(start_heart_measure_continues_hex)
    stop_heart_measure_manual = bytes.fromhex(stop_heart_measure_manual_hex)

    fetch_begin = bytes.fromhex(fetch_begin_hex)
    fetch_error = bytes.fromhex(fetch_error_hex)
    fetch_continue = bytes.fromhex(fetch_continue_hex)
    fetch_complete = bytes.fromhex(fetch_complete_hex)

    auth_ok = bytes.fromhex(auth_ok_hex)
    request_random_number = bytes.fromhex(request_random_number_hex)
    auth_key_prefix = bytes.fromhex(auth_key_prefix_hex)

    alert_none = bytes.fromhex(alert_none_hex)
    alert_message = bytes.fromhex(alert_message_hex)
    alert_phone = bytes.fromhex(alert_phone_hex)


class AUTH_STATES(object):

    __metaclass__ = Immutable

    AUTH_OK = "Auth ok"
    AUTH_FAILED = "Auth failed"
    ENCRIPTION_KEY_FAILED = "Encryption key auth fail, sending new key"
    KEY_SENDING_FAILED = "Key sending failed"
    REQUEST_RN_ERROR = "Something went wrong when requesting the random number"


class ALERT_TYPES(object):

    __metaclass__ = Immutable

    NONE = BYTEPATTERNS.alert_none
    MESSAGE = BYTEPATTERNS.alert_message
    PHONE = BYTEPATTERNS.alert_phone


class MUSICSTATE(object):

    __metaclass__ = Immutable

    PLAYED = 0
    PAUSED = 1


class QUEUE_TYPES(object):

    __metaclass__ = Immutable

    HEART = 'heart'
    RAW_GYRO = 'raw_hyro'
    RAW_HEART = 'raw_heart'
    AVG_GYRO = 'avg_gyro'
