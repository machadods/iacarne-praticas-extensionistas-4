"""Avaliar o Ridge fixo em janelas expansivas com `python -m modeling.temporal_cv`."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from modeling.baseline import ROOT, SOURCE, seasonal_baseline
from modeling.dataset import HISTORY, LOOKBACK
from modeling.features import FEATURES, METADATA, TARGET, build_features
from modeling.train import _features_and_target, _score_validation, build_pipelines
from modeling.tune import _read_partitions
from modeling.validation import PERIODS, _daily_dates


DEVELOPMENT_START = pd.Timestamp(PERIODS[0][1])
DEVELOPMENT_END = pd.Timestamp(PERIODS[1][2])
# Cada par contém o último dia inclusivo do treino e da avaliação.
FOLDS = (
    ("2025-12-31", "2026-02-28"),
    ("2026-02-28", "2026-04-30"),
    ("2026-04-30", "2026-06-30"),
)
RIDGE_PARAMS = {"alpha": 100.0, "solver": "cholesky"}
CATALOG = Path("pipeline/contrato.json")
CALENDAR = ("dia_semana", "fim_de_semana", "mes", "semana_ano")


def _windows(folds):
    windows = []
    for train_end, evaluation_end in folds:
        train_end, evaluation_end = _daily_dates(pd.Series([train_end, evaluation_end]))
        if not (DEVELOPMENT_START + pd.Timedelta(days=LOOKBACK - 1)
                <= train_end < evaluation_end <= DEVELOPMENT_END):
            raise ValueError("Fold fora do desenvolvimento ou sem histórico suficiente")
        if windows and train_end != windows[-1][1]:
            raise ValueError("Avaliações dos folds devem ser contíguas e sem sobreposição")
        windows.append((train_end, evaluation_end))
    if not windows or windows[-1][1] != DEVELOPMENT_END:
        raise ValueError("O último fold deve encerrar o período de desenvolvimento")
    return windows


def _prepare_development(frame):
    if frame.empty or tuple(frame.columns) != ("data", TARGET, *FEATURES):
        raise ValueError("Colunas ou registros diferentes do contrato de modelagem")
    dates = _daily_dates(frame.data)
    if not dates.between(DEVELOPMENT_START, DEVELOPMENT_END).all():
        raise ValueError("Observações fora do período de desenvolvimento")
    order = ["data", "produto_id"]
    development = frame.assign(data=dates).sort_values(order).reset_index(drop=True)
    # Reusar a regra causal e a validação de chaves e continuidade por produto.
    reference = build_features(development).sort_values(order).reset_index(drop=True)
    days = (DEVELOPMENT_END - DEVELOPMENT_START).days + 1
    if not development.groupby("produto_id").size().eq(days).all():
        raise ValueError("Cobertura diária incompleta no desenvolvimento")
    if development.groupby("corte").produto_id.nunique().ne(1).any():
        raise ValueError("Identidade produto/corte inconsistente")

    features, target = _features_and_target(development)
    if not features.loc[:, list(CALENDAR)].eq(reference.loc[:, list(CALENDAR)]).all().all():
        raise ValueError("Atributos de calendário incompatíveis com a data")
    observed = features.loc[:, list(HISTORY)].to_numpy()
    expected = reference.loc[:, list(HISTORY)].to_numpy()
    verifiable = np.isfinite(expected)
    if (observed < 0).any() or not np.allclose(observed[verifiable], expected[verifiable], rtol=0, atol=1e-10):
        raise ValueError("Atributos históricos incompatíveis com vendas observadas até D−1")
    return development, features, target


def _metrics(rows):
    metrics, by_cut = _score_validation(
        rows.observado, rows.corte, {"baseline": rows.baseline, "ridge": rows.ridge},
    )
    return {"metricas": metrics, "por_corte": by_cut}


def _period(dates):
    return {
        "inicio": dates.iloc[0].strftime("%Y-%m-%d"),
        "fim": dates.iloc[-1].strftime("%Y-%m-%d"),
        "n_observacoes": len(dates),
    }


def evaluate_development(frame: pd.DataFrame, folds=FOLDS) -> dict:
    """Ajustar um Ridge por fold e agregar previsões de avaliações disjuntas."""
    windows = _windows(folds)
    development, features, target = _prepare_development(frame)
    results, evaluations = [], []
    for number, (train_end, evaluation_end) in enumerate(windows, start=1):
        fit = development.data.le(train_end)
        evaluate = development.data.gt(train_end) & development.data.le(evaluation_end)
        evaluation_features = features.loc[evaluate]
        observed = target.loc[evaluate]
        baseline = seasonal_baseline(evaluation_features)
        pipeline = build_pipelines()["ridge"].set_params(
            regressor__alpha=RIDGE_PARAMS["alpha"], regressor__solver=RIDGE_PARAMS["solver"],
        )
        pipeline.fit(features.loc[fit], target.loc[fit])
        ridge = np.asarray(pipeline.predict(evaluation_features))
        if ridge.shape != observed.shape or not baseline.index.equals(observed.index):
            raise ValueError("Previsões incompatíveis com as observações do fold")
        rows = pd.DataFrame({
            "corte": development.loc[evaluate, "corte"],
            "observado": observed,
            "baseline": baseline,
            "ridge": pd.Series(ridge, index=observed.index),
        })
        results.append({
            "fold": number,
            "treino": _period(development.loc[fit, "data"]),
            "avaliacao": _period(development.loc[evaluate, "data"]),
            **_metrics(rows),
        })
        evaluations.append(rows)

    return {
        "avaliacao": "validacao_cruzada_temporal_complementar",
        "hiperparametros": dict(RIDGE_PARAMS),
        "desenvolvimento": _period(development.data),
        "produtos": int(development.produto_id.nunique()),
        "folds": results,
        "agregado": _metrics(pd.concat(evaluations, verify_integrity=True)),
    }


def evaluate_cv(root=ROOT) -> dict:
    """Ler o desenvolvimento da matriz fixa e conferir o catálogo oficial."""
    root = Path(root).resolve()
    source = root / SOURCE
    if source.is_symlink() or source.resolve() != source:
        raise ValueError(f"Fonte redirecionada: {source}")
    contents = source.read_bytes()
    train, validation, counts = _read_partitions(contents)
    development = pd.concat([train, validation], ignore_index=True)
    catalog = json.loads((root / CATALOG).read_text(encoding="utf-8"))["produtos"]
    expected = {(product, *(fields[name] for name in METADATA[1:])) for product, fields in catalog.items()}
    observed = set(development.loc[:, list(METADATA)].itertuples(index=False, name=None))
    if observed != expected:
        raise ValueError("Identidades dos produtos diferentes do catálogo oficial")
    return {
        "fonte": SOURCE.as_posix(),
        "hash_sha256_modelagem": hashlib.sha256(contents).hexdigest(),
        "linhas_teste_final_excluidas": counts["teste"],
        **evaluate_development(development),
    }


def main():
    try:
        result = evaluate_cv()
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"Falha na validação cruzada temporal: {exc}") from exc
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
