# Sprint 4 — Insights da EDA avançada

## Objetivo e bases
Analisar atributos para prever venda observada por produto no dia seguinte, sem treinar modelos.
Os dados são sintéticos. A matriz `data/modeling/iacarne_modelagem.csv` tem 7.077 registros,
21 produtos e 337 dias por produto, de 29/09/2025 a 31/08/2026.
São 17 colunas, zero nulos e zero duplicatas produto/data. Os hashes foram conferidos contra os relatórios.
A base tratada tem 7.665 registros, de 01/09/2025 a 31/08/2026,
e foi usada para o contexto operacional e a conferência das defasagens. Não foi usado ground truth.

## Distribuição e cortes
A venda média é 14,95 kg por produto/dia; a mediana é 13,35 kg.
O percentil 95 é 28,38 kg.
Acém apresenta a maior média diária (28,55 kg),
e Filé Mignon a menor (7,59 kg).
São médias diárias, não volumes acumulados. A média do total diário dos 21 cortes é 314,03 kg.

## Comportamento temporal
Sábado tem a maior média por produto/dia (21,15 kg)
e Segunda a menor (11,46 kg).
Entre os meses com pelo menos 28 dias observados, 2025-12 tem a maior média
(18,31 kg por produto/dia) e 2026-02 a menor (13,59 kg).
Setembro/2025 tem somente dois dias após o aquecimento; sua média não representa o mês completo.
A base contém apenas um ano sintético, sem evidência de repetição anual em dados reais.

## Lags e médias móveis
Os históricos foram conferidos contra a base tratada: apenas valores até D-1, por produto.
As médias usam janela completa de 7, 14 ou 28 dias após shift(1).

| Feature | Pearson global com alvo | Pearson após centrar por produto |
|---|---:|---:|
| venda_lag_1 | 0,7795 | 0,3985 |
| venda_lag_7 | 0,9148 | 0,7680 |
| venda_lag_14 | 0,9036 | 0,7378 |
| venda_lag_28 | 0,8859 | 0,6902 |
| venda_media_7 | 0,8107 | 0,2738 |
| venda_media_14 | 0,8102 | 0,2633 |
| venda_media_28 | 0,8046 | 0,2153 |

A centralização subtrai a média de cada produto somente para esta análise descritiva.
Ela não é uma transformação de treino e não altera o dataset.
O maior coeficiente após centralização entre os lags é de `venda_lag_7`
(0,7680); entre as médias, de `venda_media_7`
(0,2738).
Esses atributos são candidatos a testar, não vencedores comprovados.
A diferença entre os coeficientes globais e centrados mostra a influência dos níveis de venda dos produtos.
Os históricos também podem ser redundantes entre si; a correlação não substitui validação temporal.

## Ruptura e promoção
Na base tratada completa, há 1242 observações com ruptura em 7665
(16,20%). A venda média é 17,16 kg
com ruptura e 14,47 kg sem ruptura.
Esses grupos têm composições distintas. Não se infere efeito causal: em ruptura,
a venda pode ser censurada pela disponibilidade e não revela a demanda não atendida.
Ruptura de D não entra nas features de D.

Com promoção, a média observada é 16,73 kg;
sem promoção, 14,77 kg.
Os preços médios agrupados são R$ 41,84/kg e
R$ 48,26/kg, respectivamente.
Não são comparações controladas por corte/data e não medem causalidade ou elasticidade.
Preço, promoção e desconto permanecem excluídos: disponibilidade antecipada não comprovada.

## Features para a Sprint 5
- `produto_id`
- `corte`
- `categoria_anatomica`
- `perfil_uso`
- `dia_semana`
- `fim_de_semana`
- `mes`
- `semana_ano`
- `venda_lag_1`
- `venda_lag_7`
- `venda_lag_14`
- `venda_lag_28`
- `venda_media_7`
- `venda_media_14`
- `venda_media_28`

`data` é referência temporal e `quantidade_vendida_kg` é o alvo, nunca feature contemporânea.
As categorias ainda precisam de codificação no pipeline de ML. Produto e nome do corte são redundantes;
a manutenção de ambos segue o contrato inicial e poderá ser avaliada em experimentos posteriores.
Receita, custo total, margem, perdas, saldo final e ruptura do próprio dia permanecem fora da matriz.

## Limitações e próximos cuidados
Dados sintéticos, apenas um ano e padrões influenciados pelas premissas da simulação.
Não há dados reais autorizados, inferência causal, ganho operacional ou redução de desperdício comprovados.
Nenhum modelo, baseline ou divisão treino/teste foi criado nesta etapa.
A EDA explorou todo o período; não constitui avaliação independente de um modelo.
Na Sprint 5, definir avaliação temporal, manter datas futuras fora do treino e ajustar codificações
somente no treino. Em avaliação diária, atualizar históricos apenas quando a venda anterior estiver disponível;
prever vários dias de uma vez exigiria outro protocolo. Não usar resultados de D para prever D.

Foram produzidos 9 gráficos em `reports/sprint4/figures/`.
