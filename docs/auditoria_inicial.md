# Auditoria inicial dos arquivos oficiais

Inspeção somente de leitura realizada antes da organização. A pasta acadêmica continha exclusivamente os seis arquivos fornecidos, sem Git, README de projeto, package.json, documentação acadêmica, pipeline ou notebooks. O repositório Git próprio foi iniciado por decisão do usuário.

O repositório da aplicação, separado, estava em `main`, HEAD `424f665`, árvore limpa. Sua organização real é monorepositório com `apps/web`, `apps/api` e `packages`, diferente da estrutura antiga descrita no README. Não foram identificados arquivos AGENTS.md pelo levantamento. Scripts de raiz existentes: dev, build, lint, type-check, format, test:e2e e generate-secrets; não existe script check. Nenhuma alteração da aplicação é necessária à entrega acadêmica.

## Integridade e conteúdo

Os seis hashes SHA-256 estão no [manifesto](integridade_dataset.json). Eles permitem detectar alterações posteriores; não equivalem a assinatura externa de autenticidade. O ZIP interno do XLSX passou na verificação de integridade. As abas Dados_Brutos e Auditoria_GT possuem respectivamente 7.680 e 7.665 registros e correspondem integralmente aos CSVs, considerando equivalência numérica e células vazias.

| Item | Observação verificada |
|---|---|
| Versão e seed | 1.0.0; 26092026 |
| Período | 2025-09-01 a 2026-08-31 |
| Granularidade | Dia × corte, 365 observações únicas por corte |
| CSV bruto | 7.680 linhas, 26 colunas |
| Chaves únicas | 7.665, 21 produtos |
| Duplicatas exatas | 15 |
| Estoque inicial ausente | 23 |
| Preço com vírgula decimal | 19 |
| Nome não canônico | 38 |
| Evento vazio no bruto | 7.428; ausência de evento, não defeito |
| Ground truth | 7.665 linhas, mesmas chaves da base única |
| Preços observados | R$ 23,86 a R$ 112,73 por kg |
| Venda por dia/corte | 4,32 a 50,16 kg |
| Balanço disponível − vendido − perda − final | Resíduo máximo de 0,00 kg |

As abas Resumo, Dicionario e Premissas_Fontes foram inspecionadas. O dicionário corresponde aos campos; as premissas de dia da semana, mês, promoções, estoque e perdas são declaradamente simuladas. Não há dados pessoais identificáveis nos campos examinados. A plausibilidade operacional é compatível com as regras documentadas, sem comprovar calibração comercial externa.

## Decisão do gate
**Dataset Gate resolvido.** Nenhum dataset foi gerado ou regenerado. O gerador foi lido como código e preservado. A especificação e o README fornecidos são referências oficiais de origem; as fontes externas citadas pelo fornecedor não foram revalidadas de forma independente nesta auditoria. Não se reproduzem estatísticas externas como resultados desta entrega.

Riscos principais: confundir simulação com operação real, usar demanda latente como atributo e interpretar vendas censuradas como demanda irrestrita. O plano é preservar originais, copiar somente o CSV operacional para raw, documentar regras, validar ETL e produzir EDA sem modelagem.
