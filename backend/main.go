package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
)

var (
	dbpool *pgxpool.Pool
	err    error
)

func main() {
	dbpool, err = pgxpool.Connect(context.Background(), os.Getenv("DATABASE_URL"))
	if err != nil {
		log.Fatalf("Unable to connect to database: %v\n", err)
	}
	defer dbpool.Close()

	http.HandleFunc("/", decoderHandle)
	if err := http.ListenAndServe(":1919", nil); err != nil {
		log.Fatal(err)
	}
}

func decoderHandle(w http.ResponseWriter, r *http.Request) {
	defer r.Body.Close()

	payload, _ := ioutil.ReadAll(r.Body)

	packet, err := parsePacket(payload)
	if err != nil {
		http.Error(w, "Can't decode packet.", http.StatusBadRequest)
		fmt.Println(err)
		return
	}

	for _, frame := range packet.Frames {
		var wifis []wifi_go_t
		for _, w := range frame.Wifis {
			wifis = append(wifis, w.toGoType())
		}

		row := dbpool.QueryRow(context.Background(), `INSERT INTO frames(
			client_id,
			timestamp,
			battery,
			hall_sensor,
			temperatur_sensor,
			wifis,
			beacon_count
			) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id`,
			packet.Header.ClientID,
			time.Unix(int64(frame.Header.TimeStamp), 0),
			frame.Header.BatteryStatus,
			frame.Header.HallSensor,
			frame.Header.TemperaturSensor,
			wifis,
			frame.Header.BeaconCount,
		)
		var frameID int64
		if err := row.Scan(&frameID); err != nil && err == pgx.ErrNoRows {
			log.Println(err)
		}

		var beacons []beacon_go_t
		for _, b := range frame.Beacons {
			bg := b.toGoType()
			beacons = append(beacons, bg)
			if _, err := dbpool.Exec(context.Background(), "INSERT INTO beacons(data, rssi, frame_id) VALUES ($1, $2, $3)", bg.Data, bg.RSSI, frameID); err != nil {
				log.Println(err)
			}
		}

		bla := struct {
			Client           int16
			Timestamp        int32
			Battery          uint16
			HallSensor       int16
			TemperaturSensor int16
			Wifis            []wifi_go_t
			Beacons          []beacon_go_t
		}{
			packet.Header.ClientID,
			frame.Header.TimeStamp,
			frame.Header.BatteryStatus,
			frame.Header.HallSensor,
			frame.Header.TemperaturSensor,
			wifis,
			beacons,
		}

		j, err := json.MarshalIndent(bla, "", "  ")
		if err != nil {
			log.Println(err)
		}

		fmt.Println(string(j))
	}

	if _, err := w.Write(packet.Checksum[:]); err != nil {
		fmt.Println("Response failed:", err)
		return
	}
}
