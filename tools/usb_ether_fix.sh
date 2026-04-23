#!/bin/bash
# Recovery: force USB-ethernet gadget back up after a hang on the Seestar.
#
# Symptom it fixes: device's dwc3 controller gets into a state where
# "failed to enable ep0out" appears in dmesg and host enumeration fails
# with error -71 / "device not responding to setup address". Unbinding
# and rebinding dwc3 clears the controller state; reloading g_ether
# reattaches a clean gadget; reassigning usb0's IP restores the net link.
#
# Safe to run anytime. Briefly pauses zwoair_imager, rebuilds gadget,
# resumes zwoair_imager.
#
# Host-side expectation after running this:
#   - new netdev appears (enx<mac> or usb0)
#   - device reachable at 169.254.100.100
set -x
IMAGER_PID=$(pgrep -x zwoair_imager)
[ -n "$IMAGER_PID" ] && sudo kill -STOP "$IMAGER_PID"
sudo rmmod g_ether 2>/dev/null
echo ffd00000.dwc3 | sudo tee /sys/bus/platform/drivers/dwc3/unbind >/dev/null
sleep 1
echo ffd00000.dwc3 | sudo tee /sys/bus/platform/drivers/dwc3/bind >/dev/null
sleep 2
sudo modprobe g_ether
sleep 2
sudo ip addr add 169.254.100.100/16 dev usb0 2>/dev/null
sudo ip link set usb0 up
[ -n "$IMAGER_PID" ] && sudo kill -CONT "$IMAGER_PID"
ip addr show usb0
