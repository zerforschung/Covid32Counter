from micropython import const

import gc
import machine
import network
import ntptime
import ubinascii
import ubluetooth
import uhashlib
import ustruct
import utime

import uuurequests

_SCAN_TIME = const(2)  # seconds
_SLEEP_TIME = const(5)  # seconds

_SEC_2_USEC = const(1000 * 1000)
_SEC_2_MSEC = const(1000)

_EPOCH_OFFSET = const(946681200)  # seconds between 1970 and 2000

_IRQ_SCAN_RESULT = const(5)
_IRQ_SCAN_DONE = const(6)

# see https://covid19.apple.com/contacttracing for description
_EXPOSURE_NOTIFICATION_FLAGS_LENGTH = ubinascii.unhexlify("02")
_EXPOSURE_NOTIFICATION_FLAGS_TYPE = ubinascii.unhexlify("01")
_EXPOSURE_NOTIFICATION_FLAGS_FLAGS = ubinascii.unhexlify("1a")
_EXPOSURE_NOTIFICATION_SERVICE_UUID_LENGTH = ubinascii.unhexlify("03")
_EXPOSURE_NOTIFICATION_SERVICE_UUID_TYPE = ubinascii.unhexlify("03")
_EXPOSURE_NOTIFICATION_SERVICE_UUID_UUID = ubinascii.unhexlify("6ffd")
_EXPOSURE_NOTIFICATION_SERVICE_DATA_LENGTH = ubinascii.unhexlify("17")
_EXPOSURE_NOTIFICATION_SERVICE_DATA_TYPE = ubinascii.unhexlify("16")
_EXPOSURE_NOTIFICATION_SERVICE_DATA_UUID = ubinascii.unhexlify("6ffd")
_EXPOSURE_NOTIFICATION = (
    _EXPOSURE_NOTIFICATION_FLAGS_LENGTH
    + _EXPOSURE_NOTIFICATION_FLAGS_TYPE
    + _EXPOSURE_NOTIFICATION_FLAGS_FLAGS
    + _EXPOSURE_NOTIFICATION_SERVICE_UUID_LENGTH
    + _EXPOSURE_NOTIFICATION_SERVICE_UUID_TYPE
    + _EXPOSURE_NOTIFICATION_SERVICE_UUID_UUID
    + _EXPOSURE_NOTIFICATION_SERVICE_DATA_LENGTH
    + _EXPOSURE_NOTIFICATION_SERVICE_DATA_TYPE
    + _EXPOSURE_NOTIFICATION_SERVICE_DATA_UUID
)


def collectGarbage():
    print(
        "--- [GC] before collection: {} allocated, {} free ---".format(
            gc.mem_alloc(), gc.mem_free()
        )
    )
    gc.collect()
    print(
        "--- [GC] after collection: {} allocated, {} free ---".format(
            gc.mem_alloc(), gc.mem_free()
        )
    )


def connectWLAN(name: str, passphrase: str):
    wlan.connect(name, passphrase)
    connect_delay_counter = 0
    while not wlan.isconnected():
        if connect_delay_counter > 10:
            return False
        connect_delay_counter = connect_delay_counter + 1
        utime.sleep_ms(500)
        print(".")

    # if we didn't wake up from deepsleep, we lost the RTC-RAM and need to get the current time
    if machine.reset_cause() != machine.DEEPSLEEP:
        ntptime.settime()

    return True


def bleInterruptHandler(event: int, data):
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data

        # ExposureNotifications are exactly 31 bytes long
        if len(adv_data) != 31:
            return

        # ExposureNotications start with these 11 static bytes
        if adv_data[0:11] != _EXPOSURE_NOTIFICATION:
            return

        # very likely a real ExposureNotification, add it to the list
        beacons[bytes(adv_data)[11:31]] = rssi
        return

    if event == _IRQ_SCAN_DONE:
        return


# init RTC
rtc = machine.RTC()

beacons = {}
ble = ubluetooth.BLE()
ble.active(True)
ble.irq(bleInterruptHandler)
ble.gap_scan(
    1000 * _SCAN_TIME,
    1000 * 1000 * _SCAN_TIME,
    1000 * 1000 * _SCAN_TIME,
)

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.disconnect()
nets = wlan.scan()
connectWLAN("BVG Wi-Fi")

# micropython's epoch begins at 2000-01-01 00:00:00, so we add _EPOCH_OFFSET
timeStamp = utime.time() + _EPOCH_OFFSET

payload = ustruct.pack("<i", timeStamp)  # encode timestamp
payload += ustruct.pack("<B", len(nets))  # encode wifi count
payload += ustruct.pack("<B", len(beacons))  # encode BLE beacon count

# encode mac/rssi for every wifi
for net in nets:
    ssid, mac, channel, rssi, authmode, hidden = net
    payload += ustruct.pack("<6sb", mac, rssi)

# encode beacons
for beacon, rssi in beacons.items():
    print(
        """Beacon Length: {}
Beacon Content: {}
Beacon RSSI: {}
""".format(
            len(beacon),
            ubinascii.hexlify(beacon, "-"),
            rssi,
        )
    )

    payload += ustruct.pack("<20s", beacon)

hexPayload = ubinascii.hexlify(payload)

print(
    """
Payload Length: {}
HexPayload: {}

Timestamp: {}

Wifi count: {}

Beacon count: {}
""".format(
        len(payload),
        hexPayload,
        timeStamp,
        len(nets),
        len(beacons),
    )
)

# url = "https://requestbin.io/1jk439t1"
# url = "http://requestbin.net/zvr97czv"
url = "http://backend:1919/"

# collectGarbage()
# t1 = utime.ticks_ms()
checksumServer = uuurequests.post(url, data=payload).content
checksumClient = uhashlib.sha1(payload).digest()

if checksumClient == checksumServer:
    print(
        """Server returned checksum: {}
Client calculated checksum: {}
Matching: {}
""".format(
            ubinascii.hexlify(checksumServer),
            ubinascii.hexlify(checksumClient),
            checksumServer == checksumClient,
        )
    )
# print("request took: {} ms".format(utime.ticks_diff(utime.ticks_ms(), t1)))

# machine.deepsleep(_SEC_2_MSEC * _SLEEP_TIME)
