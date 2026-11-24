"""🏉 Rugby Analytics — app web para analizar partidos a partir de eventos etiquetados.

Ejecutar:  streamlit run app.py
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from rugby import demo_data, insights, metrics as M, pitch, schema

st.set_page_config(page_title="Rugby Analytics", page_icon="🏉", layout="wide")

# ---------------------------------------------------------------- datos
@st.cache_data
def _demo_partido():
    return demo_data.generar_partido("Club Azul", "Club Rojo", 0.2, -0.1, semilla=7, nombre="Demo: Azul vs Rojo")


@st.cache_data
def _demo_temporada():
    return demo_data.temporada("Club Azul", n=6)


def _leer(archivo) -> pd.DataFrame:
    nombre = archivo.name.rsplit(".", 1)[0]
    if archivo.name.lower().endswith((".xlsx", ".xls")):
        raw = pd.read_excel(archivo)
    else:
        contenido = archivo.getvalue().decode("utf-8-sig", errors="replace")
        sep = ";" if contenido.count(";") > contenido.count(",") else ","
        raw = pd.read_csv(io.StringIO(contenido), sep=sep)
    if "partido" not in [c.strip().lower() for c in raw.columns]:
        raw["partido"] = nombre
    return raw


if "etiquetado" not in st.session_state:
    st.session_state.etiquetado = pd.DataFrame(columns=schema.COLUMNAS)

with st.sidebar:
    st.title("🏉 Rugby Analytics")
    fuente = st.radio("Datos", ["Partido de ejemplo", "Temporada de ejemplo", "Subir archivo(s)", "Etiquetado en vivo"],
                      help="Los ejemplos son datos FICTICIOS generados para probar la herramienta.")
    raw = None
    if fuente == "Partido de ejemplo":
        raw = _demo_partido()
    elif fuente == "Temporada de ejemplo":
        raw = _demo_temporada()
    elif fuente == "Subir archivo(s)":
        archivos = st.file_uploader("CSV o Excel (un partido por archivo)", type=["csv", "xlsx", "xls"],
                                    accept_multiple_files=True)
        if archivos:
            try:
                raw = pd.concat([_leer(a) for a in archivos], ignore_index=True)
            except Exception as e:  # noqa: BLE001
                st.error(f"No pude leer el archivo: {e}")
        st.download_button("⬇️ Descargar plantilla CSV", schema.plantilla().to_csv(index=False).encode("utf-8"),
                           "plantilla_partido.csv", "text/csv")
    else:
        raw = st.session_state.etiquetado if len(st.session_state.etiquetado) else None

    with st.expander("⚙️ Umbrales de las conclusiones"):
        st.caption("Referencias orientativas: ajustalas al nivel de tu competencia.")
        U = insights.UMBRALES_DEFECTO.copy()
        U["tackle"] = st.slider("Efectividad de tackle mínima %", 70, 98, int(U["tackle"]))
        U["line"] = st.slider("Line ganado mínimo %", 60, 98, int(U["line"]))
        U["scrum"] = st.slider("Scrum ganado mínimo %", 60, 98, int(U["scrum"]))
        U["ruck"] = st.slider("Retención de ruck mínima %", 70, 99, int(U["ruck"]))
        U["pateo"] = st.slider("Pateo a palos mínimo %", 40, 95, int(U["pateo"]))
        U["penales"] = st.slider("Penales máximos aceptables", 4, 20, int(U["penales"]))

# ---------------------------------------------------------------- etiquetado en vivo
def pantalla_etiquetado():
    st.header("✍️ Etiquetado en vivo")
    st.caption("Mirá el partido (o el video) y cargá cada acción con un clic. Al terminar, descargá el CSV.")
    c1, c2, c3 = st.columns(3)
    local = c1.text_input("Equipo 1", "Mi Club")
    visita = c2.text_input("Equipo 2", "Rival")
    partido = c3.text_input("Partido", f"{local} vs {visita}")

    c1, c2, c3, c4 = st.columns([1, 1, 2, 2])
    minuto = c1.number_input("Minuto", 0.0, 100.0, step=1.0, key="min")
    equipo = c2.radio("Equipo", [local, visita], key="eq")
    jugador = c3.text_input("Jugador (opcional)", key="jug")
    detalle = c4.text_input("Detalle (opcional: motivo del penal, amarilla…)", key="det")
    usar_xy = st.checkbox("Registrar posición en la cancha", value=True)
    x = y = None
    if usar_xy:
        cx, cy = st.columns(2)
        x = cx.slider("Metros desde el try PROPIO (0 = mi in-goal, 100 = in-goal rival)", 0, 100, 50, key="x")
        y = cy.select_slider("Ancho", options=[5, 15, 25, 35, 45, 55, 65], value=35,
                             format_func=lambda v: {5: "touch izq.", 35: "centro", 65: "touch der."}.get(v, str(v)))

    def agregar(evento, resultado=None):
        fila = dict(partido=partido, minuto=minuto, periodo=1 if minuto <= 40 else 2, equipo=equipo,
                    jugador=jugador or None, evento=evento, resultado=resultado, x=x, y=y, metros=None,
                    detalle=detalle or None)
        st.session_state.etiquetado = pd.concat([st.session_state.etiquetado, pd.DataFrame([fila])], ignore_index=True)

    botones = [
        ("🟢 Tackle ✓", "tackle", "ok"), ("🔴 Tackle ✗", "tackle", "fallo"), ("🏃 Portación", "portacion", None),
        ("⚡ Quiebre", "quiebre", None), ("🟢 Ruck ✓", "ruck", "ok"), ("🔴 Ruck ✗", "ruck", "fallo"),
        ("🟢 Line ✓", "line", "ok"), ("🔴 Line ✗", "line", "fallo"), ("🟢 Scrum ✓", "scrum", "ok"),
        ("🔴 Scrum ✗", "scrum", "fallo"), ("🦶 Patada", "patada", None), ("🎯 Entrada 22", "entrada_22", None),
        ("🏉 TRY", "try", "ok"), ("🟢 Conversión ✓", "conversion", "ok"), ("🔴 Conversión ✗", "conversion", "fallo"),
        ("🟢 Penal palos ✓", "penal_palos", "ok"), ("🔴 Penal palos ✗", "penal_palos", "fallo"),
        ("🚩 Penal cometido", "penal_cometido", None), ("🟨 Tarjeta", "tarjeta", None),
        ("💥 Pérdida", "perdida", None), ("🧲 Recuperación", "recuperacion", None),
    ]
    cols = st.columns(7)
    for i, (txt, ev, res) in enumerate(botones):
        if cols[i % 7].button(txt, width="stretch", key=f"b{i}"):
            agregar(ev, res)

    st.subheader(f"Eventos cargados: {len(st.session_state.etiquetado)}")
    st.session_state.etiquetado = st.data_editor(st.session_state.etiquetado, num_rows="dynamic",
                                                 width="stretch", height=260, key="editor")
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Descargar CSV", st.session_state.etiquetado.to_csv(index=False).encode("utf-8"),
                       f"{partido}.csv", "text/csv", width="stretch")
    if c2.button("🗑️ Borrar todo", width="stretch"):
        st.session_state.etiquetado = pd.DataFrame(columns=schema.COLUMNAS)
        st.rerun()
    st.info("Cuando tengas eventos de ambos equipos, el análisis aparece debajo automáticamente.")


if fuente == "Etiquetado en vivo":
    pantalla_etiquetado()
    st.divider()
    # se lee DESPUÉS de los botones para incluir el último evento cargado
    raw = st.session_state.etiquetado if len(st.session_state.etiquetado) else None

if raw is None or len(raw) == 0:
    if fuente != "Etiquetado en vivo":
        st.title("🏉 Rugby Analytics")
        st.markdown(
            "Subí uno o varios CSV/Excel con los eventos del partido, o probá con los **datos de ejemplo**.\n\n"
            "**Columnas mínimas:** `minuto`, `equipo`, `evento`. "
            "Opcionales: `periodo`, `jugador`, `resultado` (ok/fallo), `x`, `y`, `metros`, `detalle`."
        )
        st.dataframe(pd.DataFrame([{"código": k, "evento": v[0], "cómo cargarlo": v[1]}
                                   for k, v in schema.EVENTOS.items()]), hide_index=True, width="stretch")
    st.stop()

try:
    datos, avisos = schema.normalizar(raw)
except schema.ErrorDatos as e:
    st.error(str(e))
    st.stop()
for a in avisos:
    st.warning(a)
if datos.empty:
    st.stop()

# ---------------------------------------------------------------- selección
partidos = list(dict.fromkeys(datos["partido"]))
vista_temporada = len(partidos) > 1
c1, c2 = st.columns([3, 1])
partido_sel = c1.selectbox("Partido", partidos, index=len(partidos) - 1) if vista_temporada else partidos[0]
df = datos[datos["partido"] == partido_sel]
eqs = M.equipos(df)
if len(eqs) != 2:
    st.error(f"El partido necesita exactamente 2 equipos y tiene {len(eqs)}: {eqs}")
    st.stop()
color = {eqs[0]: pitch.COLORES[0], eqs[1]: pitch.COLORES[1]}

# ---------------------------------------------------------------- encabezado
mar = M.marcador(df)
st.markdown(f"<h2 style='text-align:center;margin-bottom:0'>"
            f"<span style='color:{color[eqs[0]]}'>{eqs[0]}</span> {mar[eqs[0]]} – {mar[eqs[1]]} "
            f"<span style='color:{color[eqs[1]]}'>{eqs[1]}</span></h2>"
            f"<p style='text-align:center;color:gray'>{partido_sel} · {len(df)} eventos</p>", unsafe_allow_html=True)

tab_names = ["📋 Resumen", "🗺️ Territorio", "⚔️ Ataque", "🛡️ Defensa", "🧱 Formaciones", "🚩 Disciplina",
             "👤 Jugadores", "📈 Momentum"]
if vista_temporada:
    tab_names.append("📅 Temporada")
tabs = st.tabs(tab_names)
tabla = M.tabla_comparativa(df)


def barras_comparar(filas: list[str], titulo: str = "", pct: bool = False):
    t = tabla.loc[filas].T.reset_index(names="equipo").melt("equipo", var_name="métrica", value_name="valor")
    fig = px.bar(t, x="valor", y="métrica", color="equipo", barmode="group", orientation="h",
                 color_discrete_map=color, text=t["valor"].map(lambda v: "—" if pd.isna(v) else f"{v:.0f}"),
                 title=titulo)
    fig.update_layout(height=110 + 70 * len(filas), yaxis_title=None, xaxis_title="%" if pct else None,
                      legend_title=None, margin=dict(t=40, b=10))
    if pct:
        fig.update_xaxes(range=[0, 105])
    st.plotly_chart(fig, width="stretch")


def fmt_tabla(t: pd.DataFrame) -> pd.DataFrame:
    return t.apply(lambda col: col.map(lambda v: "—" if pd.isna(v) else (f"{v:.0f}" if float(v).is_integer() else f"{v:.1f}")))


# ---------------------------------------------------------------- 1. resumen
with tabs[0]:
    concl = insights.generar(df, U)
    c1, c2 = st.columns([3, 2])
    with c1:
        st.subheader("🧠 Conclusiones automáticas")
        st.caption("Generadas con reglas transparentes y los umbrales de la barra lateral. Confirmalas con el video.")
        for eq in eqs:
            st.markdown(f"**<span style='color:{color[eq]}'>{eq}</span>**", unsafe_allow_html=True)
            propias = [c for c in concl if c.equipo == eq]
            if not propias:
                st.write("Sin observaciones destacadas.")
            for c in propias:
                st.markdown(f"{c.icono} {c.texto}")
    with c2:
        st.subheader("Números clave")
        clave = ["Puntos", "Tries", "Posesión estimada %", "Territorio %", "Efectividad tackle %",
                 "Line ganado %", "Scrum ganado %", "Penales cometidos", "Entradas a 22",
                 "Puntos por entrada 22", "Balance de pelotas"]
        st.dataframe(fmt_tabla(tabla.loc[clave]), width="stretch", height=420)
    with st.expander("Ver todas las métricas"):
        st.dataframe(fmt_tabla(tabla), width="stretch")
        st.download_button("⬇️ Descargar métricas (CSV)", tabla.to_csv().encode("utf-8"),
                           f"metricas_{partido_sel}.csv", "text/csv")
    st.caption("ℹ️ *Posesión estimada* = proporción de acciones con pelota (portaciones, rucks, patadas…), "
               "no tiempo real de posesión. *Territorio* = % de esas acciones en campo rival (requiere coordenadas).")

# ---------------------------------------------------------------- 2. territorio
with tabs[1]:
    c1, c2 = st.columns(2)
    for col, eq in zip((c1, c2), eqs):
        with col:
            st.plotly_chart(pitch.mapa_calor(df[df["equipo"] == eq], M.ACCIONES_POSESION,
                                             f"Dónde jugó {eq} con la pelota", "YlOrRd"), width="stretch")
    z = pitch.zonas(df, M.ACCIONES_POSESION)
    if not z.empty:
        fig = px.bar(z, x="zona", y="%", color="equipo", barmode="group", color_discrete_map=color,
                     text=z["%"].map(lambda v: f"{v:.0f}%"), title="Distribución territorial de las acciones con pelota",
                     category_orders={"zona": [n for *_, n in pitch.ZONAS]})
        fig.update_layout(legend_title=None, yaxis_title="% de acciones", xaxis_title=None)
        st.plotly_chart(fig, width="stretch")
    pat = df[df["evento"] == "patada"]
    if len(pat):
        st.plotly_chart(px.box(pat, x="equipo", y="metros", color="equipo", color_discrete_map=color, points="all",
                               title="Distancia de las patadas en juego (m)"), width="stretch")

# ---------------------------------------------------------------- 3. ataque
with tabs[2]:
    barras_comparar(["Portaciones", "Quiebres", "Offloads", "Entradas a 22", "Tries"], "Volumen ofensivo")
    c1, c2 = st.columns(2)
    for col, eq in zip((c1, c2), eqs):
        with col:
            st.plotly_chart(pitch.mapa_eventos(df[df["equipo"] == eq], ["quiebre", "try", "entrada_22"],
                                               f"Quiebres, entradas a 22 y tries · {eq}", color_por_resultado=False),
                            width="stretch")
    p22 = M.puntos_por_entrada_22(df)
    t22 = pd.DataFrame(p22).T.reset_index(names="equipo")
    c1, c2 = st.columns(2)
    c1.plotly_chart(px.bar(t22, x="equipo", y="ppe", color="equipo", color_discrete_map=color, text_auto=".1f",
                           title="Puntos por entrada a 22 (eficiencia en zona roja)"), width="stretch")
    car = df[(df["evento"] == "portacion") & df["metros"].notna()]
    if len(car):
        c2.plotly_chart(px.histogram(car, x="metros", color="equipo", color_discrete_map=color, barmode="overlay",
                                     nbins=20, opacity=0.65, title="Metros por portación"), width="stretch")
    st.caption("Puntos por entrada a 22: cada anotación se atribuye a la última entrada a 22 del mismo equipo en "
               "los 3 minutos previos (heurística).")

# ---------------------------------------------------------------- 4. defensa
with tabs[3]:
    barras_comparar(["Efectividad tackle %"], "Efectividad de tackle", pct=True)
    c1, c2 = st.columns(2)
    for col, eq in zip((c1, c2), eqs):
        with col:
            st.plotly_chart(pitch.mapa_eventos(df[df["equipo"] == eq], ["tackle"],
                                               f"Tackles de {eq} (blanco = hecho, amarillo ✗ = errado)"),
                            width="stretch")
    tk = df[(df["evento"] == "tackle") & df["resultado"].notna()].copy()
    if len(tk):
        tk["tramo"] = pd.cut(tk["minuto"], [0, 10, 20, 30, 40, 50, 60, 70, 200],
                             labels=["0-10", "10-20", "20-30", "30-40", "40-50", "50-60", "60-70", "70+"], include_lowest=True)
        ef = tk.groupby(["equipo", "tramo"], observed=False)["resultado"].apply(
            lambda s: (s == "ok").mean() * 100 if len(s) else np.nan).reset_index(name="efectividad")
        fig = px.line(ef, x="tramo", y="efectividad", color="equipo", markers=True, color_discrete_map=color,
                      title="Efectividad de tackle por tramo de 10 minutos (¿hay caída física?)")
        fig.add_hline(y=U["tackle"], line_dash="dot", annotation_text=f"referencia {U['tackle']:.0f}%")
        fig.update_layout(yaxis_title="%", legend_title=None)
        st.plotly_chart(fig, width="stretch")
    barras_comparar(["Recuperaciones", "Pérdidas"], "Batalla por la pelota")

# ---------------------------------------------------------------- 5. formaciones
with tabs[4]:
    barras_comparar(["Line ganado %", "Scrum ganado %", "Retención ruck %", "Efectividad pateo a palos %"],
                    "Efectividad en formaciones y pateo", pct=True)
    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(pitch.mapa_eventos(df, ["line"], "Lines (todos)"), width="stretch")
    with c2:
        st.plotly_chart(pitch.mapa_eventos(df, ["penal_palos", "conversion", "drop"], "Pateo a los palos"),
                        width="stretch")
    st.dataframe(fmt_tabla(tabla.loc[["Lines", "Line ganado %", "Scrums", "Scrum ganado %", "Rucks", "Retención ruck %"]]),
                 width="stretch")

# ---------------------------------------------------------------- 6. disciplina
with tabs[5]:
    barras_comparar(["Penales cometidos", "Penales en campo propio", "Amarillas", "Rojas"], "Disciplina")
    pm = M.penales_por_motivo(df)
    c1, c2 = st.columns(2)
    if not pm.empty:
        c1.plotly_chart(px.bar(pm, y="motivo", x="cantidad", color="equipo", color_discrete_map=color, orientation="h",
                               barmode="group", title="Penales por motivo"), width="stretch")
    pen = df[df["evento"] == "penal_cometido"]
    if len(pen):
        pen = pen.assign(minuto_tramo=(pen["minuto"] // 10 * 10).astype(int))
        c2.plotly_chart(px.histogram(pen, x="minuto", color="equipo", color_discrete_map=color, nbins=8,
                                     barmode="group", title="¿Cuándo se cometen los penales?"), width="stretch")
    for eq in eqs:
        st.plotly_chart(pitch.mapa_eventos(df[df["equipo"] == eq], ["penal_cometido", "tarjeta"],
                                           f"Dónde comete penales {eq} (coordenadas desde su propio in-goal)",
                                           color_por_resultado=False), width="stretch")

# ---------------------------------------------------------------- 7. jugadores
with tabs[6]:
    j = M.jugadores(df)
    if j.empty:
        st.info("Cargá la columna `jugador` para ver estadísticas individuales.")
    else:
        eq_sel = st.radio("Equipo", eqs, horizontal=True, key="eqj")
        je = j[j["equipo"] == eq_sel].drop(columns="equipo")
        st.dataframe(je, width="stretch", hide_index=True, column_config={
            "Efectividad tackle %": st.column_config.ProgressColumn("Efectividad tackle %", format="%.0f",
                                                                   min_value=0, max_value=100),
        })
        c1, c2 = st.columns(2)
        top_t = je.nlargest(8, "Tackles hechos")
        c1.plotly_chart(px.bar(top_t, x=["Tackles hechos", "Tackles errados"], y="jugador", orientation="h",
                               title="Top tackleadores", color_discrete_sequence=["#43a047", "#e53935"])
                        .update_layout(yaxis={"categoryorder": "total ascending"}, legend_title=None),
                        width="stretch")
        top_c = je.nlargest(8, "Metros") if je["Metros"].sum() else je.nlargest(8, "Portaciones")
        c2.plotly_chart(px.bar(top_c, x="Metros" if je["Metros"].sum() else "Portaciones", y="jugador", orientation="h",
                               title="Top portadores", color_discrete_sequence=[color[eq_sel]])
                        .update_layout(yaxis={"categoryorder": "total ascending"}), width="stretch")

# ---------------------------------------------------------------- 8. momentum
with tabs[7]:
    ev = M.evolucion_marcador(df)
    fig = go.Figure()
    for eq in eqs:
        e = ev[ev["equipo"] == eq]
        fig.add_trace(go.Scatter(x=e["minuto"], y=e["acumulado"], mode="lines+markers", line_shape="hv", name=eq,
                                 line=dict(color=color[eq], width=3),
                                 text=e.get("evento", pd.Series(dtype=str)).fillna("") + " " +
                                 e.get("jugador", pd.Series(dtype=str)).fillna("").astype(str),
                                 hovertemplate="min %{x:.0f}: %{y} pts<br>%{text}<extra></extra>"))
    fig.add_vline(x=40, line_dash="dot", annotation_text="entretiempo")
    fig.update_layout(title="Evolución del marcador", xaxis_title="minuto", yaxis_title="puntos", legend_title=None)
    st.plotly_chart(fig, width="stretch")

    # índice de presión: acciones con pelota en campo rival por tramo de 5'
    d = df[df["evento"].isin(M.ACCIONES_POSESION)].copy()
    d["tramo"] = (d["minuto"] // 5 * 5).astype(int)
    d["peso"] = np.where(d["x"].fillna(50) > 50, 1.0, 0.4)
    pr = d.groupby(["tramo", "equipo"])["peso"].sum().unstack(fill_value=0)
    if len(pr.columns) == 2:
        dif = (pr[eqs[0]] - pr[eqs[1]]).reset_index(name="dominio")
        dif["quién domina"] = np.where(dif["dominio"] >= 0, eqs[0], eqs[1])
        fig = px.bar(dif, x="tramo", y="dominio", color="quién domina", color_discrete_map=color,
                     title=f"Momentum: dominio territorial por tramo de 5' (arriba = {eqs[0]}, abajo = {eqs[1]})")
        fig.update_layout(xaxis_title="minuto", yaxis_title="índice de dominio", legend_title=None)
        st.plotly_chart(fig, width="stretch")
        st.caption("Índice = acciones con pelota ponderadas (1 en campo rival, 0,4 en campo propio). "
                   "Es una aproximación para ver quién empujó en cada momento.")
    pp = M.por_periodo(df)
    if not pp.empty:
        st.subheader("1º vs 2º tiempo")
        cols = ["Puntos", "Efectividad tackle %", "Penales cometidos", "Retención ruck %", "Line ganado %", "Pérdidas"]
        st.dataframe(fmt_tabla(pp.set_index(["equipo", "periodo"])[cols].T), width="stretch")

# ---------------------------------------------------------------- 9. temporada
if vista_temporada:
    with tabs[8]:
        todos = sorted(set(datos["equipo"]), key=lambda e: -(datos["equipo"] == e).sum())
        eq_t = st.selectbox("Equipo a seguir", todos)
        tt = M.tendencia_temporada(datos, eq_t)
        if tt.empty:
            st.info("Ese equipo no aparece en los partidos cargados.")
        else:
            tt["Resultado"] = np.select([tt["Puntos"] > tt["Puntos rival"], tt["Puntos"] < tt["Puntos rival"]],
                                        ["G", "P"], "E")
            g, e_, p = (tt["Resultado"] == "G").sum(), (tt["Resultado"] == "E").sum(), (tt["Resultado"] == "P").sum()
            c = st.columns(4)
            c[0].metric("Partidos", len(tt))
            c[1].metric("G-E-P", f"{g}-{e_}-{p}")
            c[2].metric("Puntos a favor / partido", f"{tt['Puntos'].mean():.1f}")
            c[3].metric("Puntos en contra / partido", f"{tt['Puntos rival'].mean():.1f}")
            met = st.multiselect("Métricas", [k for k in tt.columns if k not in ("partido", "Rival", "Resultado")],
                                 default=["Efectividad tackle %", "Line ganado %", "Penales cometidos"])
            if met:
                m = tt.melt(id_vars=["partido"], value_vars=met, var_name="métrica", value_name="valor")
                fig = px.line(m, x="partido", y="valor", color="métrica", markers=True,
                              title=f"Tendencia de {eq_t} partido a partido")
                fig.update_layout(xaxis_title=None, legend_title=None)
                st.plotly_chart(fig, width="stretch")
            # correlación simple ganar vs métricas
            st.subheader("¿Qué se asocia con ganar?")
            num = tt.select_dtypes("number").drop(columns=["Puntos", "Puntos rival"], errors="ignore")
            dif = tt["Puntos"] - tt["Puntos rival"]
            if len(tt) >= 4:
                corr = num.apply(lambda c: c.corr(dif) if c.std() > 0 else np.nan).dropna().sort_values()
                corr = corr[corr.abs() >= 0.3]
                if len(corr):
                    fig = px.bar(corr, orientation="h", title="Correlación con la diferencia de puntos",
                                 color=corr > 0, color_discrete_map={True: "#43a047", False: "#e53935"})
                    fig.update_layout(showlegend=False, xaxis_title="correlación (−1 a 1)", yaxis_title=None)
                    st.plotly_chart(fig, width="stretch")
                st.caption(f"Con {len(tt)} partidos, esto es solo orientativo: correlación no implica causa y "
                           "con pocas muestras puede ser casualidad.")
            else:
                st.info("Se necesitan al menos 4 partidos para buscar patrones.")
            st.dataframe(fmt_tabla(tt.set_index("partido").drop(columns=["Rival", "Resultado"]).T), width="stretch")
