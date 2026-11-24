"""Cálculo de métricas a partir de eventos normalizados (ver schema.normalizar)."""
from __future__ import annotations

import numpy as np
import pandas as pd

# Acciones que implican tener la pelota: se usan para ESTIMAR posesión y territorio.
ACCIONES_POSESION = ["portacion", "quiebre", "offload", "ruck", "patada", "entrada_22"]


def _pct(ok: float, total: float) -> float:
    return float(ok) / float(total) * 100 if total else np.nan


def equipos(df: pd.DataFrame) -> list[str]:
    return list(dict.fromkeys(df["equipo"]))  # orden de aparición


def rival(df: pd.DataFrame, equipo: str) -> str | None:
    otros = [e for e in equipos(df) if e != equipo]
    return otros[0] if otros else None


def marcador(df: pd.DataFrame) -> dict[str, int]:
    return {e: int(df.loc[df["equipo"] == e, "puntos"].sum()) for e in equipos(df)}


def _exito(d: pd.DataFrame, evento: str) -> tuple[int, int]:
    s = d.loc[(d["evento"] == evento) & d["resultado"].notna(), "resultado"]
    return int((s == "ok").sum()), int(len(s))


def puntos_por_entrada_22(df: pd.DataFrame) -> dict[str, dict]:
    """Atribuye cada anotación a la última entrada a 22 si fue del mismo equipo,
    en el mismo período y en los 3 minutos previos (heurística)."""
    out = {e: {"entradas": 0, "puntos": 0} for e in equipos(df)}
    entradas = df[df["evento"] == "entrada_22"]
    for e in out:
        out[e]["entradas"] = int((entradas["equipo"] == e).sum())
    anot = df[df["puntos"] > 0]
    for _, a in anot.iterrows():
        previas = entradas[(entradas["minuto"] <= a["minuto"]) &
                           (entradas["periodo"] == a["periodo"]) &
                           (entradas["partido"] == a["partido"])]
        if previas.empty:
            continue
        ult = previas.iloc[-1]
        if ult["equipo"] == a["equipo"] and a["minuto"] - ult["minuto"] <= 3:
            out[a["equipo"]]["puntos"] += int(a["puntos"])
    for v in out.values():
        v["ppe"] = v["puntos"] / v["entradas"] if v["entradas"] else np.nan
    return out


def resumen_equipo(df: pd.DataFrame, equipo: str) -> dict:
    d = df[df["equipo"] == equipo]
    riv = rival(df, equipo)
    dr = df[df["equipo"] == riv] if riv else df.iloc[0:0]
    ev = d["evento"].value_counts()

    tk_ok, tk_tot = _exito(d, "tackle")
    rk_ok, rk_tot = _exito(d, "ruck")
    ln_ok, ln_tot = _exito(d, "line")
    sc_ok, sc_tot = _exito(d, "scrum")
    pat_ok = int(((d["evento"].isin(["conversion", "penal_palos", "drop"])) & (d["resultado"] == "ok")).sum())
    pat_tot = int(((d["evento"].isin(["conversion", "penal_palos", "drop"])) & d["resultado"].notna()).sum())

    pos_propia = int(d["evento"].isin(ACCIONES_POSESION).sum())
    pos_rival = int(dr["evento"].isin(ACCIONES_POSESION).sum())

    acc = d[d["evento"].isin(ACCIONES_POSESION) & d["x"].notna()]
    territorio = _pct((acc["x"] > 50).sum(), len(acc))

    pen = d[d["evento"] == "penal_cometido"]
    pen_campo_propio = int((pen["x"] < 50).sum()) if pen["x"].notna().any() else np.nan

    tarjetas = d[d["evento"] == "tarjeta"]["detalle"].fillna("amarilla")
    p22 = puntos_por_entrada_22(df).get(equipo, {})

    return {
        "Puntos": int(d["puntos"].sum()),
        "Tries": int(ev.get("try", 0) + ev.get("try_penal", 0)),
        "Posesión estimada %": _pct(pos_propia, pos_propia + pos_rival),
        "Territorio %": territorio,
        "Portaciones": int(ev.get("portacion", 0)),
        "Metros ganados": float(d.loc[d["evento"] == "portacion", "metros"].sum(min_count=1)) if "metros" in d else np.nan,
        "Quiebres": int(ev.get("quiebre", 0)),
        "Offloads": int(ev.get("offload", 0)),
        "Entradas a 22": p22.get("entradas", 0),
        "Puntos por entrada 22": p22.get("ppe", np.nan),
        "Tackles hechos": tk_ok,
        "Tackles errados": tk_tot - tk_ok,
        "Efectividad tackle %": _pct(tk_ok, tk_tot),
        "Rucks": rk_tot,
        "Retención ruck %": _pct(rk_ok, rk_tot),
        "Lines": ln_tot,
        "Line ganado %": _pct(ln_ok, ln_tot),
        "Scrums": sc_tot,
        "Scrum ganado %": _pct(sc_ok, sc_tot),
        "Efectividad pateo a palos %": _pct(pat_ok, pat_tot),
        "Patadas en juego": int(ev.get("patada", 0)),
        "Penales cometidos": int(ev.get("penal_cometido", 0)),
        "Penales en campo propio": pen_campo_propio,
        "Amarillas": int((tarjetas.str.contains("amar")).sum()),
        "Rojas": int((tarjetas.str.contains("roj")).sum()),
        "Pérdidas": int(ev.get("perdida", 0)),
        "Recuperaciones": int(ev.get("recuperacion", 0)),
        "Balance de pelotas": int(ev.get("recuperacion", 0)) - int(ev.get("perdida", 0)),
    }


def tabla_comparativa(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({e: resumen_equipo(df, e) for e in equipos(df)})


def por_periodo(df: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for p, dp in df.groupby("periodo"):
        for e in equipos(df):
            r = resumen_equipo(dp.assign(), e) if e in set(dp["equipo"]) else {}
            if r:
                filas.append({"periodo": int(p), "equipo": e, **r})
    return pd.DataFrame(filas)


def evolucion_marcador(df: pd.DataFrame) -> pd.DataFrame:
    filas = []
    for e in equipos(df):
        d = df[(df["equipo"] == e) & (df["puntos"] > 0)][["minuto", "puntos", "evento", "jugador"]]
        acumulado = d["puntos"].cumsum()
        filas.append(pd.DataFrame({"equipo": e, "minuto": [0.0], "acumulado": [0]}))
        filas.append(pd.DataFrame({"equipo": e, "minuto": d["minuto"].values, "acumulado": acumulado.values,
                                   "evento": d["evento"].values, "jugador": d["jugador"].values}))
        filas.append(pd.DataFrame({"equipo": e, "minuto": [max(80.0, df["minuto"].max())],
                                   "acumulado": [int(d["puntos"].sum())]}))
    return pd.concat(filas, ignore_index=True)


def mejor_racha(df: pd.DataFrame) -> dict | None:
    """Mayor cantidad de puntos seguidos de un equipo sin que el rival anote."""
    anot = df[df["puntos"] > 0]
    if anot.empty:
        return None
    mejor, actual = None, None
    for _, a in anot.iterrows():
        if actual and actual["equipo"] == a["equipo"]:
            actual["puntos"] += a["puntos"]
            actual["hasta"] = a["minuto"]
        else:
            actual = {"equipo": a["equipo"], "puntos": int(a["puntos"]), "desde": a["minuto"], "hasta": a["minuto"]}
        if mejor is None or actual["puntos"] > mejor["puntos"]:
            mejor = dict(actual)
    return mejor


def jugadores(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["jugador"].notna() & (df["jugador"] != "")]
    if d.empty:
        return pd.DataFrame()
    g = d.groupby(["equipo", "jugador"])
    t = pd.DataFrame({
        "Puntos": g["puntos"].sum(),
        "Tries": g["evento"].apply(lambda s: int(s.isin(["try"]).sum())),
        "Portaciones": g["evento"].apply(lambda s: int((s == "portacion").sum())),
        "Metros": d[d["evento"] == "portacion"].groupby(["equipo", "jugador"])["metros"].sum(),
        "Quiebres": g["evento"].apply(lambda s: int((s == "quiebre").sum())),
        "Tackles hechos": d[(d["evento"] == "tackle") & (d["resultado"] == "ok")].groupby(["equipo", "jugador"]).size(),
        "Tackles errados": d[(d["evento"] == "tackle") & (d["resultado"] == "fallo")].groupby(["equipo", "jugador"]).size(),
        "Recuperaciones": g["evento"].apply(lambda s: int((s == "recuperacion").sum())),
        "Penales": g["evento"].apply(lambda s: int((s == "penal_cometido").sum())),
        "Pérdidas": g["evento"].apply(lambda s: int((s == "perdida").sum())),
    }).fillna(0)
    tot = t["Tackles hechos"] + t["Tackles errados"]
    t["Efectividad tackle %"] = np.where(tot > 0, t["Tackles hechos"] / tot.replace(0, np.nan) * 100, np.nan)
    num = [c for c in t.columns if c != "Efectividad tackle %"]
    t[num] = t[num].astype(int)
    return t.reset_index().sort_values(["equipo", "Puntos", "Tackles hechos"], ascending=[True, False, False])


def penales_por_motivo(df: pd.DataFrame) -> pd.DataFrame:
    d = df[df["evento"] == "penal_cometido"].copy()
    d["motivo"] = d["detalle"].fillna("sin especificar")
    return d.groupby(["equipo", "motivo"]).size().rename("cantidad").reset_index()


def tendencia_temporada(df: pd.DataFrame, equipo: str) -> pd.DataFrame:
    """Una fila por partido con las métricas del equipo elegido."""
    filas = []
    for p, dp in df.groupby("partido", sort=False):
        if equipo not in set(dp["equipo"]):
            continue
        r = resumen_equipo(dp, equipo)
        riv = rival(dp, equipo)
        r["Puntos rival"] = int(dp.loc[dp["equipo"] == riv, "puntos"].sum()) if riv else 0
        r["Rival"] = riv
        r["partido"] = p
        filas.append(r)
    return pd.DataFrame(filas)


# (evento, resultado, de quién) -> categoría. "propio" = errores del equipo; "rival" = lo que le hicieron.
_REVISAR = [
    ("tackle", "fallo", "propio", "Tackle errado"),
    ("penal_cometido", None, "propio", "Penal cometido"),
    ("tarjeta", None, "propio", "Tarjeta"),
    ("line", "fallo", "propio", "Line perdido"),
    ("scrum", "fallo", "propio", "Scrum perdido"),
    ("ruck", "fallo", "propio", "Ruck perdido"),
    ("perdida", None, "propio", "Pérdida"),
    ("quiebre", None, "rival", "Quiebre sufrido"),
    ("try", None, "rival", "Try recibido"),
]


def _mmss(s) -> str:
    if pd.isna(s):
        return "—"
    s = int(s)
    h, m, x = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{x:02d}" if h else f"{m}:{x:02d}"


def momentos_para_revisar(df: pd.DataFrame, equipo: str) -> pd.DataFrame:
    """Lista de jugadas a revisar en video para un equipo: sus errores y lo que le hizo daño el rival."""
    riv = rival(df, equipo)
    partes = []
    for ev, res, quien, cat in _REVISAR:
        eq = equipo if quien == "propio" else riv
        m = (df["equipo"] == eq) & (df["evento"] == ev)
        if res:
            m &= df["resultado"] == res
        d = df[m].copy()
        d["categoría"] = cat
        partes.append(d)
    if not partes:
        return pd.DataFrame()
    r = pd.concat(partes).sort_values("minuto")
    if r.empty:
        return pd.DataFrame()
    # coordenadas siempre desde la perspectiva del equipo analizado
    x_eq = np.where(r["equipo"] == equipo, r["x"], 100 - r["x"])
    zona = pd.Series(x_eq, index=r.index).map(lambda x: "—" if pd.isna(x) else ("propio 22" if x < 22 else "campo propio" if x < 50
                                                        else "campo rival" if x < 78 else "22 rival"))
    return pd.DataFrame({
        "Video": r["video_seg"].map(_mmss),
        "Min": r["minuto"].round(0).astype(int).astype(str) + "'",
        "categoría": r["categoría"],
        "Equipo": r["equipo"],
        "Jugador": r["jugador"].fillna("—"),
        "Zona": zona,
        "Detalle": r["detalle"].fillna(""),
    })
