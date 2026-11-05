# Sprint 5 — Etapa 3 — Ajuste e seleção

A configuração escolhida para a avaliação final é Ridge com `alpha=100.0`
e solver `cholesky`. O ajuste desta etapa usou uma única janela de validação
e o alvo `quantidade_vendida_kg` por produto e dia.

## Checkpoints e protocolo

A `main` estava limpa e sincronizada com o GitHub no início dos experimentos.
O remoto confirmou o commit `b4b4966` da Etapa 2, posterior a `562f901` da
Etapa 1. Os valores históricos vêm da
[comparação inicial](comparacao_inicial.md) e do
[protocolo temporal](protocolo_validacao.md).

| Conjunto | Período inclusivo | Observações | Uso |
|---|---|---:|---|
| Treino | 29/09/2025 a 30/04/2026 | 4.494 | Ajuste de transformadores e regressores |
| Validação | 01/05/2026 a 30/06/2026 | 1.281 | Previsões, métricas e seleção |
| Teste final reservado | 01/07/2026 a 31/08/2026 | 1.302 | Conferência das chaves e da cobertura |

O teste final permaneceu reservado. A leitura em duas passagens primeiro
carrega somente data, produto e corte. Na segunda, pula as linhas do teste
antes de carregar os atributos e o alvo. As observações são ordenadas pelas
mesmas chaves da Etapa 2. Todos os métodos foram comparados nos mesmos
1.281 pares de validação, com 61 observações por corte.

A previsão para D é feita após o fechamento de D−1. Os 15 atributos da
Etapa 2 foram usados, incluindo lags e médias móveis que dependem somente
de vendas observadas até D−1. SHA-256 da matriz
`1a6b482dcca3497ed605a821ae13cdd46404186c5d9b94716f8cb2e8f0131772`.

## Grade e resultados

Foram **10 treinamentos na matriz oficial**, quatro Ridge e seis Random
Forest. Cada configuração reutilizou o pipeline da Etapa 2, incluindo
a codificação categórica e a padronização numérica exclusiva do Ridge.
Cada pipeline recebeu um único ajuste, somente no treino. O baseline
sazonal D−7 é uma regra fixa sem treino.

- Ridge manteve `solver="cholesky"` e `fit_intercept=True`. Variou somente
  `alpha` entre 0,1, 1, 10 e 100.
- Random Forest manteve `n_estimators=100`, `random_state=42`, `n_jobs=1`
  e os demais parâmetros da Etapa 2. Cruzou profundidade livre, 8 e 12
  com 1 ou 4 observações mínimas por folha.

| Método | Parâmetros variados | MAE (kg) | RMSE (kg) | R² | Variação do MAE vs. baseline |
|---|---|---:|---:|---:|---:|
| Baseline sazonal | D−7 | 1,863521 | 2,571085 | 0,834811 | 0,00% |
| Ridge | `alpha=0.1` | 1,478550 | 1,987183 | 0,901321 | -20,66% |
| Ridge | `alpha=1.0` (Etapa 2) | 1,478469 | 1,987425 | 0,901297 | -20,66% |
| Ridge | `alpha=10.0` | 1,477209 | 1,989931 | 0,901048 | -20,73% |
| Ridge | `alpha=100.0` | 1,475061 | 2,001563 | 0,899888 | -20,85% |
| Random Forest | `max_depth=None`, `min_samples_leaf=1` (Etapa 2) | 1,564788 | 2,166297 | 0,882731 | -16,03% |
| Random Forest | `max_depth=None`, `min_samples_leaf=4` | 1,567506 | 2,160391 | 0,883369 | -15,88% |
| Random Forest | `max_depth=8`, `min_samples_leaf=1` | 1,572717 | 2,171450 | 0,882172 | -15,61% |
| Random Forest | `max_depth=8`, `min_samples_leaf=4` | 1,571736 | 2,165599 | 0,882806 | -15,66% |
| Random Forest | `max_depth=12`, `min_samples_leaf=1` | 1,565475 | 2,161563 | 0,883243 | -15,99% |
| Random Forest | `max_depth=12`, `min_samples_leaf=4` | 1,567026 | 2,158113 | 0,883615 | -15,91% |

As linhas originais reproduziram os resultados históricos no arredondamento
de seis casas. A variação de MAE usa o baseline como denominador e é calculada
antes de arredondar.

## Seleção

A regra parte do menor MAE global. Entre as configurações com MAE e RMSE
até 0,005 kg acima dos valores dessa referência, favorece-se menor capacidade.
O limiar foi fixado antes dos experimentos. É uma tolerância prática de
5 g por observação, metade do incremento de 0,01 kg registrado nas vendas.
Para resultados próximos, a regra prefere Ridge a Random Forest. Dentro
do Ridge, prefere maior regularização. Dentro da floresta, prefere menor
profundidade e maior número mínimo de observações por folha.

O Ridge com `alpha=100.0` teve o menor MAE, **1,475061 kg**, uma redução
de **20,85%** sobre o baseline e de **0,003408 kg** (0,23%) sobre o Ridge
original. A configuração usa a maior regularização da grade. Seu RMSE foi
**2,001563 kg**, aumento de **0,014139 kg** frente ao Ridge original, e
seu R² caiu de 0,901297 para 0,899888. O Ridge com `alpha=0.1` teve
o menor RMSE da grade, 1,987183 kg. A escolha segue a prioridade dada ao
MAE, com esses resultados como critérios complementares.

O Ridge escolhido reduziu o MAE frente ao baseline nos 21 cortes e frente
ao Ridge original em 10 deles. A maior piora frente ao Ridge original
foi na Fraldinha, de 1,216105 para 1,266987 kg. O ganho global de
0,003408 kg é pequeno e descreve esta janela de validação.

## MAE por corte da configuração escolhida

| Corte | Observações | Baseline D−7 (kg) | Ridge original (kg) | Ridge alpha=100 (kg) |
|---|---:|---:|---:|---:|
| Acém | 61 | 3,945738 | 3,218005 | 3,203044 |
| Alcatra | 61 | 2,291967 | 1,769265 | 1,805297 |
| Capa de Filé | 61 | 1,418689 | 1,089439 | 1,079900 |
| Costelão | 61 | 2,376557 | 2,217506 | 2,245958 |
| Coxão Duro | 61 | 2,218689 | 1,594972 | 1,633954 |
| Coxão Mole | 61 | 2,301639 | 1,954411 | 1,973710 |
| Cupim | 61 | 1,149672 | 0,912463 | 0,915428 |
| Filé Mignon | 61 | 0,850492 | 0,852241 | 0,755685 |
| Filé Simples | 61 | 1,984590 | 1,522608 | 1,481438 |
| Filé de Agulha | 61 | 1,665738 | 1,469441 | 1,419085 |
| Fraldinha | 61 | 1,831803 | 1,216105 | 1,266987 |
| Lagarto | 61 | 1,857541 | 1,448695 | 1,447722 |
| Maminha | 61 | 1,503770 | 1,211140 | 1,210625 |
| Músculo Dianteiro | 61 | 1,443770 | 1,162344 | 1,155284 |
| Músculo Traseiro | 61 | 1,855246 | 1,470931 | 1,486663 |
| Paleta | 61 | 2,107541 | 1,537110 | 1,578453 |
| Patinho | 61 | 3,215574 | 2,332179 | 2,358888 |
| Pescoço | 61 | 1,080164 | 0,979139 | 0,892368 |
| Picanha | 61 | 1,499344 | 1,073414 | 1,079304 |
| Ponta de Peito | 61 | 1,206230 | 0,978951 | 0,947990 |
| Vazio | 61 | 1,329180 | 1,037491 | 1,038508 |

## Sobreajuste e limites da seleção

A regularização mais forte do Ridge coincidiu com menor MAE e maior RMSE.
Na floresta, a profundidade livre com uma observação mínima por folha
manteve o menor MAE da família. A configuração de profundidade 12 e quatro
observações por folha teve o menor RMSE da família. A redução da capacidade
teve efeitos distintos conforme a métrica. Com métricas calculadas apenas
na validação, esses contrastes são insuficientes para diagnosticar
sobreajuste do treino.

As dez configurações foram comparadas na mesma janela de 61 dias. Usar essa
janela para escolher a configuração pode favorecer a que melhor se adapta
ao período e produzir uma estimativa otimista. As diferenças são
descritivas. A matriz é sintética e as vendas podem ser limitadas por
estoque. A EDA da Sprint 4 já incluiu o período reservado, conforme
registrado na Etapa 1.

## Reprodução

Ambiente validado com Python 3.10.11, NumPy 2.2.6, pandas 2.3.3 e scikit-learn
1.7.2. A execução imprime métricas e configuração escolhida em JSON. Os
modelos ajustados ficam em memória.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m modeling.tune
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
git diff --check
git status -sb
```

A suíte completa passou com **57 testes**, incluindo 5 novos. Eles verificam
a grade e os parâmetros fixos, a regra de seleção, os dados recebidos pelos
pipelines, as estatísticas do escalonador, o determinismo e a preservação
dos pares e do arquivo. A leitura do teste foi verificada com linhas
embaralhadas e valores reservados nos campos descartados. O `pip check`
passou.
