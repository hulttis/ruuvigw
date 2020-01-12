#!/bin/bash
# copy to app directory (one level up from ruuvigw)
systemctl stop ruuvigw
rm -frv /app/ruuvigw/new
cp -v /app/ruuvigw/ruuvigw.json /app/ruuvigw.json.bk
git clone --single-branch https://github.com/hulttis/ruuvigw.git /appruuvigw/new
cp -vr /app/ruuvigw/new/* /app/ruuvigw/.
cp -vr /app/ruuvigw.json.bk /app/ruuvigw/ruuvigw.json
source /app/ruuvigw/env/bin/activate
pip install -r /app/ruuvigw/requirements.txt
deactivate
systemctl start ruuvigw
