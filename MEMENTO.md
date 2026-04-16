# Seestar

This project automates the firmware update process for Seestar devices, specifically addressing issues with AP initialization and channel configuration that cause sound 33 errors during OTA updates.

**Stack:** Bash scripting, Rockchip development tools, Linux networking (hostapd, ifconfig), OTA update automation

## Current Status
- The firmware update script is failing to initialize the AP correctly after OTA pushes, resulting in sound 33 errors
- The AP never comes back up after firmware update, indicating a failure in hostapd restart or channel configuration
- The system is using Rockchip's rkdeveloptool for flashing, not traditional recovery methods

## Recent Decisions
- 2024-04-15: Decided to focus on analyzing the rc.local and asiair.sh startup scripts to understand where AP initialization fails
- 2024-04-15: Confirmed that the 6.45 firmware package does not include .ZWO/ data in pi.tgz, meaning pre-upgrade changes are lost on OTA flash
- 2024-04-15: Identified that the imager binary contains a direct hostapd restart command that may bypass normal startup paths

## Open Issues
- AP fails to come back up after OTA push, causing sound 33 error
- The system's AP initialization logic does not handle channel=0 correctly
- Pre-upgrade changes to /root/.ZWO/ are lost during OTA flash

## Key Files
- `seestar_ota.sh`: Main OTA update script that orchestrates flashing and post-update steps
- `rc.local`: System startup script that runs asiair.sh and initializes AP
- `asiair.sh`: Core startup script that configures networking and AP settings
- `AP_5G.conf`: Configuration file for 5GHz AP channel and settings
- `imager`: Binary that handles device initialization and AP restart
- `network.sh`: Network management script used by asiair.sh
- `log_updater.txt`: Logs AP initialization status and errors
- `seestar_tool`: OTA tool used to flash firmware images

## Recent Activity
- 2024-04-15: Analyzed startup flow from rc.local to asiair.sh to identify AP restart failure
- 2024-04-15: Discovered that OTA flash wipes mmcblk0p5, losing pre-upgrade changes
- 2024-04-15: Identified direct hostapd restart command in imager binary as a potential failure point
- 2024-04-15: Verified that AP_5G.conf channel=0 causes 5-30 second ACS scan that never resolves
- 2024-04-15: Confirmed that log_updater.txt is the source of ap_id_inited logging
- 2024-04-15: Found that seestar_tool OTA flash wipes the pi partition and restores from pi.tgz
- 2024-04-15: Tracked down the specific line in rc.local that starts asiair.sh as sudo -u pi
- 2024-04-15: Analyzed the exact command sequence that restarts hostapd in imager binary
