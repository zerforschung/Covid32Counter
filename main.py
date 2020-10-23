from micropython import const
import utime
import uctypes
import ustruct
import ubinascii
import ubluetooth


_IRQ_SCAN_RESULT = const(5)

_ENFlags = {
    "length": 0 | uctypes.UINT8,
    "type": 1 | uctypes.UINT8,
    "flags": 2 | uctypes.UINT8,
}
_ENServiceUUID = {
    "length": 0 | uctypes.UINT8,
    "type": 1 | uctypes.UINT8,
    "uuid": (2 | uctypes.ARRAY, 2 | uctypes.UINT8),
}
_ENServiceData = {
    "length": 0 | uctypes.UINT8,
    "type": 1 | uctypes.UINT8,
    "uuid": (2 | uctypes.ARRAY, 2 | uctypes.UINT8),
    "rolling_identifier": (4 | uctypes.ARRAY, 16 | uctypes.UINT8),
    "encrypted_metadata": (20 | uctypes.ARRAY, 4 | uctypes.UINT8),
}
_ENPayload = {
    "flags": (0, _ENFlags),
    "service_uuid": (3, _ENServiceUUID),
    "service_data": (7, _ENServiceData),
}


def bt_irq(event, data):
    if event == _IRQ_SCAN_RESULT:
        addr_type, addr, adv_type, rssi, adv_data = data

        if (addr_type != 0x1) or (adv_type != 0x3):
            return

        print(
            "addt_type:{} adv_type:{} rssi:{} addr:{} data:{}".format(
                addr_type,
                adv_type,
                rssi,
                ubinascii.hexlify(addr, ":"),
                ubinascii.hexlify(adv_data, "-"),
            )
        )

        t = utime.ticks_us()

        payload = uctypes.struct(uctypes.addressof(adv_data), _ENPayload)

        print(
            payload.flags.length,
            payload.flags.type,
            payload.flags.flags,
            payload.service_uuid.length,
            payload.service_uuid.type,
            ubinascii.hexlify(
                ustruct.pack("<H", *ustruct.unpack(">H", payload.service_uuid.uuid))
            ),
            payload.service_data.length,
            payload.service_data.type,
            ubinascii.hexlify(
                ustruct.pack("<H", *ustruct.unpack(">H", payload.service_data.uuid))
            ),
            ubinascii.hexlify(
                ustruct.pack(
                    "<8H",
                    *ustruct.unpack(">8H", payload.service_data.rolling_identifier)
                )
            ),
            ubinascii.hexlify(
                ustruct.pack(
                    "<2H",
                    *ustruct.unpack(">2H", payload.service_data.encrypted_metadata)
                )
            ),
        )
        print("--------")

        delta = utime.ticks_diff(utime.ticks_us(), t)
        print("parsing took: {:6.3f}ms".format(delta / 1000))

        print("--------\n\n")


bleh = ubluetooth.BLE()
bleh.active(True)
bleh.irq(bt_irq)

bleh.gap_scan()
