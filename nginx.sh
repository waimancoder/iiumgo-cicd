#!/bin/bash

sudo cp -rf app.conf /etc/nginx/conf.d
chmod 710 /root/iiumgo

sudo nginx -t

sudo systemctl start nginx
sudo systemctl enable nginx

echo "Nginx has been started"

sudo systemctl restart nginx

sudo systemctl status nginx