#!/bin/bash
set -e

echo "Fixing SvxLink-Dash permissions..."

mkdir -p /opt/dashboard/config
mkdir -p /opt/dashboard/backups
mkdir -p /etc/svxlink/svxlink.d
mkdir -p /usr/share/svxlink/events.d/local

chown -R svxlink:svxlink /opt/dashboard
chmod -R u+rwX,g+rwX,o+rX  /opt/dashboard

chown -R svxlink:svxlink /etc/svxlink
chmod -R u+rwX,g+rwX,o+rX  /etc/svxlink

chown -R svxlink:svxlink /usr/share/svxlink/events.d/local
chmod -R u+rwX,g+rwX,o+rX /usr/share/svxlink/events.d/local

chown -R svxlink:svxlink /opt/dashboard/backups
chmod -R u+rwX,g+rwX,o+rX /opt/dashboard/backups

echo "Permissions fixed."