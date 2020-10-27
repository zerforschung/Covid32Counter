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
	metadataWireSize = 6
	wifiWireSize     = 7
	beaconWireSize   = 20
	checksumWireSize = 20
)

type metadata_t struct {
	TimeStamp   int32
	WifiCount   uint8
	BeaconCount uint8
}

type wifi_t struct {
	MAC  [6]byte
	RSSI int8
}

type beacon_t [20]byte

type protocol struct {
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

	var metadata metadata_t
	metadataOffset := metadataWireSize
	metadataBytes := bytes.NewReader(payload[0:metadataOffset])
	if err := binary.Read(metadataBytes, binary.LittleEndian, &metadata); err != nil {
		fmt.Println("binary.Read failed:", err)
		http.Error(w, "Can't decode metadata.", http.StatusBadRequest)
	}

	wifis := make([]wifi_t, metadata.WifiCount)
	wifiOffset := metadataOffset + len(wifis)*wifiWireSize
	wifiBytes := bytes.NewReader(payload[metadataOffset:wifiOffset])
	if err := binary.Read(wifiBytes, binary.LittleEndian, &wifis); err != nil {
		fmt.Println("binary.Read failed:", err)
		http.Error(w, "Can't decode wifi data.", http.StatusBadRequest)
	}

	beacons := make([]beacon_t, metadata.BeaconCount)
	beaconOffset := wifiOffset + len(wifis)*beaconWireSize
	beaconBytes := bytes.NewReader(payload[wifiOffset:beaconOffset])
	if err := binary.Read(beaconBytes, binary.LittleEndian, &beacons); err != nil {
		fmt.Println("binary.Read failed:", err)
		http.Error(w, "Can't decode beacons data.", http.StatusBadRequest)
	}

	calculatedChecksum := sha1.Sum(payload)

	fmt.Printf(`
Payload Length: %d
HexPayload: %s

Timestamp: %d

Wifi Count: %d`,
		len(payload),
		hexPayload,
		time.Unix(int64(metadata.TimeStamp), 0).Unix(),
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
