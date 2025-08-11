#!/bin/bash
echo "Stopping all wrapper processes..."
pkill -f wrapper || echo "No wrapper processes found"
sleep 1
pkill -9 -f wrapper || true
fuser -k 10020/tcp 20020/tcp >/dev/null 2>&1 || true
echo "Cleanup complete. Current wrapper processes:"
ps aux | grep '[w]rapper'
