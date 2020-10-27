package main

import (
	"bytes"
	"crypto/sha1"
	"encoding/binary"
	"encoding/hex"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"time"
)

const (
	headerWireSize   = 4
	metadataWireSize = 8
	wifiWireSize     = 7
	beaconWireSize   = 20
	checksumWireSize = 20
)

var CWA_MAGIC = [3]byte{
	0x43, // C
	0x57, // W
	0x41, // A
}

type header_t struct {
	Magic   [3]byte
	Version uint8
}

type metadata_t struct {
	TimeStamp   int32
	ClientID    int16
	WifiCount   uint8
	BeaconCount uint8
}

type wifi_t struct {
	MAC  [6]byte
	RSSI int8
}

type beacon_t [20]byte

type protocol struct {
	Header   header_t
	Metadata metadata_t
	Wifis    []wifi_t
	Beacons  []beacon_t
}

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

	var header header_t
	headerOffset := headerWireSize
	headerBytes := bytes.NewReader(payload[0:headerOffset])
	if err := binary.Read(headerBytes, binary.BigEndian, &header); err != nil {
		fmt.Println("header - binary.Read failed:", err)
		http.Error(w, "Can't decode header.", http.StatusBadRequest)
		return
	}

	if header.Magic != CWA_MAGIC {
		fmt.Println("header - Magic not correct.")
		http.Error(w, "You didn't say the magic word.", http.StatusBadRequest)
		return
	}

	var metadata metadata_t
	metadataOffset := headerOffset + metadataWireSize
	metadataBytes := bytes.NewReader(payload[headerOffset:metadataOffset])
	if err := binary.Read(metadataBytes, binary.BigEndian, &metadata); err != nil {
		fmt.Println("metadata - binary.Read failed:", err)
		http.Error(w, "Can't decode metadata.", http.StatusBadRequest)
	}

	wifis := make([]wifi_t, metadata.WifiCount)
	wifiOffset := metadataOffset + len(wifis)*wifiWireSize
	wifiBytes := bytes.NewReader(payload[metadataOffset:wifiOffset])
	if err := binary.Read(wifiBytes, binary.BigEndian, &wifis); err != nil {
		fmt.Println("wifi - binary.Read failed:", err)
		http.Error(w, "Can't decode wifi data.", http.StatusBadRequest)
	}

	beacons := make([]beacon_t, metadata.BeaconCount)
	beaconOffset := wifiOffset + len(wifis)*beaconWireSize
	beaconBytes := bytes.NewReader(payload[wifiOffset:beaconOffset])
	if err := binary.Read(beaconBytes, binary.BigEndian, &beacons); err != nil {
		fmt.Println("beacon - binary.Read failed:", err)
		http.Error(w, "Can't decode beacons data.", http.StatusBadRequest)
	}

	calculatedChecksum := sha1.Sum(payload)

	fmt.Printf(`
Payload Length: %d
HexPayload: %s

Header Magic: %s
Header Version: %d

Timestamp: %d
Client ID: %d

Wifi Count: %d`,
		len(payload),
		hexPayload,
		header.Magic,
		header.Version,
		time.Unix(int64(metadata.TimeStamp), 0).Unix(),
		metadata.ClientID,
		metadata.WifiCount,
	)

	for _, w := range wifis {
		fmt.Printf(`
	MAC: %X
	RSSI: %d
`, w.MAC, w.RSSI)
	}

	fmt.Printf(`
Beacon Count: %d`, metadata.BeaconCount)

	for _, b := range beacons {
		fmt.Printf(`
	Payload: %X
`, b)
	}

	fmt.Printf(`
Calculated Checksum: %X
`, calculatedChecksum)
	fmt.Println("-----------------------")

	if _, err := w.Write(calculatedChecksum[:]); err != nil {
		fmt.Println("Response failed:", err)
	}

}
