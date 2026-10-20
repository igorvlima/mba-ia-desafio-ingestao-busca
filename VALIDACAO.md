# Validação executada — 20/10/2026

## Aprovado

- Ambiente virtual Python 3.12.14; instalação das dependências e `pip check`.
- 13 testes automatizados: 9 locais e 4 com PostgreSQL/pgVector reais.
- PDF original: 67 chunks, todos com até 1.000 caracteres (maior: 999), splitter configurado com overlap 150.
- Ingestão, persistência, reingestão sem duplicação e recuperação de 10 resultados.
- Substituição do documento e preservação do anterior quando embeddings ou transação falham.
- Isolamento de coleções com dimensões distintas.
- Instanciação dos clientes LangChain para OpenAI, Google e OpenRouter, sem chamadas aos dois primeiros.
- Catálogo público do OpenRouter confirma `deepseek/deepseek-v4-flash` e `openai/text-embedding-3-small`.

Os testes do banco usaram PostgreSQL 18.6 e pgVector 0.8.1, extraídos de pacotes oficiais Ubuntu em uma pasta temporária. Usaram embeddings determinísticos locais para verificar armazenamento e distância; isso **não valida a qualidade semântica de um provedor real**.

## Pendente

- Teste de ponta a ponta com OpenRouter: a chave fornecida foi recusada com HTTP 401, `API key expired`. Nenhuma resposta do DeepSeek foi validada. Após renovar a chave, executar `python tests/integration.py` com o banco ativo.
- Docker Compose: o ambiente de desenvolvimento não possui Docker; o Compose do repositório original foi preservado, restringindo a porta ao localhost e removendo o nome fixo do container. A imagem configurada é PostgreSQL 17; sua execução ainda precisa ser validada em Docker.
- OpenAI e Google: configurados, mas não testados com credenciais reais desses provedores.

Não confundir o teste de persistência com o teste completo de RAG. Este último depende da renovação da chave.
