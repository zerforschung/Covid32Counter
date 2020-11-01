from micropython import const

import btree
import esp32
import machine
import network
import ntptime
import ubinascii
import ubluetooth
import uhashlib
import ustruct
import utime

import captive_bvg
import exposure_notification
import util
import uuurequests


DEBUG = True
CLIENT_ID = const(1337)
WAKEUP_COUNTER = 10
SCAN_TIME = const(1)  # seconds
SLEEP_TIME = const(5)  # seconds
AP_NAME = "Hotspot"
AP_PASS = None
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
    # check of this should be done after captive portal login
    if machine.reset_cause() != machine.DEEPSLEEP:
        try:
            ntptime.settime()
            util.syslog("Time", rtc.datetime())
        except Exception as e:
            print("Error getting NTP", e)
            pass

    return True


@micropython.native
def bleInterruptHandler(event: int, data):
    global ble_scan_done

    if event == util.IRQ_SCAN_RESULT:
        (addr_type, addr, adv_type, rssi, adv_data) = data

        if exposure_notification.isExposureNotification(adv_data):
            beacons[bytes(adv_data)[11:31]] = rssi

    if event == util.IRQ_SCAN_DONE:
        util.syslog("BLE", "Scan done, stopping Bluetooth...")
        ble.active(False)
        ble_scan_done = True
        return


if DEBUG:
    p2 = machine.Pin(util.ONBOARD_LED, machine.Pin.OUT)
    p2.on()


needsUpload = False

util.syslog("RTC", "Init...")
rtc = machine.RTC()

# RTC-RAM is empty after a real reboot (no deepsleep)
if len(rtc.memory()) == 0:
    util.syslog("RTC", "RTC-RAM clean...")
    rtc.memory(ustruct.pack(">B", WAKEUP_COUNTER))
    needsUpload = True

# RTC-RAM not empty, get WAKEUP_COUNTER
WAKEUP_COUNTER = ustruct.unpack(">B", rtc.memory())[0]

if WAKEUP_COUNTER < 1:
    WAKEUP_COUNTER = 0
    needsUpload = True

# setup voltage measurements
adc = machine.ADC(machine.Pin(36, machine.Pin.IN))
adc.atten(adc.ATTN_11DB)

beacons = {}
util.syslog("BLE", "Starting Bluetooth...")
ble = ubluetooth.BLE()
ble.active(True)
ble.irq(bleInterruptHandler)
util.syslog("BLE", "Scanning...")
ble.gap_scan(
    util.second_to_millisecond(SCAN_TIME),
    util.second_to_microsecond(SCAN_TIME),
    util.second_to_microsecond(SCAN_TIME),
)

ble_scan_done = False
while not ble_scan_done:
    utime.sleep_ms(50)

util.syslog("Wifi", "Starting Wifi...")
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.disconnect()
nets = wlan.scan()

framePayload = ustruct.pack(">i", util.now())  # encode timestamp
framePayload += ustruct.pack(">H", adc.read_u16())  # encode battery level
framePayload += ustruct.pack(">h", esp32.hall_sensor())  # encode hall sensor
framePayload += ustruct.pack(">h", esp32.raw_temperature())  # encode temperature sensor
framePayload += ustruct.pack(">B", len(nets))  # encode wifi count
framePayload += ustruct.pack(">B", len(beacons))  # encode BLE beacon count

ap_available = False
# encode mac/rssi for every wifi
for net in nets:
    ssid, mac, channel, rssi, authmode, hidden = net
    framePayload += ustruct.pack(">6sb", mac, rssi)
    if ssid.decode() == AP_NAME:
        ap_available = True

# encode beacons
for beacon, rssi in beacons.items():
    framePayload += ustruct.pack(">20s", beacon)


util.syslog("Storage", "Storing...")
try:
    f = util.openFile("v1.db")
    db = btree.open(f)
    db[str(ubinascii.crc32(framePayload))] = framePayload
    db.flush()
    f.flush()
    db.close()
except Exception as e:
    util.syslog("Storage", "Failed with error: {}".format(e))
    pass
finally:
    f.close()
util.syslog("Storage", "Done.")

if needsUpload and ap_available:
    connected = connectWLAN(AP_NAME, AP_PASS)
    if connected:
        has_web_connection = False
        try:
            has_web_connection = captive_bvg.accept_captive_portal()
        except Exception:
            util.syslog("Network", "Problem checking online status")

        if has_web_connection:
            util.syslog("Network", "We should have a web connection")
            util.syslog("Upload", "Uploading stored measurements...")

            packetPayload = ustruct.pack(">3s", "CWA")  # encode magic
            packetPayload += ustruct.pack(">B", 1)  # encode version number
            packetPayload += ustruct.pack(">H", CLIENT_ID)  # encode clientID

            frameCount = 0

            try:
                f = util.openFile("v1.db")
                db = btree.open(f)

                for frame in db:
                    frameCount += 1

                packetPayload += ustruct.pack(
                    ">B", frameCount
                )  # encode amount of frames

                for frame in db:
                    packetPayload += db[frame]  # add every frame

                # add checksum
                checksum = uhashlib.sha256(packetPayload).digest()
                packetPayload += checksum

                util.syslog("Upload", "Uploading {} bytes...".format(len(packetPayload)))
                returnedChecksum = uuurequests.post(
                    UPLOAD_URL, data=packetPayload
                ).content

                if checksum != returnedChecksum:
                    raise "Checksum mismatch!"

                util.syslog("Upload", "Successful, deleting frames...")
                for frame in db:
                    del db[frame]

            except Exception as e:
                util.syslog(
                    "Upload", "Upload failed with error '{}', skipping...".format(e)
                )

            finally:
                util.syslog("Storage", "Flushing database...")
                db.flush()
                db.close()
                f.close()

        else:
            util.syslog("Network", "Looks like we have no real connection")
    else:
        util.syslog("Upload", "no connection, can't upload...")


WAKEUP_COUNTER = WAKEUP_COUNTER - 1
rtc.memory(ustruct.pack(">B", WAKEUP_COUNTER))
util.syslog(
    "Machine", "{} remaining wakeups until we try to upload...".format(WAKEUP_COUNTER)
)
util.syslog("Machine", "Going to sleep for {} seconds...".format(SLEEP_TIME))
machine.deepsleep(util.second_to_millisecond(SLEEP_TIME))
