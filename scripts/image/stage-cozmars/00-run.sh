#!/bin/bash -e
# Cài Cozmars fat bundle vào rootfs image — không pip trên robot sau flash.
# FILE: cozmars-bundle.tgz phải nằm trong stage FILES/ (build-sd-image.sh copy vào).

on_chroot << EOF
set -e
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y hostapd dnsmasq iw avahi-daemon i2c-tools libportaudio2 || true
mkdir -p /opt/cozmars /home/pi/.cozmars
EOF

install -d "${ROOTFS_DIR}/tmp"
if [ -f files/cozmars-bundle.tgz ]; then
  install -m 644 files/cozmars-bundle.tgz "${ROOTFS_DIR}/tmp/cozmars-bundle.tgz"
else
  echo "ERROR: thiếu files/cozmars-bundle.tgz — chạy pack-fat.sh trên Pi rồi đặt path vào build-sd-image.sh" >&2
  exit 1
fi

on_chroot << EOF
set -e
cd /tmp
tar -xzf cozmars-bundle.tgz
BUNDLE=\$(find /tmp -maxdepth 2 -type d -name cozmars-bundle | head -1)
if [ -d "\$BUNDLE/opt/cozmars" ]; then
  rm -rf /opt/cozmars
  cp -a "\$BUNDLE/opt/cozmars" /opt/cozmars
fi
if [ -f /opt/cozmars/install-fat.sh ]; then
  bash /opt/cozmars/install-fat.sh --from-bundle || true
fi
# install-fat --from-bundle expects already at /opt; also copy systemd from bundle
if [ -d "\$BUNDLE/etc/systemd/system" ]; then
  cp -a "\$BUNDLE/etc/systemd/system/"* /etc/systemd/system/ || true
fi
if [ -f "\$BUNDLE/usr/local/bin/cozmars-autohotspot" ]; then
  install -m 755 "\$BUNDLE/usr/local/bin/cozmars-autohotspot" /usr/local/bin/cozmars-autohotspot
fi
# Rewrite + enable (idempotent)
bash /opt/cozmars/install-fat.sh --from-bundle
# Enable SSH + SPI/I2C markers for first boot
touch /boot/ssh || touch /boot/firmware/ssh || true
raspi-config nonint do_i2c 0 || true
raspi-config nonint do_spi 0 || true
raspi-config nonint do_camera 0 || true
rm -f /tmp/cozmars-bundle.tgz
rm -rf /tmp/cozmars-bundle /tmp/cozmars-bundle-*
echo "Cozmars stage OK"
EOF
