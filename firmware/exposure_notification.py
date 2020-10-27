import ubinascii

# see https://covid19.apple.com/contacttracing for description
_FLAGS_LENGTH = ubinascii.unhexlify("02")
_FLAGS_TYPE = ubinascii.unhexlify("01")
_FLAGS_FLAGS = ubinascii.unhexlify("1a")
_SERVICE_UUID_LENGTH = ubinascii.unhexlify("03")
_SERVICE_UUID_TYPE = ubinascii.unhexlify("03")
_SERVICE_UUID_UUID = ubinascii.unhexlify("6ffd")
_SERVICE_DATA_LENGTH = ubinascii.unhexlify("17")
_SERVICE_DATA_TYPE = ubinascii.unhexlify("16")
_SERVICE_DATA_UUID = ubinascii.unhexlify("6ffd")

EXPOSURE_NOTIFICATION = (
    _FLAGS_LENGTH
    + _FLAGS_TYPE
    + _FLAGS_FLAGS
    + _SERVICE_UUID_LENGTH
    + _SERVICE_UUID_TYPE
    + _SERVICE_UUID_UUID
    + _SERVICE_DATA_LENGTH
    + _SERVICE_DATA_TYPE
    + _SERVICE_DATA_UUID
)


@micropython.native
def isExposureNotification(buf: memoryview) -> bool:
    # ExposureNotifications are exactly 31 bytes long
    if len(buf) != 31:
        return False

    # ExposureNotications start with these 11 static bytes
    if buf[0:11] != EXPOSURE_NOTIFICATION:
        return False

    # very likely an ExposureNotification
    return True
