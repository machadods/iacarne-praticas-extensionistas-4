# Estudo de viabilidade

## Técnica
O volume oficial de 7.680 linhas e 26 colunas permite processamento local em Python, sem banco ou infraestrutura distribuída. CSV facilita inspeção e interoperabilidade; notebooks permitem relacionar estatísticas, gráficos e interpretação. Git registra evolução e revisão das regras. A aplicação Next.js existente permanece independente: a Fase 1 não exige servidor web nem integração. Dashboard é possibilidade futura.

O ambiente identificado possui Windows, Python 3.10.11 e Git. As versões efetivamente usadas e comandos de reprodução serão documentados no fechamento. A experiência profissional do acadêmico contribui para interpretar o domínio, mas não substitui validação externa. O risco técnico principal está nas regras de qualidade, na granularidade e na interpretação de vendas limitadas pelo estoque, e não na escala computacional.

## Operacional
O problema deriva do conhecimento da rotina de açougue informado pelo acadêmico. A primeira versão pode ser demonstrada localmente, sem acessar sistemas do empregador. Não existe parceria formal ou aceite de cliente comprovado nesta entrega. Avaliação com gestor, entrevistas e UAT permanecem pendentes; suas evidências só serão registradas se ocorrerem.

## Dados
A versão 1.0.0 fornecida é sintética, sem dados pessoais reais, com premissas operacionais explícitas. São 365 dias e 21 cortes, totalizando 7.665 observações-base, acrescidas de 15 duplicatas no bruto. A inspeção confirmou correspondência entre CSV e abas de dados do XLSX. O gerador e os metadados serão preservados.

As lacunas controladas de estoque inicial podem ser reconstruídas pela identidade estoque disponível menos entrada, desde que a consistência seja validada. Os eventos vazios significam ausência de evento selecionado pelo simulador; não representam erro de preenchimento. A demanda latente pertence exclusivamente à auditoria e não será utilizada pelo ETL nem pela EDA operacional.

A base permite verificar o funcionamento do pipeline; não prova comportamento comercial real nem eficácia preditiva. Dados reais futuros dependem de autorização, anonimização, contrato de campos e nova auditoria. Mudanças na origem ou nas regras exigirão avaliação de compatibilidade e versionamento explícito, sem sobrescrever a versão oficial.

## Temporal
A Fase 1 abrange pré-projeto, viabilidade, requisitos, casos de uso, diagramas, dados, ETL e EDA. O cronograma é orientado por dependências e critérios verificáveis, sem inventar data de entrega institucional. O intervalo mínimo real de 30 minutos entre commits é uma restrição do roteiro e pode exigir espera após validação da unidade de trabalho.

Engenharia de atributos para previsão, baseline, modelos, avaliação temporal e integração de interface pertencem à fase posterior. O protótipo de baixa fidelidade é opcional e não deve comprometer os itens obrigatórios.

## Econômica
A execução local aproveita o computador e as ferramentas disponíveis. Não requer contratação de nuvem ou serviço pago. Não foram medidos custo de trabalho, economia de perdas ou retorno financeiro; a viabilidade comercial continua em aberto.

## Manutenção
Módulos pequenos de extração, validação, transformação e exportação reduzem acoplamento. Dependências devem ser limitadas ao uso efetivo e fixadas no ambiente validado. Testes precisam cobrir integridade, regras aritméticas, erros de entrada, determinismo e separação do ground truth. Documentação deve permitir reprodução sem edição manual dos CSVs.

## Riscos e encaminhamentos

| Risco | Efeito | Encaminhamento |
|---|---|---|
| Interpretar simulação como histórico real | Conclusões indevidas | Identificar natureza sintética em documentos, notebook e gráficos |
| Vazamento de resultados do dia | Avaliação futura artificialmente favorável | Separar alvo, indicadores posteriores e atributos disponíveis no momento da previsão |
| Ruptura censurar vendas | Subestimar demanda | Analisar incidência e limitar interpretação; não imputar demanda latente |
| Alterar originais | Perder rastreabilidade | Hashes, cópias verificadas e saída em diretório próprio |
| Generalizar um único ano | Alegar sazonalidade não demonstrada | Tratar padrões como exploratórios e decorrentes de premissas |
| Ausência de UAT | Usabilidade não comprovada | Registrar pendência e planejar avaliação futura |

## Parecer
A execução técnica da Fase 1 é viável no ambiente local com o dataset fornecido. Essa conclusão diz respeito à construção e verificação do pipeline e da análise exploratória; impacto operacional, aceitação por usuários e benefício econômico dependem de avaliação posterior.
