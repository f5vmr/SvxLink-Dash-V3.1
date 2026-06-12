#!/bin/bash
set -e

REPO_URL="https://github.com/f5vmr/{{ version_info.dashboard_name }}.git"
INSTALL_DIR="/opt/dashboard"

echo "Installing {{ version_info.dashboard_name }}..."

apt update
apt install -y git python3 python3-flask python3-jinja2 python3-werkzeug

if [ ! -d /opt ]; then
    mkdir -p /opt
fi

if [ -d "$INSTALL_DIR" ]; then
    echo "$INSTALL_DIR already exists."
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning dashboard..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

chmod +x "$INSTALL_DIR/install/fix-permissions.sh"
"$INSTALL_DIR/install/fix-permissions.sh"

cp "$INSTALL_DIR/install/svxlink-dash.service" /etc/systemd/system/svxlink-dash.service
chmod +x "$INSTALL_DIR/install/fix-permissions.sh"
"$INSTALL_DIR/install/fix-permissions.sh"

cat > /etc/sudoers.d/svxlink-dash <<'EOF'
# {{ version_info.dashboard_name }} controlled service permissions

svxlink ALL=(root) NOPASSWD: \
    /usr/bin/systemctl restart svxlink.service, \
    /usr/bin/systemctl is-active svxlink.service, \
    /usr/bin/systemctl stop svxlink.service, \
    /usr/bin/systemctl start svxlink.service, \
    /usr/bin/systemctl restart svxlink-dash.service, \
    /usr/bin/systemctl is-active svxlink-dash.service, \
    /usr/sbin/shutdown, \
    /usr/bin/mkdir, \
    /usr/bin/chown, \
    /usr/bin/chmod, \
    /usr/bin/git, \
    /usr/bin/systemd-run, \
    /usr/bin/install, \
    /usr/bin/pkill, \
    /usr/bin/sh
EOF


chmod 0440 /etc/sudoers.d/svxlink-dash
visudo -c -f /etc/sudoers.d/svxlink-dash
# Wifi install
# -------------------------------------------------
# Install network failsafe helper
# -------------------------------------------------
#
#install -o root -g root -m 755 \
#    network_failsafe.py \
#    /opt/dashboard/services/network_failsafe.py
#
# -------------------------------------------------
# Install systemd service
# -------------------------------------------------

cat > /etc/systemd/system/network-failsafe.service <<'EOF'
[Unit]
Description=SvxLink Dashboard Network Failsafe
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/usr/bin/python3 /opt/dashboard/services/network_failsafe.py
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

chmod 644 /etc/systemd/system/network-failsafe.service
chown root:root /etc/systemd/system/network-failsafe.service

# -------------------------------------------------
# Enable failsafe service
# -------------------------------------------------

systemctl daemon-reload
systemctl enable --now network-failsafe.service

# -------------------------------------------------
# Create hotspot profile
# -------------------------------------------------

echo "Creating NetworkManager hotspot profile..."

nmcli connection add \
    type wifi \
    ifname wlan0 \
    con-name Hotspot \
    autoconnect no \
    ssid svxlink || true

nmcli connection modify Hotspot \
    802-11-wireless.mode ap \
    802-11-wireless.band bg \
    ipv4.method shared \
    wifi-sec.key-mgmt wpa-psk \
    wifi-sec.psk "password" || true
#end- Wifi profile

cat > /etc/logrotate.d/svxlink <<'EOF'
/var/log/svxlink.log /var/log/svxlink {
    su svxlink svxlink
    weekly
    rotate 4
    compress
    missingok
    notifempty
    copytruncate
}
EOF

chmod 644 /etc/logrotate.d/svxlink
chown root:root /etc/logrotate.d/svxlink

cp "$INSTALL_DIR/install/svxlink-dash.service" /etc/systemd/system/svxlink-dash.service
systemctl daemon-reload
systemctl enable svxlink-dash
systemctl restart svxlink-dash

echo "SvxLink-Dash installed."
echo "Open: http://<node-ip>:5000/"