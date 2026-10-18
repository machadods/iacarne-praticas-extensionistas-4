"""Preparar a base de modelagem: python -m modeling.dataset."""

import hashlib
import io
import json
import math
import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from modeling.features import FEATURES, TARGET, build_features


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("data/processed/iacarne_vendas_tratado.csv")
DESTINATION = Path("data/modeling")
CSV_NAME = "iacarne_modelagem.csv"
JSON_NAME = "relatorio_modelagem.json"
HISTORY = tuple(name for name in FEATURES if name.startswith(("venda_lag_", "venda_media_")))
LOOKBACK = max(int(name.rsplit("_", 1)[1]) for name in HISTORY)


def _checked_paths(root):
    root = Path(root).resolve()
    source = root / SOURCE
    destination = root / DESTINATION
    # Caminhos fixos e sem redirecionamento por links protegem os originais.
    for path in (source, destination, destination / CSV_NAME, destination / JSON_NAME):
        if path.is_symlink() or path.resolve() != path:
            raise ValueError(f"Caminho protegido: {path}")
    return source, destination


def _publish(destination, contents):
    """Preparar ambos os arquivos antes de substituir; reverter erro de escrita.

    A reversão cobre exceções de escrita, não interrupção abrupta do processo.
    Não executar duas preparações simultaneamente no mesmo destino.
    """
    destination.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".preparacao-", dir=destination) as temporary:
        staging = Path(temporary)
        previous = {}
        for name, content in contents.items():
            target = destination / name
            previous[name] = target.read_bytes() if target.exists() else None
            (staging / name).write_bytes(content)
            if previous[name] is not None:
                (staging / (name + ".anterior")).write_bytes(previous[name])
        replaced = []
        try:
            for name in contents:
                os.replace(staging / name, destination / name)
                replaced.append(name)
        except OSError:
            for name in reversed(replaced):
                if previous[name] is None:
                    (destination / name).unlink()
                else:
                    os.replace(staging / (name + ".anterior"), destination / name)
            raise


def prepare_dataset(root=ROOT):
    """Ler a fonte fixa e publicar CSV/JSON; root permite testes isolados."""
    source, destination = _checked_paths(root)
    source_bytes = source.read_bytes()
    frame = pd.read_csv(io.BytesIO(source_bytes), keep_default_na=False)
    featured = build_features(frame)
    missing_history = featured[list(HISTORY)].isna().any(axis=1)
    warmup = featured.groupby("produto_id", sort=False).cumcount().lt(LOOKBACK)
    if not missing_history.equals(warmup):
        raise ValueError("Ausência de histórico fora do aquecimento esperado")
    result = featured.loc[~missing_history].reset_index(drop=True)
    if result.empty or set(result.produto_id) != set(featured.produto_id):
        raise ValueError("Histórico insuficiente: todos os produtos precisam superar o aquecimento")
    if list(result.columns) != ["data", TARGET, *FEATURES]:
        raise ValueError("Colunas de modelagem diferentes do contrato")
    if result.isna().any().any() or result.duplicated(["produto_id", "data"]).any():
        raise ValueError("Saída contém nulos ou chaves duplicadas")
    for column in (TARGET, *HISTORY):
        if not result[column].map(math.isfinite).all():
            raise ValueError(f"Valor não finito na saída: {column}")

    report = {
        "versao_preparacao": "1.0.0",
        "arquivo_fonte": SOURCE.as_posix(),
        "hash_sha256_fonte": hashlib.sha256(source_bytes).hexdigest(),
        "target": TARGET,
        "natureza_dados": "sinteticos",
        "objetivo": "Previsão de venda observada, não de demanda verdadeira.",
        "granularidade": "produto/dia",
        "horizonte_conceitual": "Um dia à frente, com histórico disponível até D-1.",
        "registros_entrada": len(featured),
        "registros_saida": len(result),
        "registros_removidos_aquecimento": int(missing_history.sum()),
        "produtos": int(result.produto_id.nunique()),
        "data_minima_entrada": featured.data.min().strftime("%Y-%m-%d"),
        "data_maxima_entrada": featured.data.max().strftime("%Y-%m-%d"),
        "data_minima_modelagem": result.data.min().strftime("%Y-%m-%d"),
        "data_maxima_modelagem": result.data.max().strftime("%Y-%m-%d"),
        "maior_lag_dias": LOOKBACK,
        "aquecimento_dias_por_produto": LOOKBACK,
        "features": list(FEATURES),
        "features_condicionais_excluidas": [
            "estoque_inicial_kg", "estoque_disponivel_kg", "entrada_kg",
            "preco_venda_kg", "promocao", "desconto_pct", "custo_estimado_kg", "evento_calendario",
        ],
        "features_excluidas_por_leakage": [
            TARGET, "receita_bruta_rs", "custo_total_estimado_rs",
            "margem_bruta_estimada_rs", "perda_kg", "estoque_final_kg", "ruptura_estoque",
        ],
        "observacao_target": "O alvo de D é mantido como resposta, nunca como feature de D.",
        "colunas_controle_excluidas": ["registro_id", "estoque_inicial_reconstruido"],
        "observacao_ruptura": "As vendas observadas podem ser limitadas pela disponibilidade de estoque.",
        "observacao_dados_reais": "Dados reais ainda dependem de autorização e não fazem parte desta base.",
    }
    csv_bytes = result.to_csv(index=False, date_format="%Y-%m-%d", lineterminator="\n").encode("utf-8")
    report["hash_sha256_modelagem"] = hashlib.sha256(csv_bytes).hexdigest()
    json_bytes = (json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    _checked_paths(root)
    _publish(destination, {CSV_NAME: csv_bytes, JSON_NAME: json_bytes})
    return report


def main():
    try:
        report = prepare_dataset()
    except (ValueError, OSError) as exc:
        raise SystemExit(f"Falha na preparação: {exc}") from exc
    print("Dataset de modelagem preparado.")
    print(f"Entrada: {report['registros_entrada']} registros")
    print(f"Saída: {report['registros_saida']} registros")
    print(f"Produtos: {report['produtos']}")
    start = pd.Timestamp(report["data_minima_modelagem"]).strftime("%d/%m/%Y")
    end = pd.Timestamp(report["data_maxima_modelagem"]).strftime("%d/%m/%Y")
    print(f"Período: {start} a {end}")


if __name__ == "__main__":
    main()
