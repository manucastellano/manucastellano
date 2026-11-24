"""Prueba el flujo de video->IA->informe con un cliente simulado (no llama a la API real)."""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from rugby import video_ai as V


class _Stream:
    def __init__(self, resp): self.resp = resp
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def get_final_message(self): return self.resp


class ClienteFalso:
    """Imita client.beta.messages.stream(...) y client.messages.stream(...)."""
    def __init__(self):
        self.llamadas = []
        self.messages = SimpleNamespace(stream=self._stream)
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **kw):
        self.llamadas.append(kw)
        contenido = kw["messages"][0]["content"]
        imgs = [c for c in contenido if c["type"] == "image"]
        if imgs:  # llamada de tramo
            seg = float(contenido[1]["text"].strip("[]").split()[1])
            data = {"resumen": "Ataque de A en campo rival", "es_juego": True, "eventos": [
                {"video_seg": seg, "evento": "tackle", "equipo": "Rival", "resultado": "fallo", "x": 40,
                 "descripcion": "tackle alto errado", "confianza": "media"},
                {"video_seg": seg + 2, "evento": "observacion", "equipo": "Mi Club", "resultado": "desconocido",
                 "x": None, "descripcion": "poco apoyo en el ruck", "confianza": "baja"}]}
        else:     # informe final
            data = {"resumen_partido": "x", "fortalezas": ["a"], "debilidades": ["b"],
                    "recomendaciones": [{"prioridad": 1, "area": "Ruck", "problema": "p", "accion": "a",
                                         "ejercicio": "e", "evidencia_seg": [12, 70], "confianza": "media"}],
                    "para_verificar": ["v"], "limitaciones": "l"}
        return _Stream(SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text=json.dumps(data))],
                                       usage=SimpleNamespace(input_tokens=1000, output_tokens=200)))


@unittest.skipUnless(shutil.which("ffmpeg") or V._ffmpeg() != "ffmpeg", "requiere ffmpeg")
class TestVideoIA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.video = cls.tmp / "partido.mp4"
        subprocess.run([V._ffmpeg(), "-loglevel", "error", "-y", "-f", "lavfi", "-i",
                        "testsrc=duration=130:size=640x360:rate=5", "-pix_fmt", "yuv420p", str(cls.video)], check=True)

    def test_duracion_y_costo(self):
        self.assertAlmostEqual(V.duracion_video(str(self.video)), 130, delta=1)
        cfg = V.Config(video=str(self.video), cada_seg=2, tramo_seg=60)
        est = V.estimar_costo(cfg, 130)
        self.assertEqual(est["tramos"], 3)
        self.assertEqual(est["imagenes"], 65)
        self.assertGreater(est["usd_aprox"], 0)

    def test_flujo_completo(self):
        cfg = V.Config(video=str(self.video), equipo_a="Mi Club", equipo_b="Rival", cada_seg=5, tramo_seg=60,
                       fin_seg=125, paralelo=2)
        cli = ClienteFalso()
        out = V.analizar_video(cfg, client=cli, carpeta_salida=self.tmp / "res")
        self.assertEqual(out["errores"], [])
        self.assertEqual(len(out["tramos"]), 3)
        self.assertEqual(len(cli.llamadas), 4)                    # 3 tramos + informe
        n_imgs = sum(1 for c in cli.llamadas[0]["messages"][0]["content"] if c["type"] == "image")
        self.assertEqual(n_imgs, 12)                              # 60 s / 5 s
        self.assertEqual(len(out["eventos"]), 3)                  # observaciones no van al CSV
        self.assertTrue((self.tmp / "res" / "partido_informe.md").exists())
        # el CSV de la IA es compatible con el resto de la herramienta
        import pandas as pd
        from rugby import schema
        df, _ = schema.normalizar(pd.read_csv(self.tmp / "res" / "partido_ia_eventos.csv"))
        self.assertEqual(set(df["evento"]), {"tackle"})
        self.assertIn("Ver en video:** 0:12, 1:10", (self.tmp / "res" / "partido_informe.md").read_text())

    def test_rechazo(self):
        resp = SimpleNamespace(stop_reason="refusal", stop_details=SimpleNamespace(category="x"), content=[])
        with self.assertRaises(V.ErrorIA):
            V._texto_json(resp)


if __name__ == "__main__":
    unittest.main()
