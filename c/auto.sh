#! /bin/bash
# sudo from /etc/rc.local using &

cd /home/pi/GPS
./a.out >/dev/null

if [ $? == 0 ]; then
    sync
    shutdown now
fi
