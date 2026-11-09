#!/usr/bin/env bash
# Transcribe el audio con Whisper (local, gratis) y quema los subtítulos en el video.
# Uso: ./subtitular.sh entrada.mp4 salida.mp4 [modelo]
#   modelo: tiny | base | small (default) | medium  -> más grande = más preciso y más lento
# Requisitos: ffmpeg y openai-whisper  (pip install -U openai-whisper)
# Revisá el .srt generado antes de publicar: Whisper puede equivocarse con nombres propios.
set -euo pipefail
if [ $# -lt 2 ]; then echo "Uso: $0 entrada.mp4 salida.mp4 [modelo]" >&2; exit 1; fi
ENTRADA="$1"; SALIDA="$2"; MODELO="${3:-small}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

whisper "$ENTRADA" --model "$MODELO" --language Spanish \
  --output_format srt --output_dir "$TMP" \
  --word_timestamps True --max_words_per_line 4

SRT="$TMP/$(basename "${ENTRADA%.*}").srt"
cp "$SRT" "${SALIDA%.*}.srt"   # copia editable al lado del video

# Estilo: blanco, borde negro grueso, centrado en el tercio medio (Alignment=2 + MarginV)
ESTILO="FontName=Arial,FontSize=14,Bold=1,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=0,Alignment=2,MarginV=90"
ffmpeg -y -i "$ENTRADA" -vf "subtitles='$SRT':force_style='$ESTILO'" \
  -c:v libx264 -preset medium -crf 20 -c:a copy -movflags +faststart "$SALIDA"
echo "Listo: $SALIDA  (subtítulos editables en ${SALIDA%.*}.srt)"
