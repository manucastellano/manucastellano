# 06 — Personaje animado 3D (Google Flow)

El personaje es **la cara del canal sin mostrar la tuya**. Aparece en el gancho (0–3 s) y en el cierre;
el resto del video es el juego con la voz encima.

> Lo que sigue sobre Google Flow (modelos Veo, función para reutilizar un personaje, créditos) es lo que yo sé
> y puede haber cambiado: confirmá en la app los nombres de las funciones, la duración de cada clip y el costo.

## Ficha del personaje

| | |
|---|---|
| **Nombre** (elegí uno, o inventá) | Neón · Flaco Vice · Tano Palmera · Rulo |
| **Rol** | Guía canchero que "ya se sabe todos los atajos" |
| **Personalidad** | Seguro, rápido, un poco pícaro, nunca grita |
| **Rasgos fijos** | Anteojos de aviador espejados (nunca se le ven los ojos), camisa rosa pastel con hojas de palmera, cadena dorada, pelo ondulado oscuro, sonrisa de costado |
| **Paleta** | Rosa/magenta + cian, fondo nocturno con neón |
| **Lo que NO es** | No es parecido a Jason, Lucía ni ningún personaje de Rockstar. Sin logos ni marcas. |

## Bloque de descripción fija

Copiá **este bloque igual, palabra por palabra, al principio de cada prompt**. Es lo que más ayuda a que el
personaje salga igual en todas las escenas (junto con la imagen de referencia).

```
CHARACTER: Stylized 3D animated character in a polished animated-feature-film style.
A charismatic young man, slim build, wavy dark brown hair, light-tan skin, mirrored gold
aviator sunglasses that always hide his eyes, pastel pink short-sleeve shirt with a
white palm-leaf pattern, unbuttoned at the collar, thin gold chain, black trousers.
Confident sideways smirk. Same design in every shot.
STYLE: vibrant pink and cyan neon lighting, tropical city at night, soft cinematic depth of field.
No logos, no text, no real brands, no subtitles.
```

## Paso 1 — Imagen de referencia

Generá la imagen (en Flow o en el generador de imágenes que uses) y quedate con **una sola**:

```
[BLOQUE FIJO]
Character turnaround reference sheet: front view, three-quarter view, side view, full body,
neutral relaxed pose, plain dark background with subtle pink and cyan rim light.
```

Y una segunda en vertical, para usar como base de las escenas:

```
[BLOQUE FIJO]
Waist-up portrait, facing camera, vertical 9:16, standing on a neon-lit street with palm trees
and a retro sports car blurred in the background.
```

Elegí la que más te guste y **usala como referencia del personaje en todas las escenas**
(en Flow, cargándola como ingrediente/elemento del personaje si la función sigue existiendo).

## Paso 2 — Banco de clips reutilizables

Clips cortos, verticales (9:16), **sin diálogo** (ver "¿Habla o no?" abajo). Generá cada uno con:
`[BLOQUE FIJO]` + la línea de la escena + `Vertical 9:16, medium shot, smooth camera.`

| # | Uso | Escena (agregar después del bloque fijo) |
|---|---|---|
| 1 | Gancho "dato" | He looks into the camera, raises one finger as if saying "listen up", slight smirk. |
| 2 | Gancho "secreto" | He leans toward the camera and covers one side of his mouth as if telling a secret. |
| 3 | Gancho "error" | He winces and shakes his head slowly, like he just saw someone make a big mistake. |
| 4 | Gancho "plata" | He fans a thick stack of cash in front of the camera, confident grin. |
| 5 | Gancho "sorpresa" | He lowers his sunglasses slightly with one finger (eyes stay in shadow), surprised expression. |
| 6 | Gancho "noticia" | He holds up a phone toward the camera, the screen glowing (screen content not readable). |
| 7 | Señalar arriba | He points up toward the top of the frame, as if pointing at text above him. |
| 8 | Señalar abajo | He points down toward the bottom of the frame, nodding. |
| 9 | Pensar | He rubs his chin, looking up, thinking. |
| 10 | Ranking | He counts on his fingers: one, two, three, looking at the camera. |
| 11 | Manejando | He drives a retro convertible along a neon coastal road at night, one hand on the wheel. |
| 12 | Celebrar | He does a small victorious fist pump and laughs. |
| 13 | Cierre "comentá" | He points at the camera, then makes a "write to me" gesture with his hand. |
| 14 | Cierre "guardá" | He taps his temple, as if saying "remember this", and winks behind the sunglasses. |
| 15 | Cierre "parte 2" | He walks away from the camera, turns his head back and gives a two-finger salute. |
| 16 | Transición | He snaps his fingers and the scene flashes with pink neon light. |
| 17 | Reacción "mmm" | He raises one eyebrow above the sunglasses, skeptical. |
| 18 | Reacción "jaja" | He laughs, shoulders shaking, hand on his belly. |

Generá 2–3 versiones de cada uno y quedate con la mejor. Guardalas con nombres claros
(`pj_01_gancho_dato.mp4`, `pj_13_cierre_comenta.mp4`…).

## ¿Habla o no?

| Opción | Cómo | Recomendación |
|---|---|---|
| **A. No habla en pantalla** | Clips de gestos (banco de arriba) + tu voz o voz de IA encima | **Empezá por acá.** Más barato, no hay problemas de sincronía de labios, una sola voz en todo el canal. |
| **B. Habla en pantalla** | Clips donde dice la frase del gancho | Para más adelante. No sé qué tan bien sincroniza hoy los labios en español: probá 2–3 antes de producir en serie. |

Prompt de prueba para la opción B:
```
[BLOQUE FIJO]
He looks into the camera and says in Latin American Spanish, confident and fast:
"Si vas a jugar GTA 6, no gastes tu primera plata en esto."
Vertical 9:16, medium close-up, lip-synced dialogue, quiet city ambience.
```

## Cómo encaja en cada video

```
0–3 s    Clip del personaje (gancho #1–6) + texto del gancho en pantalla + voz
3–35 s   Gameplay / trailer con voz y subtítulos (sin personaje, o en una esquina, ver abajo)
35–45 s  Clip del personaje (cierre #13–15) + pregunta en pantalla
```

**Opcional — personaje en la esquina:** recortá un clip de gestos (#7, #8, #9) y ponelo chico abajo
a la izquierda mientras corre el gameplay. Para eso conviene generar algunos clips con fondo liso:
`[BLOQUE FIJO] ... plain solid green background` y quitar el fondo en tu editor (CapCut tiene
quitar fondo / croma).

## Avisos

- **Etiqueta de IA:** marcá los videos como contenido generado con IA cuando la plataforma lo pida
  (revisá las reglas actuales de TikTok, YouTube e Instagram).
- **Derechos:** revisá los términos de uso de Google Flow para uso comercial del contenido que generás.
- **Consistencia:** si un clip sale con el personaje cambiado (otra camisa, se le ven los ojos), descartalo.
  Un personaje que cambia de cara se nota y le resta identidad al canal.
