#!/bin/bash
source "/Users/michaelrobinson/Desktop/HTBot/htb Current/venv/bin/activate"
cd "/Users/michaelrobinson/Desktop/HTBot/htb Current"
export PYTHONPATH="/Users/michaelrobinson/Desktop/HTBot/htb Current:/Users/michaelrobinson/Desktop/HTBot/htb Current/src"
exec "/Users/michaelrobinson/Desktop/HTBot/htb Current/venv/bin/celery" -A src.celery_app worker -l info
