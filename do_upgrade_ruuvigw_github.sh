#!/bin/bash
# copy to app directory (one level up from ruuvigw)
systemctl stop ruuvigw
rm -frv ./ruuvigw/new
cp -v ./ruuvigw/ruuvigw.json ruuvigw.json.upg
git clone --single-branch https://github.com/hulttis/ruuvigw.git ruuvigw/new
cp -vr ./ruuvigw/new/* ./ruuvigw/.
cp -vr ruuvigw.json.upg ./ruuvigw/ruuvigw.json
systemctl start ruuvigw
