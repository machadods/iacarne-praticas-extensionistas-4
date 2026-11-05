"""Verificar o treino temporal com séries diárias pequenas e controladas."""

from contextlib import ExitStack
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal
from sklearn.pipeline import Pipeline

from modeling.features import FEATURES, TARGET, build_features
from modeling.train import (
    CATEGORICAL, NUMERIC, SOURCE, _score_validation, build_pipelines, compare_models,
    evaluate_models,
)
from modeling.validation import split_temporal


class TrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sales = pd.DataFrame([
            {"data": day, "produto_id": product, "corte": cut,
             "categoria_anatomica": "01", "perfil_uso": "07",
             TARGET: offset + 0.1 * index + day.dayofweek}
            for product, cut, offset in (("001", "002", 10), ("1", "2", 20))
            for index, day in enumerate(pd.date_range("2025-09-01", "2026-08-31"))
        ])
        cls.frame = build_features(sales).dropna().reset_index(drop=True)

    def test_modelos_e_transformadores_ajustados_somente_no_treino(self):
        frame = self.frame.assign(ruptura_estoque=1)
        validation_days = frame.data.between("2026-05-01", "2026-06-30")
        frame.loc[validation_days, "perfil_uso"] = "99"
        frame.loc[validation_days, "venda_lag_1"] += 100
        splits = split_temporal(frame)
        pipelines = build_pipelines()
        with ExitStack() as stack:
            stack.enter_context(patch("modeling.train.build_pipelines", return_value=pipelines))
            fits = {name: stack.enter_context(patch.object(pipeline, "fit", wraps=pipeline.fit))
                    for name, pipeline in pipelines.items()}
            predictions = {name: stack.enter_context(patch.object(pipeline, "predict", wraps=pipeline.predict))
                           for name, pipeline in pipelines.items()}
            result = compare_models(frame)

        self.assertEqual(result["contagens"], {"treino": 428, "validacao": 122, "teste": 124})
        self.assertEqual(result["avaliacao"], "validacao")
        for name, pipeline in pipelines.items():
            with self.subTest(modelo=name):
                fits[name].assert_called_once()
                predictions[name].assert_called_once()
                train_x, train_y = fits[name].call_args.args
                validation_x, = predictions[name].call_args.args
                self.assertEqual(tuple(train_x.columns), FEATURES)
                self.assertEqual(tuple(validation_x.columns), FEATURES)
                assert_series_equal(train_y, splits["treino"][TARGET])
                assert_series_equal(train_x.venda_lag_1, splits["treino"].venda_lag_1)
                assert_series_equal(validation_x.venda_lag_1, splits["validacao"].venda_lag_1)
                self.assertEqual(len(validation_x), 122)
                encoder = pipeline.named_steps["preprocessamento"].named_transformers_["categoricas"]
                categories = dict(zip(CATEGORICAL, encoder.categories_))
                self.assertEqual(set(categories["produto_id"]), {"001", "1"})
                self.assertEqual(set(categories["corte"]), {"002", "2"})
                self.assertEqual(list(categories["categoria_anatomica"]), ["01"])
                self.assertEqual(list(categories["perfil_uso"]), ["07"])
                # O perfil só observado na validação é codificado com zeros.
                profile_index = sum(len(categories[column]) for column in CATEGORICAL[:3])
                encoded = encoder.transform(validation_x.loc[:, list(CATEGORICAL)])
                np.testing.assert_array_equal(encoded[:, profile_index], np.zeros(len(validation_x)))

        ridge_scaler = pipelines["ridge"].named_steps["preprocessamento"].named_transformers_["numericas"]
        np.testing.assert_allclose(ridge_scaler.mean_, splits["treino"].loc[:, list(NUMERIC)].mean())
        self.assertEqual(ridge_scaler.n_samples_seen_, 428)
        forest_transformers = pipelines["random_forest"].named_steps["preprocessamento"].transformers
        self.assertEqual(forest_transformers[1][1], "passthrough")

    def test_previsoes_finitas_e_deterministicas_sem_uso_dos_valores_do_teste(self):
        changed = self.frame.astype(str).sample(frac=1, random_state=17)
        test_rows = changed.data.ge("2026-07-01")
        changed.loc[test_rows, [*NUMERIC, TARGET, "perfil_uso"]] = "reservado"
        original = self.frame.copy(deep=True)
        changed_original = changed.copy(deep=True)
        captured = []
        predict = Pipeline.predict

        def capture(pipeline, features):
            forecast = predict(pipeline, features)
            captured.append(forecast.copy())
            return forecast

        with patch.object(Pipeline, "predict", capture):
            first = compare_models(self.frame)
            second = compare_models(changed)
        self.assertEqual(first, second)
        self.assertEqual(len(captured), 4)
        for forecast, repeated in zip(captured[:2], captured[2:]):
            self.assertEqual(forecast.shape, (122,))
            self.assertTrue(np.isfinite(forecast).all())
            self.assertTrue((forecast >= 0).all())
            np.testing.assert_array_equal(forecast, repeated)
        self.assertEqual(first["hiperparametros"]["random_forest"]["random_state"], 42)
        assert_frame_equal(self.frame, original)
        assert_frame_equal(changed, changed_original)

    def test_cobertura_invalida_interrompe_antes_de_treinar(self):
        with patch("modeling.train.build_pipelines") as factory:
            with self.assertRaisesRegex(ValueError, "Cobertura"):
                compare_models(self.frame.drop(index=0))
            factory.assert_not_called()

    def test_leitura_preserva_arquivo_e_codigos_com_zeros_a_esquerda(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = root / SOURCE
            source.parent.mkdir(parents=True)
            self.frame.to_csv(source, index=False, date_format="%Y-%m-%d")
            before = source.read_bytes()
            result = evaluate_models(root)
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual(list(source.parent.iterdir()), [source])
            self.assertEqual({row["corte"] for row in result["por_corte"]}, {"002", "2"})

    def test_metricas_globais_por_corte_e_variacao_do_mae(self):
        index = [10, 20, 30, 40]
        observed = pd.Series([1, 3, 5, 7], index=index)
        cuts = pd.Series(["A", "A", "B", "B"], index=index)
        predictions = {
            "baseline": pd.Series([2, 1, 7, 6], index=index),
            "ridge": pd.Series([1, 4, 5, 7], index=index),
            "random_forest": pd.Series([0, 1, 2, 3], index=index),
        }
        scores, by_cut = _score_validation(observed, cuts, predictions)
        expected = {"baseline": (1.5, np.sqrt(2.5), 0.5, 0),
                    "ridge": (0.25, 0.5, 0.95, -100 * 5 / 6),
                    "random_forest": (2.5, np.sqrt(7.5), -0.5, 100 * 2 / 3)}
        for name, score in scores.items():
            self.assertEqual(score["n_observacoes"], 4)
            for key, value in zip(("mae_kg", "rmse_kg", "r2", "variacao_mae_pct"), expected[name]):
                self.assertAlmostEqual(score[key], value)
        self.assertEqual(by_cut, [
            {"corte": "A", "n_observacoes": 2, "mae_kg": {"baseline": 1.5, "ridge": 0.5, "random_forest": 1.5}},
            {"corte": "B", "n_observacoes": 2, "mae_kg": {"baseline": 1.5, "ridge": 0.0, "random_forest": 3.5}},
        ])


if __name__ == "__main__":
    unittest.main()
