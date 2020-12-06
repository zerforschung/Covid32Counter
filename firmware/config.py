from micropython import const

CLIENT_ID = const(1337)
WAKEUP_THRESHOLD = const(10)  # upload every N wakeups
WIFI_CONNECT_TIMEOUT = const(10)  # seconds
SCAN_TIME = const(1)  # seconds
SLEEP_TIME = const(60)  # seconds
EXTENDED_SLEEP_TIME = const(300)  # seconds
AP_NAME = "Hotspot"
AP_PASS = ""
UPLOAD_URL = "http://backend:1919/submit"
OTA_URL = "http://backend:1919/ota"
OTA_INTERVAL = 10  # OTA every N uploads
MAX_PACKET_SIZE = const(10000)  # bytes
MAX_FRAMES_PER_PACKET = const(30)
EMPTY_WIFI_THRESHOLD = const(10)  # after N scans with no wifis, use EXTENDED_SLEEP_TIME

SSID_EXCLUDE_PREFIX = [
    "AndroidAP",
]
SSID_EXCLUDE_SUFFIX = [
    "_nomap",
]
SSID_EXCLUDE_REGEX = [
    ".*[M|m]obile[ |\-|_]?[H|h]otspot.*",
    ".*[M|m]obile[ |\-|_]?[W|w][I|i][ |\-]?[F|f][I|i].*",
    ".*[M|m][I|i][\-]?[F|f][I|i].*",
    ".*Samsung.*",
    ".*BlackBerry.*",
    ".*iPhone.*",
    ".*iPad.*",
]

SPECIAL_SSIDS = []
SPECIAL_MACS = []
