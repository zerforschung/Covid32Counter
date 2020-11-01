from micropython import const
import machine
import ntptime
import ubinascii
import uos
import utime


IRQ_SCAN_RESULT = const(5)
IRQ_SCAN_DONE = const(6)

EPOCH_OFFSET = const(946681200)  # seconds between 1970 and 2000

ONBOARD_LED = const(2)


@micropython.native
def second_to_millisecond(i: int) -> int:
    return i * 1000


@micropython.native
def second_to_microsecond(i: int) -> int:
    return i * 1000 * 1000


@micropython.native
def now() -> int:
    return utime.time() + EPOCH_OFFSET


@micropython.native
def syslog(categorie: str, message: str):
    print("-- [{}] -- {}".format(categorie, message))


@micropython.native
def openFile(filename: str):
    try:
        return open(filename, "r+b")
    except OSError:
        return open(filename, "w+b")


@micropython.native
def syncTime():
    if (
        (machine.reset_cause() != machine.DEEPSLEEP)  # if fresh start
        or (EPOCH_OFFSET + utime.time() < 1600000000)  # if time is before 2020-09-13
        or ((ubinascii.crc32(uos.urandom(1)) % 10) == 0)  # if randInt%10 == 0
    ):
        try:
            ntptime.settime()
            syslog("Time", "Synced via NTP.")
        except Exception as e:
            syslog("Time", "Error getting NTP: {}", e)
            pass
