# Herramientas

Scripts para Mac/Linux (en Windows: usar WSL o Git Bash). Requieren **ffmpeg**; `subtitular.sh` además **openai-whisper**.

```bash
# Instalar requisitos
# Mac:    brew install ffmpeg
# Ubuntu: sudo apt install ffmpeg
pip install -U openai-whisper

chmod +x *.sh
```

| Script | Uso |
|---|---|
| `vertical.sh` | `./vertical.sh clip.mp4 clip_vertical.mp4` — pasa 16:9 a 9:16 (1080×1920) recortando el centro |
| `recortar.sh` | `./recortar.sh partida.mp4 125 30 fragmento.mp4` — corta 30 s desde el segundo 125 |
| `subtitular.sh` | `./subtitular.sh video.mp4 video_subs.mp4 [modelo]` — transcribe con Whisper y quema subtítulos |

Flujo típico: `recortar.sh` → `vertical.sh` → montar voz/clips en tu editor → `subtitular.sh` sobre el video final.

> Si los subtítulos quedan muy grandes o chicos, cambiá `FontSize` en `subtitular.sh`.
> Si Whisper escribe mal una palabra, corregí el `.srt` y volvé a quemarlo con:
> `ffmpeg -i video.mp4 -vf "subtitles=video_subs.srt" -c:a copy salida.mp4`
