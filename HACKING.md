# Seestar

A project to manage firmware flashing and recovery for Seestar astronomical devices, including tools for flashing, recovery, and handling known problematic firmware versions that cause WiFi chip wedges.

**Stack:** Python, Bash, SSH, firmware signing, embedded systems

## Current Status
- Firmware flashing and recovery tools are functional, with protections against known-bad versions
- A wedge issue has been identified in firmware versions 5.82 and 5.97 due to mount MCU firmware updates

## Recent Decisions
- 2026-04-22: Added wedge-version protection to the flash tool to prevent flashing known-bad firmware versions like 2.7.0 and 2.7.1
- 2026-04-22: Identified mount MCU firmware update as the likely trigger for WiFi chip wedges in 5.82 and 5.97
- 2026-04-22: Built a modified firmware variant (2.6.4_no_mount) to test the mount MCU update hypothesis

## Open Issues
- WiFi chip wedge persists in firmware versions 5.82 and 5.97 due to mount MCU firmware update
- Need to validate if 2.6.4_no_mount resolves the wedge issue

## Key Files
- `tools/seestar_firmware_flash.py`: Main firmware flashing tool with version safety checks
- `tools/seestar-recovery.sh`: Recovery script for initial setup and flashing
- `firmware/signed/iscope_2.6.4_no_mount`: Modified firmware variant without mount MCU update for testing
- `firmware/decompiled/seestar_v2.7.0_decompiled/resources/assets/iscope`: Firmware package for version 2.7.0, flagged as likely to cause wedge
- `firmware/packages/fw_2.6.1`: Known-good firmware package for recovery baseline
- `update_package.sh`: Script that handles firmware updates including mount MCU flashing
- `seestar_firmware_flash.py`: Python script for flashing firmware to Seestar devices
- `seestar_recovery.sh`: Bash script for recovery operations including key installation and pre-upgrade setup

## Recent Activity
- 2026-04-22: Identified mount MCU firmware update as root cause of WiFi chip wedges in 5.82 and 5.97
- 2026-04-22: Built modified firmware variant (2.6.4_no_mount) for testing hypothesis
- 2026-04-22: Updated flash tool to block flashing known-bad firmware versions
- 2026-04-22: Confirmed 5.97 also causes chip wedge, ruling out 5.97 as a fix for 5.82 issues
- 2026-04-21: Identified ownership and chmod bugs in firmware update process
- 2026-04-21: Added safety check to prevent flashing firmware versions that cause chip wedges
- 2026-04-21: Documented the chip wedge issue and its relation to mount MCU updates
- 2026-04-21: Pushed 5.97 firmware to test if it resolves the issue (it did not)
- 2026-04-21: Pushed 5.82 firmware to verify wedge issue was present
- 2026-04-21: Installed SSH key and set up recovery environment for flashing
