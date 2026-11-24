#!/bin/bash
# Doble clic en Mac para abrir Rugby Analytics.
# La primera vez prepara un entorno de Python (tarda unos minutos); después abre directo.
cd "$(dirname "$0")" || exit 1

PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo ""
  echo "❌ Necesitás Python 3.10 o más nuevo."
  echo "   Descargalo de https://www.python.org/downloads/ (botón 'Download Python'),"
  echo "   instalalo y volvé a hacer doble clic en este archivo."
  echo ""
  read -r -p "Enter para cerrar…"
  exit 1
fi

if [ ! -x ".venv/bin/streamlit" ] || [ requirements.txt -nt .venv/.instalado ]; then
  echo "⏳ Preparando todo (solo la primera vez, puede tardar unos minutos)…"
  "$PY" -m venv .venv || { read -r -p "Error creando el entorno. Enter para cerrar…"; exit 1; }
  .venv/bin/python -m pip install --upgrade pip -q
  if ! .venv/bin/python -m pip install -r requirements.txt; then
    read -r -p "❌ Falló la instalación (copiá el error de arriba). Enter para cerrar…"
    exit 1
  fi
  touch .venv/.instalado
fi

PUERTO=8501
echo "🏉 Abriendo Rugby Analytics en el navegador… (para cerrarla, cerrá esta ventana)"
# Se abre el navegador desde acá para que Streamlit no pida un email en la terminal.
( sleep 4; command -v open >/dev/null 2>&1 && open "http://localhost:$PUERTO" ) &
exec .venv/bin/streamlit run app.py --server.headless true --server.port "$PUERTO" --browser.gatherUsageStats false
