from __future__ import annotations

import csv
import json
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 26092026
VERSION = "1.0.0"

cuts = [
    ("pescoco", "Pescoço", "dianteiro", "cozimento", 31.90, 8.0, 0.018),
    ("acem", "Acém", "dianteiro", "dia_a_dia", 36.95, 26.0, 0.014),
    ("ponta_de_peito", "Ponta de Peito", "dianteiro", "cozimento", 36.90, 10.0, 0.017),
    ("paleta", "Paleta", "dianteiro", "dia_a_dia", 38.90, 16.0, 0.015),
    ("musculo_dianteiro", "Músculo Dianteiro", "dianteiro", "cozimento", 34.90, 13.0, 0.016),
    ("cupim", "Cupim", "dianteiro", "churrasco", 49.90, 9.0, 0.019),
    ("capa_file", "Capa de Filé", "dianteiro", "churrasco", 42.90, 9.0, 0.017),
    ("file_agulha", "Filé de Agulha", "dianteiro", "dia_a_dia", 39.90, 11.0, 0.016),
    ("file_simples", "Filé Simples", "traseiro", "dia_a_dia", 44.90, 12.0, 0.014),
    ("picanha", "Picanha", "traseiro", "churrasco", 79.90, 11.0, 0.018),
    ("file_mignon", "Filé Mignon", "traseiro", "premium", 99.90, 7.0, 0.020),
    ("alcatra", "Alcatra", "traseiro", "churrasco", 49.90, 18.0, 0.014),
    ("fraldinha", "Fraldinha", "traseiro", "churrasco", 44.90, 13.0, 0.016),
    ("coxao_mole", "Coxão Mole", "traseiro", "dia_a_dia", 46.90, 20.0, 0.013),
    ("lagarto", "Lagarto", "traseiro", "dia_a_dia", 44.90, 12.0, 0.014),
    ("costelao", "Costelão", "costela", "churrasco", 27.90, 18.0, 0.020),
    ("maminha", "Maminha", "traseiro", "churrasco", 54.90, 12.0, 0.016),
    ("coxao_duro", "Coxão Duro", "traseiro", "dia_a_dia", 40.90, 14.0, 0.014),
    ("vazio", "Vazio", "traseiro", "churrasco", 42.90, 10.0, 0.018),
    ("patinho", "Patinho", "traseiro", "dia_a_dia", 49.90, 22.0, 0.013),
    ("musculo_traseiro", "Músculo Traseiro", "traseiro", "cozimento", 34.90, 12.0, 0.016),
]

cost_ratio_by_category = {"dianteiro": 0.68, "traseiro": 0.70, "costela": 0.66}
weekday_factor = {0: 0.82, 1: 0.88, 2: 0.93, 3: 1.00, 4: 1.18, 5: 1.42, 6: 1.10}
month_factor = {1: 0.95, 2: 0.94, 3: 0.98, 4: 1.00, 5: 0.98, 6: 1.02, 7: 1.03, 8: 1.00, 9: 0.99, 10: 1.03, 11: 1.07, 12: 1.23}

special_days = {
    date(2025, 9, 7): ("Independência do Brasil", 1.08),
    date(2025, 10, 12): ("Nossa Senhora Aparecida", 1.08),
    date(2025, 11, 2): ("Finados", 1.04),
    date(2025, 11, 15): ("Proclamação da República", 1.10),
    date(2025, 11, 20): ("Consciência Negra", 1.10),
    date(2025, 12, 24): ("Véspera de Natal", 1.45),
    date(2025, 12, 25): ("Natal", 1.18),
    date(2025, 12, 31): ("Véspera de Ano Novo", 1.50),
    date(2026, 1, 1): ("Confraternização Universal", 1.12),
    date(2026, 4, 3): ("Sexta-feira Santa", 0.82),
    date(2026, 4, 21): ("Tiradentes", 1.08),
    date(2026, 5, 1): ("Dia do Trabalho", 1.10),
}

SOURCES = [
    {
        "fonte": "Procon Joinville — Pesquisa de Preços Churrasco, maio/2026",
        "url": "https://www.joinville.sc.gov.br/wp-content/uploads/2026/05/Pesquisa-de-Precos-Churrasco-mai-2026.pdf",
    },
    {
        "fonte": "Epagri/Cepa — Preços Agrícolas",
        "url": "https://cepa.epagri.sc.gov.br/index.php/mercado-agricola/",
    },
    {
        "fonte": "IBGE — Pesquisa Trimestral do Abate de Animais, 1º tri/2026",
        "url": "https://agenciadenoticias.ibge.gov.br/agencia-sala-de-imprensa/2013-agencia-de-noticias/releases/47166-brasil-registra-alta-no-abate-de-bovinos-frangos-e-suinos-no-1-trimestre-em-comparacao-com-2025",
    },
    {
        "fonte": "UNEP — Relatório do Índice de Desperdício de Alimentos 2024",
        "url": "https://www.unep.org/pt-br/resources/publicacoes/relatorio-do-indice-de-desperdicio-de-alimentos-2024",
    },
]

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def months_since_start(d: date, start: date) -> int:
    return (d.year - start.year) * 12 + d.month - start.month

def generate(out_dir: str | Path = ".") -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(SEED)

    start = date(2025, 9, 1)
    end = date(2026, 8, 31)
    prev_closing = {c[0]: 0.0 for c in cuts}
    rows = []
    gt = []

    current = start
    while current <= end:
        dow = current.weekday()
        is_weekend = int(dow >= 5)
        event_name, event_factor = special_days.get(current, ("", 1.0))
        m_factor = month_factor[current.month]
        price_trend = 1.0 + 0.007 * months_since_start(current, start)

        for cut_id, cut_name, category, use, price_ref, base_demand, base_loss in cuts:
            promo_prob = 0.075 if not is_weekend else 0.045
            promocao = rng.random() < promo_prob
            discount = rng.uniform(0.08, 0.16) if promocao else 0.0

            price_noise = rng.gauss(0, 0.025)
            price = max(15.0, price_ref * price_trend * (1 + price_noise) * (1 - discount))
            price = round(price, 2)

            factor = weekday_factor[dow] * m_factor * event_factor

            if use == "churrasco":
                if dow == 4:
                    factor *= 1.12
                elif dow == 5:
                    factor *= 1.28
                elif dow == 6:
                    factor *= 1.12
                if current.month == 12:
                    factor *= 1.12

            elasticity = 0.95 if use == "premium" else 0.55
            relative_price = price / (price_ref * price_trend)
            price_factor = clamp(1 - elasticity * (relative_price - 1), 0.78, 1.22)
            promo_factor = rng.uniform(1.12, 1.30) if promocao else 1.0
            stochastic = max(0.55, rng.gauss(1.0, 0.11))
            latent_demand = base_demand * factor * price_factor * promo_factor * stochastic

            opening = prev_closing[cut_id]
            expected = base_demand * weekday_factor[dow] * m_factor
            safety = rng.uniform(1.12, 1.38)
            target_available = expected * safety
            incoming = max(0.0, target_available - opening + rng.gauss(0, base_demand * 0.10))
            incoming = round(max(0.0, incoming), 2)
            available = opening + incoming

            sold = round(max(0.0, min(latent_demand, available)), 2)

            leftover = max(0.0, available - sold)
            seasonal_loss = 1.10 if current.month in (12, 1, 2) else 1.0
            loss_rate = clamp(base_loss * seasonal_loss * rng.gauss(1.0, 0.22), 0.002, 0.05)
            loss = round(min(leftover, leftover * loss_rate), 2)
            closing = round(max(0.0, leftover - loss), 2)
            stockout = int(latent_demand > available + 0.01)

            cost_ratio = cost_ratio_by_category.get(category, 0.69)
            cost_kg = round(price_ref * price_trend * cost_ratio * (1 + rng.gauss(0, 0.018)), 2)
            revenue = round(sold * price, 2)
            cost_total = round(sold * cost_kg, 2)
            margin = round(revenue - cost_total, 2)

            record_id = f"{current.isoformat()}_{cut_id}"
            row = {
                "registro_id": record_id,
                "data": current.isoformat(),
                "produto_id": cut_id,
                "corte": cut_name,
                "categoria_anatomica": category,
                "perfil_uso": use,
                "preco_venda_kg": price,
                "promocao": int(promocao),
                "desconto_pct": round(discount * 100, 1),
                "estoque_inicial_kg": round(opening, 2),
                "entrada_kg": incoming,
                "estoque_disponivel_kg": round(available, 2),
                "quantidade_vendida_kg": sold,
                "perda_kg": loss,
                "estoque_final_kg": closing,
                "ruptura_estoque": stockout,
                "receita_bruta_rs": revenue,
                "custo_estimado_kg": cost_kg,
                "custo_total_estimado_rs": cost_total,
                "margem_bruta_estimada_rs": margin,
                "dia_semana": ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"][dow],
                "fim_de_semana": is_weekend,
                "evento_calendario": event_name,
                "mes": current.month,
                "ano": current.year,
                "semana_ano": current.isocalendar().week,
            }
            rows.append(row)
            gt.append({
                "registro_id": record_id,
                "data": current.isoformat(),
                "produto_id": cut_id,
                "demanda_latente_kg": round(latent_demand, 2),
                "quantidade_vendida_kg": sold,
                "estoque_disponivel_kg": round(available, 2),
                "ruptura_estoque": stockout,
            })
            prev_closing[cut_id] = closing

        current += timedelta(days=1)

    # Dataset bruto com defeitos controlados para o ETL.
    raw = [dict(r) for r in rows]
    n = len(raw)

    for idx in rng.sample(range(n), k=max(1, round(n * 0.005))):
        val = raw[idx]["corte"]
        raw[idx]["corte"] = ("  " + val.upper() + "  ") if rng.random() < 0.5 else val.lower()

    for idx in rng.sample(range(n), k=max(1, round(n * 0.003))):
        raw[idx]["estoque_inicial_kg"] = ""

    for idx in rng.sample(range(n), k=max(1, round(n * 0.0025))):
        raw[idx]["preco_venda_kg"] = f"{float(raw[idx]['preco_venda_kg']):.2f}".replace(".", ",")

    dup_count = max(1, round(n * 0.002))
    for idx in rng.sample(range(n), k=dup_count):
        raw.append(dict(raw[idx]))
    rng.shuffle(raw)

    raw_path = out / "iacarne_vendas_bruto.csv"
    gt_path = out / "iacarne_ground_truth_auditoria.csv"
    spec_path = out / "iacarne_dataset_especificacao.json"

    headers = list(rows[0].keys())
    with raw_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(raw)

    gt_headers = list(gt[0].keys())
    with gt_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=gt_headers)
        writer.writeheader()
        writer.writerows(gt)

    spec = {
        "projeto": "iaCarne",
        "versao_dataset": VERSION,
        "natureza": "sintetico_calibrado_por_referencias_reais",
        "periodo": {"inicio": start.isoformat(), "fim": end.isoformat()},
        "granularidade": "1 linha por dia por corte bovino",
        "linhas_base": len(rows),
        "linhas_brutas_com_duplicatas": len(raw),
        "quantidade_cortes": len(cuts),
        "seed": SEED,
        "target_futuro_ml": "quantidade_vendida_kg",
        "aviso_modelagem": (
            "Venda observada pode ser censurada por ruptura. "
            "demanda_latente_kg existe somente no arquivo de auditoria e não deve ser usada como feature."
        ),
        "fontes": SOURCES,
    }
    spec_path.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Gerados: {raw_path}, {gt_path}, {spec_path}")
    print(f"Linhas base: {len(rows)} | Linhas bruto: {len(raw)} | Seed: {SEED}")

if __name__ == "__main__":
    generate(Path(__file__).resolve().parent)
