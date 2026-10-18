# Sprint 4 — EDA avançada e engenharia de atributos

## 1. Objetivo

Preparar uma matriz reproduzível para a futura etapa de Machine Learning e aprofundar a análise dos atributos temporais. A Sprint 4 foi concluída tecnicamente; não inclui modelo treinado, baseline, divisão treino/teste ou dashboard. Isso não representa aprovação institucional ou validação com usuário.

## 2. Ponto de partida

A Fase 1 forneceu ETL, EDA inicial e uma base tratada com 7.665 registros, 21 cortes e 365 dias por produto, de 01/09/2025 a 31/08/2026. Os dados são sintéticos. Seus resultados históricos permanecem no [relatório da Entrega Parcial 1](validacao_entrega.md).

Os checkpoints técnicos da Sprint 4 são `cec4373` (atributos), `07e29d8` (matriz de modelagem) e `c3befee` (EDA avançada).

## 3. Definição do problema preditivo

O alvo é `quantidade_vendida_kg`, por produto e dia, com horizonte conceitual de um dia à frente. Para prever D, o histórico deve estar disponível até o fechamento de D-1. O calendário de D é conhecido antecipadamente.

O alvo representa venda observada. Em dias de ruptura, o estoque pode limitar a venda; não conhecemos a demanda que deixou de ser atendida.

## 4. Engenharia de atributos

A função `build_features()`, em `modeling/features.py`, recebe um DataFrame e devolve outro, sem modificar a entrada ou acessar arquivos. Valida datas, alvo, metadados, chave produto/data e continuidade diária. Ordena por produto e data antes dos cálculos.

| Grupo | Features |
|---|---|
| Identidade e contexto | `produto_id`, `corte`, `categoria_anatomica`, `perfil_uso` |
| Calendário | `dia_semana`, `fim_de_semana`, `mes`, `semana_ano` |
| Defasagens | `venda_lag_1`, `venda_lag_7`, `venda_lag_14`, `venda_lag_28` |
| Médias móveis | `venda_media_7`, `venda_media_14`, `venda_media_28` |

Os lags representam a venda do mesmo produto nos dias anteriores indicados. As médias usam `shift(1)` antes de `rolling`, com janelas completas de 7, 14 ou 28 dias. Assim, a venda de D não entra nas features históricas de D. O agrupamento por produto evita misturar históricos.

São 15 features. `data` é referência temporal e `quantidade_vendida_kg` é o alvo. As linhas sem histórico permanecem na função de atributos; o gerador da matriz remove somente o aquecimento. Não há preenchimento com valores futuros, codificação de categorias ou normalização.

## 5. Variáveis excluídas

### A. Resultados contemporâneos com leakage

`receita_bruta_rs`, `custo_total_estimado_rs`, `margem_bruta_estimada_rs`, `perda_kg`, `estoque_final_kg` e `ruptura_estoque` do próprio dia não são features. São resultados posteriores ao instante da previsão; receita e custo total também dependem da quantidade vendida. O alvo de D nunca é usado como feature de D.

### B. Variáveis condicionais

`preco_venda_kg`, `promocao`, `desconto_pct`, `estoque_inicial_kg`, `estoque_disponivel_kg`, `entrada_kg`, `custo_estimado_kg` e `evento_calendario` ficaram fora da matriz inicial. Seu uso futuro depende de comprovar disponibilidade antes da previsão e distinguir planejamento de resultado realizado.

`registro_id` e `estoque_inicial_reconstruido` são controles, não preditores. O ground truth permanece exclusivo de auditoria: somente o teste histórico confere a integridade do arquivo; nenhum código da Sprint 4 o usa para atributos, EDA, seleção ou avaliação.

## 6. Dataset final de modelagem

Comando: `python -m modeling.dataset`.

| Verificação | Resultado |
|---|---|
| Fonte | `data/processed/iacarne_vendas_tratado.csv` |
| Registros de entrada | 7.665 |
| Registros finais | 7.077 |
| Aquecimento removido | 588 registros: 28 dias por produto |
| Produtos | 21 |
| Registros finais por produto | 337 |
| Período final | 29/09/2025 a 31/08/2026 |
| Colunas | 17: data, alvo e 15 features |
| Nulos e duplicatas produto/data | Zero |
| Fonte | Preservada |
| Reprodução | CSV e JSON idênticos byte a byte sobre a mesma fonte |

Saídas: `data/modeling/iacarne_modelagem.csv` e `data/modeling/relatorio_modelagem.json`. O relatório registra o hash da fonte, períodos, contagens e exclusões, sem horário variável. A escrita valida os dados antes de publicar e reverte exceções de substituição; não garante recuperação após interrupção abrupta nem execução concorrente no mesmo destino.

## 7. EDA avançada

O [notebook 02](../notebooks/02_eda_avancada_features.ipynb) tem 33 células, sendo 16 de código, executadas de 1 a 16, sem outputs de erro. Produz nove gráficos em `reports/sprint4/figures/`. A síntese está em [insights.md](../reports/sprint4/insights.md), de onde vêm os valores abaixo.

| Resultado na matriz de modelagem | Valor |
|---|---|
| Venda média e mediana | 14,95 e 13,35 kg por produto/dia |
| Percentil 95 | 28,38 kg |
| Maior média diária por corte | Acém: 28,55 kg |
| Menor média diária por corte | Filé Mignon: 7,59 kg |
| Sábado e segunda-feira | 21,15 e 11,46 kg por produto/dia |
| Maior média entre meses completos | Dezembro/2025: 18,31 kg por produto/dia |

Setembro/2025 tem somente dois dias na matriz após o aquecimento; não representa o mês completo.

| Feature | Pearson global com alvo | Pearson após centrar por produto |
|---|---:|---:|
| `venda_lag_1` | 0,7795 | 0,3985 |
| `venda_lag_7` | 0,9148 | 0,7680 |
| `venda_lag_14` | 0,9036 | 0,7378 |
| `venda_lag_28` | 0,8859 | 0,6902 |
| `venda_media_7` | 0,8107 | 0,2738 |
| `venda_media_14` | 0,8102 | 0,2633 |
| `venda_media_28` | 0,8046 | 0,2153 |

A centralização subtrai a média de cada produto para a comparação descritiva; não é uma transformação aplicada à matriz ou ao treino. A redução dos coeficientes mostra a influência das diferenças de nível entre cortes nas correlações globais.

Na base tratada completa, 1.242 observações apresentam ruptura (16,20%). A média é 17,16 kg com ruptura e 14,47 kg sem ruptura. Os grupos têm composições diferentes; não se conclui que ruptura aumenta a venda.

Com promoção, a média observada é 16,73 kg, contra 14,77 kg sem promoção. Os preços médios agrupados são R$ 41,84/kg e R$ 48,26/kg, respectivamente. São comparações descritivas, sem controle por corte/data, inferência causal ou estimativa de elasticidade. Essas variáveis continuam fora da matriz inicial.

## 8. Insights para modelagem

O lag 7 parece um candidato importante, e as defasagens de 14 e 28 dias também apresentam associação. As médias móveis capturam o nível histórico, mas parte da associação global reflete diferenças entre produtos. A correlação não determina a seleção final de features nem comprova desempenho preditivo.

As variáveis categóricas precisarão de codificação no pipeline de ML. A redundância entre `produto_id` e `corte` deverá ser avaliada nos experimentos, sem alterar retroativamente a matriz desta Sprint.

## 9. Limitações

- Dados sintéticos e apenas um ano de observações; padrões podem refletir as regras do gerador.
- Venda observada pode ser censurada pelo estoque em dias de ruptura.
- Dados reais ainda dependem de autorização; não há coleta ou autorização comprovada.
- Nenhuma inferência causal, generalização comercial ou redução de desperdício foi comprovada.
- A EDA usou o período completo; seus achados não equivalem a avaliação independente em teste.
- Nenhum modelo foi treinado ou avaliado nesta Sprint.

## 10. Preparação para Sprint 5

A próxima Sprint deverá definir formalmente o protocolo temporal, criar baseline e divisão treino/validação/teste, codificar categorias, treinar algoritmos, comparar métricas, realizar ajuste moderado de hiperparâmetros, escolher e serializar o modelo.

Transformações aprendidas devem ser ajustadas somente no treino. Na avaliação de um dia à frente, a venda anterior só pode atualizar o histórico quando estiver disponível. Previsões de vários dias feitas de uma vez exigiriam outro protocolo. Nenhum desses experimentos foi implementado aqui.

## 11. Critérios de conclusão da Sprint 4

| Critério técnico | Evidência |
|---|---|
| Features sem leakage contemporâneo | Lista explícita e testes de alteração do alvo/futuro, lags, médias e isolamento por produto |
| Dataset reproduzível | Testes de CSV/JSON idênticos e conferência dos hashes |
| 7.077 registros, sem nulos ou duplicatas | CSV e relatório de modelagem |
| EDA avançada executada | Notebook 02 com 16 células de código executadas, sem erros |
| Nove gráficos e relatório de insights | `reports/sprint4/` |
| Suíte aprovada | 28 testes: 11 da Fase 1, 11 de atributos e 6 do dataset |
| Limitações registradas | Seção 9 e plano de dados reais |

Esses critérios registram conclusão técnica. Os [critérios da Fase 1](criterios_aceite.md) foram preservados como histórico; não há declaração de aprovação institucional ou do parceiro.

## 12. Reprodução da validação

Na raiz do projeto, com o ambiente instalado conforme o README:

```powershell
python -m modeling.dataset
python scripts/execute_notebook.py notebooks/02_eda_avancada_features.ipynb
python -m unittest discover -s tests -v
python -m pip check
```

O NumPy 2.2.6 já usado no ambiente passou a constar diretamente em `requirements.txt`, pois `modeling/features.py` o importa. Nenhuma versão foi atualizada ou instalada para antecipar ML.

Na validação de fechamento, os 28 testes passaram em 8,143 s e `pip check` informou ausência de dependências quebradas. A nova geração manteve CSV e JSON idênticos byte a byte. A execução integral do notebook manteve resultados, nove figuras e insights; somente os horários internos das células mudaram, por isso o arquivo versionado foi preservado sem alteração cosmética. A base tratada e o notebook 01 também permaneceram idênticos. `git diff --check` passou sem problemas.
