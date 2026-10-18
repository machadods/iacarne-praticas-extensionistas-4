"""Atributos diários calculados somente com histórico até D-1."""

import re

import numpy as np
import pandas as pd


TARGET = "quantidade_vendida_kg"
METADATA = ("produto_id", "corte", "categoria_anatomica", "perfil_uso")
FEATURES = (
    "produto_id", "corte", "categoria_anatomica", "perfil_uso",
    "dia_semana", "fim_de_semana", "mes", "semana_ano",
    "venda_lag_1", "venda_lag_7", "venda_lag_14", "venda_lag_28",
    "venda_media_7", "venda_media_14", "venda_media_28",
)
DAYS = ("segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo")


def build_features(frame: pd.DataFrame) -> pd.DataFrame:
    """Retorna data, alvo e features; mantém as linhas de aquecimento.

    Cada produto deve ter uma série diária contínua dentro do seu período.
    Colunas extras são ignoradas. Não há leitura ou escrita de arquivos.
    """
    required = ["data", *METADATA, TARGET]
    if not frame.columns.is_unique:
        raise ValueError("Nomes de colunas duplicados")
    missing = sorted(set(required) - set(frame.columns))
    if missing:
        raise ValueError(f"Colunas obrigatórias ausentes: {missing}")
    if frame.empty:
        raise ValueError("Entrada sem registros")
    data = frame.loc[:, required].copy(deep=True)
    for column in METADATA:
        valid = data[column].map(lambda value: isinstance(value, str) and bool(value.strip()))
        if not valid.all():
            raise ValueError(f"Metadado inválido: {column}")

    # Aceitar datas ISO ou datetime sem horário/fuso; nunca truncar horários.
    if pd.api.types.is_datetime64_any_dtype(data["data"]):
        dates = data["data"]
    else:
        if not data["data"].map(
            lambda value: isinstance(value, str) and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))
        ).all():
            raise ValueError("Data inválida: use YYYY-MM-DD ou datetime sem horário")
        try:
            dates = pd.to_datetime(data["data"], format="%Y-%m-%d", errors="raise")
        except (ValueError, TypeError) as exc:
            raise ValueError("Data inválida") from exc
    if dates.isna().any() or dates.dt.tz is not None or not dates.eq(dates.dt.normalize()).all():
        raise ValueError("Data inválida: ausente, com horário ou fuso")
    data["data"] = dates
    if data.duplicated(["produto_id", "data"]).any():
        raise ValueError("Chave produto/data duplicada")

    if data[TARGET].map(lambda value: isinstance(value, (bool, np.bool_))).any():
        raise ValueError("Alvo inválido: booleano")
    try:
        target = pd.to_numeric(data[TARGET], errors="raise")
        if pd.api.types.is_complex_dtype(target):
            raise ValueError("Alvo complexo")
        target = target.astype(float)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("Alvo inválido: deve ser numérico") from exc
    if not np.isfinite(target).all() or target.lt(0).any():
        raise ValueError("Alvo inválido: deve ser finito, não nulo e não negativo")
    data[TARGET] = target
    data = data.sort_values(["produto_id", "data"], kind="stable").reset_index(drop=True)
    groups = data.groupby("produto_id", sort=False)
    if groups[list(METADATA[1:])].nunique().gt(1).any().any():
        raise ValueError("Metadados inconsistentes para o produto")
    if groups["data"].diff().dropna().ne(pd.Timedelta(days=1)).any():
        raise ValueError("Lacuna diária no histórico do produto")

    weekday = data["data"].dt.dayofweek
    data["dia_semana"] = weekday.map(dict(enumerate(DAYS)))
    data["fim_de_semana"] = weekday.ge(5).astype(int)
    data["mes"] = data["data"].dt.month
    data["semana_ano"] = data["data"].dt.isocalendar().week.astype(int)
    for lag in (1, 7, 14, 28):
        data[f"venda_lag_{lag}"] = groups[TARGET].shift(lag)
    for window in (7, 14, 28):
        data[f"venda_media_{window}"] = groups[TARGET].transform(
            lambda values: values.shift(1).rolling(window, min_periods=window).mean()
        )
    return data.loc[:, ["data", TARGET, *FEATURES]]
