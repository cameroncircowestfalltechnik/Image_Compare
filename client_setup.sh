#!/bin/bash
sudo pip3 install guizero
pip install argparse
sudo apt-get install python3-pil.imagetk
pip install subprocess.run
sudo apt-get install matchbox-keyboard -y
sudo apt-get install libmatchbox1 -y
sudo mv /home/pi/Desktop/toggle-matchbox-keyboard.sh /usr/bin
sudo chmod +x /usr/bin/toggle-matchbox-keyboard.sh
mkdir /home/pi/.matchbox
cp /usr/share/matchbox-keyboard/keyboard-lq1.xml /home/pi/.matchbox/keyboard.xml
chown pi:pi /home/pi/.matchbox/keyboard.xml
mkdir /home/pi/.config/autostart
sudo mv /home/pi/Desktop/start.desktop /home/pi/.config/autostart

