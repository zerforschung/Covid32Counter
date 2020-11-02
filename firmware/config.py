from micropython import const

CLIENT_ID = const(1337)
WAKEUP_THRESHOLD = const(3)
WIFI_CONNECT_TIMEOUT = const(5)  # second
SCAN_TIME = const(1)  # seconds
SLEEP_TIME = const(5)  # seconds
AP_NAME = "Hotspot"
AP_PASS = None
UPLOAD_URL = "http://backend:1919/"
MAX_PACKET_SIZE = const(10000)  # bytes
MAX_FRAMES_PER_PACKET = const(1)
