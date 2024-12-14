#!/bin/bash

# Kill any existing supervisor processes
pkill -f supervisord

# Clean up socket and pid files
rm -f /tmp/supervisor.sock
rm -f /tmp/supervisord.pid

# Start supervisor
supervisord -c "$(pwd)/supervisord.conf"

# Wait for socket file to be created
sleep 2

# Check status
supervisorctl status
