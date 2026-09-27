# Processo operacional inicial

**Status: versão inicial — validação com usuário/parceiro pendente.**

```mermaid
flowchart LR
    subgraph Origem
        I([Início]) --> R[Registrar dados]
        R --> X[Exportar CSV]
    end
    subgraph Analista
        X --> E[Executar ETL]
        E --> V{Dados válidos?}
        V -- Não --> C[Inspecionar erro e origem]
        C --> E
        V -- Sim --> P[Gerar base tratada]
        P --> A[Executar análise]
    end
    subgraph Gestor
        A --> G[Consultar indicadores e limitações]
        G --> F([Fim])
    end
```

Fluxo conceitual com responsabilidades, inspirado em processo BPMN; não é arquivo BPMN 2.0 executável. Nesta entrega, registrar/exportar é substituído pelo recebimento dos arquivos sintéticos já fornecidos. Não implica coleta real, entrevista ou aprovação de cliente. O ciclo de correção exige decisão rastreável; não autoriza editar os originais.

## Representação visual BPMN

![Processo BPMN inicial com as raias Origem dos Dados, Analista e Gestor](processo_bpmn.png)

O PNG fornecido complementa o fluxo textual versionável acima com a representação visual BPMN inicial. Ambos descrevem o mesmo processo: o caminho de dados inválidos retorna à execução do ETL após inspeção; o caminho válido segue para base tratada, EDA e consulta dos indicadores. A etapa de origem representa o recebimento dos arquivos sintéticos nesta entrega. O [diagrama de blocos](blocos.md) descreve a arquitetura de dados, e o [E/R](entidades.md), as entidades conceituais.

**Versão inicial — validação com usuário/parceiro pendente.**
