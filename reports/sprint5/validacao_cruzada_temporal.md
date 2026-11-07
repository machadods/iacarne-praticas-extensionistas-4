# Sprint 5 — S5-A — Validação cruzada temporal

**Validação cruzada temporal complementar, realizada após a seleção e avaliação final do Ridge v1.**

O Roteiro de Práticas Extensionistas IV da UNOESC inclui treinamento
e validação cruzada na Sprint 5 (Fase 2, p. 5). O holdout temporal
original separou treino, validação e um teste final. Esta análise
complementar examina o comportamento da configuração já escolhida em
três janelas consecutivas, com treino de origem expansiva. As
métricas servem como evidência retrospectiva e não foram critérios da
seleção original.

## Protocolo e cobertura

| Fold | Treino inclusivo | Registros | Avaliação inclusiva | Registros |
|---|---|---:|---|---:|
| 1 | 29/09/2025–31/12/2025 | 1.974 | 01/01/2026–28/02/2026 | 1.239 |
| 2 | 29/09/2025–28/02/2026 | 3.213 | 01/03/2026–30/04/2026 | 1.281 |
| 3 | 29/09/2025–30/04/2026 | 4.494 | 01/05/2026–30/06/2026 | 1.281 |

O desenvolvimento contém **5.775 observações** em 275 dias. A
identidade e os metadados dos **21 produtos** foram conferidos contra
o catálogo versionado. As datas são globais para todos os produtos.
Cada data tem uma observação por produto, sem lacunas ou duplicatas.
Em cada fold, a última data de treino antecede a primeira data de
avaliação. As janelas de avaliação são disjuntas.

Cada fold cria um pipeline novo com o mesmo pré-processamento
da Etapa 2 e Ridge `alpha=100.0`, `solver="cholesky"`. O codificador,
o escalonador e o regressor são ajustados apenas no treino do fold.
O baseline usa a venda do mesmo produto em D−7. Ambos são avaliados
nos mesmos pares de produto e dia.

Os 15 atributos estão disponíveis na matriz. Os históricos foram
conferidos contra a engenharia causal, até D−1, em todas as posições
recalculáveis no próprio desenvolvimento, incluindo toda a avaliação.
Nos primeiros dias da matriz, parte dos lags já estava disponível
graças ao aquecimento anterior ao início do desenvolvimento.
A avaliação simula previsões diárias. Vendas de dias de avaliação já
encerrados podem entrar nos históricos de dias posteriores, sem
reajustar o modelo durante a janela.

As 1.302 linhas de 01/07/2026 a 31/08/2026 foram excluídas do ajuste e
das métricas. A primeira passagem da leitura consulta somente data,
produto e corte para identificar e excluir essas linhas. A segunda
pula as linhas reservadas antes de carregar o alvo e os demais campos.
A verificação do hash opera sobre os bytes do arquivo. Os modelos dos
folds ficam em memória.

## Métricas observadas

| Fold | Método | Observações | MAE (kg) | RMSE (kg) | R² | Variação do MAE vs. D−7 |
|---|---|---:|---:|---:|---:|---:|
| 1 | Baseline D−7 | 1.239 | 2,195004 | 3,068660 | 0,736082 | 0,00% |
| 1 | Ridge | 1.239 | 3,162793 | 3,634324 | 0,629816 | 44,09% |
| 2 | Baseline D−7 | 1.281 | 1,878392 | 2,566593 | 0,833696 | 0,00% |
| 2 | Ridge | 1.281 | 1,575935 | 2,184300 | 0,879548 | -16,10% |
| 3 | Baseline D−7 | 1.281 | 1,863521 | 2,571085 | 0,834811 | 0,00% |
| 3 | Ridge | 1.281 | 1,475061 | 2,001563 | 0,899888 | -20,85% |
| Agregado | Baseline D−7 | 3.801 | 1,976585 | 2,741793 | 0,805048 | 0,00% |
| Agregado | Ridge | 3.801 | 2,059202 | 2,695108 | 0,811630 | 4,18% |

O agregado recalcula as métricas a partir das **3.801 previsões fora
do treino de cada fold**. Cada observação tem o mesmo peso. O R²
agregado usa a média observada global das três avaliações. As
métricas agregadas não são médias simples das métricas por fold.

No primeiro fold o Ridge teve MAE **44,09% maior** que o baseline.
Nos folds 2 e 3 o MAE caiu **16,10%** e **20,85%**, respectivamente.
No agregado, o MAE do Ridge ficou **4,18% acima** do baseline, enquanto
o RMSE ficou menor. O resultado do fold 3 coincide com a configuração
selecionada na janela de validação da Etapa 3. A comparação permanece
separada da [avaliação final original](avaliacao_final.md).

## MAE por corte

Todos os valores estão em kg. Cada corte tem 59 observações no fold 1,
61 no fold 2, 61 no fold 3 e 181 no agregado.

| Corte | F1 D−7 | F1 Ridge | F2 D−7 | F2 Ridge | F3 D−7 | F3 Ridge | Agreg. D−7 | Agreg. Ridge |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Acém | 3,961864 | 3,357459 | 3,673115 | 3,001586 | 3,945738 | 3,203044 | 3,859116 | 3,185484 |
| Alcatra | 2,766102 | 2,996812 | 2,517213 | 2,035608 | 2,291967 | 1,805297 | 2,522431 | 2,271310 |
| Capa de Filé | 1,622203 | 3,028610 | 1,230164 | 1,106033 | 1,418689 | 1,079900 | 1,421492 | 1,723922 |
| Costelão | 3,575593 | 3,164022 | 2,100492 | 1,921358 | 2,376557 | 2,245958 | 2,674365 | 2,435821 |
| Coxão Duro | 2,684407 | 2,805311 | 2,074754 | 1,635024 | 2,218689 | 1,633954 | 2,321989 | 2,016138 |
| Coxão Mole | 3,147458 | 3,130492 | 2,743115 | 2,309237 | 2,301639 | 1,973710 | 2,726133 | 2,463861 |
| Cupim | 1,615254 | 3,096936 | 1,343934 | 1,119506 | 1,149672 | 0,915428 | 1,366906 | 1,695305 |
| Filé Mignon | 1,005763 | 3,685467 | 1,007705 | 0,950829 | 0,850492 | 0,755685 | 0,954088 | 1,776464 |
| Filé Simples | 1,778305 | 3,210859 | 1,780164 | 1,387690 | 1,984590 | 1,481438 | 1,848453 | 2,013577 |
| Filé de Agulha | 2,071186 | 3,336341 | 1,703934 | 1,320489 | 1,665738 | 1,419085 | 1,810773 | 2,010818 |
| Fraldinha | 1,880678 | 2,931592 | 2,074918 | 1,765770 | 1,831803 | 1,266987 | 1,929669 | 1,977691 |
| Lagarto | 1,706441 | 3,200556 | 1,498689 | 1,325156 | 1,857541 | 1,447722 | 1,687348 | 1,977781 |
| Maminha | 2,070678 | 3,287510 | 1,469180 | 1,256473 | 1,503770 | 1,210625 | 1,676906 | 1,903072 |
| Músculo Dianteiro | 2,252203 | 2,880652 | 1,983770 | 1,672962 | 1,443770 | 1,155284 | 1,889282 | 1,892163 |
| Músculo Traseiro | 1,844915 | 3,264689 | 1,514098 | 1,350860 | 1,855246 | 1,486663 | 1,736906 | 2,020473 |
| Paleta | 2,713051 | 3,103709 | 1,974426 | 1,562324 | 2,107541 | 1,578453 | 2,260055 | 2,070200 |
| Patinho | 3,531695 | 3,316797 | 3,517049 | 2,670360 | 3,215574 | 2,358888 | 3,420221 | 2,776105 |
| Pescoço | 1,145593 | 3,424466 | 1,126230 | 1,158109 | 1,080164 | 0,892368 | 1,117017 | 1,807307 |
| Picanha | 1,772542 | 2,875543 | 1,368525 | 1,171001 | 1,499344 | 1,079304 | 1,544309 | 1,695722 |
| Ponta de Peito | 1,330000 | 3,351843 | 1,488033 | 1,221921 | 1,206230 | 0,947990 | 1,341547 | 1,823886 |
| Vazio | 1,619153 | 2,968982 | 1,256721 | 1,152350 | 1,329180 | 1,038508 | 1,399282 | 1,706145 |

O Ridge reduziu o MAE em 4, 20 e 21 cortes nos folds 1, 2 e 3,
respectivamente. No agregado, melhorou 7 dos 21 cortes. No Filé Mignon,
o maior aumento agregado, o MAE passou de 0,954088 para 1,776464 kg.

## Limitações

A matriz é sintética. O período avaliado, o tamanho do treino e
os meses observados mudam entre folds. Isso impede atribuir a
variação a um único fator. O primeiro treino cobre apenas o fim de
2025 e sua avaliação começa na virada do ano. Os treinos expansivos
se sobrepõem e as vendas são correlacionadas no tempo. Os resultados
são descritivos e não estabelecem significância estatística,
validação comercial ou nova escolha de modelo.

## Reprodução e integridade

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m modeling.temporal_cv
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_temporal_cv.py -v
.\.venv\Scripts\python.exe -B -m pip check
git diff --check
git status -sb
```

A execução imprime os resultados em JSON. Passaram **7 testes novos**
com dados fictícios e **61 testes históricos seguros**. A suíte
histórica de `test_pipeline.py` ficou fora da execução porque sua
preparação abre vendas brutas do período reservado e um de seus
testes lê o arquivo de auditoria sintético. Os testes históricos
de finalização executados usam matrizes fictícias e diretórios
temporários. `pip check` passou.

Os hashes SHA-256 da matriz e do Ridge v1 conferiram com os
metadados antes e depois. O Ridge v1 permaneceu byte a byte idêntico.

| Arquivo | SHA-256 antes e depois |
|---|---|
| `data/modeling/iacarne_modelagem.csv` | `1a6b482dcca3497ed605a821ae13cdd46404186c5d9b94716f8cb2e8f0131772` |
| `artifacts/models/iacarne_ridge_v1.joblib` | `67b32644862f2b3fcfb3b83b30e3f1498cbd7f7b46e3356ac9dacff86d7bc73f` |
