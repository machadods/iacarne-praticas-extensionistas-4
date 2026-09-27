"""Serialização estável e substituição de cada arquivo após escrita completa."""

import csv
import hashlib
import json
import os
from decimal import Decimal
from pathlib import Path
from tempfile import NamedTemporaryFile


def _atomic_text(path, write):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            write(stream)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def load(rows, report, destination):
    destination = Path(destination)

    def write_csv(stream):
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: format(v, ".2f") if isinstance(v, Decimal) else v for k, v in row.items()})

    _atomic_text(destination / "iacarne_vendas_tratado.csv", write_csv)
    report["sha256_saida"] = hashlib.sha256((destination / "iacarne_vendas_tratado.csv").read_bytes()).hexdigest()
    _atomic_text(destination / "relatorio_pipeline.json", lambda stream: stream.write(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"))
