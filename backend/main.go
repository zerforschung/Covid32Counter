package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"time"
)

const (
	packetHeaderWireSize = 7
	frameHeaderWireSize  = 12
	wifiWireSize         = 7
	beaconWireSize       = 21
	checksumWireSize     = 32
)

var CWA_MAGIC = [3]byte{
	0x43, // C
	0x57, // W
	0x41, // A
}

type packetHeader_t struct {
	Magic      [3]byte
	Version    uint8
	ClientID   int16
	FrameCount uint8
}

type frameHeader_t struct {
	TimeStamp        int32
	BatteryStatus    uint16
	HallSensor       int16
	TemperaturSensor int16
	WifiCount        uint8
	BeaconCount      uint8
}

type wifi_t struct {
	MAC  [6]byte
	RSSI int8
}

type beacon_t struct {
	Data [20]byte
	RSSI int8
}

// type protocol struct {
// 	Header   packetHeader_t
// 	Frame frameHeader_t
// 	Wifis    []wifi_t
// 	Beacons  []beacon_t
// 	Checksum [32]byte
// }

func main() {
	http.HandleFunc("/", decoderHandle)

	if err := http.ListenAndServe(":1919", nil); err != nil {
		log.Fatal(err)
	}
}

func decoderHandle(w http.ResponseWriter, r *http.Request) {
	defer r.Body.Close()

	payload, _ := ioutil.ReadAll(r.Body)
	hexPayload := hex.EncodeToString(payload)

	var packetHeader packetHeader_t
	packetHeaderOffset := packetHeaderWireSize
	packetHeaderBytes := bytes.NewReader(payload[0:packetHeaderOffset])
	if err := binary.Read(packetHeaderBytes, binary.BigEndian, &packetHeader); err != nil {
		fmt.Println("header - binary.Read failed:", err)
		http.Error(w, "Can't decode packet header.", http.StatusBadRequest)
		return
	}

	if packetHeader.Magic != CWA_MAGIC {
		fmt.Println("header - Magic not correct.")
		http.Error(w, "You didn't say the magic word.", http.StatusBadRequest)
		return
	}

	var frame frameHeader_t
	frameOffset := packetHeaderOffset + frameHeaderWireSize
	frameBytes := bytes.NewReader(payload[packetHeaderOffset:frameOffset])
	if err := binary.Read(frameBytes, binary.BigEndian, &frame); err != nil {
		fmt.Println("frame - binary.Read failed:", err)
		http.Error(w, "Can't decode frame.", http.StatusBadRequest)
		return
	}

	wifis := make([]wifi_t, frame.WifiCount)
	wifiOffset := frameOffset + len(wifis)*wifiWireSize
	wifiBytes := bytes.NewReader(payload[frameOffset:wifiOffset])
	if err := binary.Read(wifiBytes, binary.BigEndian, &wifis); err != nil {
		fmt.Println("wifi - binary.Read failed:", err)
		http.Error(w, "Can't decode wifi data.", http.StatusBadRequest)
		return
	}

	beacons := make([]beacon_t, frame.BeaconCount)
	beaconOffset := wifiOffset + len(wifis)*beaconWireSize
	beaconBytes := bytes.NewReader(payload[wifiOffset:beaconOffset])
	if err := binary.Read(beaconBytes, binary.BigEndian, &beacons); err != nil {
		fmt.Println("beacon - binary.Read failed:", err)
		http.Error(w, "Can't decode beacons data.", http.StatusBadRequest)
		return
	}

	calculatedChecksum := sha256.Sum256(payload)

	fmt.Printf(`
Payload Length: %d
HexPayload: %s

Packet Header Magic: %s
Packet Header Version: %d
Client ID: %d

Frame Count: %d

Timestamp: %d

Wifi Count: %d`,
		len(payload),
		hexPayload,
		packetHeader.Magic,
		packetHeader.Version,
		packetHeader.ClientID,
		time.Unix(int64(frame.TimeStamp), 0).Unix(),
		frame.WifiCount,
	)

	for _, w := range wifis {
		fmt.Printf(`
	MAC: %X
	RSSI: %d
`, w.MAC, w.RSSI)
	}

	fmt.Printf(`
Beacon Count: %d`, frame.BeaconCount)

	for _, b := range beacons {
		fmt.Printf(`
	Payload: %X
	RSSI: %d
`, b.Data, b.RSSI)
	}

	fmt.Printf(`
Calculated Checksum: %X
`, calculatedChecksum)
	fmt.Println("-----------------------")

	if _, err := w.Write(calculatedChecksum[:]); err != nil {
		fmt.Println("Response failed:", err)
		return
	}
}
