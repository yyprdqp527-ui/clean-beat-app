#!/bin/bash
# Wrapper to decode embedded base64 audio from template into static/sounds/cheer.wav
PY=./scripts/decode_cheer_from_template.py
if [ ! -f "$PY" ]; then
  echo "Missing $PY"
  exit 1
fi
python3 "$PY"
