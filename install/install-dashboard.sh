#!/bin/bash
set -e

REPO_URL="https://github.com/f5vmr/SvxLink-Dash-V3.git"
INSTALL_DIR="/opt/dashboard"

echo "Installing SvxLink-Dash-V3..."

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
# SvxLink-Dash-V3 controlled service permissions

svxlink ALL=(root) NOPASSWD: \
    /usr/bin/systemctl restart svxlink, \
    /usr/bin/systemctl is-active svxlink, \
    /usr/bin/mkdir, \
    /usr/bin/chown, \
    /usr/bin/chmod, \
    /usr/bin/git, \
    /usr/bin/nmcli, \
    /usr/bin/install
EOF


chmod 0440 /etc/sudoers.d/svxlink-dash
visudo -c
# Wifi install
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