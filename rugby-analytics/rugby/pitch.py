"""Cancha de rugby y mapas con Plotly. Coordenadas: x 0-100 (try propio -> try rival), y 0-70."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

PASTO = "#2e7d32"
LINEA = "rgba(255,255,255,0.85)"
COLORES = ["#1e88e5", "#e53935"]  # equipo 1, equipo 2

ZONAS = [(0, 22, "Propio 22"), (22, 50, "Propio 22-50"), (50, 78, "Rival 50-22"), (78, 100.01, "22 rival")]


def cancha(titulo: str = "", alto: int = 370) -> go.Figure:
    fig = go.Figure()
    s = []
    s.append(dict(type="rect", x0=-10, x1=110, y0=0, y1=70, fillcolor=PASTO, line_width=0, layer="below"))
    s.append(dict(type="rect", x0=-10, x1=0, y0=0, y1=70, fillcolor="#1b5e20", line_width=0, layer="below"))
    s.append(dict(type="rect", x0=100, x1=110, y0=0, y1=70, fillcolor="#1b5e20", line_width=0, layer="below"))
    for x, dash, w in [(0, "solid", 3), (100, "solid", 3), (22, "solid", 2), (78, "solid", 2),
                       (50, "solid", 2), (40, "dash", 1), (60, "dash", 1), (-10, "solid", 2), (110, "solid", 2)]:
        s.append(dict(type="line", x0=x, x1=x, y0=0, y1=70, line=dict(color=LINEA, width=w, dash=dash)))
    for y in (5, 15, 55, 65):
        s.append(dict(type="line", x0=0, x1=100, y0=y, y1=y, line=dict(color="rgba(255,255,255,0.35)", width=1, dash="dot")))
    s.append(dict(type="rect", x0=-10, x1=110, y0=0, y1=70, line=dict(color=LINEA, width=2)))
    fig.update_layout(shapes=s)
    # Postes
    fig.add_trace(go.Scatter(x=[0, 0, 100, 100], y=[32.2, 37.8, 32.2, 37.8], mode="markers",
                             marker=dict(symbol="line-ew-open", size=10, color="white", line_width=3),
                             hoverinfo="skip", showlegend=False))
    for x, t in [(22, "22"), (50, "50"), (78, "22")]:
        fig.add_annotation(x=x, y=72.5, text=t, showarrow=False, font=dict(color="#666", size=11))
    fig.add_annotation(x=5, y=-3.5, text="◀ campo propio", showarrow=False, font=dict(color="#666", size=11))
    fig.add_annotation(x=95, y=-3.5, text="ataque ▶", showarrow=False, font=dict(color="#666", size=11))
    fig.update_xaxes(range=[-11, 111], visible=False, fixedrange=True)
    fig.update_yaxes(range=[-6, 75], visible=False, fixedrange=True, scaleanchor="x", scaleratio=1)
    fig.update_layout(title=titulo, height=alto, margin=dict(l=5, r=5, t=40 if titulo else 10, b=5),
                      plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=-0.02))
    return fig


def mapa_eventos(df: pd.DataFrame, eventos: list[str], titulo: str = "", color_por_resultado: bool = True) -> go.Figure:
    fig = cancha(titulo)
    d = df[df["evento"].isin(eventos) & df["x"].notna()].copy()
    d["y"] = d["y"].fillna(35)
    if d.empty:
        fig.add_annotation(x=50, y=35, text="Sin datos con coordenadas", showarrow=False,
                           font=dict(color="white", size=16))
        return fig
    grupos = [("ok", "Éxito", "#ffffff", "circle"), ("fallo", "Fallo", "#ffeb3b", "x")] if color_por_resultado \
        else [(None, "Eventos", "#ffffff", "circle")]
    for res, nombre, color, simbolo in grupos:
        g = d if res is None else d[d["resultado"] == res]
        if res == "ok":
            g = d[d["resultado"] != "fallo"]
        if g.empty:
            continue
        txt = (g["minuto"].map(lambda m: f"min {m:.0f}") + " · " + g["evento"] + " · " +
               g["jugador"].fillna("—").astype(str) + " " + g["detalle"].fillna("").astype(str))
        fig.add_trace(go.Scatter(x=g["x"], y=g["y"], mode="markers", name=nombre, text=txt, hoverinfo="text",
                                 marker=dict(size=10, color=color, symbol=simbolo, opacity=0.85,
                                             line=dict(color="#111", width=1))))
    return fig


def mapa_calor(df: pd.DataFrame, eventos: list[str], titulo: str = "", color: str = "Hot") -> go.Figure:
    fig = cancha(titulo)
    d = df[df["evento"].isin(eventos) & df["x"].notna()]
    if len(d) < 3:
        fig.add_annotation(x=50, y=35, text="Pocos datos con coordenadas", showarrow=False,
                           font=dict(color="white", size=16))
        return fig
    h, xe, ye = np.histogram2d(d["x"], d["y"].fillna(35), bins=[10, 7], range=[[0, 100], [0, 70]])
    fig.add_trace(go.Heatmap(z=h.T, x=(xe[:-1] + xe[1:]) / 2, y=(ye[:-1] + ye[1:]) / 2, colorscale=color,
                             opacity=0.6, zmin=0, showscale=False, hovertemplate="%{z:.0f} acciones<extra></extra>"))
    return fig


def zonas(df: pd.DataFrame, eventos: list[str]) -> pd.DataFrame:
    d = df[df["evento"].isin(eventos) & df["x"].notna()]
    filas = []
    for eq, de in d.groupby("equipo", sort=False):
        tot = len(de)
        for x0, x1, nombre in ZONAS:
            n = int(((de["x"] >= x0) & (de["x"] < x1)).sum())
            filas.append({"equipo": eq, "zona": nombre, "acciones": n, "%": n / tot * 100 if tot else 0})
    return pd.DataFrame(filas)
