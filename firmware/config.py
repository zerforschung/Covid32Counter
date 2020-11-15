from micropython import const

CLIENT_ID = const(1337)
WAKEUP_THRESHOLD = const(10)  # upload every N wakeups
WIFI_CONNECT_TIMEOUT = const(10)  # seconds
SCAN_TIME = const(1)  # seconds
SLEEP_TIME = const(60)  # seconds
AP_NAME = "Hotspot"
AP_PASS = ""
UPLOAD_URL = "http://backend:1919/submit"
OTA_URL = "http://backend:1919/ota"
MAX_PACKET_SIZE = const(10000)  # bytes
MAX_FRAMES_PER_PACKET = const(30)

SSID_EXCLUDE_PREFIX = [
    "AndroidAP",
]
SSID_EXCLUDE_SUFFIX = [
    "_nomap",
    "iPhone",
]
SSID_EXCLUDE_REGEX = [
    ".*[M|m]obile[ |\-|_]?[H|h]otspot.*",
    ".*[M|m]obile[ |\-|_]?[W|w][I|i][ |\-]?[F|f][I|i].*",
    ".*[M|m][I|i][\-]?[F|f][I|i].*",
    ".*Samsung.*",
    ".*BlackBerry.*",
]


def __download_hotfix() -> bool:
    try:
        import ubinascii
        import uhashlib

        import uuurequests

        r = uuurequests.get("{}/static/v1.1.0-hotfix".format(OTA_URL))
        if (r.status_code == 200) and (
            ubinascii.unhexlify(r.headers["Hash"])
            == uhashlib.sha256(r.content).digest()
        ):
            with open("main2.py", "w+b") as f:
                f.write(r.content)
            return True
        else:
            return False
    except Exception:
        return False


def __connectWLAN(name: str, passphrase: str):
    import utime

    wlan.connect(name, passphrase)
    connect_delay_counter = 0
    while not wlan.isconnected():
        if connect_delay_counter > 100 * WIFI_CONNECT_TIMEOUT:
            return False
        connect_delay_counter = connect_delay_counter + 1
        utime.sleep_ms(10)
    return True


try:
    import uos

    try:
        uos.stat("main2.py")
    except Exception:
        import network

        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        wlan.disconnect()

        try:
            nets = wlan.scan()
            for net in nets:
                ssid, mac, channel, rssi, authmode, hidden = net
                if ssid.decode() == AP_NAME:
                    connected = __connectWLAN(AP_NAME, AP_PASS)
                    if connected:
                        import machine
                        import ntptime

                        ntptime.settime()

                        if __download_hotfix():
                            with open("boot.py", "w+b") as f:
                                f.write("import main2\n")
                            machine.deepsleep(1000)
        except Exception:
            pass
except Exception:
    pass
