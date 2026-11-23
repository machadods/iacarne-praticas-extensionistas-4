# iaCarne

Projeto acadêmico individual de **Ciência de Dados e Inteligência Artificial**, desenvolvido na disciplina **Práticas Extensionistas IV da UNOESC**. O objetivo é prever, um dia à frente, a **venda observada em kg** de cada um dos 21 cortes bovinos da base sintética.

## Por onde começar

- [Caderno de modelagem da Sprint 5](notebooks/03_modelagem_validacao.ipynb) reúne a metodologia, o código, as tabelas e os gráficos executados.
- [Critérios de aceite e evidências](docs/criterios_aceite.md) distingue os critérios originais da Fase 1 das evidências e pendências das Sprints 5 e 6.
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

## Previsão de um dia à frente

O adaptador `modeling.inference.predict_next_day(historico)` recebe um DataFrame com `data`, `produto_id`, `corte`, `categoria_anatomica`, `perfil_uso` e `quantidade_vendida_kg`. Cada produto precisa dos últimos 28 dias civis completos, com encerramento na mesma data e metadados do catálogo oficial. O retorno traz a data seguinte, a previsão em kg, a referência D−7 e a identificação do modelo sintético. Previsões negativas interrompem o lote com erro explícito e informação do valor.

```powershell
.\.venv\Scripts\python.exe -B -X utf8 -m modeling.inference
```

Esse comando demonstra a previsão de **01/09/2026** usando a base sintética encerrada em **31/08/2026**. Para outro histórico, informe o caminho do CSV como argumento. A data prevista acompanha o histórico fornecido.

## Dashboard beta local

Use Python 3.10.11 e reutilize o `.venv` existente. Para uma instalação nova, a preparação do ambiente está em [Como executar o caderno](#como-executar-o-caderno). Execute na raiz do projeto e abra `http://127.0.0.1:8501`.

```powershell
.\.venv\Scripts\python.exe -B -m streamlit run app.py --server.address 127.0.0.1 --browser.gatherUsageStats false
```

Selecione um corte, consulte o gráfico e as 28 observações mais recentes e clique em **Prever próximo dia**. A demonstração usa dados sintéticos até 31/08/2026 e prevê 01/09/2026. Também é possível carregar um CSV de até 5 MiB com o contrato descrito acima, processado em memória. A autorização de uso deve ser confirmada pelo responsável pelo arquivo. Os erros de validação e as previsões negativas são apresentados na página.

### Demonstração acadêmica em 3 a 5 minutos

1. Abra o dashboard pelo comando acima.
2. Explique que o Ridge v1 foi treinado com dados sintéticos de 21 cortes bovinos.
3. Selecione **Acém** ou **Picanha**.
4. Mostre as 28 observações de 04/08 a 31/08/2026, a tabela e o gráfico de vendas observadas.
5. Clique em **Prever próximo dia** e destaque **Previsão para 01/09/2026**.
6. Compare os cartões Ridge e D−7. Para Acém, mostram 24,420 kg e 22,780 kg. Para Picanha, 9,590 kg e 7,670 kg. O baseline repete a venda do mesmo corte sete dias antes.
7. Explique que o valor estima a venda observada em kg, que pode ser limitada pelo estoque. A demanda não atendida fica fora do alvo. O erro da previsão só pode ser calculado quando a venda do dia previsto estiver disponível.
8. Em **CSV autorizado**, carregue `valido.csv` preparado abaixo e gere a previsão de Acém. Depois, carregue `insuficiente.csv` e mostre a rejeição do histórico de 27 dias.

Antes da apresentação, prepare os dois CSVs em outro terminal, na raiz do projeto. O comando usa somente a base sintética tratada e grava as cópias em uma pasta temporária externa ao repositório. O caminho é exibido ao terminar.

```powershell
@'
from pathlib import Path
import tempfile
import pandas as pd
from modeling.inference import HISTORY_COLUMNS
base = pd.read_csv("data/processed/iacarne_vendas_tratado.csv", usecols=list(HISTORY_COLUMNS))
historico = base.loc[base.produto_id.eq("acem")].tail(28)
pasta = Path(tempfile.mkdtemp(prefix="iacarne_demo_"))
historico.to_csv(pasta / "valido.csv", index=False)
historico.iloc[1:].to_csv(pasta / "insuficiente.csv", index=False)
print(pasta)
'@ | .\.venv\Scripts\python.exe -B -
```

Remova essas cópias temporárias depois da demonstração. O dashboard lê o arquivo enviado em memória, com limite de 5 MiB verificado no upload e antes do processamento.

O fechamento técnico S6-C foi verificado em 23/11/2026 no ambiente atual, com 65 testes aprovados, execução pelo navegador e hashes protegidos conferidos. A [tabela de conformidade da Sprint 6](docs/criterios_aceite.md) registra as evidências e as pendências acadêmicas.

## Dados e histórico do projeto

O dataset sintético v1.0.0 cobre 01/09/2025 a 31/08/2026. A base tratada tem 7.665 observações. A matriz de modelagem começa em 29/09/2025, após o período inicial necessário para compor os históricos. A reprodução usa os arquivos fornecidos e os comandos da [documentação da Sprint 4](docs/sprint4_eda_features.md). O gerador original sobrescreve arquivos da base quando executado e fica reservado para referência. O arquivo de auditoria da demanda latente não faz parte das entradas do modelo. [Contrato e tratamento dos dados](data/README.md)

- **Fase 1:** [pré-projeto](docs/pre_projeto.md), [viabilidade](docs/viabilidade.md), [requisitos](docs/requisitos.md), [casos de uso](docs/casos_de_uso.md) e diagramas de [blocos](docs/diagramas/blocos.md), [entidades](docs/diagramas/entidades.md) e [processo](docs/diagramas/processo.md).
- **Evidências anteriores:** [auditoria inicial](docs/auditoria_inicial.md), [registro da Entrega Parcial 1](docs/validacao_entrega.md), [EDA inicial](notebooks/01_eda_inicial.ipynb) e [EDA avançada](notebooks/02_eda_avancada_features.ipynb).

## Origem das referências e premissas da simulação

Procon Joinville e Epagri-Cepa serviram de referência para preços e contexto regional, o IBGE para o contexto da cadeia bovina e o UNEP para a discussão sobre desperdício. Sazonalidade, promoções, estoque, perdas e demanda são regras da simulação. As fontes e premissas estão descritas na [especificação do dataset](iacarne_dataset_especificacao.json) e no [README original dos dados](README_dataset_iacarne.md).

## Limites e investigação complementar

Os dados são sintéticos. Vendas observadas podem ser limitadas pelo estoque e não representam necessariamente a demanda total. A EDA incluiu o período posteriormente reservado ao teste. Os resultados medem erro de previsão nessa simulação. O Ridge v1 ainda não foi validado com vendas reais do supermercado. A generalização para uma operação comercial e a redução de perdas ou rupturas ainda não foram demonstradas. A validação operacional com usuários está pendente.

A Corporación Favorita é um experimento complementar com dados comerciais reais da família `MEATS`. O alvo `sales` representa vendas agregadas por loja e família, com unidade física desconhecida e sem equivalência com vendas por corte bovino em kg. O experimento está na etapa de preparação dos dados. [Guia do experimento Favorita](experiments/favorita/README.md)

Uma futura amostra operacional do açougue depende de autorização. [Plano para dados operacionais reais](docs/plano_dados_reais.md)
