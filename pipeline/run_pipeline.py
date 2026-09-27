"""Executar da raiz: python -m pipeline.run_pipeline."""

import argparse
import hashlib
import json
from pathlib import Path
from time import perf_counter

from pipeline import __version__
from pipeline.extract import extract
from pipeline.transform import transform
from pipeline.load import load

ROOT = Path(__file__).resolve().parents[1]


def run(input_path=None, output_dir=None):
    source = Path(input_path) if input_path else ROOT / "data/raw/iacarne_vendas_bruto.csv"
    destination = Path(output_dir) if output_dir else ROOT / "data/processed"
    source = source.resolve()
    destination = destination.resolve()
    # Apenas saída derivada: impedir sobrescrita de qualquer arquivo de entrada.
    if destination == ROOT or destination == ROOT / "data/raw" or destination == source.parent:
        raise ValueError("Destino protegido: escolha diretório exclusivo para dados tratados")
    targets = [destination / n for n in ("iacarne_vendas_tratado.csv", "relatorio_pipeline.json")]
    if any(p.resolve() == source for p in targets):
        raise ValueError("Destino não pode sobrescrever a entrada")
    contract = json.loads((ROOT / "pipeline/contrato.json").read_text(encoding="utf-8"))
    spec = json.loads((ROOT / "iacarne_dataset_especificacao.json").read_text(encoding="utf-8"))
    if spec["versao_dataset"] != contract["versao_dataset"]:
        raise ValueError("Versão de dataset incompatível com o contrato")
    rows = extract(source, contract["colunas"])
    cleaned, report = transform(rows, contract, spec)
    report["versao_pipeline"] = __version__
    report["sha256_entrada"] = hashlib.sha256(source.read_bytes()).hexdigest()
    load(cleaned, report, destination)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="CSV com o contrato oficial completo")
    parser.add_argument("--output-dir", type=Path, help="Diretório exclusivo para saídas")
    args = parser.parse_args()
    start = perf_counter()
    report = run(args.input, args.output_dir)
    summary = {k: v for k, v in report.items() if k != "correcoes"}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"Arquivo gerado: {(args.output_dir or ROOT / 'data/processed') / 'iacarne_vendas_tratado.csv'}")
    print(f"Duração: {perf_counter() - start:.3f} s")


if __name__ == "__main__":
    main()
