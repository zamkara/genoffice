#!/usr/bin/env bash
# Runs inside the disposable Arch Linux container, never on the user's host.
set -euo pipefail
job_dir=$1
scripts_dir=$2
pacman -Syu --noconfirm --needed \
  rust nodejs npm git pkgconf python desktop-file-utils polkit \
  alsa-lib at-spi2-core cairo cups dbus expat glib2 gtk3 \
  libdrm libnotify libsecret libx11 libxcb libxcomposite \
  libxdamage libxext libxfixes libxkbcommon libxrandr \
  mesa nspr nss pango systemd-libs xdg-utils
useradd --create-home --uid 1000 builder
chown -R builder:builder "$job_dir"
export MAKEFLAGS='-j2'
export GENOFFICE_BUILD_JOBS=2
runuser -u builder -- bash -c 'cd "$1"; makepkg --cleanbuild --noconfirm; makepkg --printsrcinfo > .SRCINFO' bash "$job_dir"
python "$scripts_dir/validate.py" "$job_dir"
