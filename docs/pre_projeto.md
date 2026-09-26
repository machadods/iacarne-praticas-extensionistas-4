# Pré-projeto — iaCarne

## Assunto
Ciência de Dados aplicada ao comércio varejista de carnes.

## Tema
Análise de dados operacionais de vendas e estoque para apoiar a previsão de demanda de produtos cárneos.

## Título
**iaCarne — Sistema Inteligente para Análise e Previsão de Demanda de Produtos Cárneos**

Slogan: “O melhor corte da cidade, onde você estiver.”

## Delimitação
A Entrega Parcial 1 de Práticas Extensionistas IV compreende documentação acadêmica, pipeline local em Python, base tratada e análise exploratória. O dataset oficial 1.0.0 é sintético: 21 cortes bovinos, observações diárias de 01/09/2025 a 31/08/2026, 7.665 combinações dia/corte e 7.680 linhas brutas com duplicatas controladas. Não representa vendas reais de estabelecimento algum.

A entrega acadêmica ocupa repositório próprio. A aplicação iaCarne existente permanece em repositório separado, com frontend Next.js 15, TypeScript, App Router, CSS Modules, Zod e Lucide React. Esta fase não implementa integração entre a aplicação e o pipeline, nem modifica suas funcionalidades comerciais.

## Problema
Registros dispersos ou inconsistentes dificultam comparar vendas, disponibilidade e perdas. A venda observada também pode subestimar a demanda quando o estoque limita o atendimento. A primeira necessidade é organizar os registros e tornar sua qualidade verificável.

## Questão de pesquisa
Como utilizar dados de vendas, estoque e perdas para produzir informações capazes de apoiar o planejamento de demanda de produtos cárneos e reduzir situações de excesso ou falta de estoque?

## Hipóteses
A organização e análise estruturada dos dados de vendas e estoque permitem identificar padrões de consumo e sazonalidade que podem posteriormente apoiar modelos de previsão de demanda e melhorar o planejamento operacional.

Como hipótese complementar, indicadores de perdas e ruptura podem orientar a investigação de desequilíbrios entre disponibilidade e vendas. Nenhuma hipótese é considerada comprovada nesta fase: padrões do dataset podem decorrer diretamente das regras do simulador.

## Justificativa
O acadêmico conhece a rotina de açougue por sua atuação profissional. A indisponibilidade de histórico autorizado motiva o uso inicial de dados sintéticos, sem dados pessoais reais. Um pipeline pequeno, documentado e reproduzível permite estudar o problema e preparar a substituição da fonte no futuro.

## Relevância regional
O recorte considera o comércio e processamento de carnes em Santa Catarina e no Oeste Catarinense. A proposta busca aproximar pequenos estabelecimentos de ferramentas de análise operacional, com foco em controle de estoque e desperdício. Não pressupõe parceria formal, pesquisa de campo concluída ou representatividade estatística regional. Indicadores quantitativos regionais dependerão de fontes verificadas e identificadas.

## Sustentabilidade
O impacto potencial segue a cadeia: melhor previsão de demanda → melhor planejamento de compras → menor estoque excessivo → redução de perdas → uso mais eficiente de recursos. Nesta fase, mede-se o comportamento de perdas simuladas; não se declara redução ambiental comprovada.

## Impacto social
O acesso a indicadores compreensíveis pode apoiar decisões de pequenos comerciantes e a formação técnica do acadêmico. Benefícios a trabalhadores e consumidores precisarão ser avaliados em aplicação futura autorizada, com participação dos usuários.

## Potencial de inovação
A proposta combina conhecimento operacional do domínio, rastreabilidade do tratamento e análise temporal por corte. A contribuição desta fase é uma base confiável e inspecionável, sem alegar novidade científica ou desempenho preditivo ainda não medido.

## Empreendedorismo
Uma evolução possível é oferecer apoio à gestão de demanda para pequenos açougues. Viabilidade comercial, disposição a pagar e retorno financeiro não foram pesquisados; não são resultados desta entrega.

## Objetivo geral
Desenvolver um pipeline de dados para coleta, validação, limpeza, transformação e análise exploratória de registros de vendas e estoque de produtos cárneos, preparando uma base confiável para futura modelagem de previsão de demanda.

## Objetivos específicos
- Estruturar a entrada oficial e preservar sua origem e versão.
- Desenvolver extração, validação, transformação e exportação reproduzíveis.
- Identificar nulos, duplicatas, tipos inválidos e inconsistências operacionais.
- Produzir dataset tratado com rastreabilidade das correções.
- Analisar vendas por corte e período, preços, estoque, perdas e promoções.
- Investigar padrões temporais sem confundir associação com causalidade.
- Documentar restrições de uso e riscos de vazamento de informação para futura modelagem.

## Metodologia
Pesquisa aplicada, exploratória e quantitativa sobre dados sintéticos. Primeiro, auditar os seis arquivos oficiais e registrar integridade; depois, especificar requisitos e casos de uso, implementar ETL, testar regras e reprodutibilidade e executar EDA. O CSV bruto é a única entrada operacional. O XLSX é material documental; o ground truth fica restrito à auditoria e nunca fornece features ou valores para correção do ETL.

As regras de geração, seed 26092026 e metadados permanecem na versão 1.0.0 fornecida. O gerador será preservado sem execução nesta entrega. A qualidade será avaliada por completude, unicidade, domínio, consistência aritmética e temporal. A EDA usará estatísticas e gráficos com interpretações e limitações explícitas.

## Implantação
A Fase 1 será executada localmente, com Python, CSV, notebook e Git. A sequência será documentada e testada. Uma demonstração futura poderá apoiar avaliação por gestor, mas entrevista, parceria, implantação comercial e aceite pelo usuário não ocorreram nesta execução. A integração com a aplicação depende de fase posterior.

## Limitações
Um ano simulado não comprova sazonalidade recorrente nem generalização para estabelecimentos reais. Custos são estimados; vendas podem ser censuradas por ruptura. Dados reais futuros exigirão autorização e anonimização. UAT está pendente. Não haverá treinamento de ML, API de inferência, deploy ou novos módulos comerciais nesta fase.

## Fontes do projeto
As definições de origem e versão são as de [iacarne_dataset_especificacao.json](../iacarne_dataset_especificacao.json). O [README oficial do dataset](../README_dataset_iacarne.md) integra a documentação da entrega. Suas referências públicas são referências declaradas pelo fornecedor, e não uma validação independente de calibração realizada nesta etapa.
