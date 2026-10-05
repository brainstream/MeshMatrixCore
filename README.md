# MeshMatrixCore

Bridge between MeshCore channels and Matrix rooms.

![Screenshots](screenshots/screenshots.png)

## Docker

To build the Docker image, run:

```sh
docker build -t meshmatrixcore .
```

To run the Docker container, use:

```sh
docker run --rm --device=/dev/ttyACM0:/dev/ttyACM0 --volume=./config.toml:/app/config.toml meshmatrixcore:latest
```

Specify your device path and config file path as needed.
