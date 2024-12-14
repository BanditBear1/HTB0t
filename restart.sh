#!/bin/bash

echo "Stopping all existing processes..."
# Kill existing processes
pkill -f supervisord
pkill -f redis-server
pkill -f "celery worker"
pkill -f "celery beat"
pkill -f "connect_test.py"
pkill -f "ib_connection_manager.py"

# Remove stale socket and pid files
rm -f /tmp/supervisor.sock
rm -f /tmp/supervisord.pid
rm -f /tmp/celery.pid

echo "Starting supervisor..."
# Start supervisor with correct environment
PYTHONPATH=/Users/michaelrobinson/Desktop/HTBot/htb\ Current:/Users/michaelrobinson/Desktop/HTBot/htb\ Current/src supervisord -c supervisord.conf

# Wait for supervisor to start
sleep 3

echo "Starting all services..."
supervisorctl start all

echo "Starting Celery Beat for scheduled tasks..."
# Start Celery Beat for task scheduling
PYTHONPATH=/Users/michaelrobinson/Desktop/HTBot/htb\ Current:/Users/michaelrobinson/Desktop/HTBot/htb\ Current/src venv/bin/celery -A celery_app beat --detach --pidfile=/tmp/celery.pid

# Wait for services to initialize
sleep 5

echo "Checking service status..."
supervisorctl status

echo "Setup complete! The algo is ready to trade."
