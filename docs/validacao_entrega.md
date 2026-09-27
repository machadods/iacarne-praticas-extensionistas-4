# Validação técnica da Entrega Parcial 1

## Ambiente e comandos executados

Ambiente: Windows, Python 3.10.11, ambiente virtual `.venv` criado do zero. Dependências diretas: pandas 2.3.3, matplotlib 3.10.8, nbformat 5.10.4, nbclient 0.10.4 e ipykernel 7.1.0.

Esta consolidação documental utiliza as evidências já obtidas. ETL e testes foram executados novamente em 27/09/2026 no checkpoint técnico `f726709`; o notebook salvo foi inspecionado sem reexecução. Não houve nova execução de ETL, testes ou notebook apenas para atualizar este documento.

| Comando na raiz acadêmica | Resultado observado |
|---|---|
| `python -m venv .venv` | Ambiente criado |
| `.venv\Scripts\python.exe -m pip install -r requirements.txt` | Instalação concluída |
| `.venv\Scripts\python.exe -m pip check` | No broken requirements found |
| `.venv\Scripts\python.exe -m pipeline.run_pipeline` | Execução do checkpoint `f726709`: 7.680 entradas → 7.665 saídas, 28 colunas, 21 cortes e 365 dias; duração de 1,523 s |
| `.venv\Scripts\python.exe -m unittest discover -s tests -v` | Execução do checkpoint `f726709`: 11 testes aprovados em 11,143 s |
| `.venv\Scripts\python.exe scripts/execute_notebook.py` | Execução integral anterior e salvamento do notebook; estado executado reconfirmado por leitura no checkpoint `f726709` |

Uma tentativa inicial de executar o notebook na `.venv` antes de a instalação terminar falhou por ausência de `nbformat`; após conclusão da instalação, a execução integral passou. Não foi necessário alterar os arquivos oficiais.

## Qualidade e reprodutibilidade

- 15 duplicatas idênticas removidas; zero registros rejeitados na execução oficial.
- 38 nomes padronizados, 19 preços com vírgula convertidos e 23 estoques iniciais reconstruídos.
- Zero nulos obrigatórios na saída. Os 7.413 eventos vazios significam ausência de evento selecionado no dataset único.
- 7.665 chaves únicas, 365 dias completos e 21 produtos.
- Saldos reconciliados em Decimal, inclusive continuidade diária. Receita, custo total e margem validados com tolerância de R$ 0,01.
- Duas execuções comparadas byte a byte para CSV e relatório JSON nos testes.
- SHA-256 tratado: `aa45c62be75407bcc69c143fa23e720ad20431e5c4210ab372bc77234ed2bb77`.
- Os seis originais e a cópia raw passaram na comparação com o manifesto de integridade inicial.
- Teste bloqueando leitura do ground truth, XLSX e gerador passou: o ETL não depende desses arquivos.
- Testes de arquivo ausente, schema incorreto, CSV vazio/malformado, tipos inválidos, duplicata conflitante, cobertura incompleta, saldo inconsistente e destinos protegidos passaram.
- Falha de validação não publica novos arquivos. O notebook confere o hash do CSV tratado contra o relatório antes da EDA.

## EDA e inspeção visual

Notebook com 22 seções acadêmicas e 19 células de código executadas, com `execution_count` sequencial de 1 a 19, outputs salvos e nenhum output de erro. A leitura usa o CSV tratado e o relatório do ETL, sem ground truth. Oito gráficos estão embutidos e exportados: volume por corte, evolução temporal, histograma de quantidade, preços por corte, receita mensal, estoque/perdas, dia da semana e correlações. Na inspeção visual anterior, rótulos, unidades, escalas e a indicação de dados sintéticos estavam visíveis; os artefatos foram preservados.

Resultados descritivos: 114.254,29 kg vendidos, receita bruta simulada de R$ 5.275.616,69, perdas de 371,71 kg e ruptura em 1.242 de 7.665 dias/corte (16,20%). Acém apresenta 10.368,51 kg acumulados; dezembro/2025 tem a maior média diária mensal, 384,47 kg/dia. São resultados da simulação, sem inferência causal ou comprovação comercial.

Estoque diário médio e fechamento são usados no lugar de soma temporal de saldos. Taxa de perdas tem denominador explicitado. As interpretações distinguem sazonalidade imposta, efeitos aritméticos e limitações de disponibilidade.

## Diagramas e publicação

Os quatro artefatos estão versionados: [blocos](diagramas/blocos.md), [E/R](diagramas/entidades.md), [fluxo textual](diagramas/processo.md) e [BPMN visual](diagramas/processo_bpmn.png). O BPMN foi inspecionado e contém as raias Origem dos Dados, Analista e Gestor, decisão de validade, retorno ao ETL e consulta dos indicadores. **Versão inicial — validação com usuário/parceiro pendente.** A existência do diagrama não representa UAT ou aprovação de cliente.

GitHub configurado no remote `origin`: `git@github.com:machadods/iacarne-praticas-extensionistas-4.git`, branch `main`. O checkpoint técnico `f726709` foi publicado com sucesso e sua sincronização com `origin/main` foi confirmada antes desta consolidação. O procedimento de fechamento é revisar e versionar somente README e este relatório, conferir autoria e mensagem e fazer push individual. A conferência final de sincronização é realizada após esse push.

## Referências e limites da calibração

A seção [Origem das referências e premissas da simulação](../README.md#origem-das-referências-e-premissas-da-simulação) separa referências externas das regras sintéticas. Procon Joinville / Epagri-Cepa fornecem referências de preço/contexto regional quando aplicáveis; IBGE, contexto da cadeia bovina; UNEP, justificativa sobre sustentabilidade/desperdício. São contexto e âncoras parciais, sem validação científica declarada das regras de demanda, sazonalidade, promoções, estoque ou perdas.

## Registro histórico da aplicação separada — fora desta consolidação

Na execução inicial de 26/09/2026 houve inspeção no repositório `iacarne`, HEAD `424f665`, branch `main`, sem alteração de código do frontend/backend. Os resultados abaixo são exclusivamente históricos; nenhum comando foi repetido naquele repositório nesta consolidação:

| Comando | Resultado |
|---|---|
| `npm run type-check` | Aprovado: 4 tarefas bem-sucedidas, 34,531 s |
| `npm run lint` | Falhou: ESLint 9.39.4 não encontrou `eslint.config.(js|mjs|cjs)` na API; execução global interrompida |
| `npm run build` | Falhou ao criar symlinks do pacote standalone no Windows (`EPERM`); 2 de 3 tarefas concluídas, 6 min 23 s |

O build web compilou e gerou 34 páginas, mas não concluiu o empacotamento. Também registrou chamadas de rede com `ECONNREFUSED` durante geração de páginas. Não se considera o build aprovado. Essas condições foram observadas sem mudanças da entrega acadêmica no repositório da aplicação; não foram corrigidas por estarem fora do escopo. Não existe script `check` na raiz, portanto não foi inventado ou executado.

## Aceite e limites

Os critérios técnicos da camada de dados são verificáveis pelos documentos, saídas, testes e notebook. A aplicação permanece fora do escopo desta consolidação; seus checks históricos de lint/build têm as ressalvas acima. Revisão acadêmica final, UAT real e validação com parceiro estão pendentes. Não há parceria formal comprovada. Os dados são sintéticos e não representam vendas reais do estabelecimento; dados reais futuros dependem de autorização e anonimização. O modelo de ML ainda não foi desenvolvido. Redução de desperdício e impacto ambiental são benefícios potenciais, sem comprovação empírica.

O histórico Git registra as unidades de trabalho; o controle temporário de horários de commits não integra os documentos permanentes. Não houve manipulação de datas, autoria ou versão do dataset.
