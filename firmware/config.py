from micropython import const

CLIENT_ID = const(1337)
WAKEUP_THRESHOLD = const(3)
WIFI_CONNECT_TIMEOUT = const(10)  # second
SCAN_TIME = const(1)  # seconds
SLEEP_TIME = const(5)  # seconds
AP_NAME = "Hotspot"
AP_PASS = None
UPLOAD_URL = "http://backend:1919/submit"
OTA_URL = "http://backend:1919/ota"
MAX_PACKET_SIZE = const(10000)  # bytes
MAX_FRAMES_PER_PACKET = const(1)

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
