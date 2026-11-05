"""Ajustar a grade fixa e comparar na validação com `python -m modeling.tune`."""

import hashlib
import io
import json
from pathlib import Path

import pandas as pd
from sklearn.base import clone

from modeling.baseline import ROOT, SOURCE, seasonal_baseline
from modeling.features import FEATURES, TARGET
from modeling.train import _features_and_target, _score_validation, build_pipelines
from modeling.validation import split_temporal


RIDGE_ALPHAS = (0.1, 1.0, 10.0, 100.0)
FOREST_DEPTHS = (None, 8, 12)
FOREST_MIN_LEAVES = (1, 4)
NEAR_TIE_KG = 0.005


def _candidates():
    pipelines = build_pipelines()
    for alpha in RIDGE_ALPHAS:
        yield f"ridge_alpha_{alpha:g}", "ridge", {"alpha": alpha}, clone(
            pipelines["ridge"]
        ).set_params(regressor__alpha=alpha)
    for depth in FOREST_DEPTHS:
        for leaf in FOREST_MIN_LEAVES:
            label = f"rf_depth_{depth}_leaf_{leaf}"
            parameters = {"max_depth": depth, "min_samples_leaf": leaf}
            pipeline = clone(pipelines["random_forest"]).set_params(
                regressor__max_depth=depth, regressor__min_samples_leaf=leaf,
            )
            yield label, "random_forest", parameters, pipeline


def _select_candidate(experiments):
    """Partir do menor MAE e comparar capacidade dentro da tolerância em kg."""
    best = min(experiments, key=lambda run: (run["metricas"]["mae_kg"], run["metricas"]["rmse_kg"]))
    best_mae = best["metricas"]["mae_kg"]
    best_rmse = best["metricas"]["rmse_kg"]
    comparable = [
        run for run in experiments
        if run["metricas"]["mae_kg"] <= best_mae + NEAR_TIE_KG
        and run["metricas"]["rmse_kg"] <= best_rmse + NEAR_TIE_KG
    ]

    def complexity(run):
        params = run["parametros"]
        if run["modelo"] == "ridge":
            return 0, -params["alpha"], 0
        depth = params["max_depth"] if params["max_depth"] is not None else float("inf")
        return 1, depth, -params["min_samples_leaf"]

    return best, min(comparable, key=complexity)


def _read_partitions(contents):
    # A primeira passagem materializa só chaves. A segunda pula as linhas do teste.
    keys = pd.read_csv(
        io.BytesIO(contents), usecols=["data", "produto_id", "corte"],
        dtype=str, keep_default_na=False, skip_blank_lines=False,
    )
    if len(contents.splitlines()) != len(keys) + 1:
        raise ValueError("A matriz deve ter um registro por linha do CSV")
    keys["linha_csv"] = keys.index + 1
    splits = split_temporal(keys)
    test_lines = splits["teste"]["linha_csv"]
    observed_keys = keys.loc[~keys["linha_csv"].isin(test_lines)]
    development = pd.read_csv(
        io.BytesIO(contents), skiprows=test_lines.tolist(), dtype=str,
        keep_default_na=False, skip_blank_lines=False,
    )
    if tuple(development.columns) != ("data", TARGET, *FEATURES):
        raise ValueError("Colunas da matriz diferentes do contrato de modelagem")
    if not development[["data", "produto_id", "corte"]].equals(
        observed_keys[["data", "produto_id", "corte"]].reset_index(drop=True)
    ):
        raise ValueError("As chaves de treino e validação não conferem com a matriz")
    development.index = observed_keys["linha_csv"]
    train = development.loc[splits["treino"]["linha_csv"]].reset_index(drop=True)
    validation = development.loc[splits["validacao"]["linha_csv"]].reset_index(drop=True)
    return train, validation, {name: len(part) for name, part in splits.items()}


def _compare_grid(train, validation):
    train_features, train_target = _features_and_target(train)
    validation_features, validation_target = _features_and_target(validation)
    predictions = {"baseline": seasonal_baseline(validation)}
    experiments = []
    for label, model, parameters, pipeline in _candidates():
        pipeline.fit(train_features, train_target)
        predictions[label] = pd.Series(pipeline.predict(validation_features), index=validation.index)
        experiments.append({"id": label, "modelo": model, "parametros": parameters})

    metrics, by_cut = _score_validation(validation_target, validation.corte, predictions)
    for experiment in experiments:
        experiment["metricas"] = metrics[experiment["id"]]
    best, selected = _select_candidate(experiments)
    return {
        "avaliacao": "validacao",
        "n_treinamentos": len(experiments),
        "tolerancia_kg": NEAR_TIE_KG,
        "baseline": metrics["baseline"],
        "experimentos": experiments,
        "menor_mae": best["id"],
        "selecionado": selected["id"],
        "por_corte": by_cut,
    }


def evaluate_tuning(root=ROOT) -> dict:
    """Executar a comparação em memória sobre a matriz fixa."""
    source = Path(root).resolve() / SOURCE
    if source.is_symlink() or source.resolve() != source:
        raise ValueError(f"Fonte redirecionada: {source}")
    contents = source.read_bytes()
    train, validation, counts = _read_partitions(contents)
    return {
        "fonte": SOURCE.as_posix(),
        "hash_sha256_modelagem": hashlib.sha256(contents).hexdigest(),
        "contagens": counts,
        **_compare_grid(train, validation),
    }


def main():
    try:
        result = evaluate_tuning()
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"Falha no ajuste: {exc}") from exc
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
