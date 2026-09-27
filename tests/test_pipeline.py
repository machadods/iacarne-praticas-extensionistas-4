"""Testes sobre a base oficial e mutações temporárias de seus registros."""

import csv
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from pipeline.extract import extract
from pipeline.run_pipeline import ROOT, run
from pipeline.transform import transform


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads((ROOT / "pipeline/contrato.json").read_text(encoding="utf-8"))
        cls.spec = json.loads((ROOT / "iacarne_dataset_especificacao.json").read_text(encoding="utf-8"))
        cls.raw = extract(ROOT / "data/raw/iacarne_vendas_bruto.csv", cls.contract["colunas"])

    def changed(self, field, value):
        # Remover apenas as duplicatas idênticas para isolar a regra testada.
        rows = list({r["registro_id"]: dict(r) for r in self.raw}.values())
        rows[0][field] = value
        return rows

    def test_oficial_contagens_e_equacoes(self):
        rows, report = transform(self.raw, self.contract, self.spec)
        self.assertEqual((len(rows), report["duplicatas_removidas"]), (7665, 15))
        self.assertEqual(report["transformacoes"], {"nomes_padronizados": 38, "precos_convertidos": 19, "estoques_reconstruidos": 23, "calendario_corrigido": 0})
        self.assertEqual(sum(r["estoque_inicial_reconstruido"] for r in rows), 23)
        self.assertNotIn("demanda_latente_kg", rows[0])
        for row in rows:
            self.assertEqual(row["estoque_inicial_kg"] + row["entrada_kg"], row["estoque_disponivel_kg"])
            self.assertEqual(row["estoque_disponivel_kg"], row["quantidade_vendida_kg"] + row["perda_kg"] + row["estoque_final_kg"])

    def test_arquivo_ausente(self):
        with self.assertRaises(FileNotFoundError):
            extract(ROOT / "arquivo_inexistente.csv", self.contract["colunas"])

    def test_schema_e_linha_malformada(self):
        with TemporaryDirectory() as tmp:
            source = Path(tmp) / "entrada.csv"
            for text in ["errado\nvalor\n", ",".join(self.contract["colunas"]) + "\nvalor\n", ",".join(self.contract["colunas"]) + "\n"]:
                source.write_text(text, encoding="utf-8")
                with self.assertRaises(ValueError):
                    extract(source, self.contract["colunas"])

    def test_erros_criticos(self):
        for field, value in [("data", "2026-02-30"), ("preco_venda_kg", "NaN"), ("entrada_kg", "-1"), ("perda_kg", ""), ("promocao", "2"), ("custo_estimado_kg", "1.234"), ("estoque_final_kg", "999"), ("receita_bruta_rs", "999999"), ("produto_id", "desconhecido"), ("registro_id", "chave_errada"), ("preco_venda_kg", "1.234,56"), ("categoria_anatomica", "desconhecida")]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                transform(self.changed(field, value), self.contract, self.spec)

    def test_duplicata_conflitante(self):
        conflict = dict(self.raw[0], preco_venda_kg="1")
        with self.assertRaisesRegex(ValueError, "duplicata conflitante"):
            transform(self.raw + [conflict], self.contract, self.spec)

    def test_cobertura_incompleta(self):
        key = self.raw[0]["registro_id"]
        with self.assertRaisesRegex(ValueError, "Cobertura"):
            transform([r for r in self.raw if r["registro_id"] != key], self.contract, self.spec)

    def test_calendario_e_ano_iso(self):
        rows, report = transform(self.changed("mes", "1"), self.contract, self.spec)
        target = next(r for r in rows if r["registro_id"] == self.raw[0]["registro_id"])
        self.assertEqual(target["mes"], int(target["data"][5:7]))
        december = next(r for r in rows if r["data"] == "2025-12-29")
        self.assertEqual((december["ano"], december["ano_semana_iso"], december["semana_ano"]), (2025, 2026, 1))

    def test_destinos_protegidos(self):
        for path in (ROOT, ROOT / "data/raw"):
            with self.assertRaisesRegex(ValueError, "protegido"):
                run(output_dir=path)

    def test_integridade_originais(self):
        manifest = json.loads((ROOT / "docs/integridade_dataset.json").read_text())
        for name, expected in manifest.items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected, name)
        self.assertEqual((ROOT / "data/raw/iacarne_vendas_bruto.csv").read_bytes(), (ROOT / "iacarne_vendas_bruto.csv").read_bytes())

    def test_determinismo_sem_acesso_auditoria_e_xlsx(self):
        original_open = Path.open

        def guard(path, *args, **kwargs):
            if path.name in ("iacarne_ground_truth_auditoria.csv", "iacarne_dataset_v1.xlsx", "generate_iacarne_dataset.py"):
                raise AssertionError("ETL acessou arquivo fora da entrada operacional")
            return original_open(path, *args, **kwargs)

        with TemporaryDirectory() as tmp, patch.object(Path, "open", guard):
            first, second = Path(tmp) / "a", Path(tmp) / "b"
            run(output_dir=first)
            run(output_dir=second)
            for name in ("iacarne_vendas_tratado.csv", "relatorio_pipeline.json"):
                self.assertEqual((first / name).read_bytes(), (second / name).read_bytes())
            report = json.loads((first / "relatorio_pipeline.json").read_text(encoding="utf-8"))
            self.assertEqual(report["sha256_saida"], hashlib.sha256((first / "iacarne_vendas_tratado.csv").read_bytes()).hexdigest())

    def test_falha_nao_publica_saida(self):
        with TemporaryDirectory() as tmp:
            source, dest = Path(tmp) / "entrada.csv", Path(tmp) / "saida"
            with source.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=self.contract["colunas"])
                writer.writeheader()
                writer.writerows(self.changed("preco_venda_kg", "invalido"))
            with self.assertRaises(ValueError):
                run(source, dest)
            self.assertFalse(dest.exists())


if __name__ == "__main__":
    unittest.main()
