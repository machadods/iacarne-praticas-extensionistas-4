"""Preparar observações MEATS e publicar um lote local fora do repositório."""

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import quantiles
from tempfile import TemporaryDirectory
from typing import TextIO


REPOSITORY = Path(__file__).resolve().parents[2]
TRAIN_COLUMNS = ("id", "date", "store_nbr", "family", "sales", "onpromotion")
STORE_COLUMNS = ("store_nbr", "city", "state", "type", "cluster")
OUTPUT_COLUMNS = (*TRAIN_COLUMNS, "historico_d7")
OUTPUT_CSV = "meats_observado.csv"
OUTPUT_REPORT = "auditoria_meats.json"
SOURCE_URL = "https://www.kaggle.com/competitions/store-sales-time-series-forecasting/data"
DECIMAL_TEXT = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
HISTORY_STATES = ("disponivel", "data_ausente", "historico_insuficiente")


@dataclass(frozen=True, slots=True)
class Observation:
    row_id: int
    day: date
    sales_text: str
    sales: Decimal
    onpromotion: int


def _rows(stream, columns, filename):
    reader = csv.reader(stream, strict=True)
    if next(reader, None) != list(columns):
        raise ValueError(f"{filename}: cabeçalho diferente do contrato")
    for row in reader:
        if len(row) != len(columns):
            raise ValueError(f"{filename}, linha {reader.line_num}: quantidade incorreta de campos")
        yield row, reader.line_num


def _integer(text, field, location, minimum=0):
    if text.isascii() and text.isdecimal():
        value = int(text)
        if value >= minimum:
            return value
    raise ValueError(f"{location}: {field} deve ser inteiro maior ou igual a {minimum}")


def _date(text, location):
    try:
        day = date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{location}: date inválida, esperado AAAA-MM-DD") from exc
    if day.isoformat() != text:
        raise ValueError(f"{location}: date inválida, esperado AAAA-MM-DD")
    return day


def _sales(text, location):
    if not DECIMAL_TEXT.fullmatch(text):
        raise ValueError(f"{location}: sales deve ser decimal, finito e não negativo")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{location}: sales inválido") from exc
    if not value.is_finite() or value < 0:
        raise ValueError(f"{location}: sales deve ser decimal, finito e não negativo")
    return value


def _store_catalog(stores):
    catalog = set()
    for row, line in _rows(stores, STORE_COLUMNS, "stores.csv"):
        location = f"stores.csv, linha {line}"
        store = _integer(row[0], "store_nbr", location, minimum=1)
        if store in catalog:
            raise ValueError(f"{location}: store_nbr duplicado no cadastro: {store}")
        catalog.add(store)
    if not catalog:
        raise ValueError("stores.csv: cadastro de lojas vazio")
    return catalog


def _read_meats(train, catalog):
    grouped = defaultdict(list)
    seen_ids = set()
    scanned = 0
    for row, line in _rows(train, TRAIN_COLUMNS, "train.csv"):
        scanned += 1
        row_id, day, store, family, sales, onpromotion = row
        if family != "MEATS":
            continue
        location = f"train.csv, linha {line}"
        store = _integer(store, "store_nbr", location, minimum=1)
        if store not in catalog:
            raise ValueError(f"{location}: store_nbr {store} ausente de stores.csv")
        row_id = _integer(row_id, "id", location)
        if row_id in seen_ids:
            raise ValueError(f"{location}: id duplicado no recorte MEATS: {row_id}")
        seen_ids.add(row_id)
        grouped[store].append(Observation(
            row_id, _date(day, location), sales, _sales(sales, location),
            _integer(onpromotion, "onpromotion", location),
        ))
    if not grouped:
        raise ValueError('train.csv: nenhum registro com family == "MEATS"')
    return grouped, scanned


def _missing_dates(calendar, observed):
    return [date.fromordinal(day).isoformat() for day in calendar if day not in observed]


def _describe_meats(grouped):
    values = [obs.sales for series in grouped.values() for obs in series]
    q1, _, q3 = quantiles(values, n=4, method="inclusive") if len(values) > 1 else values * 3
    upper = q3 + Decimal("1.5") * (q3 - q1)
    start = min(obs.day for series in grouped.values() for obs in series)
    end = max(obs.day for series in grouped.values() for obs in series)
    calendar = range(start.toordinal(), end.toordinal() + 1)
    history = Counter(dict.fromkeys(HISTORY_STATES, 0))
    all_observed = set()
    coverage, extremes, prepared = {}, {}, []
    for store, series in sorted(grouped.items()):
        series.sort(key=lambda obs: obs.day)
        first_day = series[0].day.toordinal()
        seen_days = set()
        zero_count, zeros_until_positive = 0, 0
        first_positive = None
        store_history = Counter(dict.fromkeys(HISTORY_STATES, 0))
        for obs in series:
            day = obs.day.toordinal()
            if day in seen_days:
                raise ValueError(f"Chave store_nbr/date duplicada: {store}, {obs.day.isoformat()}")
            lag_day = day - 7
            if lag_day < first_day:
                state = "historico_insuficiente"
            elif lag_day not in seen_days:
                state = "data_ausente"
            else:
                state = "disponivel"
            store_history[state] += 1
            seen_days.add(day)
            if obs.sales.is_zero():
                zero_count += 1
                if first_positive is None:
                    zeros_until_positive += 1
            elif first_positive is None:
                first_positive = obs.day.isoformat()
            if obs.sales > upper:
                extremes.setdefault(str(store), []).append(obs.day.isoformat())
            prepared.append((obs.row_id, obs.day.isoformat(), store, "MEATS",
                             obs.sales_text, obs.onpromotion, state))
        history.update(store_history)
        all_observed.update(seen_days)
        coverage[str(store)] = {
            "registros": len(series),
            "inicio_observado": series[0].day.isoformat(),
            "fim_observado": series[-1].day.isoformat(),
            "datas_ausentes_no_intervalo_global": _missing_dates(calendar, seen_days),
            "sales_zero": zero_count,
            "primeira_venda_positiva_observada": first_positive,
            "zeros_antes_primeira_positiva": zeros_until_positive if first_positive else 0,
            "zeros_em_serie_sem_positiva": zeros_until_positive if first_positive is None else 0,
            "historico_d7": dict(store_history),
        }
    return prepared, {
        "periodo": {"inicio": start.isoformat(), "fim": end.isoformat(), "dias_civis": len(calendar)},
        "datas_ausentes_em_todas_lojas": _missing_dates(calendar, all_observed),
        "pares_loja_data_ausentes": sum(len(row["datas_ausentes_no_intervalo_global"]) for row in coverage.values()),
        "sales_zero": sum(row["sales_zero"] for row in coverage.values()),
        "zeros_antes_primeira_positiva": sum(row["zeros_antes_primeira_positiva"] for row in coverage.values()),
        "zeros_em_serie_sem_positiva": sum(row["zeros_em_serie_sem_positiva"] for row in coverage.values()),
        "historico_d7": dict(history),
        "cobertura_por_loja": coverage,
        "extremos_apenas_auditoria": {
            "metodo": "Limite superior Q3 + 1,5 × (Q3 − Q1), com quartis inclusivos de toda a amostra.",
            "q1": str(q1), "q3": str(q3), "limite_superior": str(upper), "maximo_sales": str(max(values)),
            "registros_sinalizados": sum(map(len, extremes.values())),
            "datas_sinalizadas_por_loja": extremes,
        },
    }


def prepare_meats(train: TextIO, stores: TextIO):
    """Validar as entradas, reter apenas MEATS e calcular diagnósticos em memória."""
    catalog = _store_catalog(stores)
    grouped, scanned = _read_meats(train, catalog)
    prepared, diagnostics = _describe_meats(grouped)
    return prepared, {
        "versao_contrato": "1.0.0",
        "fonte": SOURCE_URL,
        "chave": ["store_nbr", "date"],
        "alvo": "sales",
        "unidade_fisica_sales": "desconhecida",
        "contagens": {
            "linhas_lidas_train": scanned,
            "linhas_excluidas_outras_familias": scanned - len(prepared),
            "linhas_meats_preservadas": len(prepared),
            "lojas_catalogo": len(catalog),
            "lojas_meats": len(grouped),
        },
        "lojas_catalogo_sem_meats": sorted(catalog - set(grouped)),
        **diagnostics,
    }


def _fingerprint(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
        size = stream.tell()
    return {"bytes": size, "sha256": digest.hexdigest()}


def _check_destination(source, destination):
    if destination.resolve() != destination:
        raise ValueError("O destino não pode ser redirecionado")
    if destination.is_relative_to(REPOSITORY) or REPOSITORY.is_relative_to(destination):
        raise ValueError("O destino deve ficar fora do repositório")
    if destination.is_relative_to(source) or source.is_relative_to(destination):
        raise ValueError("O destino deve ficar separado da pasta dos CSVs originais")
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(f"O destino deve ser uma pasta nova: {destination}")


def prepare_favorita(source_dir, output_dir):
    """Ler os dois CSVs de entrada e publicar CSV e JSON em uma pasta nova."""
    source = Path(source_dir).resolve()
    requested_output = Path(output_dir)
    if requested_output.is_symlink():
        raise ValueError("O destino não pode ser um link")
    destination = requested_output.resolve()
    _check_destination(source, destination)
    inputs = [source / name for name in ("train.csv", "stores.csv")]
    for path in inputs:
        if not path.is_file() or path.resolve() != path:
            raise ValueError(f"Entrada ausente ou redirecionada: {path}")
    before = {path: (path.stat().st_size, path.stat().st_mtime_ns) for path in inputs}
    with inputs[0].open(encoding="utf-8-sig", newline="") as train:
        with inputs[1].open(encoding="utf-8-sig", newline="") as stores:
            rows, report = prepare_meats(train, stores)
    report["arquivos_entrada"] = {path.name: _fingerprint(path) for path in inputs}
    if before != {path: (path.stat().st_size, path.stat().st_mtime_ns) for path in inputs}:
        raise ValueError("Os CSVs de entrada mudaram durante a preparação")

    destination.parent.mkdir(parents=True, exist_ok=True)
    # O lote só aparece no destino quando ambos os arquivos estiverem completos.
    with TemporaryDirectory(prefix=".favorita-", dir=destination.parent) as temporary:
        staging = Path(temporary) / "lote"
        staging.mkdir()
        output_csv = staging / OUTPUT_CSV
        with output_csv.open("x", encoding="utf-8", newline="") as stream:
            writer = csv.writer(stream, lineterminator="\n")
            writer.writerow(OUTPUT_COLUMNS)
            writer.writerows(rows)
        report["arquivo_observacoes"] = {"nome": OUTPUT_CSV, **_fingerprint(output_csv)}
        (staging / OUTPUT_REPORT).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n",
        )
        _check_destination(source, destination)
        staging.rename(destination)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True, help="Pasta com train.csv e stores.csv")
    parser.add_argument("--output-dir", type=Path, required=True, help="Pasta externa nova para o lote MEATS")
    args = parser.parse_args()
    try:
        report = prepare_favorita(args.source_dir, args.output_dir)
    except (ValueError, OSError, csv.Error) as exc:
        raise SystemExit(f"Falha na preparação Favorita: {exc}") from exc
    print(json.dumps({
        "destino": str(args.output_dir.resolve()),
        "contagens": report["contagens"],
        "historico_d7": report["historico_d7"],
        "auditoria": OUTPUT_REPORT,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
