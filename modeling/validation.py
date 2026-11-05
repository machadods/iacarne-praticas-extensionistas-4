"""Separação por datas globais para previsão diária após o fechamento de D-1."""

import re

import pandas as pd


# Limites inclusivos; alterações exigem revisão do protocolo antes dos experimentos.
PERIODS = (
    ("treino", "2025-09-29", "2026-04-30"),
    ("validacao", "2026-05-01", "2026-06-30"),
    ("teste", "2026-07-01", "2026-08-31"),
)


def _daily_dates(values):
    """Validar datas sem descartar horários, fusos ou valores ausentes."""
    if pd.api.types.is_datetime64_any_dtype(values):
        dates = values
    else:
        if not values.map(
            lambda value: isinstance(value, str)
            and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", value))
        ).all():
            raise ValueError("Data inválida: use YYYY-MM-DD ou datetime sem horário")
        try:
            dates = pd.to_datetime(values, format="%Y-%m-%d", errors="raise")
        except (ValueError, TypeError) as exc:
            raise ValueError("Data inválida") from exc
    if dates.isna().any() or dates.dt.tz is not None or not dates.eq(dates.dt.normalize()).all():
        raise ValueError("Data inválida: ausente, com horário ou fuso")
    return dates


def split_temporal(frame: pd.DataFrame, periods=PERIODS) -> dict[str, pd.DataFrame]:
    """Separar e conferir cobertura diária de todos os produtos em cada período.

    Inspeciona apenas data, produto e corte; não avalia alvos ou features.
    Retorna cópias ordenadas por data global/produto, sem alterar a entrada.
    periods permite verificar o mesmo protocolo em séries pequenas nos testes.
    """
    if tuple(period[0] for period in periods) != ("treino", "validacao", "teste"):
        raise ValueError("Defina treino, validacao e teste nessa ordem")
    boundaries = _daily_dates(pd.Series([value for _, start, end in periods for value in (start, end)]))
    previous_end = None
    for index, (name, _, _) in enumerate(periods):
        start, end = boundaries.iloc[2 * index:2 * index + 2]
        if start > end:
            raise ValueError(f"Período invertido: {name}")
        if previous_end is not None:
            if start <= previous_end:
                raise ValueError("Sobreposição temporal entre conjuntos")
            if start != previous_end + pd.Timedelta(days=1):
                raise ValueError("Lacuna temporal entre conjuntos")
        previous_end = end

    required = {"data", "produto_id", "corte"}
    if frame.empty or not frame.columns.is_unique or not required.issubset(frame.columns):
        raise ValueError("Entrada vazia, colunas duplicadas ou colunas obrigatórias ausentes")
    data = frame.copy(deep=True)
    data["data"] = _daily_dates(data["data"])
    for column in ("produto_id", "corte"):
        if not data[column].map(lambda value: isinstance(value, str) and bool(value.strip())).all():
            raise ValueError(f"Identificação inválida: {column}")
    if data.duplicated(["produto_id", "data"]).any():
        raise ValueError("Chave produto/data duplicada")
    if (data.groupby("produto_id").corte.nunique().ne(1).any()
            or data.groupby("corte").produto_id.nunique().ne(1).any()):
        raise ValueError("Identidade produto/corte inconsistente")
    if not data.data.between(boundaries.iloc[0], boundaries.iloc[-1]).all():
        raise ValueError("Datas fora dos períodos definidos")

    products = set(data.produto_id)
    result = {}
    for index, (name, _, _) in enumerate(periods):
        start, end = boundaries.iloc[2 * index:2 * index + 2]
        part = data.loc[data.data.between(start, end)].copy()
        days = (end - start).days + 1
        counts = part.groupby("produto_id").size()
        if set(counts.index) != products or not counts.eq(days).all():
            raise ValueError(f"Cobertura diária incompleta por produto: {name}")
        result[name] = part.sort_values(["data", "produto_id"], kind="stable").reset_index(drop=True)
    return result
