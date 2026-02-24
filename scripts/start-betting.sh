#!/bin/bash
# Restart betting tracker Docker services at 6am
# Ensure Docker Desktop is running first
open -a Docker

# Wait for Docker daemon to be ready (up to 60 seconds)
for i in $(seq 1 60); do
    if /usr/local/bin/docker info >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

if ! /usr/local/bin/docker info >/dev/null 2>&1; then
    echo "Docker daemon did not start in time" >&2
    exit 1
fi

cd /Users/bsslbj/Desktop/FirstUse/betting-monitor
/usr/local/bin/docker-compose down
/usr/local/bin/docker-compose up -d
