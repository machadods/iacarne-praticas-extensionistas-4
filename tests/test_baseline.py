"""Baseline, métricas e limites de leitura, com vendas construídas em memória."""

import builtins
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal

from modeling.baseline import SOURCE, evaluate_validation, regression_metrics, seasonal_baseline
from modeling.features import TARGET, build_features


class BaselineTests(unittest.TestCase):
    def setUp(self):
        self.sales = pd.DataFrame([
            {"data": day, "produto_id": product, "corte": product,
             "categoria_anatomica": "traseiro", "perfil_uso": "cozido",
             TARGET: offset + index}
            for product, offset in (("a", 1), ("b", 1001))
            for index, day in enumerate(pd.date_range("2025-09-01", "2026-08-31"))
        ])
        self.frame = build_features(self.sales).dropna().reset_index(drop=True)
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.source = self.root / SOURCE
        self.source.parent.mkdir(parents=True)

    def write(self, frame=None):
        (self.frame if frame is None else frame).to_csv(self.source, index=False, date_format="%Y-%m-%d")

    def test_baseline_copia_lag_sem_ler_alvo_e_preserva_entrada(self):
        frame = self.frame.sample(frac=1, random_state=17)
        original = frame.copy(deep=True)
        predicted = seasonal_baseline(frame)
        assert_series_equal(predicted, frame.venda_lag_7.rename("previsao_kg"))
        assert_series_equal(predicted, seasonal_baseline(frame[["venda_lag_7"]]))
        assert_series_equal(predicted, seasonal_baseline(frame.assign(quantidade_vendida_kg=-999)))
        assert_frame_equal(frame, original)
        predicted.iloc[0] = -1
        assert_frame_equal(frame, original)

    def test_d_menos_7_exato_e_isolamento_dos_produtos(self):
        predicted = seasonal_baseline(self.frame)
        observed = self.sales.set_index(["produto_id", "data"])[TARGET]
        for index, row in self.frame.iterrows():
            previous_day = row.data - pd.Timedelta(days=7)
            self.assertEqual(row.data.dayofweek, previous_day.dayofweek)
            self.assertEqual(predicted.loc[index], observed.loc[(row.produto_id, previous_day)])
        first_a = predicted[self.frame.produto_id.eq("a")].iloc[0]
        first_b = predicted[self.frame.produto_id.eq("b")].iloc[0]
        self.assertEqual(first_b - first_a, 1000)

    def test_alvo_de_d_e_futuro_so_afetam_previsoes_a_partir_de_d_mais_7(self):
        day = pd.Timestamp("2026-06-01")
        changed = self.sales.copy()
        changed.loc[changed.data.ge(day), TARGET] += 9999
        updated = build_features(changed).dropna().reset_index(drop=True)
        before = seasonal_baseline(self.frame)
        after = seasonal_baseline(updated)
        safe = self.frame.data.lt(day + pd.Timedelta(days=7))
        assert_series_equal(before[safe], after[safe])
        affected = self.frame.data.eq(day + pd.Timedelta(days=7))
        np.testing.assert_array_equal((after - before)[affected], [9999, 9999])

    def test_metricas_com_resultados_conhecidos(self):
        metrics = regression_metrics([1, 2, 3], [1, 2, 5])
        self.assertEqual(metrics["n_observacoes"], 3)
        self.assertAlmostEqual(metrics["mae_kg"], 2 / 3)
        self.assertAlmostEqual(metrics["rmse_kg"], np.sqrt(4 / 3))
        self.assertAlmostEqual(metrics["r2"], -1)
        self.assertEqual(regression_metrics([1, 2, 3], [1, 2, 3]),
                         {"n_observacoes": 3, "mae_kg": 0.0, "rmse_kg": 0.0, "r2": 1.0})

    def test_r2_indefinido_para_alvo_constante_ou_uma_observacao(self):
        for actual, predicted in (([2, 2], [1, 3]), ([2, 2], [2, 2]), ([2], [1])):
            with self.subTest(actual=actual, predicted=predicted):
                self.assertIsNone(regression_metrics(actual, predicted)["r2"])

    def test_metricas_rejeitam_entrada_invalida_sem_descartar_linhas(self):
        for actual, predicted in (([], []), ([1], [1, 2]), ([np.nan], [1]),
                                  ([1], [np.inf]), ([[1]], [[1]]), ([True], [1]),
                                  ([1 + 2j], [1]), (["erro"], [1])):
            with self.subTest(actual=actual, predicted=predicted), self.assertRaises(ValueError):
                regression_metrics(actual, predicted)

    def test_lag_ausente_invalido_ou_negativo_falha(self):
        for values in ([], [None], [np.nan], [np.inf], [-1], [True], [1 + 2j], ["erro"]):
            with self.subTest(values=values), self.assertRaises(ValueError):
                seasonal_baseline(pd.DataFrame({"venda_lag_7": values}))
        with self.assertRaises(ValueError):
            seasonal_baseline(pd.DataFrame({TARGET: [1]}))
        with self.assertRaises(ValueError):
            seasonal_baseline(pd.DataFrame([[1, 2]], columns=["venda_lag_7", "venda_lag_7"]))

    def test_avaliacao_diaria_e_por_corte_com_erro_conhecido(self):
        self.write()
        result = evaluate_validation(self.root)
        self.assertEqual(result["avaliacao"], "validacao")
        self.assertEqual(result["metricas"]["n_observacoes"], 122)
        self.assertEqual(result["metricas"]["mae_kg"], 7)
        self.assertEqual(result["metricas"]["rmse_kg"], 7)
        self.assertEqual(len(result["por_corte"]), 2)
        for cut in result["por_corte"]:
            self.assertEqual((cut["n_observacoes"], cut["mae_kg"], cut["rmse_kg"]), (61, 7, 7))
        self.assertEqual(result["conjuntos"]["treino"]["n_observacoes"], 428)
        self.assertEqual(result["conjuntos"]["teste"]["n_observacoes"], 124)

    def test_avaliacao_rejeita_lag_de_outro_dia_ou_produto(self):
        for value in (self.frame.loc[self.frame.data.eq("2026-05-01"), "venda_lag_1"].iloc[0],
                      self.frame.loc[self.frame.data.eq("2026-05-01"), "venda_lag_7"].iloc[-1]):
            changed = self.frame.copy()
            changed.loc[changed.data.eq("2026-05-01") & changed.produto_id.eq("a"), "venda_lag_7"] = value
            self.write(changed)
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "mesmo produto em D-7"):
                evaluate_validation(self.root)

    def test_teste_final_nao_entra_no_baseline_nas_metricas_ou_no_historico(self):
        self.write()
        first = evaluate_validation(self.root)
        changed = self.frame.copy()
        test_rows = changed.data.ge("2026-07-01")
        # Se o teste for usado em qualquer cálculo, estes valores fazem a execução falhar.
        for column in (TARGET, "venda_lag_7"):
            changed[column] = changed[column].astype(object)
            changed.loc[test_rows, column] = "não consultar"
        self.write(changed)
        with patch("modeling.baseline.regression_metrics", wraps=regression_metrics) as metrics:
            with patch("modeling.baseline.seasonal_baseline", wraps=seasonal_baseline) as baseline:
                second = evaluate_validation(self.root)
        evaluated = baseline.call_args.args[0]
        self.assertTrue(evaluated.data.between("2026-05-01", "2026-06-30").all())
        self.assertEqual(baseline.call_count, 1)
        self.assertEqual(sorted(len(call.args[0]) for call in metrics.call_args_list), [61, 61, 122])
        first.pop("hash_sha256_modelagem")
        second.pop("hash_sha256_modelagem")
        self.assertEqual(first, second)

    def test_determinismo_e_leitura_exclusiva_da_matriz_sem_ground_truth(self):
        self.write()
        original_path_open = Path.open
        original_io_open, original_builtin_open = io.open, builtins.open
        reads = []

        def guarded(opener):
            def guard(file, mode="r", *args, **kwargs):
                path = Path(file).resolve()
                if path != self.source or mode != "rb":
                    raise AssertionError(f"Acesso fora da matriz permitida: {path} ({mode})")
                reads.append(path)
                return opener(file, mode, *args, **kwargs)
            return guard

        # Python 3.10 mantém uma referência própria ao open no acessor de Path.
        with patch.object(Path, "open", guarded(original_path_open)), \
                patch("io.open", guarded(original_io_open)), \
                patch("builtins.open", guarded(original_builtin_open)):
            first = evaluate_validation(self.root)
            second = evaluate_validation(self.root)
        self.assertEqual(first, second)
        self.assertGreaterEqual(len(reads), 2)
        self.assertEqual(set(reads), {self.source})
        self.write(self.frame.sample(frac=1, random_state=17))
        shuffled = evaluate_validation(self.root)
        first.pop("hash_sha256_modelagem")
        shuffled.pop("hash_sha256_modelagem")
        self.assertEqual(first, shuffled)


if __name__ == "__main__":
    unittest.main()
