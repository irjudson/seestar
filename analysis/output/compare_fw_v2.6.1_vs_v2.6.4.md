# Firmware Comparison: v2.6.1 → v2.6.4

## Version Changes
| | v2.6.1 | v2.6.4 |
|--|--|--|
| MCU firmware | Seestar_2.1.2.bin | Seestar_2.1.3.bin |
| MCU version | 2.1.2 | 2.1.3 |
| ASIAIR deb | 5.50 | 5.84 |

## Files Added (34)

- `deb-build/asiair_armhf/home/pi/ASIAIR/asiair.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/AM_Test`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/Soft03Cmt.txt`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/air_ble`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/auto_shutdown.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/beeper`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/bluetooth.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/comets.py`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/common.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/conf/rootcert.pem`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/exiv2`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/flash_power_led`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/network.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/old_log_mv.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/planet.py`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/read_power_cm4.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/read_power_mini.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/read_power_rk.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/run_update_pack.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/searchSSIDIndex.py`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/set_timezone.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/shutdownsvr.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/start_INDI.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/write_wpa_conf.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/zwoair_daemon.sh`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/zwoair_file_server`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/zwoair_guider`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/zwoair_imager`
- `deb-build/asiair_armhf/home/pi/ASIAIR/bin/zwoair_updater`
- `deb-build/asiair_armhf/home/pi/ASIAIR/config`
- `deb-build/asiair_armhf/home/pi/ASIAIR/lib/libasisdk.so`
- `deb-build/asiair_armhf/home/pi/ASIAIR/lib/libzalgorithm.so`
- `deb-build/asiair_armhf/home/pi/ASIAIR/lib/libzhistogram.so`
- `others/Seestar_2.1.3.bin`

## Files Removed (53)

- `deb/alpaca_libs_armhf.deb`
- `deb/alpaca_update_armhf.deb`
- `deb/asiair_armhf.deb`
- `deb/rsyslog_8.1901.0-1+deb10u2_armhf.deb`
- `deb/tzdata_2024a-0+deb10u1_all.deb`
- `others/S30/ak09915.ko`
- `others/S30/eaf.ko`
- `others/S30/gc2083.ko`
- `others/S30/imx662.ko`
- `others/S30/inv-mpu-iio.ko`
- `others/S30/librkaiq.so`
- `others/S30/pwm_gpio.ko`
- `others/S30/rc.local`
- `others/S30/test_asiair_file.sh`
- `others/S30/update.img`
- `others/S30/video_rkcif.ko`
- `others/S30/video_rkisp.ko`
- `others/S30/video_rkispp.ko`
- `others/S30P/imx585.ko`
- `others/S30P/imx586.ko`
- `others/S30P/libeasymedia.so.1`
- `others/S30P/update.img`
- `others/S30P/video_rkcif.ko`
- `others/S30P/video_rkisp.ko`
- `others/S50/eaf.ko`
- `others/S50/imx462.ko`
- `others/S50/video_rkcif.ko`
- `others/S50N/video_rkcif.ko`
- `others/Seestar_2.1.2.bin`
- `others/aplay`
- `others/dnsmasq.conf`
- `others/imx462_CMK-OT1234-FV0_M00-2MP-F00.xml`
- `others/libv4l/libv4l-mplane.so`
- `others/libv4l/libv4l1.so.0.0.0`
- `others/libv4l/libv4l2.so.0.0.0`
- `others/libv4l/libv4l2rds.so.0.0.0`
- `others/libv4l/libv4lconvert.so.0.0.0`
- `others/libv4l/v4l1compat.so`
- `others/libv4l/v4l2convert.so`
- `others/nginx.conf`
- `others/npu/to_sync/etc/init.d/S05NPU_init`
- `others/npu/to_sync/etc/init.d/S60NPU_init`
- `others/npu/to_sync/usr/bin/query_npu_usage`
- `others/npu/to_sync/usr/bin/rknn_server`
- `others/npu/to_sync/usr/bin/start_rknn.sh`
- `others/npu/to_sync/usr/bin/start_usb.sh`
- `others/npu/to_sync/usr/lib/libGAL.so`
- `others/npu/to_sync/usr/lib/libOpenVX.so.1.2`
- `others/npu/to_sync/usr/lib/librknn_runtime.so`
- `others/npu/to_sync/usr/lib/npu/rknn/memory_profile`
- `others/npu/to_sync/usr/lib/npu/rknn/plugins/libann_plugin.so`
- `others/pwrled_gpio.ko`
- `others/zwo-beeper.ko`
