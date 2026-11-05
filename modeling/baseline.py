"""Baseline sazonal na validação: python -m modeling.baseline. Não avalia teste."""

import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd

from modeling.features import TARGET
from modeling.validation import split_temporal


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("data/modeling/iacarne_modelagem.csv")


def _numeric_vector(values):
    raw = np.asarray(values)
    if raw.ndim != 1 or raw.dtype.kind in "bc":
        raise ValueError("Valores devem formar um vetor numérico real")
    try:
        vector = raw.astype(float)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Valores devem ser numéricos") from exc
    if not np.isfinite(vector).all():
        raise ValueError("Valores devem ser finitos e não nulos")
    return vector


def seasonal_baseline(frame: pd.DataFrame) -> pd.Series:
    """Copiar venda_lag_7, sem consultar o alvo de D ou ajustar parâmetros.

    A origem temporal do lag é conferida na avaliação. Valores ausentes ou
    negativos falham; não há preenchimento nem descarte de observações.
    """
    if not frame.columns.is_unique or "venda_lag_7" not in frame.columns:
        raise ValueError("Coluna venda_lag_7 ausente ou colunas duplicadas")
    values = _numeric_vector(frame["venda_lag_7"])
    if len(values) == 0 or (values < 0).any():
        raise ValueError("Lag vazio ou negativo")
    return pd.Series(values, index=frame.index, name="previsao_kg")


def regression_metrics(observed, predicted) -> dict:
    """MAE/RMSE em kg e R² agrupado; R² indefinido retorna None (JSON null)."""
    actual = _numeric_vector(observed)
    forecast = _numeric_vector(predicted)
    if len(actual) == 0 or actual.shape != forecast.shape:
        raise ValueError("Vetores vazios ou com tamanhos diferentes")
    errors = actual - forecast
    squared_error = float(np.sum(errors ** 2))
    total_variation = float(np.sum((actual - actual.mean()) ** 2))
    return {
        "n_observacoes": len(actual),
        "mae_kg": float(np.mean(np.abs(errors))),
        "rmse_kg": float(np.sqrt(squared_error / len(actual))),
        "r2": None if total_variation == 0 else float(1 - squared_error / total_variation),
    }


def evaluate_validation(root=ROOT) -> dict:
    """Ler somente a matriz fixa; conferir cobertura e avaliar somente validação.

    Não escreve arquivos. O teste participa apenas da conferência de datas,
    identidades e contagens. Não usa ground truth de auditoria.
    """
    source = Path(root).resolve() / SOURCE
    if source.is_symlink() or source.resolve() != source:
        raise ValueError(f"Fonte redirecionada: {source}")
    contents = source.read_bytes()
    splits = split_temporal(pd.read_csv(io.BytesIO(contents), keep_default_na=False))
    validation = splits["validacao"]
    predicted = seasonal_baseline(validation)

    # Buscar por produto e data exata, nunca por posição na tabela.
    # O histórico exclui o teste; só D-7 é consultado para prever cada D.
    history = pd.concat([splits["treino"], validation], ignore_index=True)
    lookup = pd.MultiIndex.from_arrays([
        validation.produto_id, validation.data - pd.Timedelta(days=7),
    ], names=["produto_id", "data"])
    expected = history.set_index(["produto_id", "data"])[TARGET].reindex(lookup)
    if not np.array_equal(predicted.to_numpy(), _numeric_vector(expected)):
        raise ValueError("venda_lag_7 difere da venda observada do mesmo produto em D-7")

    by_cut = []
    for product, group in validation.groupby("produto_id", sort=True):
        by_cut.append({
            "produto_id": product,
            "corte": group.corte.iloc[0],
            **regression_metrics(group[TARGET], predicted.loc[group.index]),
        })
    return {
        "fonte": SOURCE.as_posix(),
        "hash_sha256_modelagem": hashlib.sha256(contents).hexdigest(),
        "conjuntos": {
            name: {
                "inicio": part.data.min().strftime("%Y-%m-%d"),
                "fim": part.data.max().strftime("%Y-%m-%d"),
                "dias": int(part.data.nunique()),
                "produtos": int(part.produto_id.nunique()),
                "cortes": int(part.corte.nunique()),
                "n_observacoes": len(part),
                "observacoes_por_produto": int(part.groupby("produto_id").size().iloc[0]),
            }
            for name, part in splits.items()
        },
        "baseline": "venda_lag_7",
        "avaliacao": "validacao",
        "metricas": regression_metrics(validation[TARGET], predicted),
        "por_corte": by_cut,
    }


def main():
    try:
        result = evaluate_validation()
    except (OSError, ValueError, KeyError) as exc:
        raise SystemExit(f"Falha na avaliação: {exc}") from exc
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
