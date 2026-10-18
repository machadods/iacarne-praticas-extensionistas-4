"""Preparação e publicação verificadas com arquivos temporários."""

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import pandas as pd

from modeling.dataset import CSV_NAME, JSON_NAME, SOURCE, DESTINATION, prepare_dataset
from modeling.features import FEATURES, TARGET


class ModelingDatasetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / SOURCE
        self.destination = self.root / DESTINATION
        self.source.parent.mkdir(parents=True)
        self.frame = pd.DataFrame([
            {"data": day.strftime("%Y-%m-%d"), "produto_id": product,
             "corte": product, "categoria_anatomica": "traseiro", "perfil_uso": "cozido",
             TARGET: offset + index, "receita_bruta_rs": 999}
            for product, offset in (("a", 1), ("b", 101))
            for index, day in enumerate(pd.date_range("2025-09-01", periods=35))
        ])
        self.frame.to_csv(self.source, index=False)

    def contents(self):
        return {name: (self.destination / name).read_bytes() for name in (CSV_NAME, JSON_NAME)}

    def test_aquecimento_contrato_e_metadados(self):
        original = self.source.read_bytes()
        report = prepare_dataset(self.root)
        result = pd.read_csv(self.destination / CSV_NAME)
        self.assertEqual((report["registros_entrada"], len(result), report["registros_removidos_aquecimento"]), (70, 14, 56))
        self.assertEqual(result.groupby("produto_id").size().to_dict(), {"a": 7, "b": 7})
        self.assertEqual(list(result.columns), ["data", TARGET, *FEATURES])
        self.assertFalse(result.isna().any().any())
        self.assertFalse(result.duplicated(["produto_id", "data"]).any())
        self.assertEqual((result.data.min(), result.data.max()), ("2025-09-29", "2025-10-05"))
        expected = self.frame[self.frame.data.ge("2025-09-29")]
        self.assertEqual(result[TARGET].tolist(), expected[TARGET].tolist())
        self.assertEqual(report["hash_sha256_fonte"], hashlib.sha256(original).hexdigest())
        self.assertEqual(self.source.read_bytes(), original)
        self.assertEqual(json.loads((self.destination / JSON_NAME).read_text(encoding="utf-8")), report)

    def test_determinismo_e_leitura_restrita(self):
        original_open = Path.open
        def guard(path, *args, **kwargs):
            mode = args[0] if args else kwargs.get("mode", "r")
            if "r" in mode and path.resolve() != self.source and self.destination not in path.resolve().parents:
                raise AssertionError(f"Leitura fora da fonte e das saídas: {path}")
            return original_open(path, *args, **kwargs)
        with patch.object(Path, "open", guard):
            prepare_dataset(self.root)
            first = self.contents()
            prepare_dataset(self.root)
            self.assertEqual(first, self.contents())

    def test_falha_validacao_preserva_saidas_e_nao_cria_novas(self):
        self.frame.loc[0, TARGET] = -1
        self.frame.to_csv(self.source, index=False)
        with self.assertRaises(ValueError):
            prepare_dataset(self.root)
        self.assertFalse(self.destination.exists())
        self.frame.loc[0, TARGET] = 1
        self.frame.to_csv(self.source, index=False)
        prepare_dataset(self.root)
        previous = self.contents()
        self.frame.drop(index=10).to_csv(self.source, index=False)
        with self.assertRaises(ValueError):
            prepare_dataset(self.root)
        self.assertEqual(previous, self.contents())

    def test_produto_sem_historico_suficiente_gera_erro(self):
        self.frame[self.frame.produto_id.eq("a") | self.frame.data.lt("2025-09-29")].to_csv(self.source, index=False)
        with self.assertRaisesRegex(ValueError, "Histórico insuficiente"):
            prepare_dataset(self.root)
        self.assertFalse(self.destination.exists())

    def test_destino_redirecionado_e_protegido(self):
        self.destination.mkdir(parents=True)
        target = self.destination / CSV_NAME
        original = self.source.read_bytes()
        original_resolve = Path.resolve
        def redirected(path, *args, **kwargs):
            if path == target:
                return self.source
            return original_resolve(path, *args, **kwargs)
        # Simular resolução de link funciona também no Windows sem privilégio de symlink.
        with patch.object(Path, "resolve", redirected):
            with self.assertRaisesRegex(ValueError, "protegido"):
                prepare_dataset(self.root)
        self.assertEqual(self.source.read_bytes(), original)
        self.assertFalse(target.exists())

    def test_falha_na_segunda_substituicao_reverte_publicacao(self):
        replace = os.replace
        def fail_second(source, target):
            if Path(target).name == JSON_NAME and Path(source).name == JSON_NAME:
                raise OSError("Falha de escrita simulada")
            return replace(source, target)
        with patch("modeling.dataset.os.replace", side_effect=fail_second):
            with self.assertRaises(OSError):
                prepare_dataset(self.root)
        self.assertEqual(list(self.destination.iterdir()), [])
        prepare_dataset(self.root)
        previous = self.contents()
        self.frame[TARGET] += 10
        self.frame.to_csv(self.source, index=False)
        with patch("modeling.dataset.os.replace", side_effect=fail_second):
            with self.assertRaises(OSError):
                prepare_dataset(self.root)
        self.assertEqual(previous, self.contents())
        self.assertEqual(sorted(p.name for p in self.destination.iterdir()), sorted([CSV_NAME, JSON_NAME]))


if __name__ == "__main__":
    unittest.main()
