"""Análisis de video con IA (Claude).

Flujo:
  1. Se extraen fotogramas del MP4 (ffmpeg) cada N segundos.
  2. Se envían por tramos (p. ej. 60 s) a Claude, que describe lo que ve y propone
     eventos (tackles, rucks, lines…) con su segundo de video y un nivel de confianza.
  3. Una última llamada junta todas las observaciones (y las estadísticas etiquetadas,
     si existen) y redacta un informe con recomendaciones.

LIMITACIONES (importante):
  - La IA ve IMÁGENES SUELTAS, no video continuo: puede perder acciones rápidas,
    confundir equipos con camisetas parecidas o contar mal. Los eventos que propone
    son SUGERENCIAS para verificar con el etiquetador, no estadísticas confiables.
  - Cuesta dinero (API de Anthropic) y requiere una clave de API.

Uso por línea de comandos:
  python -m rugby.video_ai partido.mp4 --a "Mi Club" --color-a "azul" --b "Rival" --color-b "rojo"
"""
from __future__ import annotations

import base64
import json
import math
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import pandas as pd

from .schema import EVENTOS

MODELO = "claude-opus-5-5"
EVENTOS_IA = sorted(EVENTOS) + ["observacion"]

# Precios de referencia (USD por millón de tokens) de claude-opus-5-5 al momento de escribir esto.
# Pueden cambiar: verificá en la página de precios de Anthropic.
PRECIO_ENTRADA = 4.0
PRECIO_SALIDA = 20.0


# ----------------------------------------------------------------------------- configuración
@dataclass
class Config:
    video: str
    equipo_a: str = "Equipo A"
    color_a: str = ""
    equipo_b: str = "Equipo B"
    color_b: str = ""
    mi_equipo: str = ""           # para orientar las recomendaciones
    nivel: str = "Alto rendimiento"
    inicio_seg: float = 0.0
    fin_seg: float | None = None  # None = hasta el final
    cada_seg: float = 2.0         # un fotograma cada N segundos
    tramo_seg: float = 60.0       # segundos de video por llamada a la IA
    ancho: int = 768              # ancho de los fotogramas (px)
    contexto: str = ""            # notas del analista (plan de juego, foco del análisis…)
    paralelo: int = 4
    extra: dict = field(default_factory=dict)

    @property
    def equipo_foco(self) -> str:
        return self.mi_equipo or self.equipo_a


# ----------------------------------------------------------------------------- video
def _ffmpeg() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:  # noqa: BLE001
        return "ffmpeg"


def duracion_video(path: str) -> float:
    """Duración en segundos (usa la salida de ffmpeg; no requiere ffprobe)."""
    r = subprocess.run([_ffmpeg(), "-hide_banner", "-i", path], capture_output=True, text=True)
    for linea in r.stderr.splitlines():
        linea = linea.strip()
        if linea.startswith("Duration:"):
            h, m, s = linea.split(",")[0].split()[1].split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"No pude leer la duración del video: {path}")


def extraer_fotogramas(path: str, inicio: float, fin: float, cada_seg: float, ancho: int,
                       carpeta: Path) -> list[tuple[float, Path]]:
    """Extrae un fotograma cada `cada_seg` segundos entre inicio y fin. Devuelve [(segundo, archivo)]."""
    carpeta.mkdir(parents=True, exist_ok=True)
    patron = carpeta / f"f_{int(inicio):06d}_%04d.jpg"
    cmd = [_ffmpeg(), "-hide_banner", "-loglevel", "error", "-y", "-ss", f"{inicio:.2f}", "-i", path,
           "-t", f"{fin - inicio:.2f}", "-vf", f"fps=1/{cada_seg},scale={ancho}:-2", "-q:v", "5", str(patron)]
    subprocess.run(cmd, check=True)
    archivos = sorted(carpeta.glob(f"f_{int(inicio):06d}_*.jpg"))
    # con fps=1/N, el fotograma k corresponde aprox. a inicio + k*N (+N/2 por el redondeo de ffmpeg)
    return [(round(inicio + i * cada_seg, 1), a) for i, a in enumerate(archivos)]


def tramos(cfg: Config, duracion: float) -> list[tuple[float, float]]:
    fin = min(cfg.fin_seg or duracion, duracion)
    out, t = [], cfg.inicio_seg
    while t < fin - 1:
        out.append((t, min(t + cfg.tramo_seg, fin)))
        t += cfg.tramo_seg
    return out


# ----------------------------------------------------------------------------- costo
def estimar_costo(cfg: Config, duracion: float, alto: int | None = None) -> dict:
    """Estimación APROXIMADA. Usa la regla de ~ (ancho × alto) / 750 tokens por imagen."""
    tr = tramos(cfg, duracion)
    seg = sum(b - a for a, b in tr)
    n_img = int(seg / cfg.cada_seg)
    alto = alto or int(cfg.ancho * 9 / 16)
    tok_img = cfg.ancho * alto / 750
    entrada = n_img * (tok_img + 15) + len(tr) * 1800 + 20000
    salida = len(tr) * 2500 + 8000   # incluye razonamiento interno del modelo (estimado)
    usd = entrada / 1e6 * PRECIO_ENTRADA + salida / 1e6 * PRECIO_SALIDA
    return {"tramos": len(tr), "imagenes": n_img, "tokens_entrada": int(entrada), "tokens_salida": int(salida),
            "usd_aprox": round(usd, 2), "minutos_video": round(seg / 60, 1)}


# ----------------------------------------------------------------------------- prompts
def _sistema(cfg: Config) -> str:
    return f"""Sos un analista de video de rugby de alto rendimiento. Recibís fotogramas consecutivos de
un partido (uno cada ~{cfg.cada_seg:g} segundos), cada uno precedido por su segundo exacto de video.

Equipos:
- "{cfg.equipo_a}"{f' (camiseta: {cfg.color_a})' if cfg.color_a else ''}
- "{cfg.equipo_b}"{f' (camiseta: {cfg.color_b})' if cfg.color_b else ''}

Tu tarea en cada tramo:
1. Describir brevemente qué pasa (fase de juego, quién tiene la pelota, zona de la cancha).
2. Proponer eventos que veas con razonable evidencia en las imágenes, usando SOLO estos códigos:
   {", ".join(EVENTOS_IA)}.
   Usá "observacion" para notas tácticas (alineación defensiva, apoyo en el ruck, uso de la patada,
   espacios, formación del maul, posicionamiento de los backs, etc.).
3. Para cada evento indicá el segundo de video (el del fotograma donde mejor se ve), el equipo que
   realiza la acción ("{cfg.equipo_a}", "{cfg.equipo_b}" o "desconocido") y tu confianza.

Reglas de honestidad (muy importantes):
- Ves imágenes sueltas, no video continuo: entre fotogramas pasan cosas que no ves. No inventes.
- Si no estás seguro del equipo, poné "desconocido". Si no estás seguro del evento, confianza "baja".
- No asumas resultados (ej. tackle errado) si la imagen no lo muestra claramente.
- Repeticiones, primeros planos, tribuna o gráficos de TV: indicá que es repetición/corte y no
  cuentes de nuevo eventos ya vistos.
- x (opcional) = metros desde el in-goal PROPIO del equipo que hace la acción (0-100). Solo si las
  líneas de la cancha permiten estimarlo; si no, null."""


ESQUEMA_TRAMO = {
    "type": "object",
    "properties": {
        "resumen": {"type": "string", "description": "Qué pasa en este tramo, 1-3 oraciones."},
        "es_juego": {"type": "boolean", "description": "False si el tramo es casi todo pausa, repetición o tribuna."},
        "eventos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "video_seg": {"type": "number"},
                    "evento": {"type": "string", "enum": EVENTOS_IA},
                    "equipo": {"type": "string"},
                    "resultado": {"type": "string", "enum": ["ok", "fallo", "desconocido"]},
                    "x": {"type": ["number", "null"]},
                    "descripcion": {"type": "string"},
                    "confianza": {"type": "string", "enum": ["alta", "media", "baja"]},
                },
                "required": ["video_seg", "evento", "equipo", "resultado", "x", "descripcion", "confianza"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["resumen", "es_juego", "eventos"],
    "additionalProperties": False,
}

ESQUEMA_INFORME = {
    "type": "object",
    "properties": {
        "resumen_partido": {"type": "string"},
        "fortalezas": {"type": "array", "items": {"type": "string"}},
        "debilidades": {"type": "array", "items": {"type": "string"}},
        "recomendaciones": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "prioridad": {"type": "integer", "description": "1 = la más importante"},
                    "area": {"type": "string", "description": "Ataque, defensa, formaciones fijas, ruck, pateo, disciplina, físico…"},
                    "problema": {"type": "string"},
                    "accion": {"type": "string", "description": "Qué conviene hacer, concreto y accionable."},
                    "ejercicio": {"type": "string", "description": "Ejercicio o foco de entrenamiento sugerido."},
                    "evidencia_seg": {"type": "array", "items": {"type": "number"},
                                      "description": "Segundos de video que respaldan la recomendación."},
                    "confianza": {"type": "string", "enum": ["alta", "media", "baja"]},
                },
                "required": ["prioridad", "area", "problema", "accion", "ejercicio", "evidencia_seg", "confianza"],
                "additionalProperties": False,
            },
        },
        "para_verificar": {"type": "array", "items": {"type": "string"},
                           "description": "Dudas o datos que el analista debería confirmar mirando el video."},
        "limitaciones": {"type": "string"},
    },
    "required": ["resumen_partido", "fortalezas", "debilidades", "recomendaciones", "para_verificar", "limitaciones"],
    "additionalProperties": False,
}


# ----------------------------------------------------------------------------- llamadas a la API
class ErrorIA(RuntimeError):
    pass


def _cliente(api_key: str | None = None):
    import anthropic
    return anthropic.Anthropic(api_key=api_key, max_retries=4) if api_key else anthropic.Anthropic(max_retries=4)


def _texto_json(resp) -> dict:
    if resp.stop_reason == "refusal":
        cat = getattr(getattr(resp, "stop_details", None), "category", None)
        raise ErrorIA(f"El modelo se negó a procesar este tramo (categoría: {cat}).")
    if resp.stop_reason == "max_tokens":
        raise ErrorIA("La respuesta se cortó por longitud (max_tokens).")
    texto = next((b.text for b in resp.content if b.type == "text"), None)
    if texto is None:
        raise ErrorIA("La respuesta no trajo texto.")
    return json.loads(texto)


_USAR_FALLBACK = True


def _llamar(client, sistema: str, contenido: list, esquema: dict, esfuerzo: str, max_tokens: int) -> tuple[dict, dict]:
    """Una llamada con salida JSON validada. Usa el 'fallback' del servidor (si el modelo declina por
    sus filtros de seguridad, reintenta con otro); si la cuenta no lo admite, sigue sin él."""
    global _USAR_FALLBACK
    import anthropic
    kwargs = dict(
        model=MODELO,
        max_tokens=max_tokens,
        system=sistema,
        messages=[{"role": "user", "content": contenido}],
        output_config={"effort": esfuerzo, "format": {"type": "json_schema", "schema": esquema}},
    )
    try:
        if _USAR_FALLBACK:
            with client.beta.messages.stream(**kwargs, betas=["server-side-fallback-2026-07-01"],
                                             fallbacks="default") as stream:
                resp = stream.get_final_message()
        else:
            with client.messages.stream(**kwargs) as stream:
                resp = stream.get_final_message()
    except anthropic.BadRequestError as e:
        if not _USAR_FALLBACK or "fallback" not in str(e).lower():
            raise
        _USAR_FALLBACK = False
        with client.messages.stream(**kwargs) as stream:
            resp = stream.get_final_message()
    uso = {"entrada": resp.usage.input_tokens, "salida": resp.usage.output_tokens}
    return _texto_json(resp), uso


def analizar_tramo(client, cfg: Config, fotos: list[tuple[float, Path]], desde: float, hasta: float) -> tuple[dict, dict]:
    contenido: list[dict] = [{"type": "text", "text": f"Tramo de video {desde:.0f}s a {hasta:.0f}s. "
                                                      f"{('Contexto del analista: ' + cfg.contexto) if cfg.contexto else ''}"}]
    for seg, archivo in fotos:
        contenido.append({"type": "text", "text": f"[segundo {seg:.0f}]"})
        contenido.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                      "data": base64.standard_b64encode(archivo.read_bytes()).decode()}})
    contenido.append({"type": "text", "text": "Analizá el tramo y respondé con el JSON pedido."})
    datos, uso = _llamar(client, _sistema(cfg), contenido, ESQUEMA_TRAMO, "medium", 16000)
    datos["desde"], datos["hasta"] = desde, hasta
    return datos, uso


def informe_final(client, cfg: Config, tramos_ok: list[dict], estadisticas: str = "") -> tuple[dict, dict]:
    sistema = (f"Sos el analista principal de un staff de rugby de {cfg.nivel.lower()}. Redactás para el "
               f"head coach de \"{cfg.equipo_foco}\". Español rioplatense, directo y concreto.")
    obs = [{"desde": t["desde"], "hasta": t["hasta"], "resumen": t["resumen"], "eventos": t["eventos"]}
           for t in tramos_ok if t.get("es_juego", True)]
    texto = f"""Estas son las observaciones de un modelo de visión sobre fotogramas del partido
{cfg.equipo_a} vs {cfg.equipo_b} (tramo de video {cfg.inicio_seg:.0f}s a {cfg.fin_seg or 'final'}).
Son observaciones imperfectas: pueden faltar acciones y haber errores de equipo o de conteo.

{('Contexto del analista: ' + cfg.contexto) if cfg.contexto else ''}

{('Estadísticas etiquetadas por el staff (más confiables que las observaciones):' + chr(10) + estadisticas) if estadisticas else 'No hay estadísticas etiquetadas por el staff.'}

Observaciones por tramo (JSON):
{json.dumps(obs, ensure_ascii=False)}

Redactá el informe para {cfg.equipo_foco}:
- Recomendaciones ordenadas por prioridad, cada una con acción concreta, ejercicio sugerido y los
  segundos de video que la respaldan (para que el staff los revise).
- Basate en patrones repetidos, no en una sola jugada. Si la evidencia es escasa, decilo y bajá la confianza.
- No inventes números que no estén en los datos. En "para_verificar" poné lo que conviene confirmar en video.
- En "limitaciones" explicá en 1-2 oraciones qué tan confiable es este análisis."""
    return _llamar(client, sistema, [{"type": "text", "text": texto}], ESQUEMA_INFORME, "high", 32000)


# ----------------------------------------------------------------------------- orquestación
def analizar_video(cfg: Config, estadisticas: str = "", client=None,
                   progreso: Callable[[float, str], None] | None = None,
                   carpeta_salida: str | Path | None = None) -> dict:
    """Corre todo el análisis. Devuelve dict con 'tramos', 'informe', 'eventos' (DataFrame) y 'uso'."""
    client = client or _cliente()
    progreso = progreso or (lambda p, m: None)
    dur = duracion_video(cfg.video)
    lista = tramos(cfg, dur)
    if not lista:
        raise ErrorIA("El rango de tiempo elegido está vacío.")
    resultados, errores, uso_total = [], [], {"entrada": 0, "salida": 0}

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)

        def trabajo(desde, hasta):
            fotos = extraer_fotogramas(cfg.video, desde, hasta, cfg.cada_seg, cfg.ancho, tmp / f"t{int(desde)}")
            if not fotos:
                return {"desde": desde, "hasta": hasta, "resumen": "(sin fotogramas)", "es_juego": False, "eventos": []}, \
                    {"entrada": 0, "salida": 0}
            return analizar_tramo(client, cfg, fotos, desde, hasta)

        with ThreadPoolExecutor(max_workers=max(1, cfg.paralelo)) as ex:
            futuros = {ex.submit(trabajo, a, b): (a, b) for a, b in lista}
            for i, fut in enumerate(as_completed(futuros), 1):
                a, b = futuros[fut]
                try:
                    datos, uso = fut.result()
                    resultados.append(datos)
                    for k in uso_total:
                        uso_total[k] += uso[k]
                except Exception as e:  # noqa: BLE001  (un tramo fallido no frena el resto)
                    errores.append(f"{_mmss(a)}-{_mmss(b)}: {e}")
                progreso(0.9 * i / len(lista), f"Tramo {i}/{len(lista)} analizado")

    if not resultados:
        raise ErrorIA("No se pudo analizar ningún tramo. Errores: " + "; ".join(errores[:3]))
    resultados.sort(key=lambda t: t["desde"])
    progreso(0.92, "Redactando recomendaciones…")
    informe, uso = informe_final(client, cfg, resultados, estadisticas)
    for k in uso_total:
        uso_total[k] += uso[k]
    progreso(1.0, "Listo")

    salida = {
        "config": {k: v for k, v in cfg.__dict__.items() if k != "extra"},
        "modelo": MODELO,
        "tramos": resultados,
        "informe": informe,
        "errores": errores,
        "uso": {**uso_total, "usd_aprox": round(uso_total["entrada"] / 1e6 * PRECIO_ENTRADA +
                                                uso_total["salida"] / 1e6 * PRECIO_SALIDA, 2)},
    }
    salida["eventos"] = eventos_a_csv(salida, cfg)
    if carpeta_salida:
        guardar(salida, carpeta_salida)
    return salida


def eventos_a_csv(salida: dict, cfg: Config) -> pd.DataFrame:
    """Eventos sugeridos por la IA en el formato del etiquetador (para verificarlos con 'Revisar clips')."""
    filas = []
    partido = Path(cfg.video).stem + " (IA)"
    for t in salida["tramos"]:
        for e in t.get("eventos", []):
            if e["evento"] == "observacion":
                continue
            filas.append({
                "partido": partido, "minuto": round(e["video_seg"] / 60, 1), "periodo": pd.NA,
                "equipo": e["equipo"], "jugador": "", "evento": e["evento"],
                "resultado": "" if e["resultado"] == "desconocido" else e["resultado"],
                "x": e.get("x"), "y": pd.NA, "metros": pd.NA,
                "detalle": f"[IA {e['confianza']}] {e['descripcion']}", "video_seg": e["video_seg"],
                "confianza": e["confianza"],
            })
    return pd.DataFrame(filas)


def guardar(salida: dict, carpeta: str | Path) -> Path:
    carpeta = Path(carpeta)
    carpeta.mkdir(parents=True, exist_ok=True)
    base = Path(salida["config"]["video"]).stem
    datos = {k: v for k, v in salida.items() if k != "eventos"}
    (carpeta / f"{base}_ia.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    salida["eventos"].drop(columns=["confianza"], errors="ignore").to_csv(carpeta / f"{base}_ia_eventos.csv", index=False)
    (carpeta / f"{base}_informe.md").write_text(informe_markdown(salida), encoding="utf-8")
    return carpeta


def _mmss(s: float) -> str:
    s = int(s)
    h, m, x = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{x:02d}" if h else f"{m}:{x:02d}"


def informe_markdown(salida: dict) -> str:
    inf, cfg = salida["informe"], salida["config"]
    l = [f"# Informe IA: {cfg['equipo_a']} vs {cfg['equipo_b']}", "",
         f"> Generado automáticamente por IA a partir de fotogramas del video. **Verificá cada punto en el video.**",
         f"> {inf['limitaciones']}", "", "## Resumen", inf["resumen_partido"], "", "## Recomendaciones"]
    for r in sorted(inf["recomendaciones"], key=lambda r: r["prioridad"]):
        ev = ", ".join(_mmss(s) for s in r["evidencia_seg"][:8]) or "—"
        l += [f"### {r['prioridad']}. {r['area']} (confianza {r['confianza']})",
              f"- **Problema:** {r['problema']}", f"- **Qué hacer:** {r['accion']}",
              f"- **Ejercicio:** {r['ejercicio']}", f"- **Ver en video:** {ev}", ""]
    l += ["## Fortalezas"] + [f"- {x}" for x in inf["fortalezas"]] + ["", "## Debilidades"] + \
         [f"- {x}" for x in inf["debilidades"]] + ["", "## Para verificar"] + [f"- {x}" for x in inf["para_verificar"]]
    u = salida["uso"]
    l += ["", f"_Modelo: {salida['modelo']} · tokens entrada {u['entrada']:,} / salida {u['salida']:,} · "
              f"costo aprox. USD {u['usd_aprox']}_"]
    return "\n".join(l)


# ----------------------------------------------------------------------------- CLI
def _main():
    import argparse
    p = argparse.ArgumentParser(description="Analiza un video de rugby con IA y genera recomendaciones.")
    p.add_argument("video")
    p.add_argument("--a", default="Equipo A", help="Nombre del equipo A")
    p.add_argument("--color-a", default="", help="Color de camiseta del equipo A")
    p.add_argument("--b", default="Equipo B")
    p.add_argument("--color-b", default="")
    p.add_argument("--mi-equipo", default="", help="Equipo para el que se redactan las recomendaciones")
    p.add_argument("--desde", type=float, default=0, help="Minuto de video inicial")
    p.add_argument("--hasta", type=float, default=None, help="Minuto de video final")
    p.add_argument("--cada", type=float, default=2.0, help="Segundos entre fotogramas")
    p.add_argument("--contexto", default="")
    p.add_argument("--salida", default="resultados_ia")
    p.add_argument("--si", action="store_true", help="No pedir confirmación del costo")
    a = p.parse_args()
    cfg = Config(video=a.video, equipo_a=a.a, color_a=a.color_a, equipo_b=a.b, color_b=a.color_b,
                 mi_equipo=a.mi_equipo, inicio_seg=a.desde * 60, fin_seg=a.hasta * 60 if a.hasta else None,
                 cada_seg=a.cada, contexto=a.contexto)
    est = estimar_costo(cfg, duracion_video(a.video))
    print(f"Estimación aproximada: {est['minutos_video']} min de video, {est['imagenes']} imágenes, "
          f"{est['tramos']} llamadas, ~USD {est['usd_aprox']}")
    if not a.si and input("¿Continuar? [s/N] ").strip().lower() not in ("s", "si", "sí", "y"):
        return
    out = analizar_video(cfg, progreso=lambda p_, m: print(f"[{p_:4.0%}] {m}"), carpeta_salida=a.salida)
    print(f"\nListo. Archivos en {a.salida}/  · costo aprox. USD {out['uso']['usd_aprox']}")
    if out["errores"]:
        print("Tramos con error:", *out["errores"], sep="\n  ")


if __name__ == "__main__":
    _main()
