#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

# Instalação do Chrome
if [[ ! -d $STORAGE_DIR/chrome ]]; then
  echo "...Instalando Google Chrome..."
  mkdir -p $STORAGE_DIR/chrome
  cd $STORAGE_DIR/chrome
  wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
  dpkg -x google-chrome-stable_current_amd64.deb .
fi