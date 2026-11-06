"""Ajustar, avaliar e salvar o Ridge congelado com `python -m modeling.finalize`."""

import hashlib
import io
import json
from importlib.metadata import version
from pathlib import Path
from platform import python_version

import joblib
import numpy as np
import pandas as pd

from modeling.baseline import ROOT, SOURCE, seasonal_baseline
from modeling.dataset import HISTORY, LOOKBACK, _publish
from modeling.features import FEATURES, TARGET, build_features
from modeling.train import CATEGORICAL, NUMERIC, _features_and_target, _score_validation
from modeling.train import build_pipelines
from modeling.validation import PERIODS, split_temporal


DESTINATION = Path("artifacts/models")
MODEL_NAME = "iacarne_ridge_v1.joblib"
METADATA_NAME = "iacarne_ridge_v1.metadata.json"
EXPECTED_COUNTS = {"treino": 4494, "validacao": 1281, "teste": 1302}
PREDICTION_ATOL_KG = 1e-10


def _check_test_history(development, test, test_features):
    """Conferir os históricos do teste com observações do mesmo produto até D−1."""
    start = test.data.min() - pd.Timedelta(days=LOOKBACK)
    history = pd.concat([development.loc[development.data.ge(start)], test], ignore_index=True)
    derived = build_features(history).set_index(["data", "produto_id"])
    test_keys = pd.MultiIndex.from_frame(test[["data", "produto_id"]])
    expected = derived.loc[test_keys, list(HISTORY)].to_numpy()
    actual = test_features.loc[:, list(HISTORY)].to_numpy()
    if not np.allclose(actual, expected, rtol=0, atol=PREDICTION_ATOL_KG):
        raise ValueError("Histórico do teste difere das vendas observadas até D−1")


def _prediction_issues(prediction):
    values = prediction.to_numpy()
    finite = np.isfinite(values)
    non_finite = int((~finite).sum())
    negative = int((finite & (values < 0)).sum())
    return {"invalidas": non_finite + negative, "nao_finitas": non_finite, "negativas": negative}


def _verified_artifact(pipeline, features, prediction):
    buffer = io.BytesIO()
    joblib.dump(pipeline, buffer, compress=3)
    payload = buffer.getvalue()
    # Somente bytes produzidos nesta execução são desserializados.
    restored = joblib.load(io.BytesIO(payload))
    if tuple(pipeline.feature_names_in_) != FEATURES or tuple(restored.feature_names_in_) != FEATURES:
        raise ValueError("O artefato não preservou os nomes e a ordem dos atributos")
    restored_prediction = restored.predict(features)
    original = prediction.to_numpy()
    if restored_prediction.shape != original.shape or not np.allclose(
        restored_prediction, original, rtol=0, atol=PREDICTION_ATOL_KG,
    ):
        raise ValueError("As previsões mudaram após o carregamento do modelo")
    return payload, {
        "carregamento_ok": True,
        "ordem_features_preservada": True,
        "previsoes_comparadas": len(original),
        "tolerancia_absoluta_kg": PREDICTION_ATOL_KG,
        "maior_diferenca_absoluta_kg": float(np.max(np.abs(restored_prediction - original))),
    }


def finalize_model(root=ROOT) -> dict:
    """Avaliar a configuração congelada e publicar o pipeline e seus metadados."""
    root = Path(root).resolve()
    source = root / SOURCE
    destination = root / DESTINATION
    for path in (source, destination, destination / MODEL_NAME, destination / METADATA_NAME):
        if path.is_symlink() or path.resolve() != path:
            raise ValueError(f"Caminho protegido: {path}")

    contents = source.read_bytes()
    frame = pd.read_csv(io.BytesIO(contents), dtype=str, keep_default_na=False)
    if tuple(frame.columns) != ("data", TARGET, *FEATURES):
        raise ValueError("Colunas da matriz diferentes do contrato de modelagem")
    splits = split_temporal(frame)
    counts = {name: len(part) for name, part in splits.items()}
    if counts != EXPECTED_COUNTS:
        raise ValueError(f"Contagens diferentes do protocolo final: {counts}")

    development = pd.concat([splits["treino"], splits["validacao"]], ignore_index=True)
    fit_features, fit_target = _features_and_target(development)
    pipeline = build_pipelines()["ridge"].set_params(regressor__alpha=100.0, regressor__solver="cholesky")
    pipeline.fit(fit_features, fit_target)

    test = splits["teste"]
    test_features, test_target = _features_and_target(test)
    _check_test_history(development, test, test_features)
    predictions = {
        "baseline": seasonal_baseline(test),
        "ridge": pd.Series(pipeline.predict(test_features), index=test.index),
    }
    issues = {name: _prediction_issues(values) for name, values in predictions.items()}
    if any(count["nao_finitas"] for count in issues.values()):
        raise ValueError(f"Previsões não finitas impedem calcular as métricas: {issues}")
    metrics, by_cut = _score_validation(test_target, test.corte, predictions)
    payload, verification = _verified_artifact(pipeline, test_features, predictions["ridge"])

    metadata = {
        "versao_artefato": "1.0.0",
        "artefato": (DESTINATION / MODEL_NAME).as_posix(),
        "hash_sha256_artefato": hashlib.sha256(payload).hexdigest(),
        "algoritmo": "Ridge",
        "hiperparametros": pipeline.named_steps["regressor"].get_params(deep=False),
        "data_corte_treino": development.data.max().strftime("%Y-%m-%d"),
        "contagens": {**counts, "treino_validacao": len(development)},
        "periodos": {name: {"inicio": start, "fim": end} for name, start, end in PERIODS},
        "alvo": TARGET,
        "features": list(FEATURES),
        "features_categoricas": list(CATEGORICAL),
        "features_numericas": list(NUMERIC),
        "fonte": SOURCE.as_posix(),
        "hash_sha256_modelagem": hashlib.sha256(contents).hexdigest(),
        "versoes": {
            "python": python_version(),
            **{name: version(name) for name in ("numpy", "pandas", "scikit-learn", "scipy", "joblib")},
        },
        "protocolo": {
            "id": "previsao_diaria_d_menos_1",
            "horizonte_dias": 1,
            "historico": "Vendas observadas até D−1, incluindo dias de teste já encerrados.",
            "entrada": "Atributos tabulares prontos. Lags e médias móveis são preparados fora do pipeline.",
        },
        "avaliacao": "teste",
        "metricas_finais": metrics,
        "previsoes_invalidas": issues,
        "mae_por_corte": by_cut,
        "verificacao_serializacao": verification,
    }
    _publish(destination, {
        MODEL_NAME: payload,
        METADATA_NAME: (json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8"),
    })
    return metadata


def main():
    try:
        metadata = finalize_model()
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"Falha na avaliação final: {exc}") from exc
    print(json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
