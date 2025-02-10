#!/bin/bash

IMAGE_NAME=ghcr.io/hotosm/fmtm/basemap-generator:0.3.0

echo "Building ${IMAGE_NAME}"
docker build . --tag "${IMAGE_NAME}"

if [[ -n "$PUSH_IMG" ]]; then
    docker push "${IMAGE_NAME}"
fi
