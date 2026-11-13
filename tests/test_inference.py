"""Inferência D+1 com históricos fictícios e o artefato local conferido."""

from contextlib import ExitStack, redirect_stdout
from hashlib import sha256
import io
import json
from math import fsum
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from modeling.features import FEATURES, METADATA, TARGET, build_features
from modeling.inference import (
    CATALOG_PATH, HISTORY_COLUMNS, MODEL_NAME, MODEL_PATH, MODEL_SHA256, MODEL_VERSION,
    ROOT, load_model, main, predict_next_day, prepare_next_day,
)


class InferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["produtos"]

    def history(self, days=28, end="2026-08-31"):
        return pd.DataFrame([
            {"data": day, "produto_id": product, **self.catalog[product], TARGET: offset + index * 0.25}
            for product, offset in (("acem", 10), ("picanha", 110))
            for index, day in enumerate(pd.date_range(end=end, periods=days))
        ])

    def test_atributos_exatos_e_calculo_independente_com_28_dias(self):
        day, features = prepare_next_day(self.history())
        self.assertEqual(day, pd.Timestamp("2026-09-01"))
        self.assertEqual(tuple(features.columns), FEATURES)
        self.assertNotIn(TARGET, features.columns)
        self.assertNotIn("data", features.columns)
        self.assertEqual(features.produto_id.tolist(), ["acem", "picanha"])
        for index, offset in enumerate((10, 110)):
            values = [offset + position * 0.25 for position in range(28)]
            row = features.iloc[index]
            for lag in (1, 7, 14, 28):
                self.assertEqual(row[f"venda_lag_{lag}"], values[28 - lag])
            for window in (7, 14, 28):
                self.assertAlmostEqual(row[f"venda_media_{window}"], fsum(values[28 - window:]) / window)
            self.assertEqual((row.dia_semana, row.fim_de_semana, row.mes, row.semana_ano),
                             ("terca", 0, 9, 36))

    def test_historico_maior_usa_somente_ultimos_28_dias(self):
        history = self.history(days=45)
        day, features = prepare_next_day(history)
        recent = history.groupby("produto_id", sort=False).tail(28)
        recent_day, recent_features = prepare_next_day(recent)
        self.assertEqual(day, recent_day)
        assert_frame_equal(features, recent_features)
        changed = history.copy()
        changed.loc[~changed.index.isin(recent.index), TARGET] = 999999.25
        assert_frame_equal(features, prepare_next_day(changed)[1])

    def test_lacunas_anteriores_a_janela_sao_permitidas(self):
        history = self.history(days=40).drop(index=[0, 40])
        assert_frame_equal(prepare_next_day(history)[1], prepare_next_day(self.history(days=40))[1])

    def test_isolamento_por_produto(self):
        history = self.history()
        expected = prepare_next_day(history)[1]
        changed = history.copy()
        changed.loc[changed.produto_id.eq("picanha"), TARGET] += 500
        actual = prepare_next_day(changed)[1]
        assert_frame_equal(actual.iloc[:1], expected.iloc[:1])
        self.assertEqual(actual.loc[1, "venda_lag_7"] - expected.loc[1, "venda_lag_7"], 500)
        single = prepare_next_day(history[history.produto_id.eq("acem")])[1]
        assert_frame_equal(single, expected.iloc[:1])

    def test_determinismo_e_preservacao_da_entrada(self):
        history = self.history(days=35).sample(frac=1, random_state=42)
        before = history.copy(deep=True)
        expected = prepare_next_day(history)[1]
        assert_frame_equal(expected, prepare_next_day(history.iloc[::-1])[1])
        first = predict_next_day(history)
        assert_frame_equal(first, predict_next_day(history))
        assert_frame_equal(history, before)

    def test_datas_iso_resolucoes_datetime_e_categorias_nao_observadas(self):
        history = self.history()
        expected_day, expected_features = prepare_next_day(history)
        date_inputs = [history.data.dt.strftime("%Y-%m-%d")]
        date_inputs.extend(history.data.astype(f"datetime64[{unit}]") for unit in ("s", "ms", "us", "ns"))
        for dates in date_inputs:
            with self.subTest(dtype=str(dates.dtype)):
                day, features = prepare_next_day(history.assign(data=dates))
                self.assertEqual(day, expected_day)
                assert_frame_equal(features, expected_features)
        categorical = history.copy()
        for column in METADATA:
            categorical[column] = pd.Categorical(categorical[column]).add_categories(["nao_observada"])
        assert_frame_equal(prepare_next_day(categorical)[1], expected_features)

    def test_27_dias_falham_antes_de_carregar_modelo(self):
        with patch("modeling.inference.load_model") as load:
            with self.assertRaisesRegex(ValueError, "28 dias civis"):
                predict_next_day(self.history(days=27))
        load.assert_not_called()

    def test_duplicatas_e_lacunas_falham(self):
        history = self.history(days=35)
        invalid = (
            (pd.concat([history, history.iloc[:1]]), "duplicada"),
            (history.drop(index=10), "Lacuna"),
        )
        for frame, message in invalid:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                prepare_next_day(frame)

    def test_ultimo_dia_comum_obrigatorio(self):
        history = self.history(days=35)
        stale = history.drop(index=34)
        with self.assertRaisesRegex(ValueError, "D−1 para todos"):
            prepare_next_day(stale)

    def test_vendas_invalidas_falham_inclusive_em_registros_antigos(self):
        for value in (-1, None, np.nan, np.inf, -np.inf, True, np.bool_(False), "erro", 1 + 2j):
            history = self.history(days=35)
            history[TARGET] = history[TARGET].astype(object)
            history.loc[0, TARGET] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                prepare_next_day(history)
        for values in (self.history().data, pd.to_timedelta(np.arange(56), unit="D")):
            with self.assertRaisesRegex(ValueError, "deve ser numérica"):
                prepare_next_day(self.history().assign(**{TARGET: values}))

    def test_zero_e_valores_decimais_sao_preservados(self):
        history = self.history()
        history[TARGET] = history[TARGET].astype(str)
        history.loc[27, TARGET] = "0.000125"
        features = prepare_next_day(history)[1]
        self.assertEqual(features.loc[0, "venda_lag_1"], 0.000125)
        zero = self.history().assign(**{TARGET: 0.0})
        numeric = prepare_next_day(zero)[1].filter(regex="^venda_")
        self.assertTrue(numeric.eq(0).all().all())

    def test_produto_desconhecido_e_metadados_incompativeis_falham(self):
        for column, value in (("produto_id", "desconhecido"), ("corte", "Outro corte"),
                              ("categoria_anatomica", "inexistente"), ("perfil_uso", "inexistente")):
            history = self.history()
            history.loc[history.produto_id.eq("acem"), column] = value
            with self.subTest(column=column), self.assertRaisesRegex(ValueError, "catálogo"):
                prepare_next_day(history)
        history = self.history()
        history.loc[0, "corte"] = "Picanha"
        with self.assertRaisesRegex(ValueError, "Metadados incompatíveis"):
            prepare_next_day(history)

    def test_metadados_nulos_vazios_ou_numericos_falham(self):
        for column in METADATA:
            for value in (None, "", " ", 123):
                history = self.history()
                history.loc[0, column] = value
                with self.subTest(column=column, value=value), self.assertRaisesRegex(ValueError, "Metadado inválido"):
                    prepare_next_day(history)

    def test_datas_invalidas_horarios_e_fusos_falham(self):
        for value in (None, "2026-02-30", "31/08/2026", "2026-08-31 12:00:00", 20260831):
            history = self.history()
            history["data"] = history.data.dt.strftime("%Y-%m-%d")
            history.loc[0, "data"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Data inválida"):
                prepare_next_day(history)
        for dates in (self.history().data + pd.Timedelta(hours=1), self.history().data.dt.tz_localize("UTC")):
            with self.assertRaisesRegex(ValueError, "Data inválida"):
                prepare_next_day(self.history().assign(data=dates))

    def test_viradas_de_mes_ano_semana_iso_e_fim_de_semana(self):
        cases = (
            ("2026-01-31", "2026-02-01", "domingo", 1, 2, 5),
            ("2025-12-31", "2026-01-01", "quinta", 0, 1, 1),
            ("2025-12-28", "2025-12-29", "segunda", 0, 12, 1),
            ("2024-02-28", "2024-02-29", "quinta", 0, 2, 9),
        )
        for end, expected_day, weekday, weekend, month, week in cases:
            with self.subTest(end=end):
                day, features = prepare_next_day(self.history(end=end))
                self.assertEqual(day, pd.Timestamp(expected_day))
                row = features.iloc[0]
                self.assertEqual((row.dia_semana, row.fim_de_semana, row.mes, row.semana_ano),
                                 (weekday, weekend, month, week))

    def test_equivalencia_com_features_historicas_sem_fornecer_alvo_futuro(self):
        complete = self.history(days=36)
        forecast_date = complete.data.max()
        history = complete[complete.data.lt(forecast_date)]
        day, actual = prepare_next_day(history)
        expected = build_features(complete).loc[lambda frame: frame.data.eq(forecast_date), list(FEATURES)]
        self.assertEqual(day, forecast_date)
        assert_frame_equal(actual, expected.reset_index(drop=True), check_dtype=False)
        changed = complete.copy()
        changed.loc[changed.data.eq(forecast_date), TARGET] = 99999999
        reference = build_features(changed).loc[lambda frame: frame.data.eq(forecast_date), list(FEATURES)]
        assert_frame_equal(actual, reference.reset_index(drop=True), check_dtype=False)

    def test_colunas_extras_nao_participam_e_nao_ha_linha_futura_ficticia(self):
        history = self.history()
        extra = history.assign(estoque_inicial_kg="ignorar", preco_venda_kg=None, ruptura_estoque=True,
                               promocao=object(), venda_lag_7=-999, dia_semana="errado", mes=99)
        with patch("modeling.features.build_features", side_effect=AssertionError("Linha futura fictícia")):
            day, actual = prepare_next_day(extra)
        self.assertEqual(day, history.data.max() + pd.Timedelta(days=1))
        assert_frame_equal(actual, prepare_next_day(history)[1])
        self.assertEqual(len(history), 56)

    def test_contrato_de_colunas_e_tipo_da_entrada(self):
        history = self.history()
        for invalid in (None, [], history.iloc[:0], history.drop(columns=TARGET),
                        pd.concat([history, history[[TARGET]]], axis=1)):
            with self.subTest(tipo=type(invalid).__name__), self.assertRaises(ValueError):
                prepare_next_day(invalid)

    def test_modelo_local_carrega_com_hash_valido_e_configuracao_congelada(self):
        self.assertEqual(sha256(MODEL_PATH.read_bytes()).hexdigest(), MODEL_SHA256)
        model = load_model()
        self.assertIsInstance(model, Pipeline)
        self.assertEqual(tuple(model.feature_names_in_), FEATURES)
        regressor = model.named_steps["regressor"]
        self.assertIsInstance(regressor, Ridge)
        self.assertEqual((regressor.alpha, regressor.solver), (100.0, "cholesky"))
        metadata = json.loads(MODEL_PATH.with_suffix(".metadata.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["versao_artefato"], MODEL_VERSION)
        self.assertEqual(metadata["hash_sha256_artefato"], MODEL_SHA256)

    def test_hash_incompativel_falha_antes_de_desserializar(self):
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "invalido.joblib"
            path.write_bytes(b"conteudo que nao deve ser desserializado")
            with patch("modeling.inference.MODEL_PATH", path), patch("modeling.inference.joblib.load") as load:
                with self.assertRaisesRegex(ValueError, "Hash SHA-256"):
                    load_model()
            load.assert_not_called()

    def test_desserializacao_utiliza_os_mesmos_bytes_conferidos(self):
        payload = MODEL_PATH.read_bytes()
        sentinel = load_model()
        with patch.object(Path, "read_bytes", return_value=payload) as read:
            with patch("modeling.inference.joblib.load", return_value=sentinel) as deserialize:
                self.assertIs(load_model(), sentinel)
        read.assert_called_once_with()
        self.assertEqual(deserialize.call_args.args[0].getvalue(), payload)

    def test_modelo_incompativel_falha_com_erro_controlado(self):
        for changed in (None, "schema", "parametros"):
            model = load_model()
            if changed is None:
                model = object()
            elif changed == "schema":
                model.named_steps["preprocessamento"].feature_names_in_ = np.array(FEATURES[::-1])
            else:
                model.named_steps["regressor"].alpha = 1.0
            with self.subTest(changed=changed), patch("modeling.inference.joblib.load", return_value=model):
                with self.assertRaisesRegex(ValueError, "incompatível"):
                    load_model()

    def test_saida_real_compativel_com_pipeline_e_baseline(self):
        history = self.history()
        _, features = prepare_next_day(history)
        expected = load_model().predict(features)
        result = predict_next_day(history)
        np.testing.assert_allclose(result.previsao_ridge_kg, expected, rtol=0, atol=1e-12)
        np.testing.assert_array_equal(result.baseline_d7_kg, features.venda_lag_7)
        self.assertTrue(np.isfinite(result[["previsao_ridge_kg", "baseline_d7_kg"]]).all().all())
        self.assertEqual(result.data_previsao.tolist(), ["2026-09-01"] * 2)
        self.assertTrue(result.modelo.eq(MODEL_NAME).all())
        self.assertTrue(result.versao_modelo.eq(MODEL_VERSION).all())
        self.assertTrue(result.treinado_com_dados_sinteticos.all())
        self.assertEqual(result.corte.tolist(), ["Acém", "Picanha"])
        json.dumps(result.to_dict(orient="records"), allow_nan=False)

    def test_previsoes_nao_finitas_formato_invalido_e_negativas_falham(self):
        for values in ([np.nan, 1], [np.inf, 1], [-np.inf, 1], [[1], [2]], [1], [True, False], [-0.25, 1]):
            model = Mock()
            model.predict.return_value = values
            with self.subTest(values=values), patch("modeling.inference.load_model", return_value=model):
                with self.assertRaises(ValueError):
                    predict_next_day(self.history())
        model.predict.return_value = [-0.25, 1]
        with patch("modeling.inference.load_model", return_value=model):
            with self.assertRaisesRegex(ValueError, "negativas.*acem.*-0.25"):
                predict_next_day(self.history())

    def test_inferencia_sem_ajustes_sem_gravacao_e_com_arquivos_preservados(self):
        paths = [MODEL_PATH, MODEL_PATH.with_suffix(".metadata.json"), CATALOG_PATH,
                 ROOT / "data/modeling/iacarne_modelagem.csv", ROOT / "data/processed/iacarne_vendas_tratado.csv"]
        before = {path: sha256(path.read_bytes()).hexdigest() for path in paths}
        original_open = Path.open
        allowed_reads = {MODEL_PATH, CATALOG_PATH}

        def read_only(path, mode="r", *args, **kwargs):
            self.assertIn(path, allowed_reads)
            self.assertIn(mode, ("r", "rb"))
            return original_open(path, mode, *args, **kwargs)

        with ExitStack() as stack:
            for cls in (Pipeline, ColumnTransformer, Ridge, OneHotEncoder, StandardScaler):
                for method in ("fit", "fit_transform", "partial_fit"):
                    if hasattr(cls, method):
                        stack.enter_context(patch.object(cls, method, side_effect=AssertionError("Ajuste na inferência")))
            stack.enter_context(patch.object(Path, "open", read_only))
            result = predict_next_day(self.history())
        self.assertEqual(len(result), 2)
        self.assertEqual(before, {path: sha256(path.read_bytes()).hexdigest() for path in paths})

    def test_cli_com_fixture_temporaria_produz_json_sem_alterar_entrada(self):
        with TemporaryDirectory() as temporary:
            source = Path(temporary) / "historico.csv"
            self.history().to_csv(source, index=False, date_format="%Y-%m-%d")
            before = source.read_bytes()
            output = io.StringIO()
            with patch("sys.argv", ["modeling.inference", str(source)]), redirect_stdout(output):
                main()
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual({p.name for p in source.parent.iterdir()}, {source.name})
        rows = json.loads(output.getvalue())
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["data_previsao"], "2026-09-01")
        self.assertEqual(rows[0]["baseline_d7_kg"], 15.25)
        self.assertEqual(HISTORY_COLUMNS, ("data", *METADATA, TARGET))


if __name__ == "__main__":
    unittest.main()
