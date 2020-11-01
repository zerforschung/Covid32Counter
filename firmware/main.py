from micropython import const

import btree
import esp32
import gc
import machine
import network
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
WAKEUP_THRESHOLD = 3
WIFI_CONNECT_TIMEOUT = 5  # second
SCAN_TIME = const(1)  # seconds
SLEEP_TIME = const(5)  # seconds
AP_NAME = "Hotspot"
AP_PASS = None
UPLOAD_URL = "http://backend:1919/"
MAX_PACKET_SIZE = 10000
MAX_FRAMES_PER_PACKET = 1


@micropython.native
def connectWLAN(name: str, passphrase: str) -> bool:
    util.syslog("Wifi", "Connecting...")
    wlan.connect(name, passphrase)
    connect_delay_counter = 0
    while not wlan.isconnected():
        if connect_delay_counter > 100 * WIFI_CONNECT_TIMEOUT:
            util.syslog("Wifi", "Timeout.")
            return False
        connect_delay_counter = connect_delay_counter + 1
        utime.sleep_ms(10)
    util.syslog("Wifi", "Connected.")
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


wakeupCounter = 0
needsUpload = False

util.syslog("RTC", "Init...")
rtc = machine.RTC()

# RTC-RAM is empty after a real reboot (no deepsleep)
if len(rtc.memory()) == 0:
    util.syslog("RTC", "RTC-RAM clean...")
    needsUpload = True
else:
    # RTC-RAM not empty, get wakeupCounter
    wakeupCounter = ustruct.unpack(">B", rtc.memory())[0]

wakeupCounter += 1
if wakeupCounter > WAKEUP_THRESHOLD:
    needsUpload = True

# setup voltage measurements
adc = machine.ADC(machine.Pin(36, machine.Pin.IN))
adc.atten(adc.ATTN_11DB)

gc.collect()

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
    utime.sleep_ms(10)

gc.collect()

util.syslog("Wifi", "Starting Wifi...")
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.disconnect()
nets = wlan.scan()
if not needsUpload:
    util.syslog("Wifi", "Stopping Wifi...")
    wlan.active(False)

gc.collect()

framePayload = ustruct.pack(">i", util.now())  # encode timestamp
framePayload += ustruct.pack(">H", adc.read_u16())  # encode battery level
framePayload += ustruct.pack(">h", esp32.hall_sensor())  # encode hall sensor
framePayload += ustruct.pack(">h", esp32.raw_temperature())  # encode temperature sensor
framePayload += ustruct.pack(">B", len(nets))  # encode wifi count
framePayload += ustruct.pack(">B", len(beacons))  # encode BLE beacon count

ap_available = False
for net in nets:
    ssid, mac, channel, rssi, authmode, hidden = net
    framePayload += ustruct.pack(">6sb", mac, rssi)  # encode mac/rssi for every wifi
    if ssid.decode() == AP_NAME:
        ap_available = True

# encode beacons
for beacon, rssi in beacons.items():
    framePayload += ustruct.pack(">20s", beacon)

gc.collect()

util.syslog("Storage", "Storing...")
try:
    with util.openFile("v1.db") as f:
        db = btree.open(f)
        db[str(ubinascii.crc32(framePayload))] = framePayload
        db.close()
except Exception as e:
    util.syslog("Storage", "Failed with error: {}".format(e))
    pass
util.syslog("Storage", "Done.")

gc.collect()

if needsUpload and ap_available:
    connected = connectWLAN(AP_NAME, AP_PASS)
    gc.collect()
    if connected:
        has_web_connection = False
        try:
            has_web_connection = captive_bvg.accept_captive_portal()
            gc.collect()
        except Exception:
            util.syslog("Network", "Problem checking online status")

        if has_web_connection:
            util.syslog("Network", "We should have a web connection")

            # syncs time over NTP if needed
            util.syncTime()
            gc.collect()

            util.syslog("Upload", "Uploading stored measurements...")

            try:
                f = util.openFile("v1.db")
                db = btree.open(f)

                while True:
                    packetPayload = ustruct.pack(">3s", "CWA")  # encode magic
                    packetPayload += ustruct.pack(">B", 1)  # encode version number
                    packetPayload += ustruct.pack(">H", CLIENT_ID)  # encode clientID

                    frames = b""
                    doneFrames = []

                    for frame in db:
                        if (len(frames) > MAX_PACKET_SIZE) or (
                            len(doneFrames) >= MAX_FRAMES_PER_PACKET
                        ):
                            break
                        frames += db[frame]  # add every frame
                        doneFrames.append(frame)

                    gc.collect()

                    if len(doneFrames) == 0:
                        break

                    packetPayload += ustruct.pack(
                        ">B", len(doneFrames)
                    )  # encode amount of frames
                    packetPayload += frames

                    # add checksum
                    checksum = uhashlib.sha256(packetPayload).digest()
                    packetPayload += checksum
                    gc.collect()

                    util.syslog(
                        "Upload", "Uploading {} bytes...".format(len(packetPayload))
                    )
                    returnedChecksum = uuurequests.post(
                        UPLOAD_URL, data=packetPayload
                    ).content
                    gc.collect()

                    if checksum != returnedChecksum:
                        raise Exception("Checksum mismatch!")

                    util.syslog("Upload", "Successful, deleting frames...")
                    for frame in doneFrames:
                        del db[frame]

                    gc.collect()

                wakeupCounter = 0

            except Exception as e:
                util.syslog(
                    "Upload", "Upload failed with error '{}', skipping...".format(e)
                )

            finally:
                util.syslog("Storage", "Flushing database...")
                db.close()
                f.close()

        else:
            util.syslog("Network", "Looks like we have no real connection")
    else:
        util.syslog("Upload", "no connection, can't upload...")


if wakeupCounter <= WAKEUP_THRESHOLD:
    util.syslog(
        "Machine",
        "{} remaining wakeups until we try to upload...".format(
            WAKEUP_THRESHOLD - wakeupCounter + 1
        ),
    )
else:
    util.syslog(
        "Machine",
        "Upload failed for {} tries, trying next time again.".format(
            wakeupCounter - WAKEUP_THRESHOLD
        ),
    )

rtc.memory(ustruct.pack(">B", wakeupCounter))
util.syslog("Machine", "Going to sleep for {} seconds...".format(SLEEP_TIME))
machine.deepsleep(util.second_to_millisecond(SLEEP_TIME))
