from micropython import const

import machine
import network
import ntptime
import ubluetooth
import uhashlib
import ustruct
import utime

# import ubinascii

import exposure_notification
import util
import uuurequests

DEBUG = True
CLIENT_ID = const(1337)
# UPLOAD_URL = "https://requestbin.io/1jk439t1"
# UPLOAD_URL = "http://requestbin.net/zvr97czv"
UPLOAD_URL = "http://backend:1919/"


@micropython.native
def connectWLAN(name: str, passphrase: str) -> bool:
    util.syslog("Wifi", "Connecting...")
    wlan.connect(name, passphrase)
    connect_delay_counter = 0
    while not wlan.isconnected():
        if connect_delay_counter > 10:
            util.syslog("Wifi", "Timeout.")
            return False
        connect_delay_counter = connect_delay_counter + 1
        utime.sleep_ms(500)
        util.syslog("Wifi", ".")

    util.syslog("Wifi", "Connected.")

    # if we didn't wake up from deepsleep, we lost the RTC-RAM and need to get the current time
    if machine.reset_cause() != machine.DEEPSLEEP:
        ntptime.settime()
        util.syslog("Time", rtc.datetime())

    return True


def bleInterruptHandler(event: int, data):
    if event == util.IRQ_SCAN_RESULT:
        (addr_type, addr, adv_type, rssi, adv_data) = data

        if exposure_notification.isExposureNotification(adv_data):
            beacons[bytes(adv_data)[11:31]] = rssi

    if event == util.IRQ_SCAN_DONE:
        util.syslog("BLE", "Scan done.")
        return


if DEBUG:
    p2 = machine.Pin(util.ONBOARD_LED, machine.Pin.OUT)
    p2.on()


needsUpload = False

util.syslog("RTC", "Init...")
rtc = machine.RTC()
rtcMem = rtc.memory()
if len(rtcMem) > 0:
    util.syslog(
        "RTC", "Bits to upload stored measurements is set, scheduling upload..."
    )
    needsUpload = ustruct.unpack(">b", rtcMem)

beacons = {}
util.syslog("BLE", "Starting Bluetooth...")
ble = ubluetooth.BLE()
ble.active(True)
ble.irq(bleInterruptHandler)
util.syslog("BLE", "Scanning...")
ble.gap_scan(
    util.second_to_microsecond(SCAN_TIME),
    util.second_to_millisecond(SCAN_TIME),
    util.second_to_millisecond(SCAN_TIME),
)

util.syslog("Wifi", "Starting Wifi...")
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.disconnect()
nets = wlan.scan()
connected = connectWLAN(AP_NAME, AP_PASS)

# micropython's epoch begins at 2000-01-01 00:00:00, so we add _EPOCH_OFFSET
timeStamp = util.now()

payload = ustruct.pack(">3s", "CWA")  # encode magic
payload += ustruct.pack(">B", 1)  # encode version number
payload += ustruct.pack(">i", timeStamp)  # encode timestamp
payload += ustruct.pack(">H", CLIENT_ID)  # encode clientID
payload += ustruct.pack(">B", len(nets))  # encode wifi count
payload += ustruct.pack(">B", len(beacons))  # encode BLE beacon count

# encode mac/rssi for every wifi
for net in nets:
    ssid, mac, channel, rssi, authmode, hidden = net
    payload += ustruct.pack(">6sb", mac, rssi)

# encode beacons
for beacon, rssi in beacons.items():
    payload += ustruct.pack(">20s", beacon)

#     print(
#         """Beacon Length: {}
# Beacon Content: {}
# Beacon RSSI: {}
# """.format(
#             ubinascii.hexlify(beacon, "-"),
#             rssi,
#         )
#     )
#             len(beacon#),
# hexPayload = ubinascii.hexlify(payload)
# print(
#     """
# Payload Length: {}
#
# HexPayload: {}

# Timestamp: {}

# Wifi count: {}

# Beacon count: {}
# """.format(
#         len(payload),
#         hexPayload,
#         timeStamp,
#         len(nets),
#         len(beacons),
#     )
# )

util.collectGarbage()

writeToFlash = False

if connected:
    if needsUpload:
        try:
            util.syslog("Upload/Storage", "Uploading stored measurements...")
            util.syslog("Upload/Storage", "TODO")
        except Exception as e:
            util.syslog(
                "Upload", "Upload failed with error '{}', skipping...".format(e)
            )

    try:
        util.syslog("Upload", "Uploading {} bytes...".format(len(payload)))
        checksumServer = uuurequests.post(UPLOAD_URL, data=payload).content
        checksumClient = uhashlib.sha1(payload).digest()

        if checksumClient == checksumServer:
            #     print(
            #         """Server returned checksum: {}
            # Client calculated checksum: {}
            # Matching: {}
            #             ubinascii.#hexlify(checksumServer),
            #             ubinascii.hexlify(checksumClient),
            #             checksumServer == checksumClient,
            #         )
            # """.format(#
            #     )
            util.syslog("Upload", "Successful.")
    except Exception as e:
        util.syslog(
            "Upload/Storage",
            "Upload failed with error '{}', storing instead...".format(e),
        )
        writeToFlash = True

if writeToFlash or not connected:
    util.syslog("Storage", "Storing...")
    util.syslog("Storage", "TODO")
    util.syslog("RTC", "Setting bits so next run we try to upload stored measurements.")
    rtc.memory(ustruct.pack(">b", True))
    util.syslog("Storage", "Done.")


util.syslog("Machine", "Going to sleep for {} seconds...".format(SLEEP_TIME))
machine.deepsleep(util.second_to_microsecond(SLEEP_TIME))
