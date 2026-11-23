"""Dashboard local. Executar com python -m streamlit run app.py."""

import io

import pandas as pd
import streamlit as st

from modeling.features import METADATA, TARGET
from modeling.inference import HISTORY_COLUMNS, ROOT, predict_next_day, prepare_next_day


DEMO_SOURCE = ROOT / "data/processed/iacarne_vendas_tratado.csv"
MAX_UPLOAD_MB = 5


def read_history(source) -> pd.DataFrame:
    """Ler as colunas necessárias e validar o histórico pelo contrato da inferência."""
    try:
        history = pd.read_csv(source, usecols=list(HISTORY_COLUMNS),
                              dtype={column: str for column in METADATA}, encoding="utf-8-sig")
    except (ValueError, UnicodeError) as exc:
        raise ValueError(
            "CSV inválido. Use UTF-8, separador vírgula e as colunas " + ", ".join(HISTORY_COLUMNS)
        ) from exc
    prepare_next_day(history)
    history["data"] = pd.to_datetime(history["data"], format="%Y-%m-%d")
    return history.sort_values(["produto_id", "data"], kind="stable").reset_index(drop=True)


def main():
    st.set_page_config(page_title="iaCarne · Previsão diária", page_icon="🥩", layout="centered")
    st.title("iaCarne")
    st.caption("Dashboard beta · Ridge v1 · Treinamento com dados sintéticos")
    st.write("Previsão de vendas observadas em kg para o dia seguinte ao histórico informado.")

    source_type = st.radio("Histórico de vendas", ["Demonstração sintética", "CSV autorizado"], horizontal=True)
    source = DEMO_SOURCE
    if source_type == "CSV autorizado":
        st.caption("A autorização de uso deve ser confirmada pelo responsável pelo arquivo. "
                   "O CSV é processado em memória, com limite de 5 MiB.")
        with st.expander("Formato do histórico"):
            st.write("Colunas obrigatórias — " + ", ".join(HISTORY_COLUMNS))
            st.write("Use datas YYYY-MM-DD, vendas em kg e números com ponto decimal. "
                     "São necessários 28 dias civis completos por corte, com encerramento na mesma data "
                     "e metadados do catálogo do iaCarne.")
        upload = st.file_uploader("Carregar histórico CSV", type=["csv"], max_upload_size=MAX_UPLOAD_MB)
        if upload is None:
            st.info("Selecione um CSV para consultar o histórico e solicitar a previsão.")
            st.stop()
        contents = upload.getvalue()
        if len(contents) > MAX_UPLOAD_MB * 1024 * 1024:
            st.error("O CSV deve ter no máximo 5 MiB.")
            st.stop()
        source = io.BytesIO(contents)
    else:
        st.info("Demonstração histórica com dados até 31/08/2026 e previsão para 01/09/2026.")

    try:
        history = read_history(source)
    except (OSError, ValueError) as exc:
        st.error(f"Não foi possível usar este histórico. {exc}")
        st.stop()

    cuts = history[["produto_id", "corte"]].drop_duplicates().sort_values("corte")
    labels = dict(zip(cuts.produto_id, cuts.corte))
    product = st.selectbox("Corte bovino", options=list(labels), format_func=labels.__getitem__)
    selected = history.loc[history.produto_id.eq(product)].copy()
    recent = selected.tail(28)

    if st.button("Prever próximo dia", type="primary"):
        try:
            forecast = predict_next_day(selected).iloc[0]
        except (OSError, ValueError) as exc:
            st.error(f"Não foi possível gerar a previsão. {exc}")
        else:
            day = pd.Timestamp(forecast.data_previsao).strftime("%d/%m/%Y")
            st.subheader(f"Previsão para {day}")
            st.caption(f"{forecast.corte} · {forecast.modelo} · versão {forecast.versao_modelo} · "
                       "Treinado com dados sintéticos")
            ridge, baseline = st.columns(2)
            ridge.metric("Ridge v1", f"{forecast.previsao_ridge_kg:.3f} kg".replace(".", ","))
            baseline.metric("Referência sazonal D−7", f"{forecast.baseline_d7_kg:.3f} kg".replace(".", ","))

    st.subheader("Histórico dos últimos 28 dias")
    start, end = (recent.data.iloc[index].strftime("%d/%m/%Y") for index in (0, -1))
    st.caption(f"{labels[product]} · {start} a {end}")
    st.vega_lite_chart(recent[["data", TARGET]], {
        "mark": "line",
        "encoding": {
            "x": {"field": "data", "type": "temporal", "title": "Data",
                  "scale": {"type": "utc", "nice": False},
                  "axis": {"format": "%d/%m", "tickCount": 7, "labelAngle": 0, "labelOverlap": True}},
            "y": {"field": TARGET, "type": "quantitative", "title": "Vendas observadas (kg)"},
        },
    }, width="stretch")
    st.dataframe(recent[["data", TARGET]], hide_index=True, height=220, column_config={
        "data": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
        TARGET: st.column_config.NumberColumn("Venda observada (kg)", format="%.2f"),
    })


if __name__ == "__main__":
    main()
