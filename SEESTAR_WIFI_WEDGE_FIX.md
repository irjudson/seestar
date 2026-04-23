# ZWO Seestar S50 — the "sound-33" WiFi wedge after firmware upgrade

If your Seestar S50 has been beeping constantly after upgrading past app
version **5.82**, won't come up in AP mode, or silently fails to join your
home network even though the LED is green, this writeup is for you.
It's a real bug in ZWO's driver bundle, it affects a specific cohort of
devices, and there's a clean fix you can apply yourself over USB.

## TL;DR

- Every ZWO firmware from **app 5.82 (fw_2.6.4) onward** ships a new Broadcom
  Wi-Fi driver (`bcmdhd.ko`, built Oct 17 2025, md5 `8b75e5cd33...`).
- On a subset of S50 units — typically earlier / prototype boards — that
  driver gets stuck at chip init with `HT Avail timeout (1000000): clkctl
  0x50` in dmesg. The Wi-Fi chip never comes up. The imager process
  interprets this as a fault and enters the "sound-33" (`en33.wav`)
  recovery loop.
- **Root cause**: the Oct 2025 driver calls `mmc_hw_reset()` on the SDIO
  bus. The RV1126 dwmmc controller on the S50 does not advertise
  `cap-mmc-hw-reset` in its DTB node (`dwmmc@ffc70000`). On this
  cohort of chips the `mmc_hw_reset` call leaves the SDIO bus in a
  state where the chip never grants HT clock. The **July 2023 factory
  driver** uses `mmc_sw_reset()` instead — works reliably on the same
  hardware.
- **Fix**: patch one symbol in the driver. A 1-byte-logical change made
  with `objcopy --redefine-sym`. No kernel rebuild, no reflash, no loss
  of settings.

Affected units are fully recoverable and, once fixed, survive every
subsequent ZWO firmware push indefinitely.

## Not every S50 on Oct 2025 driver wedges

Field reports from other owners show units running the Oct 2025 driver
*without* wedging. Both working and broken units share the same DTB
state (`cap-mmc-hw-reset` absent on every S50 sampled). So whatever
tips a particular chip into the HT Avail failure mode is not purely
the DT property; something else — chip revision, SDIO timing on that
specific board, or conditions at the moment chip init runs — gates
whether the bad `mmc_hw_reset` call actually wedges it.

The patched driver (which skips the `mmc_hw_reset` call entirely) works
on every unit we have data for, broken or not. It is the safer option
if you intend to upgrade past 5.82.

## Check if you're affected

With the S50 reachable over USB-ethernet (typically `169.254.100.100`)
or WiFi:

```bash
./tools/wifi-driver-check.sh --ip <your-seestar-ip>
```

The last line of output is a single-word verdict:

| Verdict | Meaning |
|---|---|
| `FACTORY_SAFE` | Jul 2023 factory driver installed — pre-regression; safe until the next firmware push overwrites it |
| `PATCHED_SAFE` | Oct 2025 driver with the `mmc_sw_reset` patch already applied — safe |
| `WEDGED_NOW` | Stock Oct 2025 driver + HT Avail timeouts in dmesg — chip is wedged right now; apply the fix below |
| `REGRESSED_AT_RISK` | Stock Oct 2025 driver, no wedge this boot — may or may not be safe; if you want certainty, apply the fix |
| `UNKNOWN_DRIVER` | md5 doesn't match any known fingerprint — probably a future ZWO build we haven't catalogued |

You can also infer a wedged unit from the symptom: **sound-33 beep loop,
blinking red LED, or AP not broadcasting after upgrading past 5.82.**

> A previous version of this writeup used a one-liner that checked
> `/proc/device-tree/dwmmc@ffc70000/` for `cap-mmc-hw-reset`. That test
> flagged every S50 as affected, including units that work fine, so it
> has been withdrawn. The driver + dmesg check above is the current
> recommended diagnostic.

## How the fix works

The Oct 2025 `bcmdhd.ko` has one undefined kernel symbol import that differs
from the July 2023 version:

```
Jul 2023:  U mmc_sw_reset
Oct 2025:  U mmc_hw_reset
```

Your kernel exports both (confirmable via `grep mmc_.w_reset /proc/kallsyms`).
The Oct 2025 driver links against `mmc_hw_reset`, which on your DTB falls
through to `-EOPNOTSUPP`. Rewriting that one import string in the ELF
makes it link against `mmc_sw_reset` instead — same driver otherwise,
byte-identical in every other way.

```bash
arm-linux-gnueabihf-objcopy \
    --redefine-sym mmc_hw_reset=mmc_sw_reset \
    bcmdhd.ko  bcmdhd.patched.ko
```

After patching, install on the device at
`/lib/modules/4.19.111/kernel/drivers/net/wireless/rockchip_wlan/rkwifi/bcmdhd_wifi6/bcmdhd.ko`,
`depmod -a`, reboot. Chip comes up cleanly.

## Step-by-step

Prereqs on your Linux host:
- `gcc-arm-linux-gnueabihf` (for `objcopy`)
- SSH access to your S50 (USB-ethernet on `169.254.100.100` is the most
  reliable path; works even with WiFi down)

### 1. Get the stock driver off the device

```bash
scp pi@<ip>:/lib/modules/4.19.111/kernel/drivers/net/wireless/rockchip_wlan/rkwifi/bcmdhd_wifi6/bcmdhd.ko  /tmp/bcmdhd.stock.ko
```

Verify it's the Oct 2025 build:

```bash
md5sum /tmp/bcmdhd.stock.ko
# expected: 8b75e5cd33fcf850dd673129d1842312

strings /tmp/bcmdhd.stock.ko | grep "compiled on" | head -1
# expected: ...compiled on Oct 17 2025 at 16:52:35
```

### 2. Patch the symbol import

```bash
arm-linux-gnueabihf-objcopy \
    --redefine-sym mmc_hw_reset=mmc_sw_reset \
    /tmp/bcmdhd.stock.ko  /tmp/bcmdhd.patched.ko

# Verify only one import changed:
arm-linux-gnueabihf-nm -u /tmp/bcmdhd.patched.ko | grep mmc
# expected: U mmc_set_data_timeout / U mmc_sw_reset / U mmc_wait_for_req
```

md5 of the patched file will be `1fc70c15691fa675fa3e4661aa783a12`.
Everything else in the ELF is byte-identical to the stock Oct 2025
driver — same `.text`, same `.rodata`, same `modinfo`, same 55 module
parameters.

### 3. Install it

```bash
scp /tmp/bcmdhd.patched.ko  pi@<ip>:/tmp/bcmdhd.patched.ko

ssh pi@<ip> '
  # Back up whatever is currently installed (so you can roll back)
  sudo mount -o remount,rw /
  sudo cp /lib/modules/4.19.111/kernel/drivers/net/wireless/rockchip_wlan/rkwifi/bcmdhd_wifi6/bcmdhd.ko \
          /lib/modules/4.19.111/kernel/drivers/net/wireless/rockchip_wlan/rkwifi/bcmdhd_wifi6/bcmdhd.ko.prepatch_backup

  # Install patched
  sudo cp /tmp/bcmdhd.patched.ko \
          /lib/modules/4.19.111/kernel/drivers/net/wireless/rockchip_wlan/rkwifi/bcmdhd_wifi6/bcmdhd.ko
  sudo depmod -a 2>&1 || true
  sudo mount -o remount,ro / 2>/dev/null || true

  # Reboot to let the new driver initialize the chip
  sudo reboot -f
'
```

### 4. Verify it worked

After ~90 seconds, the LED should be steady green and no sound-33 beeps.
Confirm:

```bash
ssh pi@<ip> '
  sudo dmesg | grep -c "HT Avail timeout"
  # Should print: 0

  sudo iw dev uap0 info | head -5
  # Should show the S50_xxxxxxxx SSID broadcasting

  systemctl is-active hostapd.service
  # Should print: active
'
```

### 5. It survives future ZWO firmware updates... sort of

Every iscope firmware push will overwrite your patched `bcmdhd.ko` with
the stock Oct 2025 version and re-wedge the chip. To survive an update
cycle, stage the patched driver on the device beforehand in persistent
storage (e.g. `/home/pi/bcmdhd.ko.patched`) and run a post-upgrade
reinstall script.

Example pre-upgrade prep:

```bash
scp /tmp/bcmdhd.patched.ko pi@<ip>:/home/pi/bcmdhd.patched.ko
```

Example post-upgrade script to stage on the device at
`/home/pi/post_upgrade_swap.sh`:

```bash
#!/bin/bash
set -e
DRIVER_PATH=/lib/modules/4.19.111/kernel/drivers/net/wireless/rockchip_wlan/rkwifi/bcmdhd_wifi6/bcmdhd.ko
sudo mount -o remount,rw /
sudo cp "$DRIVER_PATH" "${DRIVER_PATH}.postupgrade_backup"
sudo cp /home/pi/bcmdhd.patched.ko "$DRIVER_PATH"
sudo depmod -a
sudo mount -o remount,ro / 2>/dev/null || true
sudo reboot -f
```

Run it right after any iscope push, once the device comes up with a
wedged chip but USB-ethernet still reachable.

## Rolling back

If anything goes wrong:

```bash
ssh pi@<ip> '
  sudo mount -o remount,rw /
  sudo cp /lib/modules/4.19.111/kernel/drivers/net/wireless/rockchip_wlan/rkwifi/bcmdhd_wifi6/bcmdhd.ko.prepatch_backup \
          /lib/modules/4.19.111/kernel/drivers/net/wireless/rockchip_wlan/rkwifi/bcmdhd_wifi6/bcmdhd.ko
  sudo depmod -a
  sudo mount -o remount,ro /
  sudo reboot -f
'
```

If the device is completely unreachable (USB-ethernet dead, WiFi dead,
AP down), you need a full `rkdeveloptool` reflash — out of scope for
this writeup, but doable, and there are open-source tools for it.

## What this is NOT

- **Not a fix pushed by ZWO.** ZWO support is aware of the symptom
  (they've remote-remediated for some users). But every shipping
  firmware release, including the latest 7.32 / fw_3.1.2, still contains
  the broken driver.
- **Not a DTB-level fix.** Adding `cap-mmc-hw-reset` to the DTB was
  our first hypothesis for a "proper" fix, but since field data shows
  the same DTB state on working S50s we no longer expect that edit
  alone would help, and it would require rebuild/reflash of a partition
  that no ZWO firmware update touches.
- **Not a NVRAM / Broadcom OTP issue.** Those hypotheses came up during
  the investigation and were all refuted. A friend's working production
  S50 has the byte-identical `nvram_ap6256.txt`, so NVRAM isn't the
  differentiator.

## Credits / acknowledgements

Investigation and fix developed on a prototype S50 (boardrev P304,
serial `77d826xx`). Binary diff of the two driver versions, DTB
property enumeration, and live testing across firmware 5.50 → 7.32
confirmed:

1. The driver's OTP / SPROM / CIS code is byte-identical between the
   July 2023 and October 2025 builds.
2. The `nvram_ap6256.txt` shipped on every affected device is the
   unchanged upstream `AP6256_NVRAM_V1.4_06112021` (md5 `b7772771...`).
3. The functional regression between the two builds is the
   `mmc_hw_reset` vs `mmc_sw_reset` import. Neutralising that one
   import (via `objcopy --redefine-sym`) is sufficient to restore
   correct behavior on every affected unit tested.

What is *not* established: exactly which S50 units are susceptible.
The DTB state is identical across working and broken S50s we have
data for, so the missing `cap-mmc-hw-reset` property is at best a
necessary condition, not a sufficient one. Board revision, chip
stepping, or SDIO bus timing on a specific PCB are the most likely
remaining suspects.

Patched driver md5: `1fc70c15691fa675fa3e4661aa783a12`.

If you find more S50 data points (working or broken), the verdict
line printed by `./tools/wifi-driver-check.sh` plus `dmesg | grep
boardrev` is enough to correlate.
