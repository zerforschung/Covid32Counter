from micropython import const

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
