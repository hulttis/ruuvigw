#!/bin/bash
# copy to app directory (one level up from ruuvigw)
systemctl stop ruuvigw
rm -frv /app/ruuvigw/new
cp -v /app/ruuvigw/ruuvigw.json /app/ruuvigw.json.bk
git clone --single-branch https://github.com/hulttis/ruuvigw.git /app/ruuvigw/new
cp -vr /app/ruuvigw/new/* /app/ruuvigw/.
cp -vr /app/ruuvigw.json.bk /app/ruuvigw/ruuvigw.json
source /app/ruuvigw/env/bin/activate
pip install -r /app/ruuvigw/requirements.txt
deactivate
cat /app/ruuvigw/ruuvigw_defaults.py | grep VERSION
echo journalctl -b -u ruuvigw --no-pager -n 300 -f
systemctl start ruuvigw
