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

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/jackc/pgx/v4"
	"github.com/jackc/pgx/v4/pgxpool"
)

const configTpl = `from micropython import const
import ubinascii

CLIENT_ID = const({{.ID}})
WAKEUP_THRESHOLD = const({{.WakeupThreshold}})  # upload every N wakeups
WIFI_CONNECT_TIMEOUT = const({{.WifiConnectTimeout}})  # seconds
SCAN_TIME = const({{.ScanTime}})  # seconds
SLEEP_TIME = const({{.SleepTime}})  # seconds
EXTENDED_SLEEP_TIME = const(300)  # seconds
AP_NAME = "{{.ApName}}"
AP_PASS = "{{.ApPass}}"
UPLOAD_URL = "{{.UploadURL}}"
OTA_URL = "{{.OtaURL}}"
OTA_INTERVAL = 10  # OTA every N uploads
MAX_PACKET_SIZE = const({{.MaxPacketSize}})  # bytes
MAX_FRAMES_PER_PACKET = const({{.MaxFramesPerPacket}})
EMPTY_WIFI_THRESHOLD = const(10)  # after N scans with no wifis, use EXTENDED_SLEEP_TIME

SSID_EXCLUDE_PREFIX = [
    "AndroidAP",
]
SSID_EXCLUDE_SUFFIX = [
    "_nomap",
]
SSID_EXCLUDE_REGEX = [
    ".*[M|m]obile[ |\-|_]?[H|h]otspot.*",
    ".*[M|m]obile[ |\-|_]?[W|w][I|i][ |\-]?[F|f][I|i].*",
    ".*[M|m][I|i][\-]?[F|f][I|i].*",
    ".*Samsung.*",
    ".*BlackBerry.*",
    ".*iPhone.*",
    ".*iPad.*",
]

SPECIAL_SSIDS = []
__SPECIAL_MACS = []

SPECIAL_MACS = []
for mac in SPECIAL_MACS:
    SPECIAL_MACS.append(ubinascii.unhexlify(mac))
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
	router.Use(cors.Default())

	// API Endpoints
	router.GET("/frames/recent", recentFramesHandle)

	// Firmware Endpoints
	router.GET("/ota/config", configOtaHandle)
	router.POST("/submit", submitHandle)

	if err := router.Run(":1919"); err != nil {
		log.Fatal(err)
	}
}

func recentFramesHandle(c *gin.Context) {
	clientID := c.Query("client_id")
	count := c.Query("count")
	showAllClients := false

	if clientID == "" {
		clientID = "0"
		showAllClients = true
	}
	if count == "" {
		count = "10"
	}

	rows, err := dbpool.Query(context.Background(), `SELECT
		id,
		client_id,
		timestamp,
		battery,
		hall_sensor,
		temperatur_sensor,
		wifis,
		beacon_count,
		received_timestamp
	FROM frames
	WHERE client_id = $1 OR $2
	ORDER BY timestamp DESC
	LIMIT $3`, clientID, showAllClients, count)
	if err != nil {
		if err == pgx.ErrNoRows {
			c.JSON(http.StatusNoContent, nil)
			return
		}

		log.Println(err)
		c.JSON(http.StatusInternalServerError, nil)
		return
	}

	type frame struct {
		ID                uint        `json:"id"`
		ClientID          uint        `json:"client_id"`
		Timestamp         time.Time   `json:"timestamp"`
		Battery           uint        `json:"battery"`
		HallSensor        uint        `json:"hall_sensor"`
		TemperaturSensor  uint        `json:"temperatur_sensor"`
		Wifis             []wifi_go_t `json:"wifis"`
		BeaconCount       uint        `json:"beacon_count"`
		ReceivedTimestamp time.Time   `json:"received_timestamp"`
	}

	var frames []frame
	for rows.Next() {
		var f frame
		if err := rows.Scan(
			&f.ID,
			&f.ClientID,
			&f.Timestamp,
			&f.Battery,
			&f.HallSensor,
			&f.TemperaturSensor,
			&f.Wifis,
			&f.BeaconCount,
			&f.ReceivedTimestamp,
		); err != nil {
			log.Println(err)
			c.JSON(http.StatusInternalServerError, nil)
			return
		}
		frames = append(frames, f)
	}

	c.JSON(http.StatusOK, frames)
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
		c.String(http.StatusInternalServerError, "Scanning row failed.")
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
