CREATE TABLE clients (
	id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
	firmware_version TEXT NOT NULL,
	description TEXT
);

CREATE TABLE keys (
	id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
	data TEXT,
	import_date DATE,
	UNIQUE (data)
);
CREATE INDEX keys_idx_import_date ON keys (import_date);

CREATE TABLE frames (
	id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
	client_id INTEGER REFERENCES clients,
	timestamp TIMESTAMP NOT NULL,
	battery INTEGER NOT NULL,
	hall_sensor INTEGER NOT NULL,
	temperatur_sensor INTEGER NOT NULL,
	wifis JSONB,
	beacon_count INTEGER
);
CREATE INDEX frames_idx_timestamp ON frames (timestamp);
CREATE INDEX frames_idx_client_id ON frames (client_id);

CREATE TABLE beacons (
	id INTEGER PRIMARY KEY GENERATED BY DEFAULT AS IDENTITY,
	data TEXT,
	rssi INTEGER NOT NULL,
	frame_id INTEGER REFERENCES frames,
	key_id INTEGER REFERENCES keys
);
CREATE INDEX beacons_idx_data ON beacons (data);