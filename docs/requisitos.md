# Requisitos — Entrega Parcial 1

## Contrato e fronteira
Entrada operacional: CSV oficial `data/raw/iacarne_vendas_bruto.csv`, cópia integral do original fornecido na raiz. Granularidade: um dia por corte; chave `registro_id`, consistente com `data` + `_` + `produto_id`. A especificação JSON define versão, origem e cobertura. O XLSX é auxiliar, e o ground truth é exclusivo da auditoria.

## Funcionais

| ID | Requisito | Evidência esperada |
|---|---|---|
| RF01 | Importar CSV UTF-8 com os 26 campos de vendas e estoque oficiais | Extração do arquivo e contagem de 7.680 linhas |
| RF02 | Validar schema, tipos, domínios, chave, datas e cobertura | Erros críticos identificados e execução interrompida |
| RF03 | Remover duplicatas idênticas e tratar defeitos conhecidos segundo regras documentadas | Contagens e rastreabilidade das correções |
| RF04 | Produzir indicadores de volume, preço, receita, estoque e perdas | Tabelas e gráficos da EDA com unidades e denominadores |
| RF05 | Exportar base tratada sem alterar os originais | CSV ordenado com 7.665 registros na base oficial |
| RF06 | Preparar base documentada para previsão futura | Alvo e campos sujeitos a leakage identificados; nenhum modelo treinado |
| RF07 | Analisar corte e tempo, promoções e rupturas | Agregações por produto, mês e dia da semana |
| RF08 | Apresentar relatório de qualidade e transformação | Entrada/saída, nulos, duplicatas, rejeições e correções |

## Não funcionais

| ID | Requisito mensurável | Forma de verificação |
|---|---|---|
| RNF01 | Processar o CSV oficial completo em até 30 segundos no ambiente documentado, excluindo instalação e EDA | Medição de duração do comando; meta proposta, não resultado presumido |
| RNF02 | Mesma entrada e versão do pipeline produzirem bytes idênticos no CSV tratado e relatório determinístico | Duas execuções, comparação SHA-256; duração fica fora do relatório persistido |
| RNF03 | Toda linha removida e toda correção conhecida serem contabilizadas; erro crítico impedir nova saída válida | Testes de defeitos, relatório e falhas explícitas |
| RNF04 | Não exigir dados pessoais reais e não ler ground truth no caminho operacional | Contrato fechado de campos e execução sem arquivo de auditoria |
| RNF05 | Executar no Python 3.10 com versões fixadas e comandos documentados | Ambiente isolado, testes e notebook integral |
| RNF06 | Preservar os seis arquivos originais byte a byte | Comparação com manifesto SHA-256 da auditoria inicial |

## Qualidade e tratamento
Nulos obrigatórios, valores numéricos não finitos, números negativos incompatíveis com o campo, produtos desconhecidos, chaves conflitantes e inconsistências de saldo são erros críticos. Não haverá descarte silencioso de linhas inválidas. Duplicatas idênticas são removidas; duplicatas conflitantes interrompem o processamento.

Os defeitos controlados autorizam apenas normalização de nomes de cortes, conversão da vírgula decimal no preço e reconstrução do estoque inicial ausente pela identidade disponível − entrada. Datas determinam os campos de calendário; divergências na entrada devem ser registradas quando corrigidas. Evento vazio significa ausência de evento no calendário da simulação.

## Modelagem futura
Alvo: `quantidade_vendida_kg`. `demanda_latente_kg` nunca pode ser feature. Também não podem ser usadas para previsão antes da operação do mesmo dia: `perda_kg`, `estoque_final_kg`, `receita_bruta_rs`, `custo_total_estimado_rs`, `margem_bruta_estimada_rs` e `ruptura_estoque`. A base tratada é analítica; não equivale a uma matriz pronta de features.

Preço, promoção, desconto e reposição só poderão ser features se comprovadamente disponíveis no instante da previsão. Flags de correção são controles de qualidade, não atributos preditivos automáticos. Uma fase futura deverá fazer divisão temporal, baseline e avaliar MAE e RMSE; MAPE apenas se o comportamento do alvo permitir interpretação adequada. Não há meta de desempenho antes do baseline.
