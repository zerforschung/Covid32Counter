package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"log"
	"net/http"
	"os"
	"strings"
	"text/template"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
)

const configTpl = `from micropython import const

CLIENT_ID = const({{.ID}})
WAKEUP_THRESHOLD = const({{.WakeupThreshold}})  # upload every N wakeups
WIFI_CONNECT_TIMEOUT = const({{.WifiConnectTimeout}})  # seconds
SCAN_TIME = const({{.ScanTime}})  # seconds
SLEEP_TIME = const({{.SleepTime}})  # seconds
AP_NAME = "{{.ApName}}"
AP_PASS = "{{.ApPass}}"
UPLOAD_URL = "{{.UploadURL}}"
OTA_URL = "{{.OtaURL}}"
MAX_PACKET_SIZE = const({{.MaxPacketSize}})  # bytes
MAX_FRAMES_PER_PACKET = const({{.MaxFramesPerPacket}})

SSID_EXCLUDE_PREFIX = [
    "AndroidAP",
]
SSID_EXCLUDE_SUFFIX = [
    "_nomap",
    "iPhone",
]
SSID_EXCLUDE_REGEX = [
    ".*[M|m]obile[ |\-|_]?[H|h]otspot.*",
    ".*[M|m]obile[ |\-|_]?[W|w][I|i][ |\-]?[F|f][I|i].*",
    ".*[M|m][I|i][\-]?[F|f][I|i].*",
    ".*Samsung.*",
    ".*BlackBerry.*",
]
`

var (
	tpl    *template.Template
	dbpool *pgxpool.Pool
	err    error
)

func main() {
	tpl = template.Must(template.New("config").Parse(configTpl))

	dbpool, err = pgxpool.Connect(context.Background(), os.Getenv("DATABASE_URL"))
	if err != nil {
		log.Fatalf("Unable to connect to database: %v\n", err)
	}
	defer dbpool.Close()

	router := gin.Default()

	router.GET("/ota/config", configOtaHandle)
	router.POST("/submit", submitHandle)

	if err := router.Run(":1919"); err != nil {
		log.Fatal(err)
	}
}

func configOtaHandle(c *gin.Context) {
	clientID := c.Query("client_id")
	if clientID == "" {
		c.String(http.StatusBadRequest, "Client ID missing.")
		return
	}

	row := dbpool.QueryRow(context.Background(), `SELECT
		id,
		wakeup_threshold,
		wifi_connect_timeout,
		scan_time,
		sleep_time,
		ap_name,
		ap_pass,
		upload_url,
		ota_url,
		max_packet_size,
		max_frames_per_packet
	FROM clients WHERE id = $1`, clientID)
	var clientConfig struct {
		ID                 uint
		WakeupThreshold    uint
		WifiConnectTimeout uint
		ScanTime           uint
		SleepTime          uint
		ApName             string
		ApPass             string
		UploadURL          string
		OtaURL             string
		MaxPacketSize      uint
		MaxFramesPerPacket uint
	}
	if err := row.Scan(
		&clientConfig.ID,
		&clientConfig.WakeupThreshold,
		&clientConfig.WifiConnectTimeout,
		&clientConfig.ScanTime,
		&clientConfig.SleepTime,
		&clientConfig.ApName,
		&clientConfig.ApPass,
		&clientConfig.UploadURL,
		&clientConfig.OtaURL,
		&clientConfig.MaxPacketSize,
		&clientConfig.MaxFramesPerPacket,
	); err != nil {
		log.Println(err)
		c.String(http.StatusBadRequest, "Scanning row failed.")
		return
	}

	if _, err := dbpool.Exec(context.Background(), "UPDATE clients SET last_ota_timestamp = NOW() WHERE id = $1", clientID); err != nil {
		log.Println(err)
	}

	config := new(strings.Builder)
	if err := tpl.Execute(config, clientConfig); err != nil {
		log.Println(err)
		c.String(http.StatusInternalServerError, "Template didn't execute.")
		return
	}

	digest := sha256.Sum256([]byte(config.String()))
	configHash := hex.EncodeToString(digest[:])
	c.Header("Hash", configHash)
	c.String(http.StatusOK, config.String())
}

func submitHandle(c *gin.Context) {
	payload, _ := c.GetRawData()

	packet, err := parsePacket(payload)
	if err != nil {
		c.String(http.StatusBadRequest, "Can't decode packet.")
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

		for _, b := range frame.Beacons {
			bg := b.toGoType()
			if _, err := dbpool.Exec(context.Background(), "INSERT INTO beacons(data, rssi, frame_id) VALUES ($1, $2, $3)", bg.Data, bg.RSSI, frameID); err != nil {
				log.Println(err)
			}
		}
	}

	c.Data(http.StatusOK, "application/octet-stream", packet.Checksum[:])
}
