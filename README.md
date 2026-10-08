# MeshMatrixCore

MeshMatrixCore relays text messages between [Matrix](https://matrix.org/) rooms and MeshCore channels.

![MeshMatrixCore bridging a Matrix room and a MeshCore channel](screenshots/screenshots.png)

## Configuration

Copy the example and edit it to suit your configuration:

```sh
cp config.example.toml config.toml
```

By default, the app reads `config.toml` from the current directory. When running directly, use `-c PATH` or `--config PATH` to select another file. In Docker, mount the file at `/app/config.toml`.

### Matrix

Set the homeserver URL and access token for the Matrix account the bridge will use:

```toml
[matrix]
homeserver = "https://matrix.org"
access_token = "your-access-token"
```

### MeshCore

Choose one connection type and fill in its settings. Only the selected transport's settings are used. Set `connection` under `[meshcore]` to `serial`, `ble`, or `tcp`:

```toml
[meshcore]
connection = "serial"
```

For a `serial` connection, set the device `port` (required) and optionally the `baudrate` (defaults to `115200`). Prefer a stable path such as `/dev/serial/by-id/...`; `/dev/ttyUSB0` may change after reconnecting:

```toml
[meshcore.serial]
port = "/dev/serial/by-id/usb-Espressif_ESP32-S3_w_USB_CDC_112233445566-if00"
baudrate = 115200
```

For a `ble` connection, set the device `address` (required) and optionally `pin` and `device`:

```toml
[meshcore.ble]
address = "12:34:56:78:90:AB"
pin = "123456"
device = "hci0"
```

For a `tcp` connection, set the `host` and `port` (both required):

```toml
[meshcore.tcp]
host = "192.168.1.100"
port = 4000
```

### Synchronization

Add one `[[sync.rule]]` entry per Matrix room and MeshCore channel to bridge:

```toml
[[sync.rule]]
matrix_room_id = "!Phel3ohTh5quie7fee:example.org"
meshcore_channel_idx = 1
```

Set `fanout` under `[sync]` to send a message to every matching rule. The default is `false`, which stops after the first match:

```toml
[sync]
fanout = false
```

### Logging

Set the application log verbosity under `[logging]`:

```toml
[logging]
level = "INFO"
```

Accepted values are `DEBUG`, `INFO` (default), `WARNING`, `ERROR`, and `CRITICAL`.

## Running MeshMatrixCore

### Docker

Run the published image. For a serial connection, pass the adapter device through to the container:

```sh
docker run --rm \
  --device=/dev/ttyACM0:/dev/ttyACM0 \
  --volume=./config.toml:/app/config.toml:ro \
  brainstream/meshmatrixcore:latest
```

Replace the device and config paths as needed. BLE and TCP connections do not need the `--device` option.

For Docker Compose, save this as `compose.yaml` beside `config.toml` and adjust the device path if needed:

```yaml
services:
  meshmatrixcore:
    image: brainstream/meshmatrixcore:latest
    devices:
      - /dev/ttyACM0:/dev/ttyACM0
    volumes:
      - ./config.toml:/app/config.toml:ro
    restart: unless-stopped
```

Start the service with `docker compose up -d`.

### From source

Requires Python 3.14 or newer. Install and run the package with:

```sh
python -m pip install .
python -m mmc --config config.toml
```

### Message handling

Text messages are relayed in both directions. Matrix messages include the sender's display name; long messages are split into numbered parts (up to nine). Non-text Matrix messages cannot be sent over MeshCore, so the bridge posts a notice in the room. MeshCore messages are posted to Matrix with a bold sender header and HTML and plain-text formatting. The sender is read from the incoming `name: text` format. Messages sent by the bridge are recognised to prevent loops.

## Development

Install the project and test dependencies, then run the tests and quality checks:

```sh
python -m pip install -e ".[test,debug,lint]"
python -m pytest
basedpyright .
ruff check .
ruff format --check .
```

Tests are in `tests/`; pytest adds `src/` to the import path.

## License

GNU General Public License v3.0 or later. See [`LICENSE.txt`](LICENSE.txt).
