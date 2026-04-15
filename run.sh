#!/bin/bash

echo "Starting application..."

docker compose -f docker/docker-compose.yml up --build
