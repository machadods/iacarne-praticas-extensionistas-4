# iaCarne — Dataset sintético calibrado

## Finalidade

Este conjunto foi criado para a **Entrega Parcial 1 de Práticas Extensionistas IV** como base de desenvolvimento de:

- pipeline ETL;
- dataset tratado;
- análise exploratória inicial (EDA);
- futura modelagem de previsão de demanda.

## Declaração de origem

Os registros **não são vendas reais de nenhum estabelecimento**.

A base é sintética e reproduzível, construída a partir de:
1. preços públicos observados em Santa Catarina;
2. informações oficiais sobre o mercado bovino;
3. literatura pública sobre mensuração e redução de desperdício de alimentos;
4. premissas de simulação operacional explicitamente separadas dos fatos externos.

## Período e granularidade

- Período: 01/09/2025 a 31/08/2026
- Cortes: 21
- Granularidade: 1 linha por dia por corte
- Observações-base: 7.665
- Seed: 26092026

## Arquivos

### `iacarne_vendas_bruto.csv`
Entrada oficial do ETL. Possui defeitos controlados:
- duplicatas;
- pequenas inconsistências de nome;
- alguns valores ausentes em estoque inicial;
- alguns preços com vírgula decimal.

Esses erros foram introduzidos propositalmente para que a etapa de limpeza seja verificável.

### `iacarne_ground_truth_auditoria.csv`
Arquivo exclusivo de auditoria da simulação.

Contém `demanda_latente_kg`, que representa a demanda antes da limitação pelo estoque.

**Não usar como feature no modelo acadêmico.**

### `iacarne_dataset_especificacao.json`
Metadados, seed, período e fontes.

### `generate_iacarne_dataset.py`
Gerador completo e reproduzível da versão 1.0.0.

### `iacarne_dataset_v1.xlsx`
Workbook de inspeção com:
- resumo;
- dados brutos;
- dicionário;
- premissas e fontes;
- ground truth de auditoria.

## Target futuro de ML

`quantidade_vendida_kg`

Atenção: em dias com ruptura, a venda observada pode ser inferior à demanda real. Isso deve ser discutido na fase de modelagem.

## Leakage

Para previsão feita antes da abertura/venda do dia, não usar como features:
- `perda_kg`;
- `estoque_final_kg`;
- `receita_bruta_rs`;
- `custo_total_estimado_rs`;
- `margem_bruta_estimada_rs`;
- `ruptura_estoque`.

Essas variáveis dependem total ou parcialmente do resultado do próprio dia.

## Sustentabilidade

A base permite medir perdas em kg e testar futuramente se melhor planejamento de demanda e estoque pode reduzir excedentes e desperdício. O projeto não declara redução ambiental já comprovada; isso é um impacto potencial a ser validado.

## Fontes públicas de calibração

- Procon Joinville — pesquisa de preços de churrasco (mai/2026):
  https://www.joinville.sc.gov.br/wp-content/uploads/2026/05/Pesquisa-de-Precos-Churrasco-mai-2026.pdf
- Epagri/Cepa — preços agrícolas:
  https://cepa.epagri.sc.gov.br/index.php/mercado-agricola/
- IBGE — Pesquisa Trimestral do Abate de Animais:
  https://agenciadenoticias.ibge.gov.br/agencia-sala-de-imprensa/2013-agencia-de-noticias/releases/47166-brasil-registra-alta-no-abate-de-bovinos-frangos-e-suinos-no-1-trimestre-em-comparacao-com-2025
- UNEP — Relatório do Índice de Desperdício de Alimentos 2024:
  https://www.unep.org/pt-br/resources/publicacoes/relatorio-do-indice-de-desperdicio-de-alimentos-2024
