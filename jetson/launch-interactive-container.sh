#!/bin/bash

set -xe

DIR="$(dirname "$0")"
DIR="$(cd "$DIR" && pwd)"

docker build -t robot "$DIR"
exec docker run -it --rm \
	-p 8080:8080 \
	-p 5540-5549:5540-5549 \
	-v /tmp/argus_socket:/tmp/argus_socket \
	-v "$PWD":/mnt/host \
	robot
