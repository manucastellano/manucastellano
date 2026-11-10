# 03 — Producción con IA

```
Idea → Guion (Claude) → Voz (vos o ElevenLabs) → Clips (tu captura / trailer oficial)
     → Edición vertical + subtítulos (CapCut o herramientas/) → Miniatura → Publicar en las 3
```

## 1. Guiones con Claude

### Prompt para guionar 10 videos de una vez
```
Sos guionista de un canal sin cara de videos cortos sobre GTA VI en español rioplatense neutro.
Escribí 10 guiones de 30–45 segundos con esta estructura:
GANCHO (0–2 s) / CONTEXTO (2–8 s) / VALOR (máx. 3 puntos) / CIERRE (pregunta o "parte 2").
Reglas:
- Frases de menos de 12 palabras. Sin saludos.
- NO inventes datos del juego. Usá solo los datos que te paso abajo.
  Si un guion necesita un dato que no está, poné [COMPLETAR: qué dato falta].
- Las opiniones van marcadas como opinión ("creo que...").
- Debajo de cada línea, indicá entre corchetes qué clip va en pantalla.
Temas de esta semana: [lista de 10 temas del calendario]
Datos verificados que podés usar (con fuente): [pegá los datos + links oficiales]
```

### Prompt para mejorar ganchos
```
Te paso un guion. Dame 5 ganchos alternativos de menos de 10 palabras.
Cada uno tiene que usar uno de estos mecanismos: curiosidad, número concreto, error común,
contraste (antes/después), urgencia. Marcá cuál recomendás y por qué.
[guion]
```

### Prompt para títulos y descripciones (para las 3 plataformas)
```
Para este guion, dame:
- YouTube Shorts: título de hasta 60 caracteres con la búsqueda que haría alguien.
- TikTok: texto de 1 línea + 4 hashtags.
- Instagram: texto de 2 líneas + llamada a comentar + 4 hashtags.
[guion]
```

## 2. Voz (sin cara)

| Opción | Ventaja | Contra |
|---|---|---|
| **Tu voz grabada** | Más auténtica, cero costo | Te lleva más tiempo |
| **Voz de IA (ej. ElevenLabs)** | Rápido, siempre igual | Costo mensual; algunas plataformas pueden mostrar menos el contenido 100% sintético (no lo pude verificar) |

Recomendación: si te sentís cómodo, **tu voz** (la cara sigue oculta). Si usás voz de IA, elegí una voz y
no la cambies nunca. Si clonás tu propia voz, hacelo solo con tu voz.

Tips de grabación con tu voz: celular a 15 cm, en un placard o habitación con ropa (absorbe eco), grabá los 10 guiones juntos.

## 3. Clips

- **Antes de la salida:** trailers oficiales de Rockstar, siempre con tu comentario, zoom, flechas y análisis encima.
  No subas el trailer sin modificar.
- **Después de la salida:** tu propia captura del juego (PS5/Xbox tienen grabación integrada; también una capturadora).
  **Antes de grabar, bajá a cero la música y la radio en los ajustes de audio del juego**: es la causa más común de
  reclamos de derechos de autor ([07-reglas-rockstar.md](07-reglas-rockstar.md)).
- **Sin spoilers:** no subas finales, cinemáticas sueltas ni diálogos clave de la historia.
- **Nunca:** filtraciones ni clips de otros creadores.
- Guardá una carpeta de "clips comodín" (autos, ciudad, atardecer) para rellenar.

## 4. Edición + subtítulos

**Opción fácil:** CapCut (tiene subtítulos automáticos y plantillas). Exportá en 1080×1920 sin marca de agua.

**Opción automática (gratis, en tu compu):** los scripts de [`herramientas/`](herramientas/):
```bash
# 1) Pasar un clip horizontal a vertical 9:16
./herramientas/vertical.sh clip.mp4 clip_vertical.mp4

# 2) Cortar un fragmento (inicio en segundos, duración en segundos)
./herramientas/recortar.sh partida.mp4 125 30 fragmento.mp4

# 3) Generar subtítulos con Whisper y quemarlos en el video
./herramientas/subtitular.sh video_final.mp4 video_con_subs.mp4
```
Requisitos: `ffmpeg` y `openai-whisper` (`pip install -U openai-whisper`). Ver [herramientas/README.md](herramientas/README.md).

Checklist de edición:
- [ ] El primer segundo ya tiene movimiento y texto del gancho en pantalla.
- [ ] Cortes cada 2–3 segundos.
- [ ] Subtítulos centrados en el tercio medio (que no los tapen los botones de la app).
- [ ] Música baja (−20 dB aprox.) y que sea de la biblioteca de cada plataforma.

## 5. Miniaturas / portada

Shorts y Reels usan un fotograma como portada: elegí uno con mucho contraste y poné **3–4 palabras grandes**.

Prompt para generador de imágenes (para fondos, no para imitar arte oficial):
```
Vertical 9:16 thumbnail background, neon-lit tropical city at night, pink and cyan palette,
palm trees, retro sports car silhouette, cinematic, high contrast, empty space at top for large text,
no logos, no text, no real brands
```
Después agregás el texto encima en CapCut/Canva (ej.: "PLATA RÁPIDA", "NADIE LO VIO", "NO HAGAS ESTO").

## 6. Publicar

- Mismo archivo a las 3 plataformas, con el texto adaptado (prompt de títulos de arriba).
- Programá con las herramientas nativas de cada plataforma o con una herramienta de programación de tu elección.
- Respondé los primeros comentarios en la primera hora.
