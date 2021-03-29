#!/usr/bin/env python3

# This script demonstrates the usage, capability and features of the library.

import argparse
import subprocess
import shutil
import time
from datetime import datetime

from bluepy.btle import BTLEDisconnectError
from cursesmenu import *
from cursesmenu.items import *

from constants import MUSICSTATE
from miband import miband

parser = argparse.ArgumentParser()
parser.add_argument('-m', '--mac', required=False, help='Set mac address of the device')
parser.add_argument('-k', '--authkey', required=False, help='Set Auth Key for the device')
args = parser.parse_args()

# Try to obtain MAC from the file
try:
    with open("mac.txt", "r") as f:
        mac_from_file = f.read().strip()
except FileNotFoundError:
    mac_from_file = None

# Use appropriate MAC
if args.mac:
    MAC_ADDR = args.mac
elif mac_from_file:
    MAC_ADDR = mac_from_file
else:
    print("Error:")
    print("  Please specify MAC address of the MiBand")
    print("  Pass the --mac option with MAC address or put your MAC to 'mac.txt' file")
    print("  Example of the MAC: a1:c2:3d:4e:f5:6a")
    exit(1)

# Validate MAC address
if 1 < len(MAC_ADDR) != 17:
    print("Error:")
    print("  Your MAC length is not 17, please check the format")
    print("  Example of the MAC: a1:c2:3d:4e:f5:6a")
    exit(1)

# Try to obtain Auth Key from file
try:
    with open("auth_key.txt", "r") as f:
        auth_key_from_file = f.read().strip()
except FileNotFoundError:
    auth_key_from_file = None

# Use appropriate Auth Key
if args.authkey:
    AUTH_KEY = args.authkey
elif auth_key_from_file:
    AUTH_KEY = auth_key_from_file
else:
    print("Warning:")
    print("  To use additional features of this script please put your Auth Key to 'auth_key.txt' or pass the --authkey option with your Auth Key")
    print()
    AUTH_KEY = None
    
# Validate Auth Key
if AUTH_KEY:
    if 1 < len(AUTH_KEY) != 32:
        print("Error:")
        print("  Your AUTH KEY length is not 32, please check the format")
        print("  Example of the Auth Key: 8fa9b42078627a654d22beff985655db")
        exit(1)

# Convert Auth Key from hex to byte format
if AUTH_KEY:
    AUTH_KEY = bytes.fromhex(AUTH_KEY)

# Needs Auth
def get_step_count():
    binfo = band.get_steps()
    print ('Number of steps: ', binfo['steps'])
    print ('Fat Burned: ', binfo['fat_burned'])
    print ('Calories: ', binfo['calories'])
    print ('Distance travelled in meters: ', binfo['meters'])
    input('Press a key to continue')


def general_info():
    print ('MiBand')
    print ('Soft revision:',band.get_revision())
    print ('Hardware revision:',band.get_hrdw_revision())
    print ('Serial:',band.get_serial())
    print ('Battery:', band.get_battery_info()['level'])
    print ('Time:', band.get_current_time()['date'].isoformat())
    input('Press a key to continue')


def send_notif():
    title = input ("Enter title or phone number to be displayed: ")
    print ('Reminder: at Mi Band 4 you have 10 characters per line, and up to 6 lines. To add a new line use new line character \n')
    msg = input ("Enter optional message to be displayed: ")
    ty= int(input ("1 for Mail / 2 for Message / 3 for Missed Call / 4 for Call: "))
    if(ty > 4 or ty < 1):
        print ('Invalid choice')
        time.sleep(2)
        return
    a=[1,5,4,3]
    band.send_custom_alert(a[ty-1],title,msg)


# Needs Auth
def get_heart_rate():
    print ('Latest heart rate is : %i' % band.get_heart_rate_one_time())
    input('Press a key to continue')


def heart_logger(data):
    print ('Realtime heart BPM:', data)


# Needs Auth
def get_realtime():
    band.start_heart_rate_realtime(heart_measure_callback=heart_logger)
    input('Press Enter to continue')


# Needs Auth
def restore_firmware():
    print("This feature has the potential to brick your Mi Band 4. You are doing this at your own risk.")
    path = input("Enter the path of the firmware file :")
    band.dfuUpdate(path)

# Needs Auth
def update_watchface():
    path = input("Enter the path of the watchface .bin file :")
    band.dfuUpdate(path)



# Needs Auths
def set_time():
    now = datetime.now()
    print ('Set time to:', now)
    band.set_current_time(now)


# default callbacks        
def _default_music_play():
    print("Played")
def _default_music_pause():
    print("Paused")
def _default_music_forward():
    print("Forward")
def _default_music_back():
    print("Backward")
def _default_music_vup():
    print("volume up")
def _default_music_vdown():
    print("volume down")
def _default_music_focus_in():
    print("Music focus in")
def _default_music_focus_out():
    print("Music focus out")    


def set_music(): 
    band.setMusicCallback(_default_music_play,_default_music_pause,_default_music_forward,_default_music_back,_default_music_vup,_default_music_vdown,_default_music_focus_in,_default_music_focus_out)
    fi = input("Set music track artist to : ")
    fj = input("Set music track album to: ")
    fk = input("Set music track title to: ")
    fl = int(input("Set music volume: "))
    fm = int(input("Set music position: "))
    fn = int(input("Set music duration: "))
    band.setTrack(MUSICSTATE.PLAYED,fi,fj,fk,fl,fm,fn)
    while True:
        if band.waitForNotifications(0.5):
            continue
    input("enter any key")


def lost_device():
    found = False
    notify = shutil.which("notify-send") is not None

    def lost_device_callback():
        if notify:
            subprocess.call(["notify-send", "Device Lost"])
        else:
            print("Searching for this device")
        print('Click on the icon on the band to stop searching')

    def found_device_callback():
        nonlocal found
        if notify:
            subprocess.call(["notify-send", "Found device"])
        else:
            print("Searching for this device")
        found = True

    band.setLostDeviceCallback(lost_device_callback, found_device_callback)
    print('Click "Lost Device" on the band')
    while not found:
        if band.waitForNotifications(0.5):
            continue
    input("enter any key")


def activity_log_callback(timestamp,c,i,s,h):
    print("{}: category: {}; intensity {}; steps {}; heart rate {};\n".format( timestamp.strftime('%d.%m - %H:%M'), c, i ,s ,h))

#Needs auth    
def get_activity_logs():
    #gets activity log for this day.
    temp = datetime.now()
    band.get_activity_betwn_intervals(datetime(temp.year,temp.month,temp.day),datetime.now(),activity_log_callback)
    while True:
        band.waitForNotifications(0.2)

if __name__ == "__main__":
    success = False
    while not success:
        try:
            if (AUTH_KEY):
                band = miband(MAC_ADDR, AUTH_KEY, debug=True)
                success = band.initialize()
            else:
                band = miband(MAC_ADDR, debug=True)
                success = True
            break
        except BTLEDisconnectError:
            print('Connection to the MIBand failed. Trying out again in 3 seconds')
            time.sleep(3)
            continue
        except KeyboardInterrupt:
            print("\nExit.")
            exit()
        
    menu = CursesMenu("MIBand4", "Features marked with @ require Auth Key")
    info_item = FunctionItem("Get general info of the device", general_info)
    call_item = FunctionItem("Send Mail/ Call/ Missed Call/ Message", send_notif)
    set_music_item = FunctionItem("Set the band's music and receive music controls", set_music)
    lost_device_item = FunctionItem("Listen for Device Lost notifications", lost_device)
    steps_item = FunctionItem("@ Get Steps/Meters/Calories/Fat Burned", get_step_count)
    single_heart_rate_item = FunctionItem("@ Get Heart Rate", get_heart_rate)
    real_time_heart_rate_item = FunctionItem("@ Get realtime heart rate data", get_realtime)
    get_band_activity_data_item = FunctionItem("@ Get activity logs for a day", get_activity_logs)
    set_time_item= FunctionItem("@ Set the band's time to system time", set_time)
    update_watchface_item = FunctionItem("@ Update Watchface", update_watchface)
    dfu_update_item = FunctionItem("@ Restore/Update Firmware", restore_firmware)
    
    menu.append_item(info_item)
    menu.append_item(steps_item)
    menu.append_item(call_item)
    menu.append_item(single_heart_rate_item)
    menu.append_item(real_time_heart_rate_item)
    menu.append_item(get_band_activity_data_item)
    menu.append_item(set_time_item)
    menu.append_item(set_music_item)
    menu.append_item(lost_device_item)
    menu.append_item(update_watchface_item)
    menu.append_item(dfu_update_item)
    menu.show()
