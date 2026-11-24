# 🏉 Rugby Analytics

Herramienta sencilla para **analizar partidos de rugby** a partir de eventos etiquetados
(tackles, rucks, lines, scrums, penales, tries…) y obtener **conclusiones automáticas**,
mapas de cancha y tendencias de temporada.

Inspirada en proyectos de análisis de fútbol como
[404-Possession-Not-Found](https://github.com/rodrifdezz/404-Possession-Not-Found) y
[football-blueprints](https://github.com/opengoalapp/football-blueprints), pero adaptada a la
realidad del rugby: en vez de depender de datos de tracking (difíciles de conseguir), trabaja con
**eventos que cualquier entrenador o analista puede cargar mirando el video**.

---

## ⚡ Uso rápido

```bash
cd rugby-analytics
pip install -r requirements.txt
streamlit run app.py
```

Se abre en el navegador. En la barra lateral elegís:

| Opción | Para qué |
|---|---|
| **Partido de ejemplo** | Ver la herramienta funcionando (datos ficticios) |
| **Temporada de ejemplo** | Ver la comparación entre partidos (6 fechas ficticias) |
| **Subir archivo(s)** | Analizar tus partidos (CSV o Excel; podés subir varios a la vez) |
| **Etiquetado en vivo** | Cargar el partido con botones mientras lo mirás y descargar el CSV |

## 🎬 Flujo de trabajo con videos MP4 (recomendado)

1. Abrí **[`etiquetador.html`](etiquetador.html)** con doble clic (Chrome, Edge o Safari). No necesita
   instalación ni internet, y **el video no se sube a ningún lado**: se reproduce desde tu computadora.
2. **🎬 Abrir video MP4**, escribí los nombres de los equipos y elegí hacia dónde ataca tu equipo en el 1º tiempo.
3. Pausá en el kick-off de cada tiempo y tocá **Marcar inicio 1º / 2º tiempo** (así el minuto de juego es exacto).
4. Etiquetá con el teclado mientras mirás. Cada evento guarda el **segundo exacto del video**:

   | Tecla | Evento | Tecla | Evento | Tecla | Evento |
   |---|---|---|---|---|---|
   | `1` / `2` | Equipo A / B | `T` / `Y` | Tackle ✓ / ✗ | `C` | Portación |
   | `R` / `E` | Ruck ✓ / ✗ | `L` / `K` | Line ✓ / ✗ | `S` / `D` | Scrum ✓ / ✗ |
   | `Q` | Quiebre | `O` | Offload | `X` | Patada |
   | `Z` | Entrada 22 | `P` | Penal cometido | `J` | Tarjeta |
   | `U` | Pérdida | `I` | Recuperación | `G` | TRY |
   | `V` / `N` | Conversión ✓ / ✗ | `F` / `H` | Penal palos ✓ / ✗ | `M` / `B` | Drop ✓ / ✗ |
   | `Espacio` | Play/pausa | `←` `→` | ±3 s (`Shift` ±10 s) | `⌫` | Deshacer |

   Opcional: **clic en la cancha** para marcar la posición (como se ve en la imagen; se convierte sola
   según el equipo y el tiempo), y escribir jugador, motivo del penal o metros.
5. **⬇️ Descargar CSV** y subilo a la app (`streamlit run app.py` → *Subir archivo(s)*).
6. **Revisar clips**: en el etiquetador filtrá (por ejemplo *tackle* + *fallo* + tu equipo) y tocá
   **▶️ Reproducir clips**: ves todas esas jugadas seguidas, con segundos antes y después configurables.
   Con **📂 Abrir CSV** podés retomar un partido o revisarlo otro día.

> 💡 Se guarda automáticamente en el navegador cada vez que cargás un evento, pero descargá el CSV al
> terminar (es tu respaldo real). Para un partido completo, etiquetar todo lleva varias horas:
> empezá por lo que más te importa (tackles, formaciones, penales, entradas a 22, puntos).

## 📊 Qué muestra

| Pestaña | Contenido |
|---|---|
| 📋 Resumen | Conclusiones automáticas (alertas ⚠️, fortalezas ✅, datos 📌) y números clave |
| 🗺️ Territorio | Mapa de calor de dónde jugó cada equipo, distribución por zonas, patadas |
| ⚔️ Ataque | Quiebres, entradas a 22, **puntos por entrada a 22**, metros por portación |
| 🛡️ Defensa | Efectividad de tackle, mapa de tackles hechos/errados, **caída por tramos de 10'** |
| 🧱 Formaciones | Line, scrum, retención de ruck, pateo a los palos |
| 🚩 Disciplina | Penales por motivo, por minuto y por zona; tarjetas |
| 👤 Jugadores | Tabla individual, top tackleadores y portadores |
| 📈 Momentum | Evolución del marcador, dominio por tramos de 5', 1º vs 2º tiempo |
| 🎬 Para revisar | Errores propios y daño recibido con el **tiempo exacto del video** de cada jugada |
| 📅 Temporada | (con 2+ partidos) G-E-P, tendencias y qué métricas se asocian con ganar |

## 📝 Cómo cargar un partido (formato CSV)

Una fila por acción. Descargá la plantilla: [`data/plantilla_partido.csv`](data/plantilla_partido.csv).

| Columna | ¿Obligatoria? | Ejemplo | Notas |
|---|---|---|---|
| `minuto` | ✅ | `23` | |
| `equipo` | ✅ | `Club Azul` | Escribilo siempre igual |
| `evento` | ✅ | `tackle` | Ver lista abajo |
| `resultado` | Recomendada | `ok` / `fallo` | También acepta ganado/perdido, si/no, 1/0 |
| `jugador` | Opcional | `Pérez` | Habilita la pestaña Jugadores |
| `x` | Opcional | `65` | Metros desde el in-goal **propio** del equipo que hace la acción (0 → 100) |
| `y` | Opcional | `30` | Metros a lo ancho (0 → 70) |
| `metros` | Opcional | `4` | Metros ganados (portaciones) o distancia (patadas) |
| `detalle` | Opcional | `offside` | Motivo del penal, color de tarjeta, etc. |
| `periodo` | Opcional | `2` | Si falta, se deduce del minuto |
| `partido` | Opcional | `Fecha 3 vs Halcones` | Si falta, se usa el nombre del archivo |
| `video_seg` | Opcional | `1834.5` | Segundo del video (lo completa el etiquetador) |

> 💡 **Coordenadas**: `x` se mide siempre desde el in-goal del equipo que hace la acción.
> Así los dos equipos "atacan hacia la derecha" y no hace falta invertir nada en el entretiempo.
> Si no cargás coordenadas, todo funciona salvo los mapas.

### Eventos

| Código | Qué es | `resultado` |
|---|---|---|
| `try` / `try_penal` | Try (5) / try penal (7) | — |
| `conversion` | Conversión (2) | ok / fallo |
| `penal_palos` / `drop` | Penal a los palos / drop (3) | ok / fallo |
| `tackle` | Tackle | ok = hecho, fallo = errado |
| `portacion` | Portación (carry) | — |
| `quiebre` | Quiebre de línea | — |
| `offload` | Pase en el contacto | — |
| `ruck` | Ruck propio | ok = retenido, fallo = perdido |
| `line` / `scrum` | Formación propia | ok = ganado, fallo = perdido |
| `patada` | Patada en juego | — |
| `entrada_22` | Entrada con pelota a la 22 rival | — |
| `penal_cometido` | Penal en contra | — (`detalle` = motivo) |
| `tarjeta` | Tarjeta | — (`detalle` = amarilla / roja) |
| `perdida` | Pérdida de pelota | — |
| `recuperacion` | Pelota recuperada (turnover) | — |

También se aceptan algunos nombres en inglés (`carry`, `lineout`, `line_break`, `turnover`…).

**Consejo práctico**: no hace falta cargar todo. Con solo `tackle`, `line`, `scrum`,
`penal_cometido`, puntos y `entrada_22` ya obtenés la mayoría de las conclusiones.

## 🧠 Cómo se generan las conclusiones

Son **reglas simples y transparentes** (archivo [`rugby/insights.py`](rugby/insights.py)), por ejemplo:

- Efectividad de tackle por debajo del umbral → alerta, con la cantidad de tackles errados.
- Caída de la efectividad de tackle de 8 o más puntos entre el 1º y el 2º tiempo → posible fatiga.
- Más entradas a 22 que el rival pero menos puntos → problema de definición.
- Más posesión estimada y derrota → posesión sin profundidad.
- Penales en campo propio, tarjetas, line/scrum poco confiables, balance de pelotas…

En la barra lateral elegís el **nivel de competencia** (por defecto *Alto rendimiento*):

| Umbral | Alto rendimiento | Amateur / formativo |
|---|---|---|
| Efectividad de tackle mínima | 88% | 80% |
| Line propio ganado | 88% | 80% |
| Scrum propio ganado | 90% | 80% |
| Retención de ruck | 95% | 88% |
| Pateo a los palos | 75% | 60% |
| Penales máximos | 10 | 13 |

⚠️ Estos valores son **puntos de partida orientativos que elegí yo**, no estándares oficiales ni
promedios publicados de ninguna competencia. Lo mejor en alto rendimiento es calibrarlos con
**el promedio de tus propios partidos** (pestaña *Temporada*) o con datos de referencia de tu liga,
y ajustarlos en *⚙️ Umbrales*.
Las conclusiones son un punto de partida: confirmalas siempre con el video.

### Limitaciones (para interpretar bien los números)

- **Posesión estimada** = proporción de acciones con pelota, no tiempo real de posesión.
- **Puntos por entrada a 22**: cada anotación se atribuye a la última entrada a 22 del mismo
  equipo en los 3 minutos previos (heurística).
- **Temporada → "¿Qué se asocia con ganar?"**: es una correlación con pocos partidos; sirve para
  generar preguntas, no para sacar conclusiones definitivas.
- Los datos de ejemplo son **ficticios** (generados por [`rugby/demo_data.py`](rugby/demo_data.py)).

## 🗂️ Estructura

```
rugby-analytics/
├── app.py               # App web (Streamlit)
├── etiquetador.html     # Etiquetador de video MP4 (abrir con doble clic)
├── rugby/
│   ├── schema.py        # Formato de datos, validación y alias
│   ├── metrics.py       # Métricas por equipo, jugador, período y temporada
│   ├── insights.py      # Conclusiones automáticas (reglas + umbrales)
│   ├── pitch.py         # Cancha de rugby y mapas (Plotly)
│   └── demo_data.py     # Generador de partidos ficticios
├── data/                # Plantilla y ejemplos
└── tests/               # python -m unittest discover -s tests
```

## 🐍 Usarlo desde Python / Jupyter

```python
import pandas as pd
from rugby import schema, metrics, insights

df, avisos = schema.normalizar(pd.read_csv("data/ejemplo_partido.csv"))
print(metrics.tabla_comparativa(df))
for c in insights.generar(df):
    print(c.icono, c.equipo, c.texto)
```

## 🚀 Ideas para seguir

- Exportar un informe PDF del partido.
- Etiquetar haciendo clic directamente sobre la cancha.
- Importar datos de proveedores (si tenés acceso a feeds de eventos).
- Detección automática asistida por visión por computadora (ver nota abajo).

### ¿Y detectar los eventos automáticamente desde el video?

Es posible en teoría, pero **no es algo que pueda prometer que funcione bien** con videos de
transmisión: requiere detectar jugadores y pelota con cámaras que se mueven y hacen zoom,
y luego entrenar modelos para reconocer tackles, rucks, etc. con miles de ejemplos etiquetados.
Los CSV que generes con el etiquetador son justamente esos ejemplos: si en el futuro querés
intentar automatizarlo, ya vas a tener los datos para entrenar.
