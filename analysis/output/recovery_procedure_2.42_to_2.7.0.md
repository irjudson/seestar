> **SUPERSEDED.** This document was written during the 2026-04 investigation when several root-cause hypotheses were still live. The final, confirmed cause and fix are documented in [`SEESTAR_WIFI_WEDGE_FIX.md`](../../SEESTAR_WIFI_WEDGE_FIX.md) and [`UPGRADE_PROCEDURE_VERIFIED.md`](../../UPGRADE_PROCEDURE_VERIFIED.md). Preserved here as a snapshot of the investigation, not a current description of the bug or fix.

# Recovery Procedure: Fresh 2.42 Image → App 2.7.0 (deb 5.93)

**Date:** 2026-04-13  
**Device:** Seestar S50, SN 77d82606, cpuId 2c0927865bd10180  
**Starting state:** Fresh seestarOS.img (deb 2.42), foreign device identity  
**Target:** App 2.7.0 / ASIAIR deb 5.93

---

## What you need (all already on this machine)

| Item | Location |
|------|----------|
| Flash tool | `/usr/bin/seestar-tool` |
| 2.7.0 APK | `/home/irjudson/Projects/Seestar/Seestarv2.7.0.apk` |
| Our zwoair_license | `/home/irjudson/Projects/Seestar/s50-fs/home/pi/.ZWO/zwoair_license` |
| Our ASIAIR_general.xml | `/home/irjudson/Projects/Seestar/s50-fs/home/pi/.ZWO/ASIAIR_general.xml` |

---

## Phase 1: Connect to the device

The fresh 2.42 image will broadcast a WiFi AP with an unknown SSID (whoever's
image this is). The password is almost certainly `12345678`.

```bash
# Scan for Seestar networks
nmcli dev wifi list | grep -i seestar
# Or just open your WiFi manager and look for anything starting with Seestar or ASIAIR
```

Connect to that network (password: `12345678`). The device will be at `10.0.0.1`.

```bash
ssh pi@10.0.0.1
# password: raspberry
```

If `raspberry` fails, try `newpassword`.

---

## Phase 2: Verify current state on device

```bash
# What SN does this image think it is?
python3 -c "import json; d=json.load(open('/home/pi/.ZWO/zwoair_license')); print(d['sn'])"

# What SSID is it using?
grep ssid /home/pi/AP_2.4G.conf

# Is ap_id_inited present?
grep -r ap_id_inited /home/pi/.ZWO/ASIAIR_general.xml 2>/dev/null || echo "MISSING"

# What deb version?
cat /home/pi/ASIAIR/config | grep version_string
```

---

## Phase 3: Restore our device identity (run on device via SSH)

### 3a. Restore zwoair_license

```bash
cat > /home/pi/.ZWO/zwoair_license << 'EOF'
{"sn":"77d82606","cpuId":"2c0927865bd10180","auth_code":"591746ca2eb046e99832ed462dbc5b7c","digest":"3YJqeAZoh9I4kkdjEnQDtkhLrZdPSaoZGo2P3syVlQc=","sign":"WAra8c+PqAD02UabKj9MZbTIG2gOknb7tXg650EbfqYyW7lSPLJoug1kaJFPNnlqDJ/jBDy74pbkbF0TFxGIdKRVLv8P/bK9/XJEjpjAduwtY/VCxyE0/VSGosooUDIdai5f3cSHa5IApciiQfoF9/A580XRq2R4/X2JE72jEos="}
EOF
```

### 3b. Write ASIAIR_general.xml with ap_id_inited=true

This is the critical pre-patch. The new 5.93 imager reads `setting2/network/ap_id_inited`.
The old 2.42 image does NOT have this flag. Without it, the new imager will try to
reinitialize the AP SSID and fail.

```bash
cat > /home/pi/.ZWO/ASIAIR_general.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8" ?>
<setting2 date="20190214_181215">
    <network date="20190214_181215">
        <ap_id_inited type="8" date="20190214_181215">true</ap_id_inited>
    </network>
</setting2>
EOF
```

### 3c. Set AP config to our device's SSID and password

The 5.93 imager (after update) will read the SSID from AP_2.4G.conf and AP_5G.conf.
Since ap_id_inited=true it won't overwrite them. Set them now.

```bash
# Update SSID and password in both config files
sed -i 's/^ssid=.*/ssid=SeestarS50/' /home/pi/AP_2.4G.conf
sed -i 's/^wpa_passphrase=.*/wpa_passphrase=HolyCow!/' /home/pi/AP_2.4G.conf
sed -i 's/^ssid=.*/ssid=SeestarS50/' /home/pi/AP_5G.conf
sed -i 's/^wpa_passphrase=.*/wpa_passphrase=HolyCow!/' /home/pi/AP_5G.conf
```

Verify:
```bash
grep -E "ssid|wpa_passphrase" /home/pi/AP_2.4G.conf /home/pi/AP_5G.conf
```

Expected output:
```
/home/pi/AP_2.4G.conf:ssid=SeestarS50
/home/pi/AP_2.4G.conf:wpa_passphrase=HolyCow!
/home/pi/AP_5G.conf:ssid=SeestarS50
/home/pi/AP_5G.conf:wpa_passphrase=HolyCow!
```

### 3d. Verify all three files are correct

```bash
echo "=== zwoair_license SN ===" && python3 -c "import json; print(json.load(open('/home/pi/.ZWO/zwoair_license'))['sn'])"
echo "=== ap_id_inited ===" && grep ap_id_inited /home/pi/.ZWO/ASIAIR_general.xml
echo "=== SSIDs ===" && grep ssid /home/pi/AP_2.4G.conf /home/pi/AP_5G.conf
```

Expected:
```
=== zwoair_license SN ===
77d82606
=== ap_id_inited ===
        <ap_id_inited type="8" date="20190214_181215">true</ap_id_inited>
=== SSIDs ===
/home/pi/AP_2.4G.conf:ssid=SeestarS50
/home/pi/AP_5G.conf:ssid=SeestarS50
```

**Do NOT proceed to Phase 4 until all three checks pass.**

---

## Phase 4: Push the 2.7.0 firmware with seestar-tool

Open a new terminal (keep the SSH session alive in the other one).

```bash
seestar-tool
```

The tool launches as a GUI (or falls back to TUI if no display). In the UI:

1. Load the APK: point it at `/home/irjudson/Projects/Seestar/Seestarv2.7.0.apk`
2. Set the device host: `10.0.0.1`
3. Click **Install** (or equivalent)

seestar-tool handles everything: extracts `iscope_64` from the APK, connects
to the device's update ports, transfers the firmware, and shows progress.

Watch the LED:
- Blinking yellow = update in progress
- Solid yellow = finalizing
- Green = success (device reboots)
- Red = failed (see troubleshooting below)

---

## Phase 5: After reboot

The device will reboot after the update. It will come up on the `SeestarS50` AP
with password `HolyCow!`.

```bash
# Reconnect to SeestarS50 / HolyCow! and SSH in
ssh pi@10.0.0.1

# Confirm new firmware version
cat /home/pi/ASIAIR/config | grep version_string
# Expected: version_string = 5.93

# Confirm ap_id_inited is still present
grep ap_id_inited /home/pi/.ZWO/ASIAIR_general.xml
# Expected: <ap_id_inited ... >true</ap_id_inited>

# Confirm our SN
python3 -c "import json; print(json.load(open('/home/pi/.ZWO/zwoair_license'))['sn'])"
# Expected: 77d82606

# Confirm WiFi is up
iwconfig uap0 2>/dev/null | grep ESSID
# Expected: ESSID:"SeestarS50"
```

---

## Troubleshooting

### Flash tool can't connect to 10.0.0.1:4350

The 2.42 imager may not have ports 4350/4361 open. Check:
```bash
# On device via SSH:
netstat -tlnp 2>/dev/null | grep -E "4350|4361|4700"
```

If 4350 is not open, the imager may not be fully started. Try:
```bash
sudo systemctl restart zwoair_imager.service 2>/dev/null || \
sudo /home/pi/ASIAIR/bin/zwoair_imager -d &
```

Wait 10 seconds and retry the flash tool.

### Flash tool connects but begin_recv is rejected

Try running from the Seestar app instead:
1. Connect phone/tablet to `SeestarS50` AP (or whatever foreign SSID it's on)
2. Open Seestar app v2.7.0
3. Let the app detect and push the update automatically

### Device comes up after reboot with wrong SSID

If after the update the device broadcasts a different SSID than `SeestarS50`:
```bash
# SSH in on 10.0.0.1 (still on the old AP)
ssh pi@10.0.0.1

# Force-set the correct SSID and restart AP
/home/pi/ASIAIR/bin/network.sh ap_set_ssid "SeestarS50"
/home/pi/ASIAIR/bin/network.sh ap_set_key "HolyCow!"
sudo systemctl restart hostapd.service

# Mark initialized so imager won't reset again
# (ASIAIR_general.xml should already be correct from Phase 3)
grep ap_id_inited /home/pi/.ZWO/ASIAIR_general.xml
```

### "WiFi is abnormal" message in app after update

This means the ap_id_inited flag wasn't in place when the imager started. 
The imager tried to reset the SSID and failed. Fix:

```bash
# SSH via current AP (whatever it is)
ssh pi@10.0.0.1

# Re-apply Phase 3 fixes
cat > /home/pi/.ZWO/ASIAIR_general.xml << 'EOF'
<?xml version="1.0" encoding="UTF-8" ?>
<setting2 date="20190214_181215">
    <network date="20190214_181215">
        <ap_id_inited type="8" date="20190214_181215">true</ap_id_inited>
    </network>
</setting2>
EOF

sed -i 's/^ssid=.*/ssid=SeestarS50/' /home/pi/AP_2.4G.conf
sed -i 's/^wpa_passphrase=.*/wpa_passphrase=HolyCow!/' /home/pi/AP_2.4G.conf
sed -i 's/^ssid=.*/ssid=SeestarS50/' /home/pi/AP_5G.conf
sed -i 's/^wpa_passphrase=.*/wpa_passphrase=HolyCow!/' /home/pi/AP_5G.conf
sudo systemctl restart hostapd.service
# Reconnect to SeestarS50/HolyCow! and continue
```

---

## Device Identity Reference

| Field | Value |
|-------|-------|
| SN | 77d82606 |
| cpuId | 2c0927865bd10180 |
| auth_code | 591746ca2eb046e99832ed462dbc5b7c |
| AP SSID | SeestarS50 |
| AP password | HolyCow! |
| Firmware file | iscope_64_v2.7.0 (7,461,242 bytes) |
| Target deb | 5.93 |
