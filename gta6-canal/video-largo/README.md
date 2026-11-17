# Video largo: "GTA VI: todo lo que tenés que saber" (≈20 min)

| Archivo | Qué es |
|---|---|
| [guion.md](guion.md) | Guion completo en 13 secciones (≈2.800 palabras), con los planos de trailer de cada una |
| [montaje.py](montaje.py) | Arma el video solo: planos de los trailers en cámara lenta con paneo, carteles de sección, crédito a Rockstar, tu voz |

## Paso 1 — Verificar
Revisá en el guion todo lo marcado **[VERIFICAR]** (precio, PC, online, descripciones de personajes y zonas).
Corregí el texto si algo cambió.

## Paso 2 — Grabar la voz
- **Un archivo por sección:** `00.mp3`, `01.mp3`, … `12.mp3` (sirve también `.wav` o `.m4a`).
- Podés usar el **video borrador con teleprompter** que te pasé: tiene el texto abajo, sección por sección.
  No hace falta seguir su ritmo: el montaje final se ajusta a lo que dures vos.
- Celular a 15 cm, en una habitación con ropa o cortinas (menos eco), sin música de fondo.
- Si te equivocás, repetí la frase entera.
- Metelos en una carpeta `voz/` y pasámelos (acá o por Drive).

## Paso 3 — Video final (lo hago yo, o vos con este comando)
```bash
python3 montaje.py --t1 trailer1.mp4 --t2 trailer2.mp4 --voz voz/ --salida GTA6_final.mp4
```
Genera también `GTA6_final_capitulos.txt` con los tiempos de cada sección, para pegar en la descripción.

## Para publicar en YouTube

**Título (elegí uno):**
- GTA 6: TODO lo que tenés que saber antes de jugar
- GTA 6 explicado: historia, personajes, mapa y todo lo confirmado
- Todo lo que sabemos de GTA 6 (sin rumores)

**Descripción:**
```
Todo lo confirmado de GTA 6 antes de su salida: la historia de Lucía y Jason, los trailers analizados,
el mapa de Leonida, los personajes secundarios y qué cosas todavía no se saben. Sin rumores.

[pegar acá los capítulos del archivo _capitulos.txt]

Imágenes: trailers oficiales de Rockstar Games. Video de análisis y comentario.
#GTA6 #GTAVI #GrandTheftAuto
```

**Miniatura:** fotograma de Vice City al atardecer + texto grande "TODO SOBRE GTA 6" (3–4 palabras máximo).

**Antes de subir:** checklist de [../07-reglas-rockstar.md](../07-reglas-rockstar.md). El montaje ya usa los trailers
**sin su audio** (la música tiene derechos de terceros) y evita las escenas subidas de tono.
