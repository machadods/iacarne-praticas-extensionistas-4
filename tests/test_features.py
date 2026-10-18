"""Verificações temporais com séries pequenas construídas em memória."""

import unittest

import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal

from modeling.features import FEATURES, TARGET, build_features


class FeaturesTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame([
            {"data": day, "produto_id": product, "corte": product,
             "categoria_anatomica": "traseiro", "perfil_uso": "cozido",
             TARGET: offset + index}
            for product, offset in (("a", 1), ("b", 101))
            for index, day in enumerate(pd.date_range("2025-12-15", periods=40))
        ])

    def test_entrada_preservada_ordenacao_e_determinismo(self):
        shuffled = self.frame.sample(frac=1, random_state=17)
        original = shuffled.copy(deep=True)
        first = build_features(shuffled)
        assert_frame_equal(shuffled, original)
        assert_frame_equal(first, build_features(shuffled))
        assert_frame_equal(first, build_features(self.frame))
        assert_frame_equal(first, first.sort_values(["produto_id", "data"]).reset_index(drop=True))

    def test_lags_medias_e_isolamento_entre_produtos(self):
        result = build_features(self.frame)
        for product, offset in (("a", 1), ("b", 101)):
            row = result[result.produto_id.eq(product)].iloc[28]
            for lag in (1, 7, 14, 28):
                with self.subTest(product=product, lag=lag):
                    self.assertEqual(row[f"venda_lag_{lag}"], offset + 28 - lag)
            for window in (7, 14, 28):
                with self.subTest(product=product, window=window):
                    self.assertEqual(row[f"venda_media_{window}"], np.mean(range(offset + 28 - window, offset + 28)))

    def test_alvo_do_dia_e_futuro_nao_alteram_features_passadas(self):
        original = build_features(self.frame)
        changed = self.frame.copy(deep=True)
        day = changed.loc[28, "data"]
        changed.loc[changed.data.ge(day), TARGET] = 99999
        result = build_features(changed)
        assert_frame_equal(
            original.loc[original.data.le(day), list(FEATURES)],
            result.loc[result.data.le(day), list(FEATURES)],
        )
        self.assertEqual(result.loc[28, TARGET], 99999)

    def test_aquecimento_completo_sem_descarte_ou_preenchimento(self):
        result = build_features(self.frame)
        self.assertEqual(len(result), len(self.frame))
        for _, product in result.groupby("produto_id"):
            for prefix, windows in (("lag", (1, 7, 14, 28)), ("media", (7, 14, 28))):
                for window in windows:
                    values = product[f"venda_{prefix}_{window}"]
                    self.assertTrue(values.iloc[:window].isna().all())
                    self.assertTrue(values.iloc[window:].notna().all())
        self.assertEqual(len(build_features(self.frame.iloc[:1])), 1)

    def test_chave_duplicada_e_lacuna_sao_rejeitadas(self):
        with self.assertRaisesRegex(ValueError, "duplicada"):
            build_features(pd.concat([self.frame, self.frame.iloc[:1]]))
        with self.assertRaisesRegex(ValueError, "Lacuna"):
            build_features(self.frame.drop(index=10))

    def test_datas_invalidas_sao_rejeitadas(self):
        for value in ("2025-02-30", "15/12/2025", None, "2025-12-15 12:00:00", 20251215):
            with self.subTest(value=value):
                changed = self.frame.copy()
                changed["data"] = changed.data.dt.strftime("%Y-%m-%d")
                changed.loc[0, "data"] = value
                with self.assertRaisesRegex(ValueError, "Data inválida"):
                    build_features(changed)
        changed = self.frame.copy()
        changed.loc[0, "data"] += pd.Timedelta(hours=1)
        with self.assertRaisesRegex(ValueError, "Data inválida"):
            build_features(changed)

    def test_alvos_invalidos_sao_rejeitados(self):
        for value in ("invalido", None, np.nan, np.inf, -np.inf, -1, True, 1 + 2j):
            with self.subTest(value=value):
                changed = self.frame.copy()
                changed[TARGET] = changed[TARGET].astype(object)
                changed.loc[0, TARGET] = value
                with self.assertRaisesRegex(ValueError, "Alvo inválido"):
                    build_features(changed)

    def test_metadados_inconsistentes_ou_ausentes_sao_rejeitados(self):
        for column in ("corte", "categoria_anatomica", "perfil_uso"):
            changed = self.frame.copy()
            changed.loc[0, column] = "outro"
            with self.subTest(column=column), self.assertRaisesRegex(ValueError, "inconsistentes"):
                build_features(changed)
        for column in ("produto_id", "corte", "categoria_anatomica", "perfil_uso"):
            changed = self.frame.copy()
            changed.loc[0, column] = " "
            with self.subTest(column=column), self.assertRaisesRegex(ValueError, "Metadado inválido"):
                build_features(changed)

    def test_lista_explicita_e_exclusao_de_colunas_extras(self):
        expected = (
            "produto_id", "corte", "categoria_anatomica", "perfil_uso",
            "dia_semana", "fim_de_semana", "mes", "semana_ano",
            "venda_lag_1", "venda_lag_7", "venda_lag_14", "venda_lag_28",
            "venda_media_7", "venda_media_14", "venda_media_28",
        )
        self.assertEqual(FEATURES, expected)
        extra = self.frame.assign(
            receita_bruta_rs=999, custo_total_estimado_rs=999,
            margem_bruta_estimada_rs=999, perda_kg=999, estoque_final_kg=999,
            ruptura_estoque=1, estoque_inicial_kg=999, estoque_disponivel_kg=999,
            entrada_kg=999, preco_venda_kg=999, promocao=1, desconto_pct=99,
            custo_estimado_kg=999, evento_calendario="evento", registro_id="id",
            estoque_inicial_reconstruido=1,
        )
        assert_frame_equal(build_features(extra), build_features(self.frame))
        self.assertEqual(list(build_features(extra).columns), ["data", TARGET, *expected])

    def test_calendario_recalculado_e_virada_iso(self):
        source = self.frame.assign(dia_semana="errado", mes=99, semana_ano=99, fim_de_semana=99)
        result = build_features(source)
        row = result[result.data.eq(pd.Timestamp("2025-12-29"))].iloc[0]
        self.assertEqual((row.dia_semana, row.mes, row.semana_ano, row.fim_de_semana), ("segunda", 12, 1, 0))
        self.assertEqual(result[result.data.eq(pd.Timestamp("2025-12-20"))].iloc[0].fim_de_semana, 1)
        source = self.frame.copy()
        source["data"] = source.data.dt.strftime("%Y-%m-%d")
        assert_frame_equal(build_features(source), build_features(self.frame))

    def test_contrato_de_entrada(self):
        for invalid in (self.frame.iloc[:0], self.frame.drop(columns=[TARGET]),
                        pd.concat([self.frame, self.frame[[TARGET]]], axis=1)):
            with self.assertRaises(ValueError):
                build_features(invalid)


if __name__ == "__main__":
    unittest.main()
