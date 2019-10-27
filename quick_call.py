#! /usr/bin/python3
import sys
from miband import miband
from bluepy.btle import BTLEDisconnectError

while True :
    try:
        band = miband(sys.argv[1],debug=True)
        band.send_custom_alert(3,sys.argv[2])
        band.waitForNotifications(10)
        band.disconnect()
        break
    except BTLEDisconnectError:
        print('connection to the MIBand failed. Trying out again')
        continue

