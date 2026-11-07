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
| Código e caderno no GitHub | [README](../README.md), [notebook](../notebooks/03_modelagem_validacao.ipynb) e [S5-A](../reports/sprint5/validacao_cruzada_temporal.md) | Parcialmente atendido | Em 06/11/2026, o remoto já continha o modelo e a avaliação final. Os commits do S5-A e do caderno ainda estavam locais. | Versionar a consolidação e publicar os checkpoints da Sprint 5 após revisão. |
| Formato do relatório da Sprint 5 | [Relatório de métricas](../reports/sprint5/avaliacao_final.md) | Atendido | A seção específica da Sprint 5 pede modelo e relatório de métricas, sem indicar Word ou PDF como formato obrigatório para esse relatório. | — |

As páginas 1 e 2 do roteiro pedem Word/PDF para pré-projeto e modelagem. A **comprovação desse formato da Fase 1 está pendente**. O repositório contém [pré-projeto](pre_projeto.md) e documentação de modelagem em Markdown e diagramas, mas não foi encontrado um Word/PDF versionado para esses itens. É preciso conferir a entrega institucional. Essa verificação não cria uma exigência de formato para o relatório da Sprint 5.

Para a entrega pelo GitHub, a pendência imediata é publicar os complementos da Sprint 5. A comparação de métricas está concluída, e a aplicação do critério acadêmico de limiar prévio fica para revisão docente. A validação operacional com usuários pertence à Sprint 7 e permanece pendente.
