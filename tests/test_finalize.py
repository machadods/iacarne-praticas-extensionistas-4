"""Contratos da avaliação final e do artefato com uma matriz de teste própria."""

import hashlib
import json
from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import joblib
import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from modeling.features import FEATURES, TARGET, build_features
from modeling.finalize import (
    DESTINATION, METADATA_NAME, MODEL_NAME, SOURCE, _check_test_history, finalize_model,
)
from modeling.train import NUMERIC, _features_and_target, _score_validation, build_pipelines
from modeling.validation import split_temporal


class FinalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sales = pd.DataFrame([
            {"data": day, "produto_id": f"{product:02}", "corte": f"Corte {product:02}",
             "categoria_anatomica": "traseiro", "perfil_uso": "cozido",
             TARGET: 10 + 0.4 * product + day.dayofweek + 0.01 * index + 0.3 * (index % 13)
             + (3 if day >= pd.Timestamp("2026-07-01") else 0)}
            for product in range(21)
            for index, day in enumerate(pd.date_range("2025-09-01", "2026-08-31"))
        ])
        cls.frame = build_features(cls.sales).dropna().reset_index(drop=True)
        cls.splits = split_temporal(cls.frame)

    def write_source(self, root, frame=None):
        source = root / SOURCE
        source.parent.mkdir(parents=True, exist_ok=True)
        (self.frame if frame is None else frame).to_csv(source, index=False, date_format="%Y-%m-%d")
        return source

    def test_configuracao_congelada_ajuste_exato_e_uma_avaliacao(self):
        expected_fit = pd.concat([self.splits["treino"], self.splits["validacao"]], ignore_index=True)
        expected_test = self.splits["teste"]
        numeric_types = {column: float for column in NUMERIC}
        original_fit, original_predict = Pipeline.fit, Pipeline.predict
        fits, predictions = [], []

        def observe_fit(pipeline, features, target):
            fits.append(features)
            assert_frame_equal(features, expected_fit[list(FEATURES)].astype(numeric_types))
            assert_series_equal(target, expected_fit[TARGET])
            fitted = original_fit(pipeline, features, target)
            scaler = fitted.named_steps["preprocessamento"].named_transformers_["numericas"]
            self.assertEqual(scaler.n_samples_seen_, 5775)
            np.testing.assert_allclose(scaler.mean_, expected_fit[list(NUMERIC)].mean())
            return fitted

        def observe_predict(pipeline, features):
            assert_frame_equal(features, expected_test[list(FEATURES)].astype(numeric_types))
            prediction = original_predict(pipeline, features)
            predictions.append(prediction)
            return prediction

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = self.write_source(root)
            before = source.read_bytes()
            with patch.object(Pipeline, "fit", observe_fit), patch.object(Pipeline, "predict", observe_predict):
                with patch("modeling.finalize._score_validation", wraps=_score_validation) as score:
                    result = finalize_model(root)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(json.loads((root / DESTINATION / METADATA_NAME).read_text(encoding="utf-8")), result)

        self.assertEqual(len(fits), 1)
        self.assertEqual(len(predictions), 2)
        self.assertEqual(predictions[0].shape, (1302,))
        self.assertTrue(np.isfinite(predictions[0]).all())
        self.assertTrue((predictions[0] >= 0).all())
        np.testing.assert_allclose(predictions[0], predictions[1], rtol=0, atol=1e-10)
        score.assert_called_once()
        assert_series_equal(score.call_args.args[0], expected_test[TARGET])
        original_parameters = build_pipelines()["ridge"].named_steps["regressor"].get_params(deep=False)
        self.assertEqual(result["algoritmo"], "Ridge")
        self.assertEqual(result["hiperparametros"], original_parameters | {"alpha": 100.0})
        self.assertEqual(result["data_corte_treino"], "2026-06-30")
        self.assertEqual(result["contagens"], {"treino": 4494, "validacao": 1281, "teste": 1302,
                                             "treino_validacao": 5775})
        self.assertEqual(result["avaliacao"], "teste")
        for method in ("baseline", "ridge"):
            self.assertEqual(result["metricas_finais"][method]["n_observacoes"], 1302)
            self.assertEqual(result["previsoes_invalidas"][method],
                             {"invalidas": 0, "nao_finitas": 0, "negativas": 0})
        self.assertTrue(result["verificacao_serializacao"]["carregamento_ok"])

    def test_arquivo_carrega_fora_da_pasta_de_treino_e_respeita_esquema(self):
        probe = self.splits["teste"].loc[:1, list(FEATURES)]
        with TemporaryDirectory() as inference:
            moved_model = Path(inference) / MODEL_NAME
            with TemporaryDirectory() as temporary:
                root = Path(temporary).resolve()
                self.write_source(root)
                result = finalize_model(root)
                payload = (root / DESTINATION / MODEL_NAME).read_bytes()
                self.assertEqual(hashlib.sha256(payload).hexdigest(), result["hash_sha256_artefato"])
                moved_model.write_bytes(payload)
            with ExitStack() as stack:
                for cls in (Pipeline, Ridge, OneHotEncoder, StandardScaler):
                    stack.enter_context(patch.object(cls, "fit", side_effect=AssertionError("fit na inferência")))
                # O arquivo foi gerado acima nesta execução e conferido pelo hash.
                loaded = joblib.load(moved_model)
                self.assertIsInstance(loaded.named_steps["regressor"], Ridge)
                self.assertEqual(tuple(loaded.feature_names_in_), FEATURES)
                self.assertEqual(result["features"], list(FEATURES))
                self.assertTrue(np.isfinite(loaded.predict(probe)).all())
                with self.assertRaisesRegex(ValueError, "venda_lag_7"):
                    loaded.predict(probe.drop(columns="venda_lag_7"))

    def test_reproducao_com_ordem_diferente_das_linhas(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.write_source(root)
            first = finalize_model(root)
            self.write_source(root, self.frame.sample(frac=1, random_state=17))
            second = finalize_model(root)
        self.assertNotEqual(first.pop("hash_sha256_modelagem"), second.pop("hash_sha256_modelagem"))
        self.assertEqual(first, second)

    def test_historico_do_teste_usa_dias_encerrados_e_rejeita_alvo_do_dia(self):
        development = pd.concat([self.splits["treino"], self.splits["validacao"]], ignore_index=True)
        test = self.splits["teste"]
        self.assertEqual(test.loc[0, "venda_lag_1"], development.loc[development.index[-21], TARGET])
        self.assertEqual(test.loc[21, "venda_lag_1"], test.loc[0, TARGET])
        self.assertEqual(test.loc[147, "venda_lag_7"], test.loc[0, TARGET])

        changed_sales = self.sales.copy()
        changed_sales.loc[changed_sales.data.eq("2026-07-01") & changed_sales.produto_id.eq("00"), TARGET] += 100
        changed_frame = build_features(changed_sales).dropna().reset_index(drop=True)
        changed_test = split_temporal(changed_frame)["teste"]
        assert_frame_equal(test.loc[:20, list(FEATURES)], changed_test.loc[:20, list(FEATURES)])
        self.assertAlmostEqual(changed_test.loc[21, "venda_lag_1"] - test.loc[21, "venda_lag_1"], 100)
        self.assertAlmostEqual(changed_test.loc[147, "venda_lag_7"] - test.loc[147, "venda_lag_7"], 100)
        features, _ = _features_and_target(changed_test)
        _check_test_history(development, changed_test, features)

        features.loc[0, "venda_lag_1"] = changed_test.loc[0, TARGET]
        with self.assertRaisesRegex(ValueError, "vendas observadas até D−1"):
            _check_test_history(development, changed_test, features)

    def test_previsoes_nao_finitas_impedem_publicacao(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            self.write_source(root)
            prediction = np.full(1302, 1.0)
            prediction[:2] = [np.nan, -1]
            with patch.object(Pipeline, "predict", return_value=prediction):
                with self.assertRaisesRegex(ValueError, "'nao_finitas': 1, 'negativas': 1"):
                    finalize_model(root)
            self.assertFalse((root / DESTINATION).exists())

    def test_matriz_fora_do_contrato_falha_antes_de_ajustar(self):
        invalid = [
            (self.frame.drop(columns="venda_lag_7"), "Colunas da matriz"),
            (self.frame.loc[self.frame.produto_id.ne("00")], "Contagens diferentes"),
        ]
        with TemporaryDirectory() as temporary, patch.object(Pipeline, "fit") as fit:
            root = Path(temporary).resolve()
            for frame, message in invalid:
                self.write_source(root, frame)
                with self.assertRaisesRegex(ValueError, message):
                    finalize_model(root)
            fit.assert_not_called()
            self.assertFalse((root / DESTINATION).exists())


if __name__ == "__main__":
    unittest.main()
