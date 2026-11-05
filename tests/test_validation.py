"""Cobertura, fronteiras e separação por datas globais."""

from pathlib import Path
import unittest

import pandas as pd
from pandas.testing import assert_frame_equal

from modeling.validation import PERIODS, split_temporal


SMALL_PERIODS = (
    ("treino", "2025-09-29", "2025-10-12"),
    ("validacao", "2025-10-13", "2025-10-19"),
    ("teste", "2025-10-20", "2025-10-26"),
)


class ValidationTests(unittest.TestCase):
    def setUp(self):
        # A entrada está ordenada por produto, como a matriz da Sprint 4.
        self.frame = pd.DataFrame([
            {"data": day, "produto_id": product, "corte": product}
            for product in ("a", "b")
            for day in pd.date_range("2025-09-29", "2025-10-26")
        ])

    def test_matriz_oficial_contagens_cobertura_e_datas_sem_sobreposicao(self):
        root = Path(__file__).resolve().parents[1]
        frame = pd.read_csv(root / "data/modeling/iacarne_modelagem.csv",
                            usecols=["data", "produto_id", "corte"])
        splits = split_temporal(frame)
        self.assertEqual(len(frame), 7077)
        seen_dates, seen_keys = set(), set()
        for (name, start, end), days, count in zip(PERIODS, (214, 61, 62), (4494, 1281, 1302)):
            part = splits[name]
            with self.subTest(conjunto=name):
                self.assertEqual((len(part), part.data.nunique(), part.produto_id.nunique(),
                                  part.corte.nunique()), (count, days, 21, 21))
                self.assertEqual((part.data.min(), part.data.max()), (pd.Timestamp(start), pd.Timestamp(end)))
                self.assertTrue(part.groupby("produto_id").size().eq(days).all())
                self.assertEqual(set(part.produto_id), set(frame.produto_id))
                dates = set(part.data)
                keys = set(zip(part.produto_id, part.data))
                self.assertFalse(seen_dates & dates)
                self.assertFalse(seen_keys & keys)
                seen_dates.update(dates)
                seen_keys.update(keys)
        self.assertEqual(len(seen_dates), 337)
        self.assertEqual(len(seen_keys), 7077)

    def test_limites_inclusivos_e_ordenacao_global(self):
        splits = split_temporal(self.frame, SMALL_PERIODS)
        self.assertEqual([len(part) for part in splits.values()], [28, 14, 14])
        for name, start, end in SMALL_PERIODS:
            part = splits[name]
            self.assertEqual(part.data.iloc[0], pd.Timestamp(start))
            self.assertEqual(part.data.iloc[-1], pd.Timestamp(end))
            assert_frame_equal(part, part.sort_values(["data", "produto_id"]).reset_index(drop=True))
        self.assertLess(splits["treino"].data.max(), splits["validacao"].data.min())
        self.assertLess(splits["validacao"].data.max(), splits["teste"].data.min())

    def test_periodos_sobrepostos_invertidos_e_com_lacuna_falham(self):
        for start, end, message in (
            ("2025-10-12", "2025-10-19", "Sobreposição"),
            ("2025-10-14", "2025-10-19", "Lacuna"),
            ("2025-10-19", "2025-10-13", "invertido"),
        ):
            periods = (SMALL_PERIODS[0], ("validacao", start, end), SMALL_PERIODS[2])
            with self.subTest(start=start, end=end), self.assertRaisesRegex(ValueError, message):
                split_temporal(self.frame, periods)
        with self.assertRaisesRegex(ValueError, "nessa ordem"):
            split_temporal(self.frame, SMALL_PERIODS[::-1])

    def test_lacunas_e_produto_ausente_em_um_periodo_falham(self):
        missing_product = self.frame[
            ~(self.frame.produto_id.eq("b") & self.frame.data.between("2025-10-13", "2025-10-19"))
        ]
        for invalid in (self.frame.drop(index=0), self.frame.drop(index=17), missing_product):
            with self.subTest(linhas=len(invalid)), self.assertRaisesRegex(ValueError, "Cobertura"):
                split_temporal(invalid, SMALL_PERIODS)
        outside = self.frame.copy()
        outside.loc[0, "data"] = pd.Timestamp("2025-09-28")
        with self.assertRaisesRegex(ValueError, "fora dos períodos"):
            split_temporal(outside, SMALL_PERIODS)

    def test_duplicatas_e_identidade_inconsistente_falham(self):
        with self.assertRaisesRegex(ValueError, "duplicada"):
            split_temporal(pd.concat([self.frame, self.frame.iloc[:1]]), SMALL_PERIODS)
        for column, value in (("corte", "outro"), ("corte", "b"), ("produto_id", " ")):
            changed = self.frame.copy()
            changed.loc[0, column] = value
            with self.subTest(column=column, value=value), self.assertRaises(ValueError):
                split_temporal(changed, SMALL_PERIODS)
        with self.assertRaisesRegex(ValueError, "inconsistente"):
            split_temporal(self.frame.assign(corte="igual"), SMALL_PERIODS)

    def test_datas_invalidas_nao_sao_truncadas(self):
        for value in ("2025-02-30", "29/09/2025", "2025-09-29 12:00:00", None, 20250929):
            changed = self.frame.copy()
            changed["data"] = changed.data.dt.strftime("%Y-%m-%d")
            changed.loc[0, "data"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "Data inválida"):
                split_temporal(changed, SMALL_PERIODS)
        for dates in (self.frame.data + pd.Timedelta(hours=1), self.frame.data.dt.tz_localize("UTC")):
            with self.assertRaisesRegex(ValueError, "Data inválida"):
                split_temporal(self.frame.assign(data=dates), SMALL_PERIODS)

    def test_determinismo_preservacao_e_independencia_dos_alvos(self):
        shuffled = self.frame.sample(frac=1, random_state=17)
        original = shuffled.copy(deep=True)
        first = split_temporal(shuffled, SMALL_PERIODS)
        second = split_temporal(self.frame, SMALL_PERIODS)
        assert_frame_equal(shuffled, original)
        for name in first:
            assert_frame_equal(first[name], second[name])
        # Alvos e demais features não participam da conferência de cobertura.
        extra = self.frame.assign(quantidade_vendida_kg="não consultar", venda_lag_7=None)
        for name, part in split_temporal(extra, SMALL_PERIODS).items():
            assert_frame_equal(part[self.frame.columns], second[name])
        first["treino"].loc[0, "corte"] = "alterado"
        assert_frame_equal(shuffled, original)

    def test_contrato_de_colunas(self):
        for invalid in (self.frame.iloc[:0], self.frame.drop(columns="data"),
                        pd.concat([self.frame, self.frame[["corte"]]], axis=1)):
            with self.assertRaises(ValueError):
                split_temporal(invalid, SMALL_PERIODS)


if __name__ == "__main__":
    unittest.main()
