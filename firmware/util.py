from micropython import const
import ntptime
import ubinascii
import uhashlib
import uos
import ure
import utime
import uuurequests

import config


IRQ_SCAN_RESULT = const(5)
IRQ_SCAN_DONE = const(6)

EPOCH_OFFSET = const(946681200)  # seconds between 1970 and 2000

ONBOARD_LED = const(2)

__SPECIAL_SSIDS = set()
__SPECIAL_MACS = set()


def removeIgnoredSSIDs(nets):
    new_nets = []

    compiled_regex = []
    for regex in config.SSID_EXCLUDE_REGEX:
        compiled_regex.append(ure.compile(regex))

    for net in nets:
        ssid, mac, channel, rssi, authmode, hidden = net
        isIgnored = False

        if hidden:
            continue

        for prefix in config.SSID_EXCLUDE_PREFIX:
            if ssid.startswith(prefix):
                isIgnored = True
                break

        if isIgnored:
            continue

        for suffix in config.SSID_EXCLUDE_SUFFIX:
            if ssid.endswith(suffix):
                isIgnored = True
                break

        if isIgnored:
            continue

        for r in compiled_regex:
            if r.match(ssid):
                isIgnored = True
                break

        if isIgnored:
            continue

        new_nets.append(net)

    return new_nets


def second_to_millisecond(i: int) -> int:
    return i * const(1000)


def second_to_microsecond(i: int) -> int:
    return i * const(1000 * 1000)


def now() -> int:
    return utime.time() + EPOCH_OFFSET


def syslog(categorie: str, message: str):
    print("-- [{}] -- {}".format(categorie, message))


def openFile(filename: str):
    try:
        return open(filename, "r+b")
    except OSError:
        return open(filename, "w+b")


def syncTime():
    try:
        ntptime.settime()
        syslog("Time", "Synced via NTP.")
    except Exception as e:
        syslog("Time", "Error getting NTP: {}".format(e))


def otaUpdateConfig():
    try:
        r = uuurequests.get(
            "{}/config?client_id={}".format(config.OTA_URL, config.CLIENT_ID)
        )
        if (r.status_code == 200) and (
            ubinascii.unhexlify(r.headers["Hash"])
            == uhashlib.sha256(r.content).digest()
        ):
            with openFile("new_config.py") as f:
                f.write(r.content)
            uos.rename("new_config.py", "config.py")
            syslog("OTA", "Updated config.py")
        else:
            syslog("OTA", "Hash mismatch, cowardly refusing to install update!")
    except Exception as e:
        syslog("OTA", "Error getting updates: {}".format(e))


def prepareSpecialWifiSets():
    for ssid in config.SPECIAL_SSIDS:
        __SPECIAL_SSIDS.add([ssid])

    for mac in config.SPECIAL_MACS:
        mac = mac.replace(":", "")
        mac = mac.replace("-", "")
        mac = mac.replace(" ", "")
        __SPECIAL_MACS.add([ubinascii.unhexlify(mac)])


def isSpecialWifi(ssid: str, mac: bytes) -> bool:
    if ssid in __SPECIAL_SSIDS:
        return True

    if mac in __SPECIAL_MACS:
        return True

    return False
