"""Conclusiones automáticas basadas en reglas simples y transparentes.

Los umbrales son REFERENCIAS ORIENTATIVAS, no estándares oficiales: ajustalos
al nivel de tu competencia desde la barra lateral de la app.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd

from . import metrics as M

UMBRALES_DEFECTO = {
    "tackle": 85.0,        # % efectividad de tackle
    "line": 85.0,          # % line propio ganado
    "scrum": 85.0,         # % scrum propio ganado
    "ruck": 90.0,          # % retención en ruck
    "pateo": 70.0,         # % efectividad a palos
    "penales": 10,         # penales cometidos en el partido
    "caida_tackle": 8.0,   # caída (puntos %) de efectividad de tackle entre tiempos
}


@dataclass
class Conclusion:
    tipo: str      # "fortaleza" | "alerta" | "dato"
    equipo: str
    texto: str
    prioridad: int  # 1 = más importante

    @property
    def icono(self) -> str:
        return {"fortaleza": "✅", "alerta": "⚠️", "dato": "📌"}[self.tipo]


def _ok(v) -> bool:
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def generar(df: pd.DataFrame, u: dict | None = None) -> list[Conclusion]:
    u = {**UMBRALES_DEFECTO, **(u or {})}
    out: list[Conclusion] = []
    eqs = M.equipos(df)
    if len(eqs) != 2:
        return out
    res = {e: M.resumen_equipo(df, e) for e in eqs}
    a, b = eqs

    # Resultado
    pa, pb = res[a]["Puntos"], res[b]["Puntos"]
    if pa != pb:
        g, p = (a, b) if pa > pb else (b, a)
        dif = abs(pa - pb)
        tipo = "ajustado (dentro de un try convertido)" if dif <= 7 else "claro"
        out.append(Conclusion("dato", g, f"Ganó {g} {max(pa, pb)}-{min(pa, pb)}: resultado {tipo}.", 1))
    else:
        out.append(Conclusion("dato", a, f"Empate {pa}-{pb}.", 1))

    racha = M.mejor_racha(df)
    if racha and racha["puntos"] >= 10:
        out.append(Conclusion("dato", racha["equipo"],
                              f"{racha['equipo']} hizo {racha['puntos']} puntos seguidos entre el min "
                              f"{racha['desde']:.0f} y el {racha['hasta']:.0f}: fue su momento de dominio.", 2))

    for e in eqs:
        r, rv = res[e], res[M.rival(df, e)]

        # Defensa
        tk = r["Efectividad tackle %"]
        if _ok(tk):
            if tk < u["tackle"]:
                out.append(Conclusion("alerta", e, f"Efectividad de tackle {tk:.0f}% (referencia {u['tackle']:.0f}%): "
                                                   f"{r['Tackles errados']} tackles errados. Trabajar técnica y conexión defensiva.", 2))
            elif tk >= u["tackle"] + 5:
                out.append(Conclusion("fortaleza", e, f"Defensa sólida: {tk:.0f}% de efectividad en tackle.", 3))

        # Formaciones fijas
        for clave, nombre, campo, n in [("line", "line", "Line ganado %", "Lines"),
                                        ("scrum", "scrum", "Scrum ganado %", "Scrums")]:
            v = r[campo]
            if _ok(v) and r[n] >= 3:
                if v < u[clave]:
                    out.append(Conclusion("alerta", e, f"{nombre.capitalize()} propio ganado {v:.0f}% ({r[n]} lanzamientos/formaciones): "
                                                       f"plataforma de ataque poco confiable.", 2))
                elif v >= 95:
                    out.append(Conclusion("fortaleza", e, f"{nombre.capitalize()} muy firme: {v:.0f}% ganado.", 4))

        rk = r["Retención ruck %"]
        if _ok(rk) and r["Rucks"] >= 10 and rk < u["ruck"]:
            out.append(Conclusion("alerta", e, f"Retención en ruck {rk:.0f}%: se pierden pelotas en el contacto "
                                               f"(revisar apoyo y llegada del segundo jugador).", 2))

        # Disciplina
        if r["Penales cometidos"] >= u["penales"]:
            extra = ""
            if _ok(r["Penales en campo propio"]) and r["Penales en campo propio"]:
                extra = f", {r['Penales en campo propio']} en campo propio (oportunidades de 3 puntos para el rival)"
            out.append(Conclusion("alerta", e, f"Indisciplina: {r['Penales cometidos']} penales cometidos{extra}.", 1))
        if r["Amarillas"] or r["Rojas"]:
            out.append(Conclusion("alerta", e, f"Tarjetas: {r['Amarillas']} amarilla(s), {r['Rojas']} roja(s).", 2))

        # Pateo
        pt = r["Efectividad pateo a palos %"]
        if _ok(pt) and pt < u["pateo"]:
            out.append(Conclusion("alerta", e, f"Pateo a los palos {pt:.0f}%: puntos dejados en la cancha.", 2))

        # Eficiencia ofensiva
        ppe, ppe_r = r["Puntos por entrada 22"], rv["Puntos por entrada 22"]
        if _ok(ppe) and r["Entradas a 22"] >= 3:
            if ppe < 2.5:
                out.append(Conclusion("alerta", e, f"Poca conversión en zona roja: {ppe:.1f} puntos por entrada a 22 "
                                                   f"({r['Entradas a 22']} entradas).", 2))
            elif ppe >= 4:
                out.append(Conclusion("fortaleza", e, f"Muy eficiente en 22 rival: {ppe:.1f} puntos por entrada.", 2))
            if _ok(ppe_r) and r["Entradas a 22"] > rv["Entradas a 22"] and r["Puntos"] < rv["Puntos"]:
                out.append(Conclusion("dato", e, f"{e} llegó más veces a 22 ({r['Entradas a 22']} vs {rv['Entradas a 22']}) "
                                                 f"pero hizo menos puntos: el problema fue la definición, no la llegada.", 1))

        # Posesión vs resultado
        pos = r["Posesión estimada %"]
        if _ok(pos) and pos >= 58 and r["Puntos"] < rv["Puntos"]:
            out.append(Conclusion("dato", e, f"Tuvo más la pelota (~{pos:.0f}%) y perdió: posesión sin profundidad.", 2))

        # Pelotas
        bal = r["Balance de pelotas"]
        if bal <= -4:
            out.append(Conclusion("alerta", e, f"Balance de pelotas negativo ({bal:+d}): demasiadas pérdidas.", 2))
        elif bal >= 4:
            out.append(Conclusion("fortaleza", e, f"Ganó la batalla de las pelotas ({bal:+d} recuperaciones netas).", 3))

    # Caída física/de concentración en el segundo tiempo
    pp = M.por_periodo(df)
    if not pp.empty and set(pp["periodo"]) >= {1, 2}:
        for e in eqs:
            t1 = pp[(pp["equipo"] == e) & (pp["periodo"] == 1)]["Efectividad tackle %"]
            t2 = pp[(pp["equipo"] == e) & (pp["periodo"] == 2)]["Efectividad tackle %"]
            if len(t1) and len(t2) and _ok(t1.iloc[0]) and _ok(t2.iloc[0]) and t1.iloc[0] - t2.iloc[0] >= u["caida_tackle"]:
                out.append(Conclusion("alerta", e, f"La efectividad de tackle cayó de {t1.iloc[0]:.0f}% a {t2.iloc[0]:.0f}% "
                                                   f"en el 2º tiempo: posible fatiga o falta de rotación.", 2))
            p1 = pp[(pp["equipo"] == e) & (pp["periodo"] == 1)]["Penales cometidos"]
            p2 = pp[(pp["equipo"] == e) & (pp["periodo"] == 2)]["Penales cometidos"]
            if len(p1) and len(p2) and p2.iloc[0] >= p1.iloc[0] + 4:
                out.append(Conclusion("alerta", e, f"Penales en aumento: {p1.iloc[0]} en el 1º tiempo y {p2.iloc[0]} en el 2º.", 3))

    # Jugadores destacados
    j = M.jugadores(df)
    if not j.empty:
        for e in eqs:
            je = j[j["equipo"] == e]
            if je.empty:
                continue
            top = je.sort_values("Tackles hechos", ascending=False).iloc[0]
            if top["Tackles hechos"] >= 8:
                out.append(Conclusion("fortaleza", e, f"{top['jugador']} lideró la defensa con {top['Tackles hechos']} tackles.", 4))
            err = je.sort_values("Tackles errados", ascending=False).iloc[0]
            if err["Tackles errados"] >= 4:
                out.append(Conclusion("alerta", e, f"{err['jugador']} erró {err['Tackles errados']} tackles: revisar en video.", 3))

    return sorted(out, key=lambda c: (c.prioridad, {"alerta": 0, "dato": 1, "fortaleza": 2}[c.tipo]))
