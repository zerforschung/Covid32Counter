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

const configTpl = `# generated by server, will be overwritten #

CLIENT_ID = {{.ID}}
WAKEUP_THRESHOLD = {{.WakeupThreshold}}  # upload every N wakeups
WIFI_CONNECT_TIMEOUT = {{.WifiConnectTimeout}}  # seconds
SCAN_TIME = {{.ScanTime}}  # seconds
SLEEP_TIME = {{.SleepTime}}  # seconds
EXTENDED_SLEEP_TIME = {{.ExtendedSleepTime}}  # seconds
AP_NAME = "{{.ApName}}"
AP_PASS = "{{.ApPass}}"
UPLOAD_URL = "{{.UploadURL}}"
OTA_URL = "{{.OtaURL}}"
OTA_INTERVAL = {{.OtaInterval}}  # OTA every N uploads
MAX_PACKET_SIZE = {{.MaxPacketSize}}  # bytes
MAX_FRAMES_PER_PACKET = {{.MaxFramesPerPacket}}
EMPTY_WIFI_THRESHOLD = {{.EmptyWifiThreshold}}  # after N scans with no wifis, use EXTENDED_SLEEP_TIME

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

DEPOT_SSIDS = []
DEPOT_MACS = [
    # Britz
    "5C4979F71880",
    "5E4979F71880",
    "7079B36062C1",
    "7079B36062C2",
    "7079B36062C3",
    "7079B36062C4",
    "7079B3606461",
    "7079B3606462",
    "7079B3606463",
    "7079B3606464",
    "7079B36067C1",
    "7079B36067C2",
    "7079B36067C3",
    "7079B36067C4",
    "7079B3606CE1",
    "7079B3606CE2",
    "7079B3606CE3",
    "7079B3606CE4",
    "7079B3606E21",
    "7079B3606E22",
    "7079B3606E23",
    "7079B3606E24",
    "7079B3627121",
    "7079B3627122",
    "7079B3627123",
    "7079B3627124",
    "7079B368ABC1",
    "7079B368ABC2",
    "7079B368ABC3",
    "7079B368ABC4",
    "7079B368CEC1",
    "7079B368CEC2",
    "7079B368CEC3",
    "7079B368CEC4",
    "7079B368D0E1",
    "7079B368D0E3",
    "7079B368D0E4",
    "7079B368D1A1",
    "7079B368D1A2",
    "7079B368D1A3",
    "7079B368D1A4",
    "7079B368D741",
    "7079B368D742",
    "7079B368D743",
    "7079B368D744",
    "7079B3691621",
    "7079B3691622",
    "7079B3691623",
    "7079B3691624",
    "7079B3692101",
    "7079B3692102",
    "7079B3692103",
    "7079B3692104",
    "7079B3692441",
    "7079B3692442",
    "7079B3692443",
    "7079B3692444",
    "7079B36927E1",
    "7079B36927E2",
    "7079B36927E3",
    "7079B36927E4",
    "7079B36E2381",
    "7079B36E2382",
    "7079B36E2383",
    "7079B36E2384",
    "7079B36E2C21",
    "7079B36E2C22",
    "7079B36E2C23",
    "7079B36E2C24",
    "7079B36E2C61",
    "7079B36E2C62",
    "7079B36E2C63",
    "7079B36E2C64",
    "74427F142436",
    "862519605B80",
    "D861627701AB",
    "DE4F22416DFB",
    "E4AA5D8479A1",
    "E4AA5D8479A2",
    "E4AA5D8479A3",
    "E4AA5D8479E1",
    "E4AA5D8479E2",
    "E4AA5D8479E3",
    # Friedrichsfelde
    "001B2F5BBD82",
    "0081C49D68C1",
    "0081C49D68C2",
    "0081C49D68C3",
    "0081C49D68C4",
    "0081C49DB3D1",
    "0081C49DB3D2",
    "0081C49DB3D3",
    "0081C49DB3D4",
    "0081C4F624A2",
    "0081C4F624A4",
    "0081C4F624A5",
    "0081C4F624A6",
    "0081C4F624A8",
    "0081C4F624A9",
    "0081C4F624AA",
    "0081C4F624AB",
    "6802B82C23D3",
    "6A02F82C23D3",
    "7079B3626821",
    "7079B3626822",
    "7079B3626823",
    "7079B3626824",
    "7079B3626D41",
    "7079B3626D42",
    "7079B3626D43",
    "7079B368D861",
    "7079B368D862",
    "7079B368D863",
    "7079B368D864",
    "7079B368D921",
    "7079B368D922",
    "7079B368D923",
    "7079B368D924",
    "7079B3691A23",
    "7079B3691A24",
    "7079B36920E1",
    "7079B36920E2",
    "7079B36920E3",
    "7079B36920E4",
    "7079B3692201",
    "7079B3692202",
    "7079B3692203",
    "7079B3692204",
    "7079B3692541",
    "7079B3692542",
    "7079B3692543",
    "7079B3692544",
    "7079B3692A61",
    "7079B3692A62",
    "7079B3692A63",
    "7079B3692A64",
    "7079B3692A81",
    "7079B3692A82",
    "7079B3692A83",
    "7079B3692A84",
    "7079B36E2261",
    "7079B36E2262",
    "7079B36E2263",
    "7079B36E2264",
    "78DD12CD544C",
    "78DD12CD544E",
    "905C44D07012",
    "946AB025F33D",
    "989BCB51B56A",
    "F086208A0B5E",
    # Grunewald
    "000B6C4443B2",
    "000B6C4447B7",
    "000B6C4447C1",
    "40E230E6521B",
    "704F5718A98E",
    "7079B36063C1",
    "7079B36063C2",
    "7079B36063C3",
    "7079B36063C4",
    "7079B36065A1",
    "7079B36065A2",
    "7079B36065A3",
    "7079B36065A4",
    "7079B360F041",
    "7079B360F042",
    "7079B360F043",
    "7079B360F044",
    "7079B368D3A1",
    "7079B368D3A2",
    "7079B368D3A3",
    "7079B368FDE2",
    "7079B368FDE3",
    "7079B368FDE4",
    "7079B3692521",
    "7079B3692522",
    "7079B3692523",
    "7079B3692524",
    "7079B36927C1",
    "7079B36927C2",
    "7079B36927C3",
    "7079B36927C4",
    "7079B36E2664",
    "7079B36E2701",
    "7079B36E2702",
    "7079B36E2703",
    "7079B36E2704",
    "7079B36E3201",
    "7079B36E3202",
    "7079B36E3203",
    "7079B36E3204",
    "9653307C892C",
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
		HallSensor        int         `json:"hall_sensor"`
		TemperaturSensor  int         `json:"temperatur_sensor"`
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
		extended_sleep_time,
		ap_name,
		ap_pass,
		upload_url,
		ota_url,
		ota_interval,
		max_packet_size,
		max_frames_per_packet,
		empty_wifi_threshold
	FROM clients WHERE id = $1`, clientID)
	var clientConfig struct {
		ID                 uint
		WakeupThreshold    uint
		WifiConnectTimeout uint
		ScanTime           uint
		SleepTime          uint
		ExtendedSleepTime  uint
		ApName             string
		ApPass             string
		UploadURL          string
		OtaURL             string
		OtaInterval        uint
		MaxPacketSize      uint
		MaxFramesPerPacket uint
		EmptyWifiThreshold uint
	}
	if err := row.Scan(
		&clientConfig.ID,
		&clientConfig.WakeupThreshold,
		&clientConfig.WifiConnectTimeout,
		&clientConfig.ScanTime,
		&clientConfig.SleepTime,
		&clientConfig.ExtendedSleepTime,
		&clientConfig.ApName,
		&clientConfig.ApPass,
		&clientConfig.UploadURL,
		&clientConfig.OtaURL,
		&clientConfig.OtaInterval,
		&clientConfig.MaxPacketSize,
		&clientConfig.MaxFramesPerPacket,
		&clientConfig.EmptyWifiThreshold,
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
