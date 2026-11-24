import unittest

import pandas as pd

from rugby import demo_data, insights, metrics as M, schema


def _df(filas):
    df, _ = schema.normalizar(pd.DataFrame(filas))
    return df


class TestSchema(unittest.TestCase):
    def test_faltan_columnas(self):
        with self.assertRaises(schema.ErrorDatos):
            schema.normalizar(pd.DataFrame({"minuto": [1], "equipo": ["A"]}))

    def test_alias_y_resultados(self):
        df = _df([
            {"Minuto": 1, "Equipo": "A", "Evento": "Lineout", "Resultado": "ganado"},
            {"Minuto": 2, "Equipo": "B", "Evento": "carry"},
            {"Minuto": 50, "Equipo": "A", "Evento": "ensayo"},
            {"Minuto": 51, "Equipo": "A", "Evento": "volea_rara"},
        ])
        self.assertEqual(list(df["evento"]), ["line", "portacion", "try"])
        self.assertEqual(df.loc[0, "resultado"], "ok")
        self.assertEqual(df.loc[2, "periodo"], 2)       # inferido por minuto > 40
        self.assertEqual(df.loc[2, "puntos"], 5)        # try sin resultado suma

    def test_plantilla_valida(self):
        df, avisos = schema.normalizar(schema.plantilla())
        self.assertEqual(avisos, [])
        self.assertEqual(M.marcador(df), {"Club Azul": 5, "Club Rojo": 3})


class TestMetricas(unittest.TestCase):
    def setUp(self):
        self.df = _df([
            {"minuto": 1, "equipo": "A", "evento": "tackle", "resultado": "ok"},
            {"minuto": 2, "equipo": "A", "evento": "tackle", "resultado": "ok"},
            {"minuto": 3, "equipo": "A", "evento": "tackle", "resultado": "ok"},
            {"minuto": 4, "equipo": "A", "evento": "tackle", "resultado": "fallo"},
            {"minuto": 5, "equipo": "B", "evento": "entrada_22", "x": 80},
            {"minuto": 6, "equipo": "B", "evento": "try", "x": 100},
            {"minuto": 6.5, "equipo": "B", "evento": "conversion", "resultado": "ok"},
            {"minuto": 10, "equipo": "A", "evento": "penal_palos", "resultado": "ok"},
            {"minuto": 20, "equipo": "B", "evento": "entrada_22", "x": 85},
        ])

    def test_marcador_y_tackle(self):
        self.assertEqual(M.marcador(self.df), {"A": 3, "B": 7})
        self.assertAlmostEqual(M.resumen_equipo(self.df, "A")["Efectividad tackle %"], 75.0)

    def test_puntos_por_entrada(self):
        p = M.puntos_por_entrada_22(self.df)
        self.assertEqual(p["B"]["entradas"], 2)
        self.assertEqual(p["B"]["puntos"], 7)
        self.assertAlmostEqual(p["B"]["ppe"], 3.5)

    def test_racha(self):
        self.assertEqual(M.mejor_racha(self.df)["equipo"], "B")

    def test_alerta_tackle(self):
        textos = [c.texto for c in insights.generar(self.df) if c.equipo == "A"]
        self.assertTrue(any("tackle" in t for t in textos))


class TestDemo(unittest.TestCase):
    def test_partido_y_temporada(self):
        df, avisos = schema.normalizar(demo_data.generar_partido(semilla=1))
        self.assertEqual(avisos, [])
        self.assertEqual(len(M.equipos(df)), 2)
        self.assertGreater(len(insights.generar(df)), 0)
        t, _ = schema.normalizar(demo_data.temporada(n=3))
        self.assertEqual(len(M.tendencia_temporada(t, "Club Azul")), 3)


if __name__ == "__main__":
    unittest.main()
