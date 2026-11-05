"""Comparar os modelos iniciais na validação com `python -m modeling.train`."""

import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from modeling.baseline import ROOT, SOURCE, regression_metrics, seasonal_baseline
from modeling.features import FEATURES, METADATA, TARGET
from modeling.validation import split_temporal


CATEGORICAL = (*METADATA, "dia_semana")
NUMERIC = tuple(column for column in FEATURES if column not in CATEGORICAL)
RANDOM_STATE = 42


def build_pipelines() -> dict[str, Pipeline]:
    """Criar os dois pipelines com configurações fixas para a comparação inicial."""
    configurations = {
        "ridge": (Ridge(alpha=1.0, solver="cholesky"), StandardScaler()),
        "random_forest": (
            RandomForestRegressor(n_estimators=100, random_state=RANDOM_STATE, n_jobs=1),
            "passthrough",
        ),
    }
    pipelines = {}
    for name, (estimator, numeric_transformer) in configurations.items():
        preprocessing = ColumnTransformer([
            ("categoricas", OneHotEncoder(handle_unknown="ignore", sparse_output=False), list(CATEGORICAL)),
            ("numericas", numeric_transformer, list(NUMERIC)),
        ], remainder="drop")
        pipelines[name] = Pipeline([("preprocessamento", preprocessing), ("regressor", estimator)])
    return pipelines


def _features_and_target(part):
    # Converter por nome depois da divisão mantém o tipo independente do teste.
    types = {column: str for column in CATEGORICAL} | {column: float for column in NUMERIC}
    features = part.loc[:, list(FEATURES)].astype(types)
    target = part[TARGET].astype(float)
    if not np.isfinite(features.loc[:, list(NUMERIC)].to_numpy()).all():
        raise ValueError("Atributos numéricos devem ser finitos")
    if not np.isfinite(target).all() or target.lt(0).any():
        raise ValueError("O alvo deve ser finito e não negativo")
    return features, target


def _score_validation(observed, cuts, predictions):
    metrics = {name: regression_metrics(observed, forecast) for name, forecast in predictions.items()}
    baseline_mae = metrics["baseline"]["mae_kg"]
    for score in metrics.values():
        score["variacao_mae_pct"] = (
            100 * (score["mae_kg"] - baseline_mae) / baseline_mae if baseline_mae else None
        )

    by_cut = []
    for cut, group in cuts.groupby(cuts, sort=True):
        indices = group.index
        by_cut.append({
            "corte": cut,
            "n_observacoes": len(group),
            "mae_kg": {
                name: float((observed.loc[indices] - forecast.loc[indices]).abs().mean())
                for name, forecast in predictions.items()
            },
        })
    return metrics, by_cut


def compare_models(frame: pd.DataFrame) -> dict:
    """Ajustar os pipelines no treino e calcular as métricas na validação."""
    splits = split_temporal(frame)
    validation = splits["validacao"]
    train_features, train_target = _features_and_target(splits["treino"])
    validation_features, validation_target = _features_and_target(validation)

    predictions = {"baseline": seasonal_baseline(validation)}
    pipelines = build_pipelines()
    for name, pipeline in pipelines.items():
        pipeline.fit(train_features, train_target)
        predictions[name] = pd.Series(pipeline.predict(validation_features), index=validation.index)

    metrics, by_cut = _score_validation(validation_target, validation.corte, predictions)
    return {
        "contagens": {name: len(part) for name, part in splits.items()},
        "avaliacao": "validacao",
        "atributos": list(FEATURES),
        "hiperparametros": {
            name: pipeline.named_steps["regressor"].get_params(deep=False)
            for name, pipeline in pipelines.items()
        },
        "metricas": metrics,
        "por_corte": by_cut,
    }


def evaluate_models(root=ROOT) -> dict:
    """Executar a comparação sobre a matriz fixa em modo de leitura."""
    source = Path(root).resolve() / SOURCE
    if source.is_symlink() or source.resolve() != source:
        raise ValueError(f"Fonte redirecionada: {source}")
    contents = source.read_bytes()
    frame = pd.read_csv(io.BytesIO(contents), dtype=str, keep_default_na=False)
    if tuple(frame.columns) != ("data", TARGET, *FEATURES):
        raise ValueError("Colunas da matriz diferentes do contrato de modelagem")
    return {
        "fonte": SOURCE.as_posix(),
        "hash_sha256_modelagem": hashlib.sha256(contents).hexdigest(),
        **compare_models(frame),
    }


def main():
    try:
        result = evaluate_models()
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"Falha na comparação: {exc}") from exc
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
