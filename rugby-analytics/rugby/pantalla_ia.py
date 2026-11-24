"""Pantalla de Streamlit: '🤖 Analizar video con IA'."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from . import metrics as M
from . import schema
from . import video_ai as V

CARPETA = Path(__file__).resolve().parent.parent / "resultados_ia"


def _mmss(s) -> str:
    return V._mmss(float(s))


def _video_desde_upload(archivo) -> str:
    destino = Path(tempfile.gettempdir()) / "rugby_ia_videos"
    destino.mkdir(exist_ok=True)
    ruta = destino / archivo.name
    if not ruta.exists() or ruta.stat().st_size != archivo.size:
        with open(ruta, "wb") as fh:
            fh.write(archivo.getbuffer())
    return str(ruta)


def _estadisticas_texto(archivo) -> str:
    try:
        raw = pd.read_csv(archivo, sep=None, engine="python")
        df, _ = schema.normalizar(raw)
        if len(M.equipos(df)) != 2:
            return ""
        return M.tabla_comparativa(df).round(1).to_string()
    except Exception:  # noqa: BLE001
        return ""


def mostrar_resultado(res: dict):
    inf, cfg = res["informe"], res["config"]
    st.success(f"Análisis listo · costo aprox. USD {res['uso']['usd_aprox']} · "
               f"{len(res['tramos'])} tramos analizados")
    if res.get("errores"):
        with st.expander(f"⚠️ {len(res['errores'])} tramos no se pudieron analizar"):
            st.write("\n".join(f"- {e}" for e in res["errores"]))
    st.warning(f"**Generado por IA a partir de fotogramas: verificá cada punto en el video.** {inf['limitaciones']}")

    st.subheader("🧭 Resumen")
    st.write(inf["resumen_partido"])

    st.subheader(f"🎯 Recomendaciones para {cfg.get('mi_equipo') or cfg['equipo_a']}")
    icon = {"alta": "🟢", "media": "🟡", "baja": "🔴"}
    for r in sorted(inf["recomendaciones"], key=lambda r: r["prioridad"]):
        with st.expander(f"{r['prioridad']}. {r['area']} — {r['problema']}  ·  confianza {icon[r['confianza']]} {r['confianza']}",
                         expanded=r["prioridad"] <= 3):
            st.markdown(f"**Qué hacer:** {r['accion']}\n\n**Ejercicio sugerido:** {r['ejercicio']}")
            if r["evidencia_seg"]:
                st.markdown("**Ver en el video:** " + " · ".join(f"`{_mmss(s)}`" for s in r["evidencia_seg"][:12]))

    c1, c2 = st.columns(2)
    c1.subheader("✅ Fortalezas")
    c1.markdown("\n".join(f"- {x}" for x in inf["fortalezas"]) or "—")
    c2.subheader("⚠️ Debilidades")
    c2.markdown("\n".join(f"- {x}" for x in inf["debilidades"]) or "—")
    if inf["para_verificar"]:
        st.subheader("🔍 Para verificar en el video")
        st.markdown("\n".join(f"- {x}" for x in inf["para_verificar"]))

    with st.expander("🕒 Qué vio la IA en cada tramo"):
        st.dataframe(pd.DataFrame([{"Desde": _mmss(t["desde"]), "Hasta": _mmss(t["hasta"]),
                                    "Juego": "sí" if t.get("es_juego", True) else "pausa/repetición",
                                    "Resumen": t["resumen"], "Eventos": len(t.get("eventos", []))}
                                   for t in res["tramos"]]), hide_index=True, width="stretch")
    ev = res.get("eventos")
    if ev is None:
        ev = V.eventos_a_csv(res, V.Config(**{k: v for k, v in cfg.items() if k in V.Config.__dataclass_fields__}))
    if len(ev):
        with st.expander(f"📋 {len(ev)} eventos sugeridos por la IA (sin verificar)"):
            vista = ev.assign(Video=ev["video_seg"].map(_mmss))[["Video", "equipo", "evento", "resultado", "confianza", "detalle"]]
            st.dataframe(vista, hide_index=True, width="stretch")

    st.subheader("⬇️ Descargas")
    c1, c2, c3 = st.columns(3)
    base = Path(cfg["video"]).stem
    c1.download_button("Informe (Markdown)", V.informe_markdown(res).encode("utf-8"), f"{base}_informe.md",
                       width="stretch")
    c2.download_button("Eventos IA (CSV)", ev.drop(columns=["confianza"], errors="ignore").to_csv(index=False).encode("utf-8"),
                       f"{base}_ia_eventos.csv", width="stretch",
                       help="Abrilo en el etiquetador junto al video y usá 'Revisar clips' para verificar cada uno.")
    datos = {k: v for k, v in res.items() if k != "eventos"}
    c3.download_button("Análisis completo (JSON)", json.dumps(datos, ensure_ascii=False, indent=2).encode("utf-8"),
                       f"{base}_ia.json", width="stretch", help="Para volver a verlo sin pagar de nuevo.")


def pantalla(nivel: str):
    st.header("🤖 Analizar video con IA")
    st.markdown(
        "La app toma **fotogramas del video**, se los muestra a un modelo de IA (Claude) por tramos y al final "
        "redacta **recomendaciones** con los minutos del video que las respaldan.")
    st.info("**Qué esperar:** sirve para detectar patrones (cómo defienden, cómo atacan, problemas repetidos) y "
            "ahorrar horas de visionado. **No reemplaza al etiquetado**: la IA ve imágenes sueltas, puede perder "
            "acciones rápidas o confundir equipos. Por eso cada recomendación trae los segundos exactos para que "
            "las verifiques. Si además subís un CSV etiquetado, las recomendaciones usan esos números.")

    tab_nuevo, tab_ver = st.tabs(["Nuevo análisis", "Ver un análisis guardado"])
    with tab_ver:
        f = st.file_uploader("Archivo *_ia.json*", type=["json"], key="ia_json")
        if f:
            mostrar_resultado(json.load(f))

    with tab_nuevo:
        clave = os.environ.get("ANTHROPIC_API_KEY", "")
        if not clave:
            clave = st.text_input("Clave de API de Anthropic", type="password",
                                  help="Se crea en console.anthropic.com. Se usa solo en esta sesión; no se guarda.")
            st.caption("También podés definir la variable de entorno `ANTHROPIC_API_KEY` antes de abrir la app.")

        st.markdown("**1. Video**")
        c1, c2 = st.columns(2)
        ruta = c1.text_input("Ruta del archivo en tu computadora (recomendado para partidos completos)",
                             placeholder=r"C:\Videos\fecha3.mp4  o  /Users/yo/Videos/fecha3.mp4")
        sub = c2.file_uploader("…o subilo (hasta 2 GB)", type=["mp4", "mov", "m4v", "mkv", "webm"], key="ia_video")
        video = None
        if sub is not None:
            video = _video_desde_upload(sub)
        elif ruta.strip():
            p = Path(ruta.strip().strip('"'))
            if p.exists():
                video = str(p)
            else:
                st.error("No encuentro ese archivo. Revisá la ruta.")
        if not video:
            return
        try:
            dur = V.duracion_video(video)
        except Exception as e:  # noqa: BLE001
            st.error(f"No pude leer el video: {e}")
            return
        st.caption(f"Duración: {V._mmss(dur)}")

        st.markdown("**2. Equipos**")
        c1, c2, c3, c4 = st.columns(4)
        a = c1.text_input("Equipo A", "Mi Club")
        ca = c2.text_input("Camiseta A", placeholder="ej. azul con vivos blancos")
        b = c3.text_input("Equipo B", "Rival")
        cb = c4.text_input("Camiseta B", placeholder="ej. roja, short negro")
        mi = st.radio("Recomendaciones para", [a, b], horizontal=True)

        st.markdown("**3. Qué analizar**")
        total_min = max(1, int(dur // 60) + 1)
        desde, hasta = st.slider("Minutos del video", 0, total_min, (0, total_min),
                                 help="Analizar solo una parte cuesta menos (por ej. solo el 2º tiempo).")
        c1, c2 = st.columns(2)
        cada = c1.select_slider("Un fotograma cada…", options=[1, 2, 3, 5], value=2, format_func=lambda v: f"{v} s",
                                help="Menos segundos = más detalle y más costo.")
        tramo = c2.select_slider("Segundos por consulta", options=[30, 45, 60, 90], value=60)
        contexto = st.text_area("Contexto para la IA (opcional)",
                                placeholder="ej. Queremos revisar la defensa en nuestra 22 y la salida desde el ruck. "
                                            "El rival patea mucho al fondo.")
        csv = st.file_uploader("CSV etiquetado del mismo partido (opcional, mejora las recomendaciones)",
                               type=["csv"], key="ia_csv")

        cfg = V.Config(video=video, equipo_a=a, color_a=ca, equipo_b=b, color_b=cb, mi_equipo=mi, nivel=nivel,
                       inicio_seg=desde * 60, fin_seg=min(hasta * 60, dur), cada_seg=cada, tramo_seg=tramo,
                       contexto=contexto)
        est = V.estimar_costo(cfg, dur)
        st.markdown("**4. Costo y ejecución**")
        c = st.columns(4)
        c[0].metric("Video a analizar", f"{est['minutos_video']} min")
        c[1].metric("Imágenes", est["imagenes"])
        c[2].metric("Consultas a la IA", est["tramos"] + 1)
        c[3].metric("Costo aprox.", f"USD {est['usd_aprox']}")
        st.caption(f"Estimación aproximada con precios de referencia de {V.MODELO} (USD {V.PRECIO_ENTRADA}/"
                   f"{V.PRECIO_SALIDA} por millón de tokens de entrada/salida). El costo real puede variar: "
                   "verificá los precios vigentes de Anthropic y el consumo en tu consola.")
        ok = st.checkbox("Entiendo que esto consume créditos de mi cuenta de Anthropic")
        if st.button("🚀 Analizar", type="primary", disabled=not (ok and clave)):
            barra = st.progress(0.0, "Extrayendo fotogramas…")
            try:
                res = V.analizar_video(cfg, estadisticas=_estadisticas_texto(csv) if csv else "",
                                       client=V._cliente(clave), progreso=lambda p, m: barra.progress(p, m),
                                       carpeta_salida=CARPETA)
            except Exception as e:  # noqa: BLE001
                st.error(f"El análisis falló: {e}")
                return
            st.session_state["ia_resultado"] = res
            st.caption(f"También se guardó en `{CARPETA}`.")
        if "ia_resultado" in st.session_state:
            mostrar_resultado(st.session_state["ia_resultado"])
