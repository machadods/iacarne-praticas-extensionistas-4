# Dados e regras de tratamento

## Origem e preservação
Dataset oficial **1.0.0**, sintético, fornecido pelo acadêmico. Os seis arquivos originais permanecem na raiz, sem alterações. O [README oficial](../README_dataset_iacarne.md) e a [especificação](../iacarne_dataset_especificacao.json) integram esta documentação. Os hashes de referência estão em [integridade_dataset.json](../docs/integridade_dataset.json).

`raw/iacarne_vendas_bruto.csv` é cópia byte a byte da entrada oficial. `processed/` contém somente saídas do pipeline. Nunca corrigir raw manualmente. `iacarne_dataset_v1.xlsx` é auxiliar, e `iacarne_ground_truth_auditoria.csv` serve exclusivamente à auditoria. Nenhum deles é lido pelo fluxo operacional. O gerador original foi preservado e não executado.

## Contrato
O [contrato](../pipeline/contrato.json) transcreve os 26 campos do CSV e as identidades dos 21 produtos declaradas no gerador, sem executar a geração. O JSON oficial define período, versão e contagens. A implementação trata a cobertura completa dessa versão; não é importador genérico para outras bases. Novos períodos ou produtos exigem revisão explícita do contrato.

Tipos: identificadores e descrições são texto; `data` usa ISO YYYY-MM-DD; quantidades são kg, preços/custos unitários R$/kg e valores monetários R$. Indicadores binários são 0/1; `desconto_pct` usa escala 0–100. `semana_ano` é semana ISO; `ano` é ano civil.

## Regras
1. Ler UTF-8 com ou sem BOM, cabeçalho exato, sem colunas extras. CSV vazio ou malformado falha.
2. Remover apenas linhas idênticas com a mesma chave. Duplicata conflitante falha.
3. Validar identidade de produto, nome, categoria e perfil. Corrigir apenas caixa, espaços externos e normalização Unicode dos nomes compatíveis com o catálogo.
4. Converter vírgula decimal apenas no preço. Usar Decimal e rejeitar valores ausentes obrigatórios, não finitos, ambíguos e precisão maior que duas casas.
5. Reconstruir estoque inicial ausente como disponível − entrada. Não usar média, futuro ou ground truth. Registrar a correção e flag `estoque_inicial_reconstruido`.
6. Validar não negatividade (margem pode ser negativa), indicadores binários, preços/custos positivos e descontos compatíveis com promoção. As faixas promocionais 8–16% são da simulação v1.0.0, não regras universais de varejo.
7. Validar disponível = inicial + entrada e final = disponível − vendido − perda, com igualdade decimal exata. Validar continuidade entre fechamento e abertura do dia seguinte; a simulação inicia com estoque zero.
8. Validar receita = quantidade × preço, custo total = quantidade × custo e margem = receita − custo. Tolerância monetária de R$ 0,01 acomoda arredondamento do gerador em ponto flutuante; não corrige valores monetários silenciosamente.
9. Conferir que ruptura declarada implica estoque final zero. A recíproca não é assumida: saldo zero não prova demanda não atendida. A classificação exata depende de demanda latente e fica fora do ETL.
10. Derivar calendário da data e registrar eventuais divergências corrigidas. Acrescentar `ano_semana_iso`, pois a primeira semana ISO pode pertencer a outro ano civil. Não inventar feriados/eventos; evento vazio é ausência de evento selecionado pelo simulador.
11. Validar cobertura de cada data/produto do período oficial. Ordenar por data/produto e exportar UTF-8, ponto decimal, duas casas e quebra LF.

## Saída e falhas
CSV tratado: 26 campos originais e dois controles derivados (flag de reconstrução e ano ISO). O relatório JSON contém contagens, nulos, hashes da entrada e saída e cada correção por chave/campo. O notebook confere o hash do tratado antes de analisar, detectando arquivo alterado ou relatório incompatível. Datas de execução e duração ficam fora dos arquivos determinísticos; duração é apresentada no terminal.

Erros críticos interrompem com código de saída não zero antes de publicar novas saídas. Não há quarentena silenciosa: na execução bem-sucedida, rejeições são zero; duplicatas são contabilizadas separadamente. Se já houver saída de execução anterior, ela permanece e não deve ser interpretada como resultado da tentativa que falhou. Cada arquivo é substituído atomicamente, mas o par CSV/JSON não constitui uma transação: uma falha de disco entre gravações exige nova execução completa e conferência.

## Agregação e previsão futura
Somar vendas, receitas e perdas ao longo do tempo. Estoque é saldo: apresentar médias diárias ou fechamento, nunca soma temporal como estoque físico. Preço realizado ponderado = receita total / kg vendidos. Taxa de perdas = perdas / estoque disponível acumulado no período, uma razão de exposição diária que pode contar estoque carregado entre dias repetidamente; não equivale a perdas / compras.

Campos do resultado do dia ficam disponíveis para EDA, mas não podem ser features de previsão anterior à operação: perdas, fechamento, ruptura, receita, custo total e margem. O alvo também não é feature. Preço, promoção, desconto, entrada e disponível exigem avaliação de disponibilidade temporal futura. Não treinar usando automaticamente todas as colunas do CSV.
