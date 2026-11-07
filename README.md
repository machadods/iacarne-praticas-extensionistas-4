# iaCarne

Projeto acadêmico individual de **Ciência de Dados e Inteligência Artificial**, desenvolvido na disciplina **Práticas Extensionistas IV da UNOESC**. O objetivo é prever, um dia à frente, a **venda observada em kg** de cada um dos 21 cortes bovinos da base sintética.

## Por onde começar

- [Caderno de modelagem da Sprint 5](notebooks/03_modelagem_validacao.ipynb) reúne a metodologia, o código, as tabelas e os gráficos executados.
- [Critérios de aceite e evidências](docs/criterios_aceite.md) distingue os critérios da Fase 1 dos resultados e das pendências da Sprint 5.
- [Cronograma](docs/cronograma.md) situa as etapas concluídas e planejadas.

## Resultados da Sprint 5

A matriz tem **7.077 observações**, uma por corte e dia, com 15 atributos. Os lags e as médias móveis usam vendas observadas até **D−1**. O baseline sazonal copia a venda do mesmo corte em **D−7**. Ridge e Random Forest foram comparados em uma validação cronológica. A configuração escolhida foi Ridge com `alpha=100.0` e solver `cholesky`.

| Avaliação | MAE D−7 (kg) | MAE Ridge (kg) | Diferença do Ridge |
|---|---:|---:|---|
| Teste final registrado, julho e agosto de 2026 | 1,860814 | 1,475517 | **20,7058% menor** |
| Validação cruzada complementar, três folds expansivos | 1,976585 | 2,059202 | **4,18% maior** |

O Ridge teve MAE menor em dois dos três folds. A validação cruzada foi feita retrospectivamente, depois da seleção e da avaliação final, e não orientou a escolha original. Os dois resultados correspondem a períodos e ajustes diferentes.

Os detalhes estão no [protocolo temporal](reports/sprint5/protocolo_validacao.md), na [comparação inicial](reports/sprint5/comparacao_inicial.md), na [seleção de hiperparâmetros](reports/sprint5/selecao_modelo.md), na [validação cruzada complementar](reports/sprint5/validacao_cruzada_temporal.md) e na [avaliação final](reports/sprint5/avaliacao_final.md).

O [Ridge v1](artifacts/models/iacarne_ridge_v1.joblib) contém o pré-processamento tabular e o regressor. A entrada requer os 15 atributos prontos, inclusive os históricos. Os [metadados](artifacts/models/iacarne_ridge_v1.metadata.json) registram a ordem dos atributos, os hashes e as métricas finais.

## Como executar o caderno

Na raiz do repositório, em Windows com Python 3.10.11:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -B scripts/execute_notebook.py notebooks/03_modelagem_validacao.ipynb
```

O notebook também pode ser aberto com os outputs salvos. Ao executá-lo, ele confere os hashes, reproduz o baseline da validação e os três folds no período de desenvolvimento. A comparação inicial, a seleção e o teste final são carregados dos registros existentes.

## Dados e histórico do projeto

O dataset sintético v1.0.0 cobre 01/09/2025 a 31/08/2026. A base tratada tem 7.665 observações. A matriz de modelagem começa em 29/09/2025, após o período inicial necessário para compor os históricos. A reprodução usa os arquivos fornecidos e os comandos da [documentação da Sprint 4](docs/sprint4_eda_features.md). O gerador original sobrescreve arquivos da base quando executado e fica reservado para referência. O arquivo de auditoria da demanda latente não faz parte das entradas do modelo. [Contrato e tratamento dos dados](data/README.md)

- **Fase 1:** [pré-projeto](docs/pre_projeto.md), [viabilidade](docs/viabilidade.md), [requisitos](docs/requisitos.md), [casos de uso](docs/casos_de_uso.md) e diagramas de [blocos](docs/diagramas/blocos.md), [entidades](docs/diagramas/entidades.md) e [processo](docs/diagramas/processo.md).
- **Evidências anteriores:** [auditoria inicial](docs/auditoria_inicial.md), [registro da Entrega Parcial 1](docs/validacao_entrega.md), [EDA inicial](notebooks/01_eda_inicial.ipynb) e [EDA avançada](notebooks/02_eda_avancada_features.ipynb).

## Origem das referências e premissas da simulação

Procon Joinville e Epagri-Cepa serviram de referência para preços e contexto regional, o IBGE para o contexto da cadeia bovina e o UNEP para a discussão sobre desperdício. Sazonalidade, promoções, estoque, perdas e demanda são regras da simulação. As fontes e premissas estão descritas na [especificação do dataset](iacarne_dataset_especificacao.json) e no [README original dos dados](README_dataset_iacarne.md).

## Limites e investigação complementar

Os dados são sintéticos. Vendas observadas podem ser limitadas pelo estoque e não representam necessariamente a demanda total. A EDA incluiu o período posteriormente reservado ao teste. Os resultados medem erro de previsão nessa simulação. A generalização para uma operação comercial e a redução de perdas ou rupturas ainda não foram demonstradas. A validação operacional com usuários está pendente.

Há uma investigação separada com dados comerciais reais da Corporación Favorita, família `MEATS`. O alvo `sales` tem unidade física desconhecida e representa vendas agregadas por loja e família. Isso não equivale a vendas por corte em kg, não substitui o Ridge sintético e ainda não fornece evidência de desempenho preditivo em dados reais.
