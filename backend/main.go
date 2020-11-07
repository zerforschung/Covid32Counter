package main

import (
	"encoding/hex"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"time"
)

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

	packet, err := parsePacket(payload)
	if err != nil {
		http.Error(w, "Can't decode packet.", http.StatusBadRequest)
		fmt.Println(err)
		return
	}

	fmt.Printf(`
Payload Length: %d
HexPayload: %s

Packet Header
	Magic: %s
	Version: %d
	Client ID: %d
	Frame Count: %d
`,
		len(payload),
		hexPayload,
		packet.Header.Magic,
		packet.Header.Version,
		packet.Header.ClientID,
		packet.Header.FrameCount,
	)

	for _, f := range packet.Frames {
		fmt.Printf(`
Frame
	Timestamp: %s
	Battery Status: %d
	Temperatur Sensor: %d
	Hall Sensor: %d
	Wifi Count: %d
	Beacon Count: %d`,
			time.Unix(int64(f.Header.TimeStamp), 0),
			f.Header.BatteryStatus,
			f.Header.TemperaturSensor,
			f.Header.HallSensor,
			f.Header.WifiCount,
			f.Header.BeaconCount,
		)

		fmt.Printf(`

	Wifis:`)

		for _, w := range f.Wifis {
			fmt.Printf(`
		MAC: %X
		RSSI: %d`, w.MAC, w.RSSI)
		}

		fmt.Printf(`

	Beacons:`)

		for _, b := range f.Beacons {
			fmt.Printf(`
		Payload: %X
		RSSI: %d`, b.Data, b.RSSI)
		}
	}

	fmt.Printf(`

Checksum: %X
`, packet.Checksum)
	fmt.Println("-----------------------")

	if _, err := w.Write(packet.Checksum[:]); err != nil {
		fmt.Println("Response failed:", err)
		return
	}
}
