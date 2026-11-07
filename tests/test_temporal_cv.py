"""Validação cruzada com séries fictícias e arquivos em diretórios temporários."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal
from sklearn.pipeline import Pipeline

from modeling.features import FEATURES, METADATA, TARGET, build_features
from modeling.temporal_cv import CATALOG, FOLDS, SOURCE, evaluate_cv, evaluate_development
from modeling.train import NUMERIC, _score_validation


class TemporalCVTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sales = pd.DataFrame([
            {"data": day, "produto_id": product, "corte": product,
             "categoria_anatomica": "traseiro", "perfil_uso": "cozido",
             TARGET: offset + index + 3 * day.dayofweek}
            for product, offset in (("a", 10), ("b", 1000))
            for index, day in enumerate(pd.date_range("2025-09-01", "2026-08-31"))
        ])
        cls.full_frame = build_features(sales).dropna().reset_index(drop=True)
        cls.development = cls.full_frame.loc[cls.full_frame.data.le("2026-06-30")].reset_index(drop=True)
        cls.observed = sales.set_index(["produto_id", "data"])[TARGET]

    def write_source(self, root, frame, change_catalog=False):
        source = root / SOURCE
        source.parent.mkdir(parents=True)
        frame.to_csv(source, index=False, date_format="%Y-%m-%d")
        catalog = self.development[list(METADATA)].drop_duplicates().set_index("produto_id").to_dict("index")
        if change_catalog:
            catalog["a"]["corte"] = "outro"
        path = root / CATALOG
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"produtos": catalog}), encoding="utf-8")
        return source

    def test_folds_isolam_ajuste_e_alinham_baseline_previsoes_e_alvos(self):
        ordered = self.development.sort_values(["data", "produto_id"]).reset_index(drop=True)
        expected = (
            ("2025-12-31", "2026-01-01", "2026-02-28", 188, 118),
            ("2026-02-28", "2026-03-01", "2026-04-30", 306, 122),
            ("2026-04-30", "2026-05-01", "2026-06-30", 428, 122),
        )
        original_fit, original_predict = Pipeline.fit, Pipeline.predict
        fits, forecasts = [], []

        def observe_fit(pipeline, features, target):
            fits.append((pipeline, features, target))
            return original_fit(pipeline, features, target)

        def observe_predict(pipeline, features):
            forecast = original_predict(pipeline, features)
            forecasts.append((pipeline, features, forecast))
            return forecast

        with patch.object(Pipeline, "fit", observe_fit), patch.object(Pipeline, "predict", observe_predict):
            with patch("modeling.temporal_cv._score_validation", wraps=_score_validation) as score:
                result = evaluate_development(self.development)

        self.assertEqual(len(fits), 3)
        self.assertEqual(len({id(pipeline) for pipeline, _, _ in fits}), 3)
        self.assertEqual(len(forecasts), 3)
        self.assertEqual(score.call_count, 4)
        self.assertEqual(result["hiperparametros"], {"alpha": 100.0, "solver": "cholesky"})
        for i, (train_end, eval_start, eval_end, train_count, eval_count) in enumerate(expected):
            with self.subTest(fold=i + 1):
                fold = result["folds"][i]
                self.assertEqual(fold["treino"], {"inicio": "2025-09-29", "fim": train_end,
                                                 "n_observacoes": train_count})
                self.assertEqual(fold["avaliacao"], {"inicio": eval_start, "fim": eval_end,
                                                     "n_observacoes": eval_count})
                fit_rows = ordered.loc[ordered.data.le(train_end)]
                evaluation = ordered.loc[ordered.data.between(eval_start, eval_end)]
                self.assertLess(fit_rows.data.max(), evaluation.data.min())
                fitted, train_x, train_y = fits[i]
                predicted, evaluation_x, ridge = forecasts[i]
                self.assertIs(fitted, predicted)
                assert_frame_equal(train_x, fit_rows[list(FEATURES)].astype({name: float for name in NUMERIC}))
                assert_series_equal(train_y, fit_rows[TARGET])
                assert_frame_equal(evaluation_x, evaluation[list(FEATURES)].astype({name: float for name in NUMERIC}))
                scaler = fitted.named_steps["preprocessamento"].named_transformers_["numericas"]
                self.assertEqual(scaler.n_samples_seen_, train_count)
                np.testing.assert_allclose(scaler.mean_, fit_rows[list(NUMERIC)].mean())
                y_eval, cuts, predictions = score.call_args_list[i].args
                assert_series_equal(y_eval, evaluation[TARGET].rename("observado"))
                assert_series_equal(cuts, evaluation.corte)
                np.testing.assert_array_equal(predictions["ridge"], ridge)
                lookup = [(row.produto_id, row.data - pd.Timedelta(days=7))
                          for row in evaluation.itertuples()]
                np.testing.assert_array_equal(predictions["baseline"], self.observed.loc[lookup])
                self.assertTrue(all(fold["metricas"][method]["n_observacoes"] == eval_count
                                    for method in ("baseline", "ridge")))
                self.assertEqual(fold["metricas"]["baseline"]["mae_kg"], 7.0)
                self.assertEqual(fold["metricas"]["baseline"]["rmse_kg"], 7.0)

        pooled_y, _, pooled_predictions = score.call_args.args
        self.assertEqual(len(pooled_y), 362)
        self.assertTrue(pooled_y.index.is_unique)
        np.testing.assert_array_equal(pooled_predictions["ridge"], np.concatenate([f[2] for f in forecasts]))
        self.assertAlmostEqual(result["agregado"]["metricas"]["ridge"]["mae_kg"],
                               (pooled_y - pooled_predictions["ridge"]).abs().mean())

    def test_periodos_invalidos_sao_rejeitados_antes_do_ajuste(self):
        invalid = (
            (),
            (("2025-12-31", "2025-12-31"), *FOLDS[1:]),
            (("2025-10-01", "2026-02-28"), *FOLDS[1:]),
            (("2025-12-31 00:00:00", "2026-02-28"), *FOLDS[1:]),
            (FOLDS[0], ("2026-02-27", "2026-04-30"), FOLDS[2]),
            (FOLDS[0], ("2026-03-01", "2026-04-30"), FOLDS[2]),
            (*FOLDS[:2], ("2026-04-30", "2026-07-01")),
            FOLDS[:2],
        )
        with patch.object(Pipeline, "fit") as fit:
            for folds in invalid:
                with self.subTest(folds=folds), self.assertRaises(ValueError):
                    evaluate_development(self.development, folds)
            fit.assert_not_called()

    def test_dados_invalidos_falham_sem_ajuste(self):
        corrupted = self.development.copy()
        index = corrupted.index[corrupted.data.eq("2026-01-01")][0]
        corrupted.loc[index, "venda_lag_7"] = corrupted.loc[index, TARGET]
        missing = self.development.copy()
        missing.loc[0, "venda_media_28"] = np.nan
        invalid = (
            (self.full_frame, "fora do período"),
            (self.development.drop(columns="venda_lag_7"), "contrato"),
            (self.development.iloc[1:], "Cobertura diária"),
            (pd.concat([self.development, self.development.iloc[:1]]), "duplicada"),
            (corrupted, "históricos incompatíveis"),
            (missing, "finitos"),
        )
        with patch.object(Pipeline, "fit") as fit:
            for frame, message in invalid:
                with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                    evaluate_development(frame)
            fit.assert_not_called()

    def test_leitor_exclui_valores_do_teste_e_preserva_o_artefato(self):
        frame = self.full_frame.astype(str).sample(frac=1, random_state=17).reset_index(drop=True)
        reserved = frame.data.ge("2026-07-01")
        frame.loc[reserved, [TARGET, *NUMERIC]] = "reservado"
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source = self.write_source(root, frame)
            source_before = source.read_bytes()
            artifact = root / "artifacts/models/iacarne_ridge_v1.joblib"
            artifact.parent.mkdir(parents=True)
            artifact.write_bytes(b"artefato ficticio protegido")
            with patch("modeling.tune.pd.read_csv", wraps=pd.read_csv) as reader:
                with patch("joblib.load", side_effect=AssertionError("O modelo salvo não deve ser carregado")):
                    result = evaluate_cv(root)
            self.assertEqual(source.read_bytes(), source_before)
            self.assertEqual(artifact.read_bytes(), b"artefato ficticio protegido")
            self.assertEqual(list(artifact.parent.iterdir()), [artifact])
        self.assertEqual(result["linhas_teste_final_excluidas"], 124)
        self.assertEqual(result["desenvolvimento"]["n_observacoes"], 550)
        keys, values = reader.call_args_list
        self.assertEqual(set(keys.kwargs["usecols"]), {"data", "produto_id", "corte"})
        self.assertCountEqual(values.kwargs["skiprows"], (frame.index[reserved] + 1).tolist())
        self.assertEqual(result["agregado"], evaluate_development(self.development)["agregado"])

    def test_catalogo_incompativel_falha_antes_do_ajuste(self):
        with TemporaryDirectory() as temporary, patch.object(Pipeline, "fit") as fit:
            root = Path(temporary).resolve()
            self.write_source(root, self.full_frame, change_catalog=True)
            with self.assertRaisesRegex(ValueError, "catálogo oficial"):
                evaluate_cv(root)
            fit.assert_not_called()

    def test_resultado_deterministico_e_entrada_preservada(self):
        original = self.development.copy(deep=True)
        self.assertEqual(evaluate_development(self.development),
                         evaluate_development(self.development.sample(frac=1, random_state=17)))
        assert_frame_equal(self.development, original)

    def test_previsao_desalinhada_falha(self):
        with patch.object(Pipeline, "predict", return_value=np.array([1.0])):
            with self.assertRaisesRegex(ValueError, "Previsões incompatíveis"):
                evaluate_development(self.development)


if __name__ == "__main__":
    unittest.main()
