#!/bin/bash
PID=`pidof matchbox-keyboard`
if [ ! -e $PID ]; then
 killall matchbox-keyboard
else
 matchbox-keyboard&
fi
