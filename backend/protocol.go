package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/binary"
	"encoding/hex"
	"errors"
	"fmt"
	"strings"
)

const (
	PACKET_HEADER_WIRESIZE uint = 7
	FRAME_HEADER_WIRESIZE  uint = 12
	WIFI_WIRESIZE          uint = 7
	BEACON_WIRESIZE        uint = 21
	CHECKSUM_WIRESIZE      uint = 32
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

type wifi_go_t struct {
	MAC  string `json:"macAddress"`
	RSSI int8   `json:"signalStrength"`
}

func (w *wifi_t) toGoType() wifi_go_t {
	sl := strings.Split(hex.EncodeToString(w.MAC[:]), "")
	var sl2 []string
	for i, v := range sl {
		sl2 = append(sl2, v)
		if i+1 == len(sl) {
			break
		}
		if (i+1)%2 == 0 {
			sl2 = append(sl2, ":")
		}
	}
	macAddress := strings.Join(sl2, "")

	return wifi_go_t{
		strings.ToUpper(macAddress),
		w.RSSI,
	}
}

type beacon_t struct {
	Data [20]byte
	RSSI int8
}

type beacon_go_t struct {
	Data string
	RSSI int8
}

func (b *beacon_t) toGoType() beacon_go_t {
	return beacon_go_t{
		strings.ToUpper(hex.EncodeToString(b.Data[:])),
		b.RSSI,
	}
}

type frame_t struct {
	Header  frameHeader_t
	Wifis   []wifi_t
	Beacons []beacon_t
}

type packet_t struct {
	Header   packetHeader_t
	Frames   []frame_t
	Checksum [CHECKSUM_WIRESIZE]byte
}

func parsePacket(buf []byte) (packet_t, error) {
	var packet packet_t

	checksumOffset := len(buf) - int(CHECKSUM_WIRESIZE)
	packetHeaderOffset := PACKET_HEADER_WIRESIZE

	packetHeaderBytes := bytes.NewReader(buf[0:packetHeaderOffset])
	if err := binary.Read(packetHeaderBytes, binary.BigEndian, &packet.Header); err != nil {
		// http.Error(w, "Can't decode packet header.", http.StatusBadRequest)
		return packet_t{}, fmt.Errorf("header - binary.Read failed: %s", err.Error())
	}

	if packet.Header.Magic != CWA_MAGIC {
		// http.Error(w, "You didn't say the magic word.", http.StatusBadRequest)
		return packet_t{}, errors.New("header - Magic not correct.")
	}

	packet.Checksum = sha256.Sum256(buf[:checksumOffset])
	receivedChecksum := buf[checksumOffset : checksumOffset+int(CHECKSUM_WIRESIZE)]
	if !bytes.Equal(receivedChecksum, packet.Checksum[:]) {
		return packet_t{}, errors.New("Checksum mismatch")
	}

	var err error
	if packet.Frames, err = parseFrames(buf[packetHeaderOffset:checksumOffset], packet.Header.FrameCount); err != nil {
		return packet_t{}, err
	}

	return packet, nil
}

func parseFrames(buf []byte, frameCount uint8) ([]frame_t, error) {
	var frames []frame_t

	var frameOffset uint = 0

	for i := 0; i < int(frameCount); i++ {
		var (
			frame frame_t
			err   error
		)

		wifiOffset := frameOffset + FRAME_HEADER_WIRESIZE

		frameHeaderBytes := bytes.NewReader(buf[frameOffset:wifiOffset])
		if err := binary.Read(frameHeaderBytes, binary.BigEndian, &frame.Header); err != nil {
			// http.Error(w, "Can't decode frame header.", http.StatusBadRequest)
			return nil, fmt.Errorf("frame header - binary.Read failed: %s", err.Error())
		}

		beaconOffset := wifiOffset + uint(frame.Header.WifiCount)*WIFI_WIRESIZE

		if frame.Wifis, err = parseWifis(buf[wifiOffset:beaconOffset], frame.Header.WifiCount); err != nil {
			return nil, err
		}

		beaconEnd := beaconOffset + uint(frame.Header.BeaconCount)*BEACON_WIRESIZE
		if frame.Beacons, err = parseBeacons(buf[beaconOffset:beaconEnd], frame.Header.BeaconCount); err != nil {
			return nil, err
		}

		frames = append(frames, frame)
		frameOffset = beaconEnd
	}

	return frames, nil
}

func parseWifis(buf []byte, wifiCount uint8) ([]wifi_t, error) {
	wifis := make([]wifi_t, wifiCount)

	wifiBytes := bytes.NewReader(buf)
	if err := binary.Read(wifiBytes, binary.BigEndian, &wifis); err != nil {
		// http.Error(w, "Can't decode wifi data.", http.StatusBadRequest)
		return nil, fmt.Errorf("wifi - binary.Read failed: %s", err)
	}

	return wifis, nil
}

func parseBeacons(buf []byte, beaconCount uint8) ([]beacon_t, error) {
	beacons := make([]beacon_t, beaconCount)

	beaconBytes := bytes.NewReader(buf)
	if err := binary.Read(beaconBytes, binary.BigEndian, &beacons); err != nil {
		// http.Error(w, "Can't decode beacon data.", http.StatusBadRequest)
		return nil, fmt.Errorf("beacon - binary.Read failed: %s", err)
	}

	return beacons, nil
}
