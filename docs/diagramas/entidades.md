# Modelo E/R conceitual

```mermaid
erDiagram
    PRODUTO ||--o{ OPERACAO_DIARIA : possui
    PRODUTO {
        string produto_id PK
        string corte
        string categoria_anatomica
        string perfil_uso
    }
    OPERACAO_DIARIA {
        string registro_id PK
        date data
        string produto_id FK
        decimal preco_venda_kg
        boolean promocao
        decimal desconto_pct
        decimal estoque_inicial_kg
        decimal entrada_kg
        decimal estoque_disponivel_kg
        decimal quantidade_vendida_kg
        decimal perda_kg
        decimal estoque_final_kg
        boolean ruptura_estoque
        decimal receita_bruta_rs
        decimal custo_estimado_kg
        decimal custo_total_estimado_rs
        decimal margem_bruta_estimada_rs
        string evento_calendario
    }
```

Modelo adaptado à granularidade oficial: operação diária agregada por corte, não transação ou item de cupom. `(data, produto_id)` também é chave única. Promoção é atributo diário: não existe identificador ou campanha independente no schema, portanto não se cria entidade artificial. Vendas e saldos compartilham a mesma observação diária.

O armazenamento físico da Fase 1 é CSV desnormalizado. Campos de calendário são derivados de `data`; controles de qualidade acrescentados pelo ETL não representam entidades. Este diagrama não propõe migração do banco da aplicação existente.
