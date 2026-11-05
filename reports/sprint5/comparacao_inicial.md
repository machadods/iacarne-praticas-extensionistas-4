# Sprint 5 — Etapa 2 — Treinamento inicial

Experimento executado em 05/11/2026 para prever `quantidade_vendida_kg`
por produto e dia. A comparação mede o desempenho de uma configuração inicial
de Ridge e uma de Random Forest na validação.

## Auditoria

- A árvore de trabalho estava limpa após o commit local `562f901` da Etapa 1.
  Na consulta inicial, a `main` no GitHub ainda apontava para `2b7dee6`.
  Os experimentos locais seguiram a autorização para avançar após o commit.
- Os contratos de `modeling/validation.py` e `modeling/baseline.py` foram
  reutilizados. O baseline reproduziu os valores do
  [protocolo da Etapa 1](protocolo_validacao.md).
- A matriz tem 7.077 linhas e 17 colunas, incluindo a data ISO, o alvo em kg e
  os 15 atributos do contrato. Os quatro metadados de produto e o dia da
  semana são textuais. A matriz contém três atributos inteiros de calendário
  e sete atributos históricos de ponto flutuante.
- SHA-256 da matriz `1a6b482dcca3497ed605a821ae13cdd46404186c5d9b94716f8cb2e8f0131772`.

## Protocolo temporal

| Conjunto | Período inclusivo | Observações | Uso nesta etapa |
|---|---|---:|---|
| Treino | 29/09/2025 a 30/04/2026 | 4.494 | Ajuste dos transformadores e dos regressores |
| Validação | 01/05/2026 a 30/06/2026 | 1.281 | Previsões e métricas |
| Teste final | 01/07/2026 a 31/08/2026 | 1.302 | Conferência de datas, identidades e cobertura |

Todos os conjuntos têm os mesmos 21 cortes. Os três métodos foram comparados
nos mesmos pares produto/dia da validação, com 61 observações por corte.
O protocolo simula uma previsão de um dia à frente após o fechamento de
D−1. Os lags e as médias móveis vêm da matriz da Sprint 4, calculados com
vendas observadas até D−1. Os valores dos atributos e alvos do teste ficam
fora do ajuste, da previsão e do cálculo das métricas.

## Configuração dos modelos

O `ColumnTransformer` codifica `produto_id`, `corte`, `categoria_anatomica`,
`perfil_uso` e `dia_semana` com `OneHotEncoder(handle_unknown="ignore",
sparse_output=False)`. As colunas categóricas são lidas como texto, inclusive
códigos numéricos com zeros à esquerda. Categorias desconhecidas na validação
recebem zeros no bloco de sua coluna. O `Pipeline` ajusta o codificador e,
no Ridge, o `StandardScaler` exclusivamente no treino.

Os outros dez atributos são `fim_de_semana`, `mes`, `semana_ano`, quatro lags
e três médias móveis. O Ridge padroniza essas colunas. A floresta recebe os
valores na escala original. As entradas dos dois modelos seguem a lista
explícita da Sprint 4, sem data, alvo ou atributos contemporâneos excluídos.
Mantivemos os 15 atributos na comparação inicial. A equivalência entre
`produto_id` e `corte` é conhecida nessa matriz, mas o efeito de retirar a
duplicidade sobre o desempenho não foi medido.

| Modelo | Parâmetros | Semente |
|---|---|---|
| Ridge | `alpha=1.0`, `solver="cholesky"`, `fit_intercept=True` | Solução determinística sem semente |
| Random Forest | `n_estimators=100`, `criterion="squared_error"`, `max_depth=None`, `min_samples_split=2`, `min_samples_leaf=1`, `max_features=1.0`, `bootstrap=True`, `n_jobs=1` | `random_state=42` |

Os demais parâmetros seguem os padrões do scikit-learn 1.7.2 e são listados
no JSON da execução. As configurações foram definidas antes de calcular as
métricas. Cada modelo recebe um único ajuste no treino.

## Métricas globais de validação

| Método | Observações | MAE (kg) | RMSE (kg) | R² | Variação de MAE |
|---|---:|---:|---:|---:|---:|
| Baseline sazonal | 1.281 | 1,863521 | 2,571085 | 0,834811 | 0,00% |
| Ridge | 1.281 | 1,478469 | 1,987425 | 0,901297 | -20,66% |
| Random Forest | 1.281 | 1,564788 | 2,166297 | 0,882731 | -16,03% |

A variação é `100 × (MAE do método − MAE do baseline) / MAE do baseline`,
calculada antes de arredondar. Os dois modelos reduziram o MAE global, a
métrica principal. O menor MAE observado foi o do Ridge. Esses resultados
descrevem o período de validação e não estabelecem superioridade estatística
ou uma escolha definitiva.

## MAE por corte na validação

| Corte | Observações | Baseline (kg) | Ridge (kg) | Random Forest (kg) |
|---|---:|---:|---:|---:|
| Acém | 61 | 3,945738 | 3,218005 | 3,402887 |
| Alcatra | 61 | 2,291967 | 1,769265 | 1,794344 |
| Capa de Filé | 61 | 1,418689 | 1,089439 | 1,104284 |
| Costelão | 61 | 2,376557 | 2,217506 | 2,102390 |
| Coxão Duro | 61 | 2,218689 | 1,594972 | 1,700262 |
| Coxão Mole | 61 | 2,301639 | 1,954411 | 2,118575 |
| Cupim | 61 | 1,149672 | 0,912463 | 1,046405 |
| Filé Mignon | 61 | 0,850492 | 0,852241 | 0,696274 |
| Filé Simples | 61 | 1,984590 | 1,522608 | 1,439593 |
| Filé de Agulha | 61 | 1,665738 | 1,469441 | 1,505252 |
| Fraldinha | 61 | 1,831803 | 1,216105 | 1,440492 |
| Lagarto | 61 | 1,857541 | 1,448695 | 1,444484 |
| Maminha | 61 | 1,503770 | 1,211140 | 1,440569 |
| Músculo Dianteiro | 61 | 1,443770 | 1,162344 | 1,360857 |
| Músculo Traseiro | 61 | 1,855246 | 1,470931 | 1,591579 |
| Paleta | 61 | 2,107541 | 1,537110 | 1,820303 |
| Patinho | 61 | 3,215574 | 2,332179 | 2,706995 |
| Pescoço | 61 | 1,080164 | 0,979139 | 0,834630 |
| Picanha | 61 | 1,499344 | 1,073414 | 1,101789 |
| Ponta de Peito | 61 | 1,206230 | 0,978951 | 1,043702 |
| Vazio | 61 | 1,329180 | 1,037491 | 1,164877 |

O Ridge reduziu o MAE em 20 dos 21 cortes. No Filé Mignon, o MAE subiu de
0,850492 para 0,852241 kg. A floresta reduziu o MAE nos 21 cortes deste
período. Acém teve o maior MAE nos três métodos.

## Reprodução e verificação

No Windows, foram validados Python 3.10.11, NumPy 2.2.6, pandas 2.3.3
e scikit-learn 1.7.2. O `requirements.txt` passou a fixar apenas a nova
dependência direta `scikit-learn==1.7.2`. SciPy 1.15.3, joblib 1.6.0,
threadpoolctl 3.7.0 e cloudpickle 3.1.2 foram instaladas como dependências
transitivas. As versões fixadas anteriormente foram mantidas.
[Metadados da versão no PyPI](https://pypi.org/project/scikit-learn/1.7.2/).

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -X utf8 -m modeling.train
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

A comparação imprime o JSON no terminal e mantém os modelos em memória.
A suíte completa passou com **52 testes**, incluindo 5 novos. Os testes
novos verificam cobertura antes do ajuste, dados recebidos por `fit` e
`predict`, estatísticas do escalonador, categorias conhecidas e novas,
previsões finitas, determinismo, independência dos valores do teste, preservação
da matriz e métricas com resultados conhecidos. O `pip check` não apontou
dependências incompatíveis.

## Limitações

Os dados são sintéticos e cobrem um ano. O alvo é a venda observada, que
pode ser limitada pelo estoque. A validação tem 61 dias e usa produtos já
presentes no treino, com fechamento diário disponível. A EDA da Sprint 4
incluiu o período reservado ao teste, como registrado na Etapa 1. Esses
fatores limitam a interpretação dos resultados em outros períodos e em
operações reais.
