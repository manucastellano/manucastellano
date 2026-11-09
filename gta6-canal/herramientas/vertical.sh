#!/usr/bin/env bash
# Convierte un video horizontal (16:9) a vertical 1080x1920 (9:16) recortando el centro.
# Uso: ./vertical.sh entrada.mp4 salida.mp4
set -euo pipefail
if [ $# -ne 2 ]; then echo "Uso: $0 entrada.mp4 salida.mp4" >&2; exit 1; fi
ffmpeg -y -i "$1" \
  -vf "crop='min(iw,ih*9/16)':ih,scale=1080:1920,setsar=1" \
  -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 160k -movflags +faststart \
  "$2"
echo "Listo: $2"
