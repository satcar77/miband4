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

class AUTH_STATES(object):

    __metaclass__ = Immutable

    AUTH_OK = "Auth ok"
    AUTH_FAILED = "Auth failed"
    ENCRIPTION_KEY_FAILED = "Encryption key auth fail, sending new key"
    KEY_SENDING_FAILED = "Key sending failed"
    REQUEST_RN_ERROR = "Something went wrong when requesting the random number"


class ALERT_TYPES(object):

    __metaclass__ = Immutable

    NONE = '\x00'
    MESSAGE = '\x01'
    PHONE = '\x02'

class MUSICSTATE(object):

    __metaclass__ = Immutable

    PLAYED = 0
    PAUSED = 1

class QUEUE_TYPES(object):

    __metaclass__ = Immutable

    HEART = 'heart'
    RAW_ACCEL = 'raw_accel'
    RAW_HEART = 'raw_heart'

class Weekdays(object):

    __metaclass__ = Immutable

    monday    = 0x01 << 0
    tuesday   = 0x01 << 1
    wednesday = 0x01 << 2
    thursday  = 0x01 << 3
    friday    = 0x01 << 4
    saturday  = 0x01 << 5
    sunday    = 0x01 << 6
    everyday  = 0x01 << 7
    
class DISPLAY_ITEMS(object):
    
    __metaclass__ = Immutable
    STATUS = 0x01
    HEART_RATE = 0x02
    WORKOUT = 0x03
    WEATHER = 0x04
    MI_HOME = 0x05 # I have no clue what this does. Pressing it does nothing for me
    NOTIFICATIONS = 0x06
    MORE = 0x07 # While the app doesn't allow you to remove this, I tried and it works perfectly
    
    ALL_ITEMS = [STATUS, HEART_RATE, WORKOUT, WEATHER, NOTIFICATIONS, MORE]
