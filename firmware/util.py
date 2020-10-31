from micropython import const
import gc
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
def collectGarbage():
    syslog("GC", "before collection: {} free".format(gc.mem_free()))
    gc.collect()
    syslog("GC", "after collection: {} free".format(gc.mem_free()))


@micropython.native
def openFile(filename: str):
    try:
       return open(filename, "r+b")
    except OSError:
       return open(filename, "w+b")
