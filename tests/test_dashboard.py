"""Integração da página local com o histórico e o adaptador D+1."""

from hashlib import sha256
import io
import json
from unittest import TestCase
from unittest.mock import patch

import pandas as pd
from pandas.testing import assert_frame_equal
from streamlit.testing.v1 import AppTest

from app import DEMO_SOURCE, MAX_UPLOAD_MB, read_history
from modeling.features import TARGET
from modeling.inference import CATALOG_PATH, HISTORY_COLUMNS, MODEL_PATH, ROOT, predict_next_day


APP_PATH = ROOT / "app.py"


class DashboardTests(TestCase):
    def app(self):
        return AppTest.from_file(str(APP_PATH), default_timeout=15).run()

    def history(self, days=28):
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["produtos"]
        return pd.DataFrame([
            {"data": day, "produto_id": product, **catalog[product], TARGET: 10 + offset + index * 0.25}
            for offset, product in enumerate(("acem", "alcatra", "picanha"))
            for index, day in enumerate(pd.date_range(end="2026-08-31", periods=days))
        ])

    def csv(self, history):
        return io.BytesIO(history.to_csv(index=False, date_format="%Y-%m-%d").encode("utf-8"))

    def test_selecao_tres_cortes_previsoes_reais_e_preservacao_dos_arquivos(self):
        protected = [DEMO_SOURCE, MODEL_PATH, MODEL_PATH.with_suffix(".metadata.json"),
                     CATALOG_PATH, ROOT / "data/modeling/iacarne_modelagem.csv"]
        before = {path: sha256(path.read_bytes()).hexdigest() for path in protected}
        history = read_history(DEMO_SOURCE)
        app = self.app()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.selectbox[0].options), 21)
        self.assertEqual(len(app.metric), 0)
        for product in ("acem", "alcatra", "picanha"):
            with self.subTest(product=product):
                expected_history = history.loc[history.produto_id.eq(product)]
                expected = predict_next_day(expected_history).iloc[0]
                app.selectbox[0].set_value(product).run()
                self.assertEqual(len(app.metric), 0)
                assert_frame_equal(app.dataframe[0].value.reset_index(drop=True),
                                   expected_history.tail(28)[["data", TARGET]].reset_index(drop=True))
                with patch("modeling.inference.predict_next_day", wraps=predict_next_day) as predict:
                    with patch("sklearn.pipeline.Pipeline.fit", side_effect=AssertionError("Treinamento no dashboard")):
                        app.button[0].click().run()
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(len(app.error), 0)
                predict.assert_called_once()
                assert_frame_equal(predict.call_args.args[0], expected_history)
                self.assertEqual(app.metric[0].value, f"{expected.previsao_ridge_kg:.3f} kg".replace(".", ","))
                self.assertEqual(app.metric[1].value, f"{expected.baseline_d7_kg:.3f} kg".replace(".", ","))
                self.assertIn("Previsão para 01/09/2026", [h.value for h in app.subheader])
                self.assertTrue(any(expected.corte in text.value and "Treinado com dados sintéticos" in text.value
                                    for text in app.caption))
        self.assertEqual(before, {path: sha256(path.read_bytes()).hexdigest() for path in protected})

    def test_csv_em_memoria_valida_e_preserva_conteudo(self):
        history = self.history()
        source = self.csv(history)
        before = source.getvalue()
        result = read_history(source)
        self.assertEqual(tuple(result.columns), HISTORY_COLUMNS)
        assert_frame_equal(result, history)
        self.assertEqual(source.getvalue(), before)

    def test_upload_valido_integra_selecao_e_previsao(self):
        history = self.history()
        source = self.csv(history)
        app = self.app()
        with patch("streamlit.file_uploader", return_value=source):
            app.radio[0].set_value("CSV autorizado").run()
            self.assertEqual(len(app.selectbox[0].options), 3)
            app.selectbox[0].set_value("picanha").run()
            app.button[0].click().run()
        expected = predict_next_day(history.loc[history.produto_id.eq("picanha")]).iloc[0]
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.error), 0)
        self.assertEqual(app.metric[0].value, f"{expected.previsao_ridge_kg:.3f} kg".replace(".", ","))
        self.assertEqual(source.getvalue(), self.csv(history).getvalue())

    def test_modo_csv_aguarda_arquivo(self):
        app = self.app()
        app.radio[0].set_value("CSV autorizado").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(len(app.selectbox), 0)
        self.assertEqual(len(app.metric), 0)
        self.assertTrue(any("Selecione um CSV" in info.value for info in app.info))

    def test_grafico_formata_datas_e_preserva_observacoes(self):
        history = read_history(DEMO_SOURCE)
        app = self.app()
        with patch("streamlit.vega_lite_chart") as chart:
            app.selectbox[0].set_value("picanha").run()
        self.assertEqual(len(app.exception), 0)
        chart.assert_called_once()
        plotted, spec = chart.call_args.args
        expected = history.loc[history.produto_id.eq("picanha")].tail(28)[["data", TARGET]]
        assert_frame_equal(plotted, expected)
        self.assertEqual(len(plotted), 28)
        self.assertTrue(plotted.data.is_monotonic_increasing)
        axis = spec["encoding"]["x"]["axis"]
        self.assertEqual(axis["format"], "%d/%m")
        self.assertEqual(axis["tickCount"], 7)
        self.assertTrue(axis["labelOverlap"])
        self.assertEqual(spec["encoding"]["x"]["scale"], {"type": "utc", "nice": False})

    def test_upload_acima_do_limite_falha_antes_da_leitura(self):
        app = self.app()
        oversized = io.BytesIO(b"x" * (MAX_UPLOAD_MB * 1024 * 1024 + 1))
        with patch("streamlit.file_uploader", return_value=oversized) as upload:
            with patch("pandas.read_csv") as read:
                app.radio[0].set_value("CSV autorizado").run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual(upload.call_args.kwargs["max_upload_size"], MAX_UPLOAD_MB)
        self.assertIn("no máximo 5 MiB", app.error[0].value)
        self.assertEqual(len(app.metric), 0)
        read.assert_not_called()

    def test_erros_de_historico_sao_exibidos_antes_da_previsao(self):
        insufficient = self.history(days=27)
        gap = self.history(days=29).drop(index=10)
        unknown = self.history()
        unknown.loc[unknown.produto_id.eq("acem"), "produto_id"] = "desconhecido"
        missing_date = self.history()
        missing_date.loc[0, "data"] = pd.NaT
        for history, message in ((insufficient, "28 dias civis"), (gap, "Lacuna"),
                                 (unknown, "Produto desconhecido"), (missing_date, "Data inválida")):
            with self.subTest(message=message):
                app = self.app()
                with patch("streamlit.file_uploader", return_value=self.csv(history)):
                    with patch("modeling.inference.predict_next_day") as predict:
                        app.radio[0].set_value("CSV autorizado").run()
                self.assertEqual(len(app.exception), 0)
                self.assertEqual(len(app.error), 1)
                self.assertIn(message, app.error[0].value)
                self.assertEqual(len(app.metric), 0)
                predict.assert_not_called()

    def test_previsao_negativa_exibe_erro_sem_resultado_convertido(self):
        app = self.app()
        with patch("modeling.inference.predict_next_day", side_effect=ValueError("Previsões negativas do Ridge (kg): acem -0.5")):
            app.button[0].click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertIn("Não foi possível gerar a previsão", app.error[0].value)
        self.assertIn("-0.5", app.error[0].value)
        self.assertEqual(len(app.metric), 0)

    def test_csv_invalido_exibe_orientacao_em_portugues(self):
        for payload in (b"coluna_errada\n1\n", b"\xff\xfe\x00"):
            with self.subTest(payload=payload):
                app = self.app()
                with patch("streamlit.file_uploader", return_value=io.BytesIO(payload)):
                    app.radio[0].set_value("CSV autorizado").run()
                self.assertEqual(len(app.exception), 0)
                self.assertIn("CSV inválido. Use UTF-8", app.error[0].value)
                self.assertEqual(len(app.metric), 0)
