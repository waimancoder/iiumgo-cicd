#!/bin/bash

cd /root/iiumgo


sudo cp -rf /root/iiumgo/celery_worker.service /etc/systemd/system/
sudo cp -rf /root/iiumgo/celery_beat.service /etc/systemd/system/

echo "$USER"
echo "$PWD"

sudo systemctl daemon-reload
sudo systemctl start celery_worker


sudo systemctl start celery_worker
echo "Celery Worker has started."

sudo systemctl start celery_beat
echo "Celery Beat has started."

sudo systemctl enable celery_worker
echo "Celery Worker has been enabled."

sudo systemctl enable celery_beat
echo "Celery Beat has been enabled."


sudo systemctl restart celery_worker
sudo systemctl restart celery_beat


sudo systemctl status celery_worker
sudo systemctl status celery_beat