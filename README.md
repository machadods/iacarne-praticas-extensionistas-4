# iaCarne — Entrega Parcial 1

**Sistema Inteligente para Análise e Previsão de Demanda de Produtos Cárneos**

“O melhor corte da cidade, onde você estiver.”

Projeto de **Práticas Extensionistas IV**: documentação acadêmica, pipeline Python, base tratada e EDA para preparar futura previsão de demanda. Os dados são **sintéticos**, não representam vendas reais e não contêm dados pessoais reais. Esta fase não treina modelos nem implementa integração comercial.

## Documentação acadêmica

- [Pré-projeto](docs/pre_projeto.md)
- [Viabilidade](docs/viabilidade.md)
- [Requisitos](docs/requisitos.md) e [critérios de aceite](docs/criterios_aceite.md)
- [Casos de uso](docs/casos_de_uso.md) e [cronograma](docs/cronograma.md)
- Diagramas: [blocos](docs/diagramas/blocos.md), [entidades](docs/diagramas/entidades.md), [fluxo textual](docs/diagramas/processo.md) e [BPMN visual](docs/diagramas/processo_bpmn.png). BPMN em versão inicial — validação com usuário/parceiro pendente.
- [Auditoria inicial](docs/auditoria_inicial.md) e [regras de dados](data/README.md)
- [Resultados das validações e limitações](docs/validacao_entrega.md)

## Arquitetura e estrutura

```text
CSV bruto → extract → validate/transform → load → CSV tratado → EDA
```

```text
data/raw/             cópia integral da entrada oficial
data/processed/       CSV tratado e relatório JSON do pipeline
docs/                 documentos acadêmicos, auditoria, Mermaid e BPMN visual
pipeline/             extração, contrato, transformação e exportação
notebooks/            01_eda_inicial.ipynb
reports/              tabelas, resumo e gráficos da EDA
scripts/              execução reproduzível do notebook
tests/                testes de qualidade, erros e reprodutibilidade
requirements.txt      dependências diretas da EDA, fixadas
```

Os seis arquivos fornecidos permanecem na raiz. A aplicação iaCarne está em **outro repositório**, com frontend Next.js 15/TypeScript e monorepositório `apps/web`, `apps/api`, `packages`. Esta entrega não altera a aplicação e não depende de Node, serviços de backend ou suas credenciais. Não há dashboard integrado: os indicadores são consultados no notebook e nos relatórios.

## Dataset oficial

Versão **1.0.0**, seed **26092026**, período **01/09/2025 a 31/08/2026**, 21 cortes bovinos. São 7.680 linhas brutas e 7.665 observações únicas, uma por dia/corte. A origem e as referências declaradas constam na [especificação oficial](iacarne_dataset_especificacao.json) e no [README fornecido](README_dataset_iacarne.md), incorporado por referência.

- `iacarne_vendas_bruto.csv`: entrada oficial; sua cópia em raw alimenta o ETL.
- `iacarne_ground_truth_auditoria.csv`: auditoria exclusivamente; não alimenta ETL, EDA operacional ou features.
- `iacarne_dataset_especificacao.json`: metadados e origem.
- `generate_iacarne_dataset.py`: gerador original preservado, não executado nesta entrega.
- `iacarne_dataset_v1.xlsx`: material auxiliar/documental; não é fonte do pipeline.
- `README_dataset_iacarne.md`: documentação original preservada.

**Não executar o gerador para reproduzir esta entrega:** executar o ETL sobre os dados fornecidos. A execução direta do gerador original sobrescreve arquivos na sua pasta. A integridade dos originais é verificável pelo [manifesto SHA-256](docs/integridade_dataset.json) e pelos testes.

## Origem das referências e premissas da simulação

| Elemento | Natureza/origem |
|---|---|
| Preços de referência e contexto regional | Referências públicas do Procon Joinville / Epagri-Cepa, quando aplicáveis |
| Contexto da cadeia bovina | IBGE |
| Justificativa sobre sustentabilidade e desperdício | UNEP |
| Fatores por dia da semana | Premissa sintética |
| Fatores mensais | Premissa sintética |
| Efeito de promoções | Premissa sintética |
| Política de estoque | Premissa sintética |
| Taxas de perdas | Premissa sintética |
| Demanda-base por corte | Premissa sintética |

As referências públicas servem como contexto e âncoras parciais de calibração. As regras de comportamento operacional, sazonalidade, estoque, promoções, perdas e demanda são premissas sintéticas da simulação e não devem ser atribuídas às fontes externas.

As fontes e seus links são os declarados na [especificação oficial](iacarne_dataset_especificacao.json) e no [README original do dataset](README_dataset_iacarne.md). Não se afirma validação científica das premissas ou calibração integral a uma operação comercial real. Os registros não representam vendas reais do estabelecimento.

## Instalação e execução

Ambiente de referência: Windows e Python **3.10.11**. O ETL e os testes usam somente a biblioteca padrão; as dependências abaixo são necessárias ao notebook. Execute na raiz deste repositório.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pipeline.run_pipeline
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe scripts/execute_notebook.py
```

Alternativamente, ative o ambiente no PowerShell com `.\.venv\Scripts\Activate.ps1` e use `python` nos comandos. Os caminhos explícitos acima dispensam alteração da política de execução do PowerShell.

Em Linux/macOS, o equivalente é `python3 -m venv .venv`, `source .venv/bin/activate`, `python -m pip install -r requirements.txt` e os mesmos comandos Python. Essa alternativa deve ser validada no respectivo sistema; o ambiente testado nesta entrega é Windows.

O notebook pode ser aberto em editor compatível com `.ipynb`, selecionando o Python da `.venv`. A execução automatizada não exige instalar ou configurar um servidor Jupyter: o script cria um kernel temporário com o mesmo interpretador e salva o notebook após execução integral. Se ocorrer erro, a exceção é apresentada e o notebook anterior não é substituído por uma execução incompleta.

## Pipeline e saídas

```powershell
python -m pipeline.run_pipeline --help
python -m pipeline.run_pipeline --output-dir data/processed_reproducao
```

Saídas padrão: `data/processed/iacarne_vendas_tratado.csv` e `data/processed/relatorio_pipeline.json`. O segundo comando é opcional para comparar uma execução em diretório distinto; esse diretório não faz parte dos entregáveis.

O relatório contabiliza entrada, saída, nulos, duplicatas, rejeições e correções por chave. O pipeline converte preços com vírgula, padroniza nomes, reconstrói estoques iniciais ausentes pela identidade disponível − entrada e verifica saldos, valores monetários, calendário, continuidade e cobertura. Erros críticos interrompem a execução antes de publicar nova saída. Consulte [as regras e limitações de escrita](data/README.md).

São acrescentados `estoque_inicial_reconstruido`, controle de qualidade, e `ano_semana_iso`, necessário para agrupar semanas sem confundir ano civil com ano ISO. Essas colunas não tornam a base uma matriz pronta de atributos preditivos.

## EDA

O [notebook](notebooks/01_eda_inicial.ipynb) apresenta qualidade, dimensões, tipos, estatísticas, volume por corte, evolução temporal, quantidades, preços, faturamento, estoque, perdas, promoções, calendário e correlações. Cada gráfico possui interpretação e é salvo em `reports/figures/`. Resumo e tabelas são exportados em `reports/`.

Médias e fechamentos representam estoque no período; somas temporais de saldo não são interpretadas como estoque físico. Comparações promocionais são descritivas, sem inferência causal.

## Resultados principais da Fase 1

| Evidência | Resultado |
|---|---|
| ETL | 7.680 linhas brutas → 7.665 tratadas; 21 cortes e 365 dias |
| Tratamento | 15 duplicatas removidas, 19 preços normalizados, 23 estoques iniciais reconstruídos e 38 nomes padronizados |
| Testes | 11 aprovados no checkpoint técnico `f726709`, incluindo determinismo, integridade dos originais e isolamento do ground truth |
| EDA | Notebook com 19 células de código executadas, outputs salvos e 8 gráficos |
| Volume e receita simulados | 114.254,29 kg e R$ 5.275.616,69 |
| Perdas e ruptura simuladas | 371,71 kg de perdas; ruptura em 16,20% dos dias/corte |

Esses valores descrevem a base sintética; não medem desempenho de um estabelecimento real. As evidências e limitações estão no [relatório de validação](docs/validacao_entrega.md).

## Limitações e roadmap

Dataset sintético, um ano de observações e padrões impostos pelo gerador. Dados reais ainda não foram utilizados e seu uso futuro depende de autorização e anonimização. UAT real ainda não ocorreu; a validação com parceiro está pendente e não há parceria formal comprovada. O modelo de ML ainda não foi desenvolvido. Redução de desperdício e benefício ambiental são impactos potenciais, não resultados comprovados. Vendas podem ser menores que demanda por ruptura. Custos são estimados.

Para previsão antes da operação, não usar o resultado do mesmo dia: perdas, estoque final, ruptura, receita, custo total e margem; demanda latente nunca é feature. Preço, promoção, desconto e reposição dependerão de disponibilidade no instante da previsão. Uma fase futura deve definir horizonte, baseline e validação temporal, avaliando MAE/RMSE e, se adequado, MAPE.

Próximas etapas: avaliação acadêmica e com usuários; autorização e anonimização de dados reais; revisão do contrato; engenharia de atributos e baseline; somente depois, modelos e eventual interface integrada. O protótipo opcional não integra esta entrega.
