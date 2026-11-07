# Favorita — Checkpoint 1 — Preparação de MEATS

O lote contém 90.936 observações comerciais de `MEATS` por loja e dia.
É um insumo para um experimento separado do iaCarne. A unidade física de
`sales` é desconhecida. Os valores permanecem na escala da fonte e não
devem ser apresentados como kg ou vendas por corte bovino.

A fonte é [Store Sales – Time Series Forecasting](https://www.kaggle.com/competitions/store-sales-time-series-forecasting/data),
com registros da Corporación Favorita no Equador. A ficha condiciona o
acesso às regras da competição. A permissão de redistribuição dos originais
e derivados permanece sem confirmação. O lote e seu manifesto detalhado
ficam fora do repositório público.
[Regras da competição](https://www.kaggle.com/competitions/store-sales-time-series-forecasting/rules).

## Executar a preparação

Da raiz do repositório, informe a pasta com `train.csv` e `stores.csv`
e uma pasta nova para a saída. Ambos os caminhos são configuráveis.
O comando abaixo usa a estrutura local com um destino novo para reprodução.

```powershell
$favoritaBase = '..\datasets_externos\favorita'
.\.venv\Scripts\python.exe -B -X utf8 -m experiments.favorita.prepare --source-dir "$favoritaBase\store-sales-time-series-forecasting" --output-dir "$favoritaBase\preparado\checkpoint1-revisao"
```

O código usa a biblioteca padrão do Python. A execução real usou Python
3.10.11 e gravou `meats_observado.csv` e `auditoria_meats.json` em
`../datasets_externos/favorita/preparado/checkpoint1/`.
O destino é recusado se estiver no repositório, se sobrepuser à pasta dos
CSV originais ou se já existir. A preparação escreve os dois arquivos
em uma pasta temporária no mesmo volume e publica o lote completo ao fim.

## Contrato e tratamento

| Campo | Regra |
|---|---|
| `store_nbr + date` | Chave única. Loja inteira positiva presente em `stores.csv` e data civil ISO válida. |
| `family` | Somente correspondência exata com `MEATS`. |
| `sales` | Alvo decimal, finito e não negativo no contrato deste lote. O texto de origem é preservado, com sua precisão e escala. |
| `id` | Identificador inteiro não negativo, único em todo o recorte `MEATS`, mantido para rastrear a origem. |
| `onpromotion` | Contagem inteira não negativa de itens promovidos. Mantida como dado de origem. |
| `historico_d7` | Diagnóstico da disponibilidade de observação na mesma loja sete dias civis antes. |

O leitor percorre o CSV linha a linha e mantém em memória apenas as
observações da família selecionada. Valida o cabeçalho e a quantidade de
campos. Valida os tipos dos registros `MEATS`, a unicidade global de seus
IDs e a unicidade dos códigos do cadastro de lojas. Duplicata de ID ou de
chave, campo inválido ou loja desconhecida interrompem a execução antes da
publicação. A regra de unicidade de ID considera somente as linhas `MEATS`.

As linhas observadas são ordenadas por loja e data. O manifesto lista
as datas sem registro em cada loja dentro do intervalo global e as datas
ausentes em todas as lojas. Datas ausentes permanecem ausentes, sem
inserção de linhas ou imputação de vendas. Zeros observados são
preservados. A primeira venda positiva e os zeros anteriores são
diagnósticos retrospectivos. Uma série inteira com zeros tem contagem
própria. Esses valores não determinam abertura, fechamento, ruptura ou
demanda não atendida.

O manifesto também sinaliza por loja e data as observações acima de
`Q3 + 1,5 × IQR`, em que `IQR = Q3 − Q1`. Os quartis inclusivos são
calculados sobre as vendas `MEATS` agregadas das 54 lojas, formando um
limite global. Lojas com volumes diferentes podem receber sinalizações
que refletem diferenças de escala. Os 5.628 registros sinalizados não
representam necessariamente erros, anomalias comprovadas ou rupturas.
A sinalização é exclusivamente descritiva. Nenhuma observação foi excluída
ou corrigida por esse critério, e o diagnóstico fica fora de qualquer
entrada preditiva futura.

## Resultado verificado

| Contagem | Registros |
|---|---:|
| Lidos de `train.csv` | 3.000.888 |
| Fora do filtro de família | 2.909.952 |
| `MEATS` preservados na saída | 90.936 |
| Registros `MEATS` excluídos, imputados ou arredondados | 0 |
| Lojas observadas e lojas do cadastro | 54 de 54 |

O período vai de 01/01/2013 a 15/08/2017. Cada loja tem 1.684
observações em 1.688 dias civis. Faltam os dias 25/12 de 2013, 2014,
2015 e 2016, totalizando 216 pares loja/data. Há 7.331 vendas iguais
a zero, das quais 6.729 antecedem a primeira venda positiva da respectiva
loja. Todas as séries observadas tiveram alguma venda positiva.

O limite de auditoria foi **962,38** na escala de `sales`. Foram sinalizados
5.628 registros. O maior valor foi **89.576,36**. A comparação independente
com a origem conferiu os seis campos originais em todas as 90.936 linhas
e o estado de D−7 por chave.

| Arquivo | Bytes | SHA-256 |
|---|---:|---|
| `train.csv` | 121.800.373 | `99a1b7f4241821df10fa71f23abdd71c634f71f901e3cab1400c0f0c583f862c` |
| `stores.csv` | 1.387 | `af503b2bce11d7906d249f81cc0598f10e2addcc9f6c59aa2d95c9f2652c296b` |
| `meats_observado.csv` | 4.395.416 | `78d98bcb9814a9cd63b8d6cb2036535d82b7db353dd40da235fe87bbe5754cb0` |

Os hashes dos CSV de entrada conferem com os registrados na auditoria
anterior à preparação.

Na revisão FAV-A, foram confirmados 90.936 IDs distintos no recorte
`MEATS`. A preparação foi repetida em uma pasta nova,
`../datasets_externos/favorita/preparado/checkpoint1-fava/`.
O CSV e o manifesto JSON resultaram idênticos byte a byte aos do lote
original, incluindo seus hashes.

## Contrato para uso preditivo futuro

Para prever `sales` no dia D, a unidade será loja e dia, com `MEATS`
constante. O histórico vem de vendas observadas até D−1. O preparo
registra a disponibilidade de D−7 sem calcular o valor do lag.

| Estado `historico_d7` | Definição | Registros |
|---|---|---:|
| `disponivel` | Há registro da mesma loja em D−7, inclusive se a venda for zero. | 90.342 |
| `data_ausente` | D−7 está dentro do histórico iniciado da loja e falta a observação. | 216 |
| `historico_insuficiente` | D−7 é anterior à primeira data observada daquela loja. | 378 |

A disponibilidade consulta somente datas anteriores da própria loja.
Em uma etapa futura, a política para históricos indisponíveis e os
períodos de treino e avaliação devem ser definidos antes dos experimentos.
As contagens e os erros precisam ser reportados sobre a mesma população
comparável e na escala da fonte. `onpromotion` só pode entrar na previsão
se estiver disponível na hora de prever. Os diagnósticos retrospectivos
de primeira venda positiva e extremos não compõem as entradas.

## Testes

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_favorita_prepare.py -v
```

Na revisão FAV-A passaram **12 testes específicos** e **47 testes
históricos compatíveis**, de ETL, atributos, matriz, baseline e divisões.
Os testes específicos incluem IDs duplicados em datas e lojas diferentes,
IDs distintos e ID repetido em outra família. Usam entradas fictícias
criadas em memória e pastas temporárias para verificar a publicação.
Os módulos `test_train`, `test_tune`, `test_finalize` e `test_temporal_cv`,
que ajustam modelos em seus cenários, ficaram fora desta revisão.
