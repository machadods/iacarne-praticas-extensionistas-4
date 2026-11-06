# Sprint 5 — Etapa 4 — Avaliação final e serialização

O Ridge congelado foi ajustado em **5.775 observações** de treino e validação.
Na avaliação final de **1.302 observações**, obteve MAE de **1,475517 kg**,
20,71% menor que o baseline D−7. O pipeline e os metadados foram salvos
como artefato versão 1.0.0.

## Protocolo

A Etapa 3 estava publicada em `1b144e0` antes da execução. A configuração
já havia sido escolhida na [Etapa 3](selecao_modelo.md) usando treino e
validação. O ajuste final criou uma instância nova do pipeline da Etapa 2,
com Ridge `alpha=100.0`, `solver="cholesky"` e `fit_intercept=True`.
Os demais hiperparâmetros foram mantidos e constam nos metadados.

| Conjunto | Período inclusivo | Observações | Uso final |
|---|---|---:|---|
| Treino | 29/09/2025 a 30/04/2026 | 4.494 | Ajuste |
| Validação | 01/05/2026 a 30/06/2026 | 1.281 | Ajuste junto ao treino |
| Teste | 01/07/2026 a 31/08/2026 | 1.302 | Avaliação final |

O codificador categórico, o escalonador numérico e o regressor foram
ajustados somente com treino e validação, até 30/06/2026. A avaliação
do Ridge e do baseline calculou métricas uma vez, nos mesmos 62 dias e
21 cortes. A configuração permaneceu congelada após a avaliação.

### Previsão diária

A previsão da venda de D usa o histórico observado até o fechamento de
D−1. Durante a simulação, vendas observadas em dias já encerrados do teste
podem compor lags e médias móveis de dias posteriores. Por exemplo, a
previsão de 02/07 pode usar a venda de 01/07. Os valores de D em diante
ficam fora dos atributos da previsão de D. Os históricos do teste foram
conferidos por produto e data contra a engenharia de atributos da Sprint 4.

As 1.302 entradas foram avaliadas em lote sobre atributos que reproduzem
essa disponibilidade diária. Uma previsão simultânea dos 62 dias a partir
de 30/06 exigiria outro protocolo, pois o histórico de julho e agosto
ainda não estaria disponível.

## Resultados no teste

| Método | Observações | MAE (kg) | RMSE (kg) | R² | Inválidas | Não finitas | Negativas |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline D−7 | 1.302 | 1,860814 | 2,510438 | 0,847855 | 0 | 0 | 0 |
| Ridge | 1.302 | 1,475517 | 1,993045 | 0,904106 | 0 | 0 | 0 |

A variação relativa de MAE é `100 × (MAE Ridge − MAE baseline) / MAE baseline`.
Foi de **−20,71%**, ou **0,385297 kg** a menos por observação. O Ridge teve
MAE menor nos 21 cortes. Previsões negativas ou não finitas contam como
inválidas. Todas as previsões oficiais foram finitas e não negativas,
sem descarte ou ajuste dos valores.

### MAE por corte

| Corte | Observações | Baseline D−7 (kg) | Ridge (kg) |
|---|---:|---:|---:|
| Acém | 62 | 4,023065 | 3,076871 |
| Alcatra | 62 | 1,980161 | 1,709716 |
| Capa de Filé | 62 | 1,458065 | 1,042368 |
| Costelão | 62 | 2,259839 | 1,865332 |
| Coxão Duro | 62 | 2,053065 | 1,546432 |
| Coxão Mole | 62 | 2,626935 | 2,258638 |
| Cupim | 62 | 1,233710 | 0,941102 |
| Filé Mignon | 62 | 0,967742 | 0,921402 |
| Filé Simples | 62 | 1,984032 | 1,474606 |
| Filé de Agulha | 62 | 1,616452 | 1,448362 |
| Fraldinha | 62 | 1,802581 | 1,303601 |
| Lagarto | 62 | 1,400645 | 1,115424 |
| Maminha | 62 | 1,784355 | 1,426450 |
| Músculo Dianteiro | 62 | 1,629677 | 1,199054 |
| Músculo Traseiro | 62 | 1,353710 | 1,135593 |
| Paleta | 62 | 2,519032 | 1,865615 |
| Patinho | 62 | 2,843226 | 2,108335 |
| Pescoço | 62 | 1,240484 | 1,037637 |
| Picanha | 62 | 1,651290 | 1,313572 |
| Ponta de Peito | 62 | 1,378387 | 1,052136 |
| Vazio | 62 | 1,270645 | 1,143616 |

## Artefato e entrada de inferência

- [Pipeline Ridge v1](../../artifacts/models/iacarne_ridge_v1.joblib).
- [Metadados do artefato](../../artifacts/models/iacarne_ridge_v1.metadata.json).
- SHA-256 do pipeline `67b32644862f2b3fcfb3b83b30e3f1498cbd7f7b46e3356ac9dacff86d7bc73f`.
- SHA-256 da matriz `1a6b482dcca3497ed605a821ae13cdd46404186c5d9b94716f8cb2e8f0131772`.

O pipeline inclui a codificação categórica, o escalonamento dos atributos
numéricos e o Ridge ajustado. A entrada é um DataFrame com os 15 atributos
na ordem indicada nos metadados, com categorias em texto e valores
numéricos finitos. A preparação dos lags e médias móveis permanece em
[modeling/features.py](../../modeling/features.py) ou em uma etapa equivalente
de preparação. Entradas brutas do PDV precisam passar por essa preparação
antes de chamar `predict`.

O carregamento preservou os 15 nomes e sua ordem. As 1.302 previsões
antes e depois da serialização tiveram diferença absoluta máxima de
**0 kg**, com tolerância de **1e-10 kg**. Essa comparação verificou a
equivalência das previsões sem recalcular as métricas. O arquivo salvo
também foi carregado em um processo separado e fez inferência sem
`fit` em uma linha de treino. Um teste automatizado confirmou a
inferência com o artefato movido após a remoção da pasta de treinamento.

Carregue somente artefatos de origem confiável. A desserialização com
`joblib` pode executar código. O hash permite conferir os bytes com
uma referência confiável, e o carregamento foi verificado nas versões
registradas nos metadados.

## Reprodução

Ambiente validado com Python 3.10.11, NumPy 2.2.6, pandas 2.3.3, SciPy 1.15.3,
scikit-learn 1.7.2 e joblib 1.6.0. O `joblib==1.6.0` já estava instalado e
passou a ser declarado como dependência direta.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -X utf8 -m modeling.finalize
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
git diff --check
git status -sb
```

O comando de avaliação imprime os metadados e grava o par de arquivos em
`artifacts/models/` após verificar a equivalência do pipeline carregado.
Cada reprodução refaz o ajuste congelado no mesmo recorte temporal e
substitui o par de arquivos local. A suíte completa passou com **63 testes**,
incluindo seis novos. `pip check` e `git diff --check` passaram.

## Limitações

O dataset é sintético. O período reservado ao teste já foi explorado
durante a EDA da Sprint 4, portanto teve exposição exploratória prévia.
O desempenho em dados operacionais reais permanece sem validação.
O alvo é venda observada, que pode ser limitada pelo estoque. O
experimento não comprova redução de perdas nem de ruptura. É necessária
validação externa futura com dados operacionais antes de usar os
resultados como evidência de desempenho real ou de impacto na operação.
