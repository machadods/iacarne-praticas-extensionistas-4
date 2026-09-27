# Casos de uso

Ator administrador/analista: executa os comandos e inspeciona qualidade. Ator gestor: consulta os resultados documentados e o notebook; não há dashboard integrado nesta fase.

## UC01 — Importar registros de vendas
- Ator: administrador/analista.
- Pré-condição: CSV oficial e metadados disponíveis; originais preservados.
- Fluxo: indicar entrada → ler UTF-8 → verificar cabeçalhos → registrar contagem.
- Alternativas: arquivo ausente, CSV ilegível ou schema incompatível interrompem a execução com mensagem explícita.
- Pós-condição: dados em memória prontos para validação; nenhum original alterado.
- Rastreabilidade: RF01, RF02; CA02, CA03.

## UC02 — Executar pipeline de tratamento
- Ator: administrador/analista.
- Pré-condição: importação válida e regras compatíveis com a versão 1.0.0.
- Fluxo: contar nulos → remover duplicatas idênticas → converter tipos → normalizar cortes → reconstruir estoque inicial permitido → validar saldos, calendário e cobertura → ordenar → exportar relatório e base.
- Alternativas: chave conflitante, tipo inválido ou saldo inconsistente bloqueiam a exportação; corrigir a origem autorizada ou revisar regras em nova versão, nunca editar silenciosamente o bruto.
- Pós-condição: base tratada e relatório rastreáveis; falhas são explícitas.
- Rastreabilidade: RF02, RF03, RF08; CA04 a CA08.

## UC03 — Visualizar indicadores de vendas
- Ator: gestor, com apoio do analista para execução local.
- Pré-condição: ETL concluído e notebook executado.
- Fluxo: abrir notebook → consultar volume por corte e período → examinar preço, receita, estoque, perdas, promoções e ruptura → ler interpretações e limitações.
- Alternativa: base ausente ou inválida exige executar/corrigir o ETL antes da análise.
- Pós-condição: indicadores exploratórios disponíveis; nenhuma decisão automatizada.
- Rastreabilidade: RF04, RF07; CA09.

## UC04 — Exportar dataset tratado
- Ator: administrador/analista.
- Pré-condição: todas as validações críticas aprovadas.
- Fluxo: ordenar por data/produto → gravar CSV em processed → gravar relatório → conferir contagens e hashes.
- Alternativas: destino protegido ou falha de escrita interrompem o comando; não apontar saídas para originais.
- Pós-condição: arquivo reproduzível disponível a análises posteriores.
- Rastreabilidade: RF05, RNF02, RNF06; CA05, CA07.

## UC05 — Consultar previsão de demanda
- Ator: gestor.
- Status: **futuro / Fase 2**, não implementado.
- Pré-condições futuras: baseline, avaliação temporal e interface definidos e validados.
- Fluxo futuro: selecionar produto e horizonte → consultar previsão e incerteza → comparar com capacidade operacional.
- Pós-condição futura: subsídio à decisão humana, sujeito à validação.
- Rastreabilidade: RF06 apenas como preparação, sem critério de modelo treinado na Fase 1.

Status geral: especificação inicial; validação com usuário/parceiro pendente.
