"""Formato de datos: un evento por fila.

Columnas obligatorias: minuto, equipo, evento
Columnas opcionales:  periodo, jugador, resultado, x, y, metros, detalle, partido,
                      video_seg (segundo del video donde ocurre; lo genera etiquetador.html)

Coordenadas (opcionales):
  x = metros desde el in-goal PROPIO del equipo que realiza la acción
      (0 = su línea de try, 100 = línea de try rival). Así cada equipo
      "ataca hacia la derecha" y no hay que invertir nada en el entretiempo.
  y = metros a lo ancho (0 a 70).
"""
from __future__ import annotations

import pandas as pd

# código -> (nombre legible, descripción)
EVENTOS: dict[str, tuple[str, str]] = {
    "try": ("Try", "Try apoyado (5 pts)"),
    "try_penal": ("Try penal", "Try penal (7 pts)"),
    "conversion": ("Conversión", "Conversión; resultado ok/fallo (2 pts)"),
    "penal_palos": ("Penal a los palos", "Penal pateado a los palos; ok/fallo (3 pts)"),
    "drop": ("Drop", "Drop; ok/fallo (3 pts)"),
    "tackle": ("Tackle", "Tackle; ok = completado, fallo = errado"),
    "portacion": ("Portación", "Portación de pelota (carry); usar 'metros' si se mide"),
    "quiebre": ("Quiebre", "Quiebre de línea (line break)"),
    "offload": ("Offload", "Pase en el contacto"),
    "ruck": ("Ruck", "Ruck propio; ok = retenido, fallo = perdido"),
    "line": ("Line", "Line propio; ok = ganado, fallo = perdido"),
    "scrum": ("Scrum", "Scrum propio; ok = ganado, fallo = perdido / penal en contra"),
    "patada": ("Patada", "Patada en juego; 'metros' opcional"),
    "penal_cometido": ("Penal cometido", "Penal en contra; 'detalle' = motivo"),
    "tarjeta": ("Tarjeta", "Tarjeta; 'detalle' = amarilla/roja"),
    "perdida": ("Pérdida", "Pérdida de pelota (knock-on, forward, robo rival...)"),
    "recuperacion": ("Recuperación", "Pelota recuperada (turnover ganado)"),
    "entrada_22": ("Entrada 22", "Entrada con posesión a la zona de 22 rival"),
}

PUNTOS_OK = {"try": 5, "try_penal": 7, "conversion": 2, "penal_palos": 3, "drop": 3}

_ALIAS_EVENTO = {
    "ensayo": "try", "penal_try": "try_penal", "conv": "conversion", "conversión": "conversion",
    "penal": "penal_palos", "penalty_goal": "penal_palos", "carry": "portacion",
    "portación": "portacion", "line_break": "quiebre", "linebreak": "quiebre",
    "lineout": "line", "kick": "patada", "penalty": "penal_cometido", "infraccion": "penal_cometido",
    "card": "tarjeta", "turnover_lost": "perdida", "error": "perdida", "turnover": "recuperacion",
    "turnover_won": "recuperacion", "22": "entrada_22", "entry_22": "entrada_22",
}
_OK = {"ok", "exito", "éxito", "ganado", "retenido", "completado", "si", "sí", "1", "true", "made", "won", "1.0"}
_FALLO = {"fallo", "falla", "errado", "perdido", "no", "0", "false", "missed", "lost", "0.0"}

OBLIGATORIAS = ["minuto", "equipo", "evento"]
COLUMNAS = ["partido", "minuto", "periodo", "equipo", "jugador", "evento",
            "resultado", "x", "y", "metros", "detalle", "video_seg"]


class ErrorDatos(ValueError):
    pass


def _norm(s) -> str:
    return str(s).strip().lower().replace(" ", "_")


def normalizar(df: pd.DataFrame, partido: str | None = None) -> tuple[pd.DataFrame, list[str]]:
    """Valida y limpia un DataFrame de eventos. Devuelve (df, avisos)."""
    avisos: list[str] = []
    df = df.copy()
    df.columns = [_norm(c) for c in df.columns]

    faltan = [c for c in OBLIGATORIAS if c not in df.columns]
    if faltan:
        raise ErrorDatos(f"Faltan columnas obligatorias: {', '.join(faltan)}")

    for c in COLUMNAS:
        if c not in df.columns:
            df[c] = pd.NA

    df = df.dropna(subset=["equipo", "evento"], how="any")
    df["equipo"] = df["equipo"].astype(str).str.strip()
    df["evento"] = df["evento"].map(_norm).replace(_ALIAS_EVENTO)

    desconocidos = sorted(set(df["evento"]) - set(EVENTOS))
    if desconocidos:
        n = int(df["evento"].isin(desconocidos).sum())
        avisos.append(f"Se ignoraron {n} filas con eventos desconocidos: {', '.join(desconocidos)}")
        df = df[df["evento"].isin(EVENTOS)]

    df["minuto"] = pd.to_numeric(df["minuto"], errors="coerce")
    sin_min = int(df["minuto"].isna().sum())
    if sin_min:
        avisos.append(f"{sin_min} filas sin minuto válido fueron descartadas")
        df = df.dropna(subset=["minuto"])

    df["periodo"] = pd.to_numeric(df["periodo"], errors="coerce")
    df["periodo"] = df["periodo"].fillna((df["minuto"] > 40).astype(int) + 1).astype(int)

    for c in ["x", "y", "metros", "video_seg"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["x"] = df["x"].clip(0, 100)
    df["y"] = df["y"].clip(0, 70)

    def _res(v, evento):
        if pd.isna(v) or str(v).strip() == "":
            # Un try siempre suma; para el resto, sin resultado = desconocido
            return "ok" if evento in ("try", "try_penal") else pd.NA
        v = _norm(v)
        if v in _OK:
            return "ok"
        if v in _FALLO:
            return "fallo"
        return pd.NA

    df["resultado"] = [_res(v, e) for v, e in zip(df["resultado"], df["evento"])]
    df["jugador"] = df["jugador"].astype("string").str.strip()
    df["detalle"] = df["detalle"].astype("string").str.strip().str.lower()

    if partido is not None:
        df["partido"] = df["partido"].fillna(partido) if df["partido"].notna().any() else partido
    df["partido"] = df["partido"].fillna("Partido").astype(str)

    equipos = df.groupby("partido")["equipo"].nunique()
    for p, n in equipos.items():
        if n != 2:
            avisos.append(f"'{p}': se esperaban 2 equipos y hay {n}. Revisá cómo están escritos los nombres.")

    df["puntos"] = [PUNTOS_OK.get(e, 0) if r == "ok" else 0 for e, r in zip(df["evento"], df["resultado"])]
    df = df.sort_values(["partido", "minuto"], kind="stable").reset_index(drop=True)
    return df[COLUMNAS + ["puntos"]], avisos


def plantilla() -> pd.DataFrame:
    filas = [
        dict(minuto=1, periodo=1, equipo="Club Azul", jugador="Pérez", evento="patada", x=40, y=35, metros=35),
        dict(minuto=2, periodo=1, equipo="Club Rojo", jugador="Gómez", evento="portacion", x=30, y=20, metros=4),
        dict(minuto=2, periodo=1, equipo="Club Azul", jugador="López", evento="tackle", resultado="ok", x=70, y=22),
        dict(minuto=3, periodo=1, equipo="Club Rojo", evento="ruck", resultado="ok", x=32, y=24),
        dict(minuto=5, periodo=1, equipo="Club Azul", evento="penal_cometido", detalle="offside", x=65, y=30),
        dict(minuto=6, periodo=1, equipo="Club Rojo", jugador="Díaz", evento="penal_palos", resultado="ok", x=65, y=30),
        dict(minuto=9, periodo=1, equipo="Club Azul", evento="line", resultado="ok", x=80, y=0),
        dict(minuto=9, periodo=1, equipo="Club Azul", evento="entrada_22", x=80, y=5),
        dict(minuto=10, periodo=1, equipo="Club Azul", jugador="Fernández", evento="try", x=100, y=10),
        dict(minuto=10, periodo=1, equipo="Club Azul", jugador="Pérez", evento="conversion", resultado="fallo", x=100, y=10),
    ]
    return pd.DataFrame(filas, columns=COLUMNAS[1:])
