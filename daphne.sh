#!/bin/bash

source /var/lib/jenkins/workspace/iiumgo-dev/venv/bin/activate

cd /var/lib/jenkins/workspace/iiumgo-dev

python3 manage.py makemigrations
python3 manage.py migrate

echo "Migrations done"

cd /var/lib/jenkins/workspace/iiumgo-dev

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

