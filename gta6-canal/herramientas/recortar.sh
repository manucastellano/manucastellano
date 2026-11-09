#!/usr/bin/env bash
# Corta un fragmento de un video.
# Uso: ./recortar.sh entrada.mp4 INICIO_SEG DURACION_SEG salida.mp4
# Ej.: ./recortar.sh partida.mp4 125 30 fragmento.mp4   (desde 2:05, 30 segundos)
set -euo pipefail
if [ $# -ne 4 ]; then echo "Uso: $0 entrada.mp4 INICIO_SEG DURACION_SEG salida.mp4" >&2; exit 1; fi
ffmpeg -y -ss "$2" -i "$1" -t "$3" \
  -c:v libx264 -preset medium -crf 20 -c:a aac -b:a 160k -movflags +faststart \
  "$4"
echo "Listo: $4"
