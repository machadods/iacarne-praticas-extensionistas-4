"""Extração estrita do CSV operacional, sem acesso ao ground truth."""

import csv
from pathlib import Path


def extract(path: Path, columns: list[str]) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as source:
        reader = csv.DictReader(source, strict=True)
        if reader.fieldnames != columns:
            raise ValueError("Schema incompatível: campos e ordem devem corresponder ao contrato oficial")
        rows = list(reader)
    if not rows:
        raise ValueError("CSV sem registros")
    for number, row in enumerate(rows, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"Linha {number}: quantidade incorreta de campos")
    return rows
