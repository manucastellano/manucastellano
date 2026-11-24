"""Generador de partidos FICTICIOS para probar la herramienta (no son datos reales)."""
from __future__ import annotations

import numpy as np
import pandas as pd

APELLIDOS = ["Acosta", "Benítez", "Cabrera", "Domínguez", "Escobar", "Figueroa", "Giménez", "Herrera",
             "Ibáñez", "Juárez", "Ledesma", "Medina", "Navarro", "Ortiz", "Paz", "Quiroga", "Ríos",
             "Sosa", "Torres", "Uriarte", "Vera", "Zárate", "Aguirre", "Bustos", "Castro", "Duarte",
             "Ferreyra", "Godoy", "Luna", "Moreno"]

POS_FORWARDS = list(range(8))   # 1-8
POS_BACKS = list(range(8, 15))  # 9-15
MOTIVOS_PENAL = ["offside", "ruck - manos", "tackle alto", "no soltar", "scrum", "obstrucción", "line"]


def _plantel(rng, n_offset):
    nombres = rng.permutation(APELLIDOS)[:15]
    return [f"{n} ({i + 1})" for i, n in enumerate(nombres)]


def generar_partido(local="Club Azul", visita="Club Rojo", nivel_local=0.0, nivel_visita=0.0,
                    semilla: int = 7, nombre: str | None = None) -> pd.DataFrame:
    """nivel_*: entre -1 y 1, cambia efectividad de tackle, retención, disciplina, etc."""
    rng = np.random.default_rng(semilla)
    eq = [local, visita]
    nivel = {local: nivel_local, visita: nivel_visita}
    plantel = {local: _plantel(rng, 0), visita: _plantel(rng, 15)}
    ev: list[dict] = []
    t = 0.0
    ataca = rng.integers(0, 2)
    x = 50.0  # coordenada del equipo que ataca

    def add(minuto, equipo, evento, jugador=None, resultado=None, x=None, y=None, metros=None, detalle=None):
        ev.append(dict(minuto=round(minuto, 1), periodo=1 if minuto <= 40 else 2, equipo=equipo,
                       jugador=jugador, evento=evento, resultado=resultado,
                       x=None if x is None else round(float(np.clip(x, 0, 100)), 1),
                       y=None if y is None else round(float(np.clip(y, 0, 70)), 1),
                       metros=metros, detalle=detalle))

    def jug(equipo, forwards=0.5):
        idx = rng.choice(POS_FORWARDS) if rng.random() < forwards else rng.choice(POS_BACKS)
        return plantel[equipo][idx]

    add(0.0, local, "patada", plantel[local][9], None, 50, 35, 40.0, "salida")  # kickoff: local primero
    for mitad in (1, 2):
        t = 0.0 if mitad == 1 else 40.0
        fin = 40.0 + rng.uniform(0.5, 2.5) if mitad == 1 else 80.0 + rng.uniform(0.5, 3)
        ataca = rng.integers(0, 2) if mitad == 1 else 1 - ataca
        x = 50.0
        while t < fin:
            a, d = eq[ataca], eq[1 - ataca]
            na, nd = nivel[a], nivel[d]
            # 2º tiempo: un poco más de cansancio para el que tiene menos nivel
            fatiga = 0.04 * (mitad - 1) * (1 - nd)
            # Inicio de posesión: formación fija
            inicio = rng.choice(["line", "scrum", "patada_rival", "juego"], p=[0.35, 0.2, 0.25, 0.2])
            yb = rng.uniform(5, 65)
            if inicio in ("line", "scrum"):
                ok = rng.random() < (0.86 + 0.07 * na if inicio == "line" else 0.88 + 0.06 * na)
                yb = 0.0 if inicio == "line" else rng.uniform(15, 55)
                add(t, a, inicio, jug(a, 1.0) if inicio == "line" else None, "ok" if ok else "fallo", x, yb)
                t += rng.uniform(0.2, 0.6)
                if not ok:
                    ataca, x = 1 - ataca, 100 - x
                    continue
            fases = 0
            while t < fin:
                fases += 1
                y = float(np.clip(yb + rng.normal(0, 12), 2, 68))
                portador = jug(a, 0.55)
                # tackle
                t_ok = rng.random() < (0.86 + 0.05 * nd - 0.03 * na - fatiga)
                gan = rng.gamma(2.0, 1.6 + 0.6 * na) if t_ok else rng.gamma(3.0, 3.5 + na)
                add(t, a, "portacion", portador, None, x, y, round(gan, 1))
                add(t, d, "tackle", jug(d, 0.6), "ok" if t_ok else "fallo", 100 - (x + gan * 0.5), 70 - y)
                if not t_ok and rng.random() < 0.45:
                    add(t, a, "quiebre", portador, None, x + gan * 0.6, y)
                    if rng.random() < 0.35:
                        add(t, a, "offload", portador, None, x + gan, y)
                x_prev, x = x, min(100, x + gan)
                if x_prev < 78 <= x:
                    add(t, a, "entrada_22", portador, None, x, y)
                t += rng.uniform(0.15, 0.45)

                if x >= 100 or (x > 94 and rng.random() < 0.35 + 0.15 * na):
                    autor = jug(a, 0.35)
                    yt = float(np.clip(y + rng.normal(0, 8), 3, 67))
                    add(t, a, "try", autor, "ok", 100, yt)
                    pateador = plantel[a][9]
                    dificultad = abs(yt - 35) / 35
                    add(t + 0.5, a, "conversion", pateador,
                        "ok" if rng.random() < 0.85 - 0.45 * dificultad + 0.05 * na else "fallo", 100, yt)
                    t += rng.uniform(1.0, 1.8)
                    ataca, x = 1 - ataca, 50.0
                    break

                r = rng.random()
                p_penal_def = 0.07 + 0.03 * (x > 60) - 0.025 * nd + fatiga * 0.5
                p_perdida = 0.045 - 0.015 * na
                p_robo = 0.03 + 0.012 * nd
                p_patada = 0.05 if x < 40 else 0.015
                if r < p_penal_def:
                    add(t, d, "penal_cometido", jug(d, 0.75), None, 100 - x, 70 - y, detalle=rng.choice(MOTIVOS_PENAL))
                    if rng.random() < 0.06:
                        add(t, d, "tarjeta", jug(d, 0.7), None, 100 - x, 70 - y, detalle="amarilla")
                    t += rng.uniform(0.4, 1.0)
                    if x >= 55 and rng.random() < 0.55:
                        dist = 100 - x
                        add(t, a, "penal_palos", plantel[a][9],
                            "ok" if rng.random() < 0.92 - dist / 90 + 0.05 * na else "fallo", x, y)
                        t += rng.uniform(1.0, 1.5)
                        ataca, x = 1 - ataca, 50.0
                        break
                    x = min(95, x + rng.uniform(10, 25))  # al touch y line
                    if x_prev < 78 <= x:
                        add(t, a, "entrada_22", None, None, x, 5)
                    yb = 0.0
                    ok = rng.random() < 0.86 + 0.07 * na
                    add(t, a, "line", jug(a, 1.0), "ok" if ok else "fallo", x, 0)
                    if not ok:
                        ataca, x = 1 - ataca, 100 - x
                        break
                    continue
                elif r < p_penal_def + p_perdida:
                    add(t, a, "perdida", portador, None, x, y, detalle=rng.choice(["knock-on", "pase forward", "pelota suelta"]))
                    t += rng.uniform(0.3, 0.7)
                    ataca, x = 1 - ataca, 100 - x
                    break
                elif r < p_penal_def + p_perdida + p_robo:
                    add(t, a, "ruck", None, "fallo", x, y)
                    add(t, d, "recuperacion", jug(d, 0.8), None, 100 - x, 70 - y)
                    t += rng.uniform(0.2, 0.5)
                    ataca, x = 1 - ataca, 100 - x
                    break
                elif r < p_penal_def + p_perdida + p_robo + p_patada:
                    m = rng.uniform(25, 50)
                    add(t, a, "patada", plantel[a][rng.choice([8, 9, 14])], None, x, y, round(m, 1))
                    t += rng.uniform(0.4, 0.9)
                    ataca, x = 1 - ataca, max(5, 100 - min(98, x + m))
                    break
                else:
                    add(t, a, "ruck", None, "ok", x, y)
    df = pd.DataFrame(ev)
    # tiempo "de video" simulado: 2' de previa y 12' de entretiempo
    df["video_seg"] = (120 + df["minuto"] * 60 + np.where(df["periodo"] == 2, 720, 0)).round(1)
    if nombre:
        df.insert(0, "partido", nombre)
    return df


def temporada(equipo="Club Azul", n=6, semilla=11) -> pd.DataFrame:
    rng = np.random.default_rng(semilla)
    rivales = ["Club Rojo", "Los Halcones", "Atlético Sur", "Universitario Norte", "Club Verde", "San Martín RC"]
    partes = []
    for i in range(n):
        riv = rivales[i % len(rivales)]
        partes.append(generar_partido(equipo, riv, nivel_local=float(np.clip(-0.3 + i * 0.12, -1, 1)),
                                      nivel_visita=float(rng.uniform(-0.4, 0.5)), semilla=semilla + i,
                                      nombre=f"Fecha {i + 1} vs {riv}"))
    return pd.concat(partes, ignore_index=True)
