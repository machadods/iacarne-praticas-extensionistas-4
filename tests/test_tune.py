"""Verificar a grade, o isolamento temporal e a seleção na validação."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal
from sklearn.pipeline import Pipeline

from modeling.features import FEATURES, TARGET, build_features
from modeling.train import CATEGORICAL, NUMERIC, build_pipelines
from modeling.tune import SOURCE, _candidates, _read_partitions, _select_candidate, evaluate_tuning
from modeling.validation import split_temporal


class TuningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sales = pd.DataFrame([
            {"data": day, "produto_id": product, "corte": product,
             "categoria_anatomica": "traseiro", "perfil_uso": "cozido",
             TARGET: offset + 0.1 * index + day.dayofweek}
            for product, offset in (("001", 10), ("002", 30))
            for index, day in enumerate(pd.date_range("2025-09-01", "2026-08-31"))
        ])
        cls.frame = build_features(sales).dropna().reset_index(drop=True)
        validation_days = cls.frame.data.between("2026-05-01", "2026-06-30")
        cls.frame.loc[validation_days, "perfil_uso"] = "assado"
        cls.frame.loc[validation_days, "venda_lag_1"] += 10

    def test_grade_muda_apenas_os_parametros_autorizados(self):
        original = build_pipelines()
        ridge, forest, labels = [], [], set()
        for label, model, params, pipeline in _candidates():
            self.assertNotIn(label, labels)
            labels.add(label)
            expected = original[model].named_steps["regressor"].get_params(deep=False) | params
            self.assertEqual(pipeline.named_steps["regressor"].get_params(deep=False), expected)
            if model == "ridge":
                self.assertEqual(set(params), {"alpha"})
                ridge.append(params["alpha"])
            else:
                self.assertEqual(set(params), {"max_depth", "min_samples_leaf"})
                forest.append((params["max_depth"], params["min_samples_leaf"]))
        self.assertEqual(ridge, [0.1, 1.0, 10.0, 100.0])
        self.assertCountEqual(forest, [(None, 1), (None, 4), (8, 1), (8, 4), (12, 1), (12, 4)])
        self.assertEqual(len(labels), 10)

    def test_selecao_prioriza_mae_de_validacao_com_tolerancia_e_rmse(self):
        best = {"id": "floresta", "modelo": "random_forest",
                "parametros": {"max_depth": None, "min_samples_leaf": 1},
                "metricas": {"mae_kg": 1.0, "rmse_kg": 1.5}}

        def ridge(label, alpha, mae, rmse):
            return {"id": label, "modelo": "ridge", "parametros": {"alpha": alpha},
                    "metricas": {"mae_kg": mae, "rmse_kg": rmse}}

        more_regular = ridge("proximo", 10, 1.004, 1.504)
        runs = [ridge("mae_distante", 100, 1.006, 1.0), best,
                ridge("rmse_distante", 100, 1.001, 1.506),
                ridge("menos_regular", 1, 1.002, 1.502), more_regular]
        self.assertEqual(_select_candidate(runs), (best, more_regular))
        self.assertEqual(_select_candidate(runs[::-1]), (best, more_regular))
        self.assertEqual(_select_candidate(runs[:3]), (best, best))

    def test_leitura_pula_todas_as_linhas_do_teste_antes_de_ler_o_alvo(self):
        frame = self.frame.sample(frac=1, random_state=17).reset_index(drop=True)
        test_rows = frame.data.ge("2026-07-01")
        frame[TARGET] = frame[TARGET].astype(str)
        frame.loc[test_rows, TARGET] = "reservado"
        contents = frame.to_csv(index=False, date_format="%Y-%m-%d").encode("utf-8")
        expected = split_temporal(self.frame)
        with patch("modeling.tune.pd.read_csv", wraps=pd.read_csv) as reader:
            train, validation, counts = _read_partitions(contents)
        self.assertEqual(counts, {"treino": 428, "validacao": 122, "teste": 124})
        self.assertEqual(reader.call_count, 2)
        metadata_call, data_call = reader.call_args_list
        self.assertEqual(set(metadata_call.kwargs["usecols"]), {"data", "produto_id", "corte"})
        self.assertCountEqual(data_call.kwargs["skiprows"], (frame.index[test_rows] + 1).tolist())
        assert_frame_equal(train, expected["treino"].astype(str))
        assert_frame_equal(validation, expected["validacao"].astype(str))

    def test_csv_com_registro_multilinha_falha_antes_da_leitura_dos_alvos(self):
        frame = self.frame.copy()
        frame.loc[0, "perfil_uso"] = "uma linha\noutra linha"
        contents = frame.to_csv(index=False, date_format="%Y-%m-%d").encode("utf-8")
        with patch("modeling.tune.pd.read_csv", wraps=pd.read_csv) as reader:
            with self.assertRaisesRegex(ValueError, "um registro por linha"):
                _read_partitions(contents)
        reader.assert_called_once()
        self.assertNotIn(TARGET, reader.call_args.kwargs["usecols"])

    def test_ajuste_no_treino_e_previsoes_deterministicas_na_validacao(self):
        expected = split_temporal(self.frame)
        original_fit, original_predict = Pipeline.fit, Pipeline.predict
        forecasts = []
        fits = []

        def observe_fit(pipeline, features, target):
            assert_frame_equal(features, expected["treino"].loc[:, list(FEATURES)].astype(
                {column: float for column in NUMERIC}
            ))
            assert_series_equal(target, expected["treino"][TARGET])
            fitted = original_fit(pipeline, features, target)
            transforms = fitted.named_steps["preprocessamento"].named_transformers_
            categories = transforms["categoricas"].categories_[CATEGORICAL.index("perfil_uso")]
            self.assertEqual(list(categories), ["cozido"])
            if hasattr(transforms["numericas"], "mean_"):
                np.testing.assert_allclose(
                    transforms["numericas"].mean_, expected["treino"].loc[:, list(NUMERIC)].mean(),
                )
            fits.append(fitted)
            return fitted

        def observe_predict(pipeline, features):
            assert_frame_equal(features, expected["validacao"].loc[:, list(FEATURES)].astype(
                {column: float for column in NUMERIC}
            ))
            forecast = original_predict(pipeline, features)
            self.assertTrue(np.isfinite(forecast).all())
            forecasts.append(forecast.copy())
            return forecast

        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / SOURCE
            source.parent.mkdir(parents=True)
            changed = self.frame.astype(str).sample(frac=1, random_state=17)
            changed.loc[changed.data.ge("2026-07-01"), [TARGET, *NUMERIC]] = "reservado"
            results = []
            with patch.object(Pipeline, "fit", observe_fit), patch.object(Pipeline, "predict", observe_predict):
                for frame in (self.frame, changed):
                    frame.to_csv(source, index=False, date_format="%Y-%m-%d")
                    before = source.read_bytes()
                    result = evaluate_tuning(root)
                    self.assertEqual(source.read_bytes(), before)
                    result.pop("hash_sha256_modelagem")
                    results.append(result)
            self.assertEqual(list(source.parent.iterdir()), [source])

        self.assertEqual(len(fits), 20)
        self.assertEqual(len(forecasts), 20)
        self.assertEqual(results[0], results[1])
        self.assertEqual(results[0]["n_treinamentos"], 10)
        self.assertEqual(results[0]["avaliacao"], "validacao")
        for first, second in zip(forecasts[:10], forecasts[10:]):
            self.assertEqual(first.shape, (122,))
            np.testing.assert_array_equal(first, second)
        self.assertTrue(all(run["metricas"]["n_observacoes"] == 122 for run in results[0]["experimentos"]))


if __name__ == "__main__":
    unittest.main()
