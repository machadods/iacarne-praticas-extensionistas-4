"""Verificar o preparo Favorita apenas com dados fictícios."""

import csv
import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiments.favorita.prepare import (
    OUTPUT_COLUMNS, OUTPUT_CSV, OUTPUT_REPORT, REPOSITORY, STORE_COLUMNS, TRAIN_COLUMNS,
    prepare_favorita, prepare_meats,
)


def csv_stream(columns, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(columns)
    writer.writerows(rows)
    stream.seek(0)
    return stream


def observation(row_id, day, store=1, sales="1.25", family="MEATS", onpromotion=0):
    return (row_id, f"2017-01-{day:02}", store, family, sales, onpromotion)


def store_stream(store_ids):
    return csv_stream(STORE_COLUMNS, [(store, "Cidade", "Estado", "A", 1) for store in store_ids])


class FavoritaPreparationTests(unittest.TestCase):
    def prepare(self, rows, stores=(1, 2)):
        return prepare_meats(csv_stream(TRAIN_COLUMNS, rows), store_stream(stores))

    def source(self, directory):
        directory.mkdir()
        (directory / "train.csv").write_text(
            csv_stream(TRAIN_COLUMNS, [observation(1, 1, sales="1.234567890")]).getvalue(),
            encoding="utf-8", newline="",
        )
        (directory / "stores.csv").write_text(store_stream((1,)).getvalue(), encoding="utf-8", newline="")
        return {path.name: path.read_bytes() for path in directory.iterdir()}

    def test_filtro_exato_preserva_nome_e_texto_de_sales(self):
        prepared, report = self.prepare([
            observation(3, 2, store=1, sales="7.2e-4"),
            ("ignorar", "data inválida", "desconhecida", "PRODUCE", "invalida", ""),
            observation(2, 1, store=2, sales="2.00000", family="meats"),
            observation(1, 1, store=1, sales="1.234567890"),
        ])
        self.assertEqual(report["contagens"], {"linhas_lidas_train": 4,
                         "linhas_excluidas_outras_familias": 2, "linhas_meats_preservadas": 2,
                         "lojas_catalogo": 2, "lojas_meats": 1})
        self.assertEqual(report["lojas_catalogo_sem_meats"], [2])
        self.assertEqual(report["chave"], ["store_nbr", "date"])
        self.assertEqual((report["alvo"], report["unidade_fisica_sales"]), ("sales", "desconhecida"))
        self.assertEqual([row[3:5] for row in prepared], [("MEATS", "1.234567890"), ("MEATS", "7.2e-4")])

    def test_duplicata_por_loja_e_data_falha_mesmo_com_ids_distintos(self):
        rows = [observation(1, 1, store="01"), observation(2, 4), observation(3, 1)]
        with self.assertRaisesRegex(ValueError, "store_nbr/date duplicada"):
            self.prepare(rows)

    def test_id_meats_duplicado_falha_em_datas_e_lojas_diferentes(self):
        for store in (1, 2):
            rows = [observation(7, 1), observation(7, 2, store=store)]
            with self.subTest(store=store), self.assertRaisesRegex(
                ValueError, "train.csv, linha 3: id duplicado no recorte MEATS: 7",
            ):
                self.prepare(rows)

    def test_ids_distintos_preservam_valores_e_ordenacao(self):
        rows = [observation(20, 2, store=2, sales="0.001"),
                observation(10, 1, store=1, sales="12.3456700")]
        prepared, report = self.prepare(rows)
        self.assertEqual([row[0] for row in prepared], [10, 20])
        self.assertEqual([row[4] for row in prepared], ["12.3456700", "0.001"])
        self.assertEqual(report["contagens"]["linhas_meats_preservadas"], 2)

    def test_id_repetido_em_outra_familia_nao_afeta_meats(self):
        rows = [observation(7, 1, family="PRODUCE"), observation(7, 2),
                observation(7, 3, store=2, family="PRODUCE")]
        prepared, report = self.prepare(rows)
        self.assertEqual([row[:4] for row in prepared], [(7, "2017-01-02", 1, "MEATS")])
        self.assertEqual(report["contagens"]["linhas_excluidas_outras_familias"], 2)

    def test_campos_invalidos_e_loja_desconhecida_falham(self):
        for field, values in {
            "id": ("x", "-1"),
            "date": ("2017-02-29", "2017-01-01T00:00:00", "01/01/2017"),
            "store_nbr": ("0", "1.0", "30"),
            "sales": ("", "NaN", "Infinity", "-1", "1,25"),
            "onpromotion": ("-1", "1.2"),
        }.items():
            for value in values:
                row = list(observation(1, 1))
                row[TRAIN_COLUMNS.index(field)] = value
                with self.subTest(field=field, value=value), self.assertRaisesRegex(ValueError, field):
                    self.prepare([row])

    def test_cadastro_duplicado_e_recorte_vazio_falham(self):
        with self.assertRaisesRegex(ValueError, "duplicado no cadastro"):
            self.prepare([observation(1, 1)], stores=(1, 1))
        with self.assertRaisesRegex(ValueError, "nenhum registro"):
            self.prepare([observation(1, 1, family="PRODUCE")])

    def test_d7_usa_dias_civis_e_apenas_a_propria_loja(self):
        rows = [observation(1, 1, sales="0"), observation(2, 3), observation(3, 8), observation(4, 9),
                observation(5, 2, store=2), observation(6, 8, store=2), observation(7, 9, store=2)]
        prepared, report = self.prepare(rows[::-1])
        history = {(row[2], row[1]): row[-1] for row in prepared}
        self.assertEqual(history[1, "2017-01-08"], "disponivel")
        self.assertEqual(history[1, "2017-01-09"], "data_ausente")
        self.assertEqual(history[2, "2017-01-08"], "historico_insuficiente")
        self.assertEqual(history[2, "2017-01-09"], "disponivel")
        self.assertEqual(report["datas_ausentes_em_todas_lojas"], [f"2017-01-0{d}" for d in range(4, 8)])
        self.assertIn("2017-01-02", report["cobertura_por_loja"]["1"]["datas_ausentes_no_intervalo_global"])
        self.assertEqual(report["pares_loja_data_ausentes"], 11)
        self.assertEqual(len(prepared), len(rows))

        with_future, _ = self.prepare([*rows, observation(8, 10, sales="999999")])
        self.assertEqual([row for row in with_future if row[1] < "2017-01-10"], prepared)

    def test_zeros_iniciais_e_serie_toda_zero_sao_distintos(self):
        rows = [observation(1, 1, sales="0.000"), observation(2, 3, sales="0"),
                observation(3, 8, sales="1.01"), observation(4, 9, sales="0"),
                observation(5, 1, store=2, sales="0"), observation(6, 9, store=2, sales="0")]
        prepared, report = self.prepare(rows)
        self.assertEqual(report["sales_zero"], 5)
        self.assertEqual(report["zeros_antes_primeira_positiva"], 2)
        self.assertEqual(report["zeros_em_serie_sem_positiva"], 2)
        self.assertEqual(report["cobertura_por_loja"]["1"]["primeira_venda_positiva_observada"], "2017-01-08")
        self.assertIsNone(report["cobertura_por_loja"]["2"]["primeira_venda_positiva_observada"])
        self.assertEqual(prepared[0][4], "0.000")

    def test_extremos_sao_sinalizados_no_relatorio_e_preservados_no_csv(self):
        rows = [observation(i, i, sales="1") for i in range(1, 8)]
        rows.append(observation(8, 8, sales="1000.125123"))
        prepared, report = self.prepare(rows)
        extremes = report["extremos_apenas_auditoria"]
        self.assertEqual(extremes["registros_sinalizados"], 1)
        self.assertEqual(extremes["datas_sinalizadas_por_loja"], {"1": ["2017-01-08"]})
        self.assertEqual(len(prepared), 8)
        self.assertEqual(prepared[-1][4], "1000.125123")
        self.assertEqual(OUTPUT_COLUMNS, (*TRAIN_COLUMNS, "historico_d7"))

    def test_publicacao_externa_e_reproducivel_sem_sobrescrever(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source, output, second = root / "originais", root / "lote", root / "lote2"
            before = self.source(source)
            first_report = prepare_favorita(source, output)
            self.assertEqual(prepare_favorita(source, second), first_report)
            for filename in (OUTPUT_CSV, OUTPUT_REPORT):
                self.assertEqual((output / filename).read_bytes(), (second / filename).read_bytes())
            with (output / OUTPUT_CSV).open(encoding="utf-8", newline="") as stream:
                data, = list(csv.DictReader(stream))
            self.assertEqual(data["sales"], "1.234567890")
            self.assertEqual(data["historico_d7"], "historico_insuficiente")
            self.assertEqual(json.loads((output / OUTPUT_REPORT).read_text(encoding="utf-8")), first_report)
            for filename, content in before.items():
                self.assertEqual((source / filename).read_bytes(), content)
                self.assertEqual(first_report["arquivos_entrada"][filename]["sha256"], hashlib.sha256(content).hexdigest())
            with self.assertRaises(FileExistsError):
                prepare_favorita(source, output)
            self.assertEqual((output / OUTPUT_CSV).read_bytes(), (second / OUTPUT_CSV).read_bytes())

    def test_destinos_protegidos_e_falha_de_escrita_nao_publicam(self):
        with TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            source, output = root / "originais", root / "lote"
            before = self.source(source)
            for invalid in (source, source / "derivados", REPOSITORY / "dados_favorita"):
                with self.subTest(destino=invalid), self.assertRaises(ValueError):
                    prepare_favorita(source, invalid)
            with patch.object(Path, "write_text", side_effect=OSError("escrita simulada")):
                with self.assertRaisesRegex(OSError, "escrita simulada"):
                    prepare_favorita(source, output)
            self.assertEqual(list(root.iterdir()), [source])
            self.assertEqual({path.name: path.read_bytes() for path in source.iterdir()}, before)


if __name__ == "__main__":
    unittest.main()
