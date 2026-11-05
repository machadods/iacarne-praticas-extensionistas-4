# Sprint 5 — Etapa 1: protocolo temporal e baseline

Registro de 04/11/2026. Esta etapa define a separação temporal e avalia somente
o baseline sazonal na validação. Não inclui treinamento de ML, seleção de
features, ajuste de hiperparâmetros ou serialização de modelos.

## Origem e verificação inicial

- A árvore Git estava limpa em `main`, no commit
  `2b7dee631d7a41fa7ff6f55658195675de6faf76`,
  `docs: documenta resultados da sprint 4`.
- `git ls-remote origin refs/heads/main` confirmou o mesmo commit no GitHub.
- Os seis arquivos exigidos da Sprint 4 foram encontrados e preservados:
  `modeling/features.py`, `modeling/dataset.py`, os dois arquivos em
  `data/modeling/`, `reports/sprint4/insights.md` e
  `docs/sprint4_eda_features.md`.
- Fonte exclusiva da execução: `data/modeling/iacarne_modelagem.csv`.
  Dados sintéticos, sem registros comerciais reais.
- SHA-256 da matriz, igual ao registrado no relatório da Sprint 4:
  `1a6b482dcca3497ed605a821ae13cdd46404186c5d9b94716f8cb2e8f0131772`.

## Períodos aceitos e cobertura

Os limites são inclusivos e fixados antes dos experimentos desta etapa.
A unidade é produto/dia; o alvo é `quantidade_vendida_kg`.

| Conjunto | Início | Fim | Dias | Produtos/cortes | Registros | Registros por produto |
|---|---|---|---:|---:|---:|---:|
| Treino | 29/09/2025 | 30/04/2026 | 214 | 21 | 4.494 | 214 |
| Validação | 01/05/2026 | 30/06/2026 | 61 | 21 | 1.281 | 61 |
| Teste final reservado | 01/07/2026 | 31/08/2026 | 62 | 21 | 1.302 | 62 |
| Total | 29/09/2025 | 31/08/2026 | 337 | 21 | 7.077 | 337 |

Foram conferidos os mesmos 21 produtos em todos os conjuntos, com identidade
produto/corte consistente, uma observação de cada produto em cada data,
zero chaves duplicadas, zero lacunas e nenhuma data compartilhada entre conjuntos.
A inspeção inicial da matriz também encontrou zero nulos.
As 588 linhas de aquecimento já haviam sido removidas na Sprint 4;
nenhuma linha adicional foi descartada aqui.

`modeling/validation.py` rejeita períodos sobrepostos, invertidos ou separados
por lacunas, datas fora do protocolo, datas com horário/fuso, duplicatas,
identidades inconsistentes e cobertura incompleta por produto em qualquer conjunto.
Retorna cópias ordenadas por data global e produto. Os produtos se repetem
nos conjuntos porque o objetivo é prever os mesmos cortes em datas futuras;
o isolamento exige que o histórico de um corte nunca alimente outro corte.

## Instante da previsão e prevenção de vazamento

Para cada data D, a previsão é feita após o fechamento de D−1, para venda
observada de D. Somente vendas realmente observadas em datas anteriores podem
entrar no histórico. A validação simula previsões diárias sucessivas:
depois do fechamento de cada dia, sua venda observada fica disponível para
previsões posteriores. Não se trata de prever todos os dias de maio e junho
de uma única vez em 30/04.

Exemplos: a previsão de 01/05 usa a venda de 24/04 do mesmo produto;
a previsão de 08/05 usa a venda observada de 01/05. O alvo de 01/05 não
participa da sua própria previsão. O histórico é atualizado com observações,
sem substituir vendas anteriores por previsões do baseline.

O lag 7 da validação é comparado, para cada produto/data, à venda observada
exatamente em D−7, consultando apenas treino e validação. Não se usa posição
de linha nem deslocamento sobre produtos misturados. Nenhuma transformação
estatística é aprendida pelo baseline. Em etapas futuras, imputação,
normalização, codificação e outras transformações aprendidas devem ser
ajustadas somente no treino e aplicadas depois à validação e ao teste.

Não aplicar `TimeSeriesSplit` diretamente à matriz ordenada por produto.
Qualquer validação cruzada futura deverá definir fronteiras por datas globais,
mantendo todos os produtos de uma mesma data no mesmo bloco e todo treino
anterior ao bloco avaliado. Não foi implementada validação cruzada nesta etapa.

O teste final participa apenas das verificações de datas, produtos e contagens.
Seus alvos e lags não entram nas previsões, no histórico de validação ou nas
métricas desta etapa. Embora a matriz inteira seja carregada, não são calculadas
métricas de treino ou teste. Não usar o teste para escolher features, algoritmos
ou hiperparâmetros. Sua avaliação depende de nova autorização, após congelar
essas decisões. Ground truth de auditoria, planilha auxiliar e gerador não são
lidos pelo fluxo desta etapa.

## Baseline e métricas

Regra fixa: `previsao(D, produto) = venda_lag_7`.
Reproduz a venda do mesmo produto no mesmo dia da semana anterior, sem ajuste
de parâmetros. Lag ausente, não finito ou negativo gera erro; não há imputação
nem descarte silencioso. A função de previsão consulta somente `venda_lag_7`.

Para n observações e erros `e = observado − previsto`:

- MAE = `soma(|e|) / n`, em kg.
- RMSE = `raiz(soma(e²) / n)`, em kg.
- R² = `1 − soma(e²) / soma((observado − média_observada)²)`, sem unidade.

As métricas globais agrupam os 1.281 pares produto/dia, com o mesmo peso
por observação. Não são uma média dos R² por corte. A média observada no
denominador do R² é parte da métrica, sem uso na previsão. Para alvo constante
ou uma única observação, R² é indefinido e retorna `None` (`null` no JSON).
Vetores vazios, de tamanhos diferentes ou com valores não finitos geram erro.
O cálculo usa NumPy já instalado; nenhuma dependência foi instalada.

### Resultado observado somente na validação

| Observações avaliadas | MAE (kg) | RMSE (kg) | R² |
|---:|---:|---:|---:|
| 1.281 | 1,863521 | 2,571085 | 0,834811 |

Valores arredondados a seis casas. A execução imprime o JSON com maior precisão,
contagens, hash da fonte e métricas por corte.

| Corte | Observações | MAE (kg) | RMSE (kg) | R² |
|---|---:|---:|---:|---:|
| Acém | 61 | 3,945738 | 5,196916 | 0,266485 |
| Alcatra | 61 | 2,291967 | 2,855116 | 0,712197 |
| Capa de Filé | 61 | 1,418689 | 1,713574 | 0,613584 |
| Costelão | 61 | 2,376557 | 3,097374 | 0,704887 |
| Coxão Duro | 61 | 2,218689 | 2,737511 | 0,339869 |
| Coxão Mole | 61 | 2,301639 | 3,213521 | 0,592094 |
| Cupim | 61 | 1,149672 | 1,432666 | 0,757134 |
| Filé de Agulha | 61 | 1,665738 | 2,108149 | 0,282715 |
| Filé Mignon | 61 | 0,850492 | 1,068349 | 0,586581 |
| Filé Simples | 61 | 1,984590 | 2,454698 | 0,273877 |
| Fraldinha | 61 | 1,831803 | 2,308086 | 0,694608 |
| Lagarto | 61 | 1,857541 | 2,472986 | 0,283911 |
| Maminha | 61 | 1,503770 | 1,976071 | 0,774515 |
| Músculo Dianteiro | 61 | 1,443770 | 1,764044 | 0,584068 |
| Músculo Traseiro | 61 | 1,855246 | 2,462637 | 0,294371 |
| Paleta | 61 | 2,107541 | 2,660391 | 0,341728 |
| Patinho | 61 | 3,215574 | 4,274507 | 0,202442 |
| Pescoço | 61 | 1,080164 | 1,426489 | 0,457619 |
| Picanha | 61 | 1,499344 | 1,785429 | 0,723192 |
| Ponta de Peito | 61 | 1,206230 | 1,455367 | 0,604316 |
| Vazio | 61 | 1,329180 | 1,559472 | 0,722959 |

Os resultados por corte mostram diferenças que o R² global não resume bem.
Por exemplo, Acém tem MAE de 3,945738 kg e R² de 0,266485. O R² global
também reflete diferenças de nível de venda entre produtos; não comprova
qualidade uniforme nem ganho comercial.

## Reprodução e testes

Na raiz do projeto, com o ambiente existente:

```powershell
.\.venv\Scripts\python.exe -X utf8 -m modeling.baseline
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
git diff --check
```

O comando do baseline não escreve arquivos. Sobre a mesma matriz, a saída é
determinística, sem semente aleatória ou horário variável. Reordenar as linhas
mantém contagens e métricas; o hash muda se os bytes da fonte mudarem.

Os testes novos verificam fronteiras inclusivas, datas sem sobreposição,
contagens e cobertura da matriz oficial, ordenação global, isolamento dos
produtos, lag D−7 exato, rejeição de lag de outro dia/produto, preservação das
entradas, ausência de influência de D e do futuro nas previsões anteriores,
métricas com exemplos de resultado conhecido e determinismo.
Também bloqueiam leituras fora da matriz fixa durante a avaliação e substituem
alvos/lags do teste por valores inválidos para conferir que não entram nos cálculos.
Os testes históricos são preservados. O teste histórico de integridade lê o
ground truth somente para conferir seu hash; isso não é uso na previsão
ou avaliação, nem acesso pelo fluxo novo.

Resultado da execução completa: **47 testes aprovados** em 7,941 s,
sendo 28 históricos e 19 novos (8 do protocolo temporal e 11 do baseline).
`git diff --check` passou; os cinco arquivos novos também foram conferidos
diretamente quanto a UTF-8, finais de linha LF e ausência de espaços finais.
As métricas documentadas, incluindo os 21 cortes, foram comparadas à saída
da execução. Nenhum teste histórico foi alterado.

## Limitações e encerramento da etapa

- A base é sintética, com somente um ano de origem. Os resultados não comprovam
  desempenho em operação ou em dados comerciais reais.
- O alvo é venda observada. Rupturas podem limitar a venda e ocultar demanda
  não atendida; o baseline não estima demanda latente.
- A EDA da Sprint 4 explorou todo o período, inclusive as datas agora reservadas
  ao teste. Portanto, o teste tem exposição exploratória prévia e não pode ser
  apresentado como completamente intocado. Nesta etapa não houve novas
  análises de desempenho sobre ele; nenhuma métrica de teste foi calculada.
- Os mesmos 21 cortes têm histórico completo. Novos produtos ou lacunas
  exigirão revisar o contrato e a estratégia de histórico.
- A operação pressupõe fechamento diário disponível antes da previsão seguinte.
  Atrasos de dados ou previsão de vários dias exigiriam outro protocolo.

Esta entrega encerra somente a Etapa 1. O baseline é uma referência observada
na validação; nenhum modelo de ML foi treinado, comparado ou serializado.
