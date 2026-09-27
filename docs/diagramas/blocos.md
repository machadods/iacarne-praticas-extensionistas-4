# Fluxo de dados

```mermaid
flowchart TD
    R[CSV bruto oficial] --> E[Extração]
    E --> V[Validação de schema]
    V --> L[Limpeza e tipos]
    L --> T[Transformação e validação operacional]
    T --> P[Dataset tratado e relatório]
    P --> A[EDA local]
    A -. Fase posterior .-> F[Engenharia de atributos]
    F -.-> M[Modelo futuro]
    M -.-> D[Dashboard iaCarne futuro]
    S[Especificação e contrato] --> V
    G[Ground truth] --> Q[Auditoria isolada]
```

O ground truth não alimenta extração, transformação, EDA operacional ou atributos. A aplicação existente permanece em repositório separado, sem dependência do pipeline. Setas tracejadas representam trabalho fora da Fase 1.
