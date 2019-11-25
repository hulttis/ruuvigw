#!/bin/bash
# copy to app directory (one level up from ruuvigw)
systemctl stop ruuvigw
rm -frv ./ruuvigw/new
cp -v ./ruuvigw/ruuvigw.json .
cp -v ./ruuvigw/ruuvigw_logging.json .
git clone --single-branch https://github.com/hulttis/ruuvigw.git ruuvigw/new
cp -vr ./ruuvigw/new/* ./ruuvigw/.
cp -vr ruuvigw.json ./ruuvigw/.
cp -vr ruuvigw_logging.json ./ruuvigw/.
systemctl start ruuvigw
