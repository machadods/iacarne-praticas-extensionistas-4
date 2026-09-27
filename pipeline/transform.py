"""Regras determinísticas e validação da operação diária sintética."""

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
import unicodedata


TEXT = {"registro_id", "data", "produto_id", "corte", "categoria_anatomica", "perfil_uso", "dia_semana", "evento_calendario"}
INTEGER = {"promocao", "ruptura_estoque", "fim_de_semana", "mes", "ano", "semana_ano"}
DAYS = ["segunda", "terca", "quarta", "quinta", "sexta", "sabado", "domingo"]
CENT = Decimal("0.01")


def normalized(value):
    return unicodedata.normalize("NFC", value.strip()).casefold()


def transform(rows, contract, spec):
    report = {
        "versao_dataset": spec["versao_dataset"],
        "linhas_entrada": len(rows),
        "nulos_entrada": {k: sum(r[k] == "" for r in rows) for k in contract["colunas"]},
        "duplicatas_removidas": 0,
        "registros_rejeitados": 0,
        "transformacoes": {},
        "correcoes": [],
    }
    unique = {}
    for row in rows:
        key = row["registro_id"]
        if key in unique:
            if row != unique[key]:
                raise ValueError(f"{key}: duplicata conflitante")
            report["duplicatas_removidas"] += 1
        else:
            unique[key] = row
    counters = Counter()
    out = []

    def correction(row, field, old, new, rule):
        counters[rule] += 1
        report["correcoes"].append({"registro_id": row["registro_id"], "campo": field, "antes": str(old), "depois": str(new), "regra": rule})

    def require(condition, row, message):
        if not condition:
            raise ValueError(f"{row['registro_id']}: {message}")

    for original in unique.values():
        row = dict(original)
        try:
            day = date.fromisoformat(row["data"])
        except ValueError as exc:
            raise ValueError(f"{row['registro_id']}: data inválida") from exc
        require(day.isoformat() == row["data"], row, "data fora do formato ISO YYYY-MM-DD")
        product = contract["produtos"].get(row["produto_id"])
        require(product is not None, row, "produto desconhecido")
        require(row["registro_id"] == f"{day.isoformat()}_{row['produto_id']}", row, "chave incompatível com data/produto")
        for field, expected in product.items():
            if field == "corte":
                require(normalized(row[field]) == normalized(expected), row, "nome não corresponde ao produto")
                if row[field] != expected:
                    correction(row, field, row[field], expected, "nomes_padronizados")
                    row[field] = expected
            else:
                require(row[field] == expected, row, f"{field} incompatível com produto")

        missing_opening = row["estoque_inicial_kg"] == ""
        row["estoque_inicial_reconstruido"] = int(missing_opening)
        for field in contract["colunas"]:
            if field in TEXT or (field == "estoque_inicial_kg" and missing_opening):
                continue
            value = row[field]
            if field == "preco_venda_kg" and "," in value:
                require(value.count(",") == 1 and "." not in value, row, "preço ambíguo")
                correction(row, field, value, value.replace(",", "."), "precos_convertidos")
                value = value.replace(",", ".")
            try:
                number = Decimal(value)
            except InvalidOperation as exc:
                raise ValueError(f"{row['registro_id']}: {field} numérico inválido ou ausente") from exc
            require(number.is_finite(), row, f"{field} não finito")
            if field in INTEGER:
                require(number == number.to_integral_value(), row, f"{field} deve ser inteiro")
                row[field] = int(number)
            else:
                require(number == number.quantize(CENT), row, f"{field} excede precisão de duas casas")
                row[field] = number
            if field != "margem_bruta_estimada_rs":
                require(number >= 0, row, f"{field} negativo")
        if missing_opening:
            value = row["estoque_disponivel_kg"] - row["entrada_kg"]
            require(value >= 0, row, "estoque inicial reconstruído negativo")
            correction(row, "estoque_inicial_kg", "", value, "estoques_reconstruidos")
            row["estoque_inicial_kg"] = value

        for field in ("promocao", "ruptura_estoque", "fim_de_semana"):
            require(row[field] in (0, 1), row, f"{field} deve ser 0 ou 1")
        require(row["preco_venda_kg"] > 0 and row["custo_estimado_kg"] > 0, row, "preço/custo deve ser positivo")
        require(0 <= row["desconto_pct"] <= 100, row, "desconto fora de 0 a 100")
        require((row["promocao"] == 0 and row["desconto_pct"] == 0) or (row["promocao"] == 1 and 8 <= row["desconto_pct"] <= 16), row, "promoção incompatível com desconto da versão 1.0.0")
        balances = [
            (row["estoque_inicial_kg"] + row["entrada_kg"], row["estoque_disponivel_kg"], "estoque disponível"),
            (row["estoque_disponivel_kg"] - row["quantidade_vendida_kg"] - row["perda_kg"], row["estoque_final_kg"], "estoque final"),
        ]
        for computed, observed, label in balances:
            require(computed == observed, row, f"balanço inconsistente: {label}")
        money = [
            (row["quantidade_vendida_kg"] * row["preco_venda_kg"], row["receita_bruta_rs"], "receita"),
            (row["quantidade_vendida_kg"] * row["custo_estimado_kg"], row["custo_total_estimado_rs"], "custo total"),
            (row["receita_bruta_rs"] - row["custo_total_estimado_rs"], row["margem_bruta_estimada_rs"], "margem"),
        ]
        for computed, observed, label in money:
            require(abs(computed - observed) <= CENT, row, f"valor inconsistente: {label}")
        require(row["ruptura_estoque"] == 0 or row["estoque_final_kg"] == 0, row, "ruptura com saldo final positivo")
        calendar = {"dia_semana": DAYS[day.weekday()], "fim_de_semana": int(day.weekday() >= 5), "mes": day.month, "ano": day.year, "semana_ano": day.isocalendar().week}
        for field, expected in calendar.items():
            if row[field] != expected:
                correction(row, field, row[field], expected, "calendario_corrigido")
                row[field] = expected
        row["ano_semana_iso"] = day.isocalendar().year
        out.append(row)

    out.sort(key=lambda r: (r["data"], r["produto_id"]))
    start, end = (date.fromisoformat(spec["periodo"][k]) for k in ("inicio", "fim"))
    expected_keys = {(start + timedelta(days=i)).isoformat() + "_" + p for i in range((end-start).days+1) for p in contract["produtos"]}
    if set(unique) != expected_keys or len(out) != spec["linhas_base"]:
        raise ValueError("Cobertura incompleta ou excedente para o período/produtos da versão oficial")
    closing = {}
    for row in out:
        product = row["produto_id"]
        require(row["estoque_inicial_kg"] == closing.get(product, Decimal(0)), row, "descontinuidade do estoque entre dias")
        closing[product] = row["estoque_final_kg"]
    report["transformacoes"] = {key: counters[key] for key in ["nomes_padronizados", "precos_convertidos", "estoques_reconstruidos", "calendario_corrigido"]}
    report["correcoes"].sort(key=lambda r: (r["registro_id"], r["campo"]))
    report["linhas_saida"] = len(out)
    report["colunas_saida"] = list(out[0])
    report["nulos_saida"] = {k: sum(r[k] == "" for r in out) for k in out[0]}
    return out, report
