# Critérios de aceite

## Fase 1 — critérios originais

Esta lista define o aceite técnico. A execução e seus resultados serão registrados no relatório final; a existência desta lista não significa aprovação pelo usuário.

| ID | Critério | Verificação | Requisitos |
|---|---|---|---|
| CA01 | Pré-projeto, viabilidade, requisitos, cronograma, casos de uso e diagramas completos | Revisão dos documentos e links locais | Escopo acadêmico |
| CA02 | Origem sintética e versão 1.0.0 documentadas; seis originais preservados | Manifesto SHA-256 e README oficial referenciado | RNF04, RNF06 |
| CA03 | Entrada oficial lida e schema/tipos validados | Pipeline completo e testes de entrada inválida | RF01, RF02 |
| CA04 | 15 duplicatas removidas, 23 estoques reconstruídos, 19 preços convertidos e 38 nomes corrigidos na base oficial | Relatório e conferência independente | RF03, RF08 |
| CA05 | 7.665 chaves únicas, 365 dias e 21 cortes na saída, sem nulos obrigatórios | Validação de cobertura e unicidade | RF05 |
| CA06 | Equações de estoque e valores monetários respeitados | Testes e validação com tolerância explícita de arredondamento | RF02, RNF03 |
| CA07 | CSV e relatório determinísticos em duas execuções | Comparação dos hashes | RNF02 |
| CA08 | ETL em até 30 segundos no ambiente testado | Medição real do comando | RNF01 |
| CA09 | Notebook integral executado e gráficos principais produzidos com interpretação | Execução sem erro; inspeção visual dos gráficos | RF04, RF07 |
| CA10 | README permitir instalação, execução, testes e EDA sem alterações manuais nos dados | Reprodução dos comandos em ambiente isolado | RNF05 |
| CA11 | Ground truth ausente do fluxo operacional; leakage documentado | Teste sem arquivo de auditoria e revisão das dependências | RF06, RNF04 |
| CA12 | Aplicação existente preservada | Estado Git do repositório separado e registro dos checks existentes | Separação de escopo |

Não são critérios desta fase: modelo treinado, acurácia, deploy, integração comercial ou redução de perdas comprovada. UAT com gestor permanece pendente mesmo após todos os critérios técnicos atendidos.

## Sprint 5 — evidências de entrega

A conferência usa o Roteiro de Práticas Extensionistas IV da UNOESC, em especial a seção de Desenvolvimento (p. 3) e a Sprint 5 (p. 5). Os estados abaixo descrevem os arquivos e resultados observados, sem representar aprovação institucional ou aceite de usuários.

| Entregável exigido | Arquivo que comprova | Estado | Evidência observada | Ação necessária |
|---|---|---|---|---|
| Treinamento dos modelos | [Comparação inicial](../reports/sprint5/comparacao_inicial.md) | Atendido | Ridge e Random Forest foram ajustados no treino e comparados na mesma validação cronológica. | — |
| Comparação, ajuste e seleção | [Relatório de seleção](../reports/sprint5/selecao_modelo.md) | Atendido | Dez configurações foram avaliadas na validação. O Ridge `alpha=100.0` foi escolhido antes do registro das métricas finais. | — |
| Validação cruzada temporal | [Relatório S5-A](../reports/sprint5/validacao_cruzada_temporal.md) | Atendido | Três folds expansivos no desenvolvimento. O MAE agregado do Ridge foi maior que o do baseline. A análise é retrospectiva. | — |
| Métricas de avaliação | [Avaliação final](../reports/sprint5/avaliacao_final.md) | Atendido | MAE, RMSE e R² registrados para o Ridge e o baseline nas mesmas 1.302 observações do teste final. | — |
| Avaliação contra critérios definidos na Fase 1 | [Requisitos originais](requisitos.md) e [protocolo temporal](../reports/sprint5/protocolo_validacao.md) | Parcialmente atendido | A Fase 1 indicou as métricas, mas não fixou um limiar numérico de erro preditivo. A comparação com D−7 foi definida no protocolo da Sprint 5. | Explicitar essa diferença na revisão acadêmica. Definir limites de erro antes de uma futura validação operacional. |
| Modelo treinado e serializado | [Ridge v1](../artifacts/models/iacarne_ridge_v1.joblib) e [metadados](../artifacts/models/iacarne_ridge_v1.metadata.json) | Atendido | O pipeline foi salvo em Joblib, formato previsto na p. 3. O registro de carregamento confirma equivalência das 1.302 previsões. | — |
| Caderno de laboratório | [Notebook de modelagem](../notebooks/03_modelagem_validacao.ipynb) | Atendido | Doze células de código executadas, com outputs, gráficos, reprodução no desenvolvimento e resultados históricos identificados. | — |
| Relatório de treinamento e resultados | [Comparação](../reports/sprint5/comparacao_inicial.md), [seleção](../reports/sprint5/selecao_modelo.md) e [avaliação final](../reports/sprint5/avaliacao_final.md) | Atendido | Os relatórios existentes registram parâmetros, períodos, métricas, limitações e reprodução. | — |
| Código e caderno no GitHub | [README](../README.md), [notebook](../notebooks/03_modelagem_validacao.ipynb) e [S5-A](../reports/sprint5/validacao_cruzada_temporal.md) | Atendido | Os commits `f1c8367` (S5-A), `b346b8a` (S5-B) e `9b1dda5` (S5-C) constam no histórico da branch `main` do GitHub. | — |
| Formato do relatório da Sprint 5 | [Relatório de métricas](../reports/sprint5/avaliacao_final.md) | Atendido | A seção específica da Sprint 5 pede modelo e relatório de métricas, sem indicar Word ou PDF como formato obrigatório para esse relatório. | — |

As páginas 1 e 2 do roteiro pedem Word/PDF para pré-projeto e modelagem. A **comprovação desse formato da Fase 1 está pendente**. O repositório contém [pré-projeto](pre_projeto.md) e documentação de modelagem em Markdown e diagramas, mas não foi encontrado um Word/PDF versionado para esses itens. É preciso conferir a entrega institucional. Essa verificação não cria uma exigência de formato para o relatório da Sprint 5.

A aplicação do critério acadêmico de limiar prévio fica para revisão docente. A validação operacional com usuários pertence à Sprint 7 e permanece pendente.

## Sprint 6 — fechamento do beta

Conferência técnica S6-C realizada em 23/11/2026. Fonte consultada fora do repositório, na pasta acadêmica do projeto, o **Roteiro de Práticas Extensionistas IV — Entregáveis**, arquivo `Roteiro e Entregáveis.pdf`, pp. 3 e 5. A p. 5 exige codificação do dashboard ou API, integração do modelo ao pipeline de inferência e um sistema beta funcional de ponta a ponta. A p. 3 reúne as exigências gerais de código, dependências, documentação e artefatos. Os estados abaixo registram evidências técnicas e pendências de comprovação acadêmica.

| Requisito e origem | Estado | Evidência observada | Pendência ou ação necessária |
|---|---|---|---|
| Codificação do dashboard, p. 5 | Atendido | [Aplicação Streamlit](../app.py) com seleção entre 21 cortes, histórico de 28 dias, tabela, gráfico e resultados em kg. | — |
| Integração do modelo e da inferência, p. 5 | Atendido | A aplicação usa [predict_next_day](../modeling/inference.py), com catálogo oficial, histórico até D−1 e carregamento do Ridge v1 após conferência SHA-256. | — |
| Sistema beta funcional de ponta a ponta, p. 5 | Atendido | Reprodução local pelo comando do [README](../README.md). Previsões de Acém e Picanha, upload real de CSV válido e rejeição de histórico insuficiente verificados no navegador. | — |
| Código e artefato acessíveis no GitHub, p. 3 | Atendido | S6-A publicado em `0ecde8d` e S6-B em `bfc0b98`. Os dois commits foram confirmados no histórico da `main` remota. [Ridge v1](../artifacts/models/iacarne_ridge_v1.joblib) e [metadados](../artifacts/models/iacarne_ridge_v1.metadata.json) versionados. | Publicar a documentação S6-C após revisão. |
| README e documentação técnica, p. 3 | Atendido | [README](../README.md), [cronograma](cronograma.md) e este documento registram execução, demonstração curta, contrato, verificações e limitações. | Revisar e versionar este fechamento. |
| Dependências e reprodução da instalação, p. 3 | Parcialmente atendido | [requirements.txt](../requirements.txt) fixa nove dependências diretas. A simulação de instalação encontrou os requisitos satisfeitos e `pip check` passou no ambiente Python 3.10.11. | Uma instalação limpa em outro ambiente ainda não foi ensaiada. As versões das dependências transitivas não estão integralmente fixadas no arquivo. |
| Comprovação de entrega e aceite institucional | Pendente | A publicação técnica no GitHub foi confirmada. Não há comprovante de envio institucional ou aprovação docente registrado neste repositório. | Conferir o procedimento e registrar a comprovação disponível. |

### Reprodução e integridade verificadas

O ambiente atual usa Python 3.10.11 e Streamlit 1.65.0. O comando do README iniciou o servidor local em `127.0.0.1:8501`, com resposta HTTP 200. A inferência gerou 21 previsões para 01/09/2026 a partir do histórico encerrado em 31/08/2026. No navegador, Acém mostrou Ridge 24,420 kg e D−7 22,780 kg. Picanha mostrou 9,590 kg e 7,670 kg. O aviso de treinamento sintético ficou visível junto aos resultados.

O roteiro de demonstração do README foi reproduzido com cópias temporárias de 28 e 27 observações sintéticas de Acém. O upload válido ofereceu somente esse corte. O arquivo insuficiente foi rejeitado com mensagem de exigência de 28 dias civis, sem traceback ou resultado anterior. Os CSVs enviados são lidos em memória. O limite de 5 MiB é aplicado pelo widget e conferido novamente antes da leitura do conteúdo pelo pandas. A autorização de uso cabe ao responsável pelo arquivo.

Passaram 65 testes, distribuídos em dashboard (9), inferência (26), atributos temporais (11), baseline (11) e divisão temporal (8). Os testes focados de dashboard e inferência podem ser repetidos com os comandos abaixo. Os testes históricos que ajustam modelos ficaram fora desta execução.

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_dashboard.py -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_inference.py -v
```

`pip check`, validação de sintaxe, referências locais e `git diff --check` passaram. Os hashes protegidos conferidos antes e depois foram os seguintes.

| Arquivo | SHA-256 |
|---|---|
| Matriz de modelagem | `1a6b482dcca3497ed605a821ae13cdd46404186c5d9b94716f8cb2e8f0131772` |
| Ridge v1 | `67b32644862f2b3fcfb3b83b30e3f1498cbd7f7b46e3356ac9dacff86d7bc73f` |

### Condições para apresentação posterior

O beta está tecnicamente preparado para uma demonstração local no ambiente verificado, com o modelo conferido pelo hash, histórico sintético identificado, previsões e baseline separados e mensagens de erro visíveis. O roteiro curto do README permite apresentar o fluxo completo. Para uma futura sessão com usuários, ainda será necessário combinar a participação e obter autorização para qualquer dado comercial utilizado.

O alvo é venda observada em kg e pode ser limitado pelo estoque. O Ridge foi treinado com dados sintéticos e ainda não foi validado com vendas reais do supermercado. Redução de perdas ou rupturas e resultados comerciais permanecem sem comprovação. O experimento Favorita é separado e usa `sales` com unidade física desconhecida. A validação operacional com usuários permanece pendente para a Sprint 7.

As exigências Word/PDF das pp. 1–2 correspondem à Fase 1. A Sprint 6, na p. 5, exige beta funcional e não define um novo documento nesse formato. A comprovação da entrega institucional da Fase 1 e a revisão docente dos critérios preditivos continuam pendentes. O fechamento S6-C foi registrado após o período planejado de 09/11–21/11, e a divergência de datas entre as pp. 5 e 6 do roteiro está registrada no cronograma para confirmação docente.
