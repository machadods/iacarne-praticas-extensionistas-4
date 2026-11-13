"""Previsão diária de vendas observadas com o Ridge v1 sintético.

prepare_next_day recebe um DataFrame com data, os quatro METADATA e TARGET.
Datas devem ser ISO ou datetime sem horário/fuso. Produtos podem ser um
subconjunto do catálogo, mas devem encerrar o histórico no mesmo dia.
Os últimos 28 dias civis de cada produto precisam estar completos. Lacunas
anteriores a essa janela são permitidas. D é o dia seguinte ao histórico,
independentemente da data atual do computador.

predict_next_day devolve um DataFrame com data ISO, metadados, previsão em kg,
baseline D−7, modelo, versão e indicação de treinamento sintético.
Uma previsão negativa interrompe todo o lote com ValueError e informa o valor.
O histórico recebido é preservado. A função apenas lê o catálogo e o modelo.

Demonstração histórica, prevendo 01/09/2026 com a base até 31/08/2026
    python -B -X utf8 -m modeling.inference
"""

import argparse
import hashlib
import io
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline

from modeling.baseline import ROOT, _numeric_vector, seasonal_baseline
from modeling.features import DAYS, FEATURES, METADATA, TARGET
from modeling.validation import _daily_dates


MODEL_PATH = ROOT / "artifacts/models/iacarne_ridge_v1.joblib"
MODEL_SHA256 = "67b32644862f2b3fcfb3b83b30e3f1498cbd7f7b46e3356ac9dacff86d7bc73f"
MODEL_NAME = "iacarne_ridge_v1"
MODEL_VERSION = "1.0.0"
CATALOG_PATH = ROOT / "pipeline/contrato.json"
HISTORY_COLUMNS = ("data", *METADATA, TARGET)
LOOKBACK = 28


def prepare_next_day(history: pd.DataFrame) -> tuple[pd.Timestamp, pd.DataFrame]:
    """Validar o histórico e retornar D e seus 15 atributos, ordenados por produto.

    Colunas adicionais são ignoradas. Todos os valores de vendas fornecidos
    devem ser reais, finitos e não negativos, inclusive fora da janela final.
    Identidade e metadados devem coincidir com o catálogo em todas as linhas.
    """
    if not isinstance(history, pd.DataFrame):
        raise ValueError("Histórico deve ser um DataFrame")
    if not history.columns.is_unique:
        raise ValueError("Nomes de colunas duplicados")
    missing = sorted(set(HISTORY_COLUMNS) - set(history.columns))
    if missing or history.empty:
        raise ValueError(f"Histórico vazio ou colunas obrigatórias ausentes: {missing}")
    data = history.loc[:, list(HISTORY_COLUMNS)].copy(deep=True)
    data["data"] = _daily_dates(data["data"])
    for column in METADATA:
        if not data[column].map(lambda value: isinstance(value, str) and bool(value.strip())).all():
            raise ValueError(f"Metadado inválido: {column}")
    if data.duplicated(["produto_id", "data"]).any():
        raise ValueError("Chave produto/data duplicada")
    if data[TARGET].map(lambda value: isinstance(value, (bool, np.bool_))).any():
        raise ValueError("Venda observada inválida: booleano")
    if data[TARGET].dtype.kind in "mM":
        raise ValueError("Venda observada deve ser numérica")
    data[TARGET] = _numeric_vector(data[TARGET])
    if data[TARGET].lt(0).any():
        raise ValueError("Venda observada negativa")

    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))["produtos"]
    data = data.sort_values(["produto_id", "data"], kind="stable")
    last_day = data["data"].max()
    prediction_day = last_day + pd.Timedelta(days=1)
    required_days = pd.date_range(end=last_day, periods=LOOKBACK)
    rows = []
    for product, group in data.groupby("produto_id", sort=True, observed=True):
        if product not in catalog:
            raise ValueError(f"Produto desconhecido no catálogo: {product}")
        for column in METADATA[1:]:
            if not group[column].eq(catalog[product][column]).all():
                raise ValueError(f"Metadados incompatíveis com o catálogo: {product}, {column}")
        if group["data"].iloc[-1] != last_day:
            raise ValueError(f"Histórico deve encerrar em D−1 para todos os produtos: {product}")
        recent = group.tail(LOOKBACK)
        if len(recent) < LOOKBACK:
            raise ValueError(f"Histórico insuficiente: {product} precisa de 28 dias civis")
        if list(recent["data"]) != list(required_days):
            raise ValueError(f"Lacuna nos últimos 28 dias civis: {product}")
        sales = recent[TARGET]
        weekday = prediction_day.dayofweek
        row = {
            "produto_id": product, **catalog[product],
            "dia_semana": DAYS[weekday], "fim_de_semana": int(weekday >= 5),
            "mes": prediction_day.month, "semana_ano": prediction_day.isocalendar().week,
        }
        row.update({f"venda_lag_{lag}": sales.iloc[-lag] for lag in (1, 7, 14, 28)})
        row.update({f"venda_media_{window}": sales.tail(window).mean() for window in (7, 14, 28)})
        rows.append(row)
    features = pd.DataFrame(rows, columns=list(FEATURES))
    numeric = features.drop(columns=[*METADATA, "dia_semana"])
    if not np.isfinite(numeric.to_numpy(dtype=float)).all():
        raise ValueError("Atributos calculados devem ser finitos")
    return prediction_day, features


def load_model() -> Pipeline:
    """Carregar apenas os bytes do Ridge local conferidos pelo SHA-256 fixo.

    Joblib pode executar código ao carregar arquivos não confiáveis. O mesmo
    conteúdo verificado é desserializado em memória, sem reabrir o arquivo.
    """
    payload = MODEL_PATH.read_bytes()
    if hashlib.sha256(payload).hexdigest() != MODEL_SHA256:
        raise ValueError("Hash SHA-256 incompatível com o Ridge v1 protegido")
    model = joblib.load(io.BytesIO(payload))
    if not isinstance(model, Pipeline) or tuple(getattr(model, "feature_names_in_", ())) != FEATURES:
        raise ValueError("Esquema do modelo incompatível com os 15 atributos")
    regressor = model.named_steps.get("regressor")
    if not isinstance(regressor, Ridge) or regressor.alpha != 100.0 or regressor.solver != "cholesky":
        raise ValueError("Configuração incompatível com o Ridge v1 congelado")
    return model


def predict_next_day(history: pd.DataFrame) -> pd.DataFrame:
    """Prever um dia à frente. Previsões negativas ou inválidas geram ValueError."""
    day, features = prepare_next_day(history)
    predictions = _numeric_vector(load_model().predict(features))
    if len(predictions) != len(features):
        raise ValueError("Quantidade de previsões incompatível com os produtos")
    if (predictions < 0).any():
        negatives = {product: float(value) for product, value in
                     zip(features.loc[predictions < 0, "produto_id"], predictions[predictions < 0])}
        raise ValueError(f"Previsões negativas do Ridge (kg): {negatives}")
    result = features.loc[:, list(METADATA)].copy(deep=True)
    result.insert(0, "data_previsao", day.strftime("%Y-%m-%d"))
    result["previsao_ridge_kg"] = predictions
    result["baseline_d7_kg"] = seasonal_baseline(features)
    result["modelo"] = MODEL_NAME
    result["versao_modelo"] = MODEL_VERSION
    result["treinado_com_dados_sinteticos"] = True
    return result


def main():
    parser = argparse.ArgumentParser(description="Prever D+1 com o Ridge v1 sintético")
    parser.add_argument("historico", nargs="?", type=Path,
                        default=ROOT / "data/processed/iacarne_vendas_tratado.csv",
                        help="CSV de histórico encerrado. O padrão é a demonstração até 31/08/2026")
    args = parser.parse_args()
    try:
        history = pd.read_csv(args.historico, usecols=list(HISTORY_COLUMNS), dtype={c: str for c in METADATA})
        result = predict_next_day(history)
    except (OSError, ValueError) as exc:
        raise SystemExit(f"Falha na previsão: {exc}") from exc
    print(json.dumps(result.to_dict(orient="records"), ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
