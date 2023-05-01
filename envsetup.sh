#!/bin/bash

if [ -d "venv" ] 
then
    echo "Python virtual environment exists." 
else
    python3 -m venv venv
fi

npm install


# sudo cp -rf docker-compose.service /etc/systemd/system/

# echo "Building docker images"
# sudo docker compose build

# echo "Starting docker images"
# sudo docker stop mytaxi
# sudo docker compose up -d --remove-orphans

source /root/iiumgo/venv/bin/activate

pip3 install -r requirements.txt

if [ -d "logs" ] 
then
    echo "Log folder exists." 
else
    mkdir logs
    touch logs/mytaxi_error.log logs/mytaxi_info.log
fi

sudo chmod -R 777 logs