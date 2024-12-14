#!/bin/bash
source "/Users/michaelrobinson/Desktop/HTBot/htb Current/venv/bin/activate"
cd "/Users/michaelrobinson/Desktop/HTBot/htb Current"
export PYTHONPATH="/Users/michaelrobinson/Desktop/HTBot/htb Current:/Users/michaelrobinson/Desktop/HTBot/htb Current/src"
exec python ib_connection_manager.py
