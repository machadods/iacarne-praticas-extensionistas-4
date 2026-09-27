# Critérios de aceite — Fase 1

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
