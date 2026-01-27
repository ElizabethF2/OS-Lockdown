#!/bin/sh

BRIDGE_PORT="0000:02:00.0"

systemctl stop display-manager.service
sleep 5
modprobe -r amdgpu
sleep 5
reg=$(setpci -s $BRIDGE_PORT BRIDGE_CONTROL)
setpci -s $BRIDGE_PORT BRIDGE_CONTROL=$(printf "%04x" $(("0x$reg" | 0x40)))
sleep 0.1
setpci -s $BRIDGE_PORT BRIDGE_CONTROL=$reg
sleep 5
modprobe amdgpu
sleep 5
systemctl start display-manager.service
