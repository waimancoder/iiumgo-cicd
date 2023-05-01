#!/bin/bash

source /root/iiumgo/venv/bin/activate

cd /root/iiumgo

python3 manage.py makemigrations
python3 manage.py migrate

echo "Migrations done"

cd /root/iiumgo

sudo cp -rf daphne_server.service /etc/systemd/system/

echo "$USER"
echo "$PWD"

sudo systemctl daemon-reload
sudo systemctl start daphne_server

echo "Daphne has started."

sudo systemctl enable daphne_server

echo "Daphne has been enabled."


sudo systemctl restart daphne_server

sudo systemctl status daphne_server

