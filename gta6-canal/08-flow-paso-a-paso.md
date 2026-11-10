# 08 — Google Flow paso a paso

> **Importante:** esto está escrito con lo que yo sé de Flow, que puede estar desactualizado (la herramienta cambia
> seguido). Los nombres de botones, modos, planes y créditos pueden ser distintos cuando entres.
> Donde dice **"si no lo ves"** tenés la alternativa. Si algo no coincide, mandame una captura y lo ajusto.

## 0. Antes de empezar

1. Entrá a **labs.google/flow** con tu cuenta de Google.
2. Flow se usa con un plan pago de Google AI (Pro o Ultra, según lo que yo sabía). Revisá en la app:
   - qué plan tenés y **cuántos créditos por mes** te da;
   - **cuántos créditos gasta cada clip** según el modelo/calidad (los modos "rápidos" suelen gastar menos).
3. **Hacé la cuenta antes de generar:** este plan necesita ~2 imágenes de referencia + 18 clips × 2–3 intentos
   ≈ 40–55 generaciones. Si los créditos no alcanzan, priorizá los clips marcados ⭐ en la tabla del paso 4.
4. Tené abierto [06-personaje.md](06-personaje.md): de ahí copiás el **bloque fijo** y las escenas.

## 1. Crear el proyecto

1. Botón **New project** (o "Nuevo proyecto").
2. Nombre: `Canal GTA VI — Personaje`.
3. Buscá la opción de **formato / relación de aspecto** y elegí **vertical 9:16**.
   - **Si no lo ves (solo horizontal 16:9):** generá en 16:9 y agregá a cada prompt
     `subject centered in frame, empty space on both sides`. Después pasalo a vertical con
     `./herramientas/vertical.sh clip.mp4 clip_vertical.mp4` (recorta el centro, donde está el personaje).

## 2. Imagen de referencia del personaje

Objetivo: **una imagen** que sea "la cara oficial" del personaje.

1. Buscá la opción de **generar imagen** dentro de Flow (en versiones que conocí había generación de imágenes
   integrada para crear "ingredientes").
   - **Si no lo ves:** generala en Gemini (app gemini.google.com, pidiéndole una imagen) o en otro generador,
     y después **subila** a Flow.
2. Pegá el prompt de **hoja de personaje** del Paso 1 de [06-personaje.md](06-personaje.md) (bloque fijo + "Character turnaround reference sheet…").
3. Generá 4 opciones. Elegí la que tenga:
   - anteojos que tapan los ojos del todo;
   - camisa rosa con hojas blancas bien visible;
   - cara simple y expresiva (las caras simples se mantienen mejor entre escenas).
4. Generá ahora la **versión vertical** (segundo prompt del Paso 1) usando la elegida como referencia.
5. **Descargá las dos** y guardalas como `pj_ref_hoja.png` y `pj_ref_vertical.png`. **Mandámelas** para ajustar el bloque fijo.

## 3. Guardar el personaje como "ingrediente"

Flow tenía un modo para generar video a partir de imágenes que le das (personaje, objeto, lugar).
En las versiones que conocí se llamaba **"Ingredients to Video"** (Ingredientes a video).

1. Elegí ese modo en el selector de modo de generación.
2. Agregá `pj_ref_vertical.png` como **ingrediente**. Si te deja guardarlo con nombre, ponele el nombre del personaje.
   - **Si no existe ese modo:** usá **"Frames to Video"** (de fotograma a video) con `pj_ref_vertical.png` como
     **primer fotograma**. El clip arranca con el personaje igual a la referencia y se anima desde ahí.
   - **Si tampoco:** usá solo texto (Text to Video) con el bloque fijo completo. Va a variar más; descartá los que cambien.

## 4. Generar el banco de clips

Para **cada clip** de la tabla:

1. Modo: **Ingredients to Video** (o Frames to Video) con la referencia cargada.
2. Prompt = **bloque fijo** + **escena** + `Vertical 9:16, medium shot, smooth camera.`
3. Si hay opción de **audio**: para estos clips pedí **sin diálogo**. Agregá al prompt `No dialogue, no speech, only soft city ambience.`
   (La voz va después, en la edición.)
4. Generá **2 versiones**. Si ninguna sirve, cambiá una sola cosa del prompt y probá de nuevo.
5. Descargá la mejor con el nombre de la tabla.

| ⭐ | Archivo | Escena (copiar del Paso 2 de 06-personaje.md) |
|---|---|---|
| ⭐ | `pj_01_gancho_dato.mp4` | #1 levanta un dedo, "escuchá" |
| ⭐ | `pj_02_gancho_secreto.mp4` | #2 se acerca y tapa la boca, secreto |
| ⭐ | `pj_03_gancho_error.mp4` | #3 hace una mueca y niega con la cabeza |
| ⭐ | `pj_04_gancho_plata.mp4` | #4 abanica un fajo de billetes |
| ⭐ | `pj_05_gancho_sorpresa.mp4` | #5 baja un poco los anteojos, sorprendido |
| ⭐ | `pj_06_gancho_noticia.mp4` | #6 muestra un celular a cámara |
| | `pj_07_senala_arriba.mp4` | #7 |
| | `pj_08_senala_abajo.mp4` | #8 |
| | `pj_09_pensar.mp4` | #9 |
| ⭐ | `pj_10_ranking.mp4` | #10 cuenta con los dedos 1, 2, 3 |
| | `pj_11_manejando.mp4` | #11 |
| | `pj_12_celebrar.mp4` | #12 |
| ⭐ | `pj_13_cierre_comenta.mp4` | #13 |
| ⭐ | `pj_14_cierre_guarda.mp4` | #14 |
| ⭐ | `pj_15_cierre_parte2.mp4` | #15 |
| | `pj_16_transicion.mp4` | #16 |
| | `pj_17_reaccion_duda.mp4` | #17 |
| | `pj_18_reaccion_risa.mp4` | #18 |

**Los 10 ⭐ alcanzan para los 10 guiones de la previa** ([09-guiones-previa.md](09-guiones-previa.md)).

## 5. Control de calidad (cada clip)

Descartalo si:
- se le ven los ojos o cambió la camisa, el pelo o la cadena;
- aparecen textos, logos o marcas;
- manos deformes o movimientos raros en los primeros 2 segundos (es lo que más se ve);
- se parece a un personaje de Rockstar.

## 6. (Opcional) Clips para la esquina

Para poner al personaje chico sobre el gameplay: generá #7, #8 y #9 de nuevo agregando
`plain solid bright green background, no environment` y en CapCut usá **quitar fondo / croma**.

## 7. (Opcional, después) Prueba de personaje que habla

Prompt de la "Opción B" de [06-personaje.md](06-personaje.md). Probá 2–3 frases. Si la boca no coincide con el
audio en español, quedate con la opción A (sin diálogo).

## Orden de archivos en tu compu

```
canal-gta6/
├── personaje/      pj_ref_hoja.png, pj_ref_vertical.png, pj_01…pj_18.mp4
├── trailers/       trailer1.mp4, trailer2.mp4 (de los canales oficiales de Rockstar)
├── voz/            v01.mp3 … v10.mp3
└── finales/        video01_final.mp4 …
```
