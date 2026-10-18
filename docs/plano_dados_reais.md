# Plano para uma amostra operacional real

## Objetivo e situação

Permitir futura substituição ou complementação da base sintética por uma amostra operacional autorizada. Dados reais continuam pendentes. Este plano não registra solicitação, concessão de autorização ou coleta já realizada.

## Campos mínimos desejáveis

Uma observação por produto e dia, com unidades e significado definidos:

- Data e identificação do produto/corte.
- Quantidade vendida em kg e preço por kg.
- Estoque inicial ou disponibilidade, distinguindo os dois conceitos.
- Entradas/reposição, se disponíveis.
- Promoção, quando planejada previamente, indicando quando a informação ficou disponível.

Registrar ausência de movimento separadamente de dado ausente. Não reconstruir demanda não atendida como se fosse venda real.

## Autorização e anonimização

Definir finalidade acadêmica, campos permitidos, período, acesso, armazenamento e limites de divulgação com o responsável antes da coleta. Não solicitar ou registrar nome de cliente, CPF, telefone, endereço ou outras informações pessoais desnecessárias. Remover identificadores pessoais e metadados desnecessários antes do recebimento; usar códigos de produto e identificações operacionais sem expor pessoas ou estabelecimento.

Mesmo sem dados pessoais, valores comerciais podem ser sensíveis. A publicação de amostras ou resultados depende do que for autorizado; não colocar arquivos reais no repositório público automaticamente.

## Separação e validação

Manter a amostra real em local separado, com acesso restrito, sem sobrescrever ou misturar silenciosamente o dataset sintético v1.0.0. Identificar a origem nas análises e avaliar cada base separadamente antes de qualquer combinação.

Criar um novo contrato de dados e realizar nova auditoria: schema, unidades, datas, cobertura diária, chaves, duplicatas, nulos e consistência de vendas/estoque. Conferir o significado de registros de ruptura e a disponibilidade temporal de cada campo. Documentar diferenças e adaptações necessárias antes de usar o pipeline ou as features atuais.
