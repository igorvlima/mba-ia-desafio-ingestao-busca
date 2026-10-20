# Ingestão de PDF e busca semântica

Implementação do [desafio Full Cycle](https://github.com/devfullcycle/mba-ia-desafio-ingestao-busca), com Python, LangChain, PostgreSQL e pgVector. O PDF original do desafio está incluído.

- `src/ingest.py`: PyPDFLoader → chunks de até 1.000 caracteres, overlap configurado em 150 → embeddings → PostgreSQL.
- `src/search.py`: vetoriza a pergunta, recupera até 10 chunks com `similarity_search_with_score(query, k=10)` e chama a LLM com o prompt do enunciado.
- `src/chat.py`: interação pelo terminal; `sair`, `exit`, `quit`, Ctrl+C ou Ctrl+D encerram.
- `src/config.py`, `providers.py`, `store.py`: configuração, clientes e armazenamento.

## Requisitos

Python 3.12 (versão validada), Docker Engine com Docker Compose v2 e uma chave com acesso aos modelos escolhidos. Não é necessário ter chaves dos três provedores. Os serviços de IA podem cobrar por uso; disponibilidade e cotas dependem da conta.

## Configuração

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.lock.txt
cp .env.example .env
```

`requirements.txt` declara dependências diretas; `requirements.lock.txt` registra as versões resolvidas e testadas. No Ubuntu, se `venv` falhar por falta de `ensurepip`, instale o pacote `python3-venv` correspondente ao seu Python.

Preencha **uma** das chaves no `.env`. O provedor será detectado automaticamente. Se preencher mais de uma, defina `AI_PROVIDER=openai`, `google` ou `openrouter`. Variáveis exportadas no terminal têm prioridade sobre o `.env`.

| Provedor | Variável | LLM padrão | Embeddings padrão |
|---|---|---|---|
| OpenAI | `OPENAI_API_KEY` | `gpt-4.1-mini` | `text-embedding-3-small` |
| Google | `GOOGLE_API_KEY` | `gemini-3.5-flash-lite` | `gemini-embedding-001` |
| OpenRouter | `OPENROUTER_API_KEY` | `deepseek/deepseek-v4-flash` | `openai/text-embedding-3-small` |

No OpenRouter, **ambos** os modelos são acessados com a chave OpenRouter. Não precisa de uma chave OpenAI. DeepSeek gera respostas; o modelo de embeddings gera vetores.

Também é possível deixar `OPENROUTER_API_KEY` vazio e configurar `OPENROUTER_API_KEY_FILE=/caminho/seguro/chave.txt`. O arquivo deve conter somente a chave. Não versione esse arquivo. `.env`, ambientes virtuais e caches estão no `.gitignore`.

Para mudar modelos, preencha `LLM_MODEL` e/ou `EMBEDDING_MODEL`. Deixe vazios para usar os padrões. Use os IDs do provedor escolhido; no OpenRouter, eles incluem o prefixo do fornecedor. Ao mudar de provedor, remova overrides do provedor anterior.

## Execução

```bash
# 1. Banco (espere ficar healthy)
docker compose up -d
docker compose ps

# 2. Ingestão
python src/ingest.py

# 3. Chat
python src/chat.py
```

O serviço `bootstrap_vector_ext` terminar com código 0 é normal: ele cria a extensão e encerra. `PGVector` também garante sua criação. O banco usa o Compose do repositório original, com a porta restrita ao computador local e sem nome fixo de container.

Exemplo baseado na primeira página do PDF incluído:

```text
PERGUNTA: Qual o faturamento da Alfa Agronegócio Indústria?
RESPOSTA: O faturamento da Alfa Agronegócio Indústria é de R$ 85.675.568,77.

PERGUNTA: Qual é a capital da França?
RESPOSTA: Não tenho informações necessárias para responder sua pergunta.
```

O texto exato da resposta factual pode variar. Não há histórico de conversa: cada pergunta deve ser completa. O prompt exige fatos explícitos e recusa perguntas sem evidência; isso reduz alucinações, mas não constitui garantia matemática de comportamento da LLM.

## PDF e coleções

`PDF_PATH` é relativo à raiz do projeto ou absoluto. PDFs digitalizados sem camada de texto precisam de OCR antes da ingestão; este projeto não executa OCR. Metadados armazenam o nome do arquivo, página (começa em 1) e índice do chunk.

Cada ingestão **substitui o PDF da coleção atual**. Repetir o comando não duplica os chunks. Embeddings são gerados antes de iniciar a transação que substitui os registros; falhas nessa etapa preservam o documento anterior. Não execute ingestões concorrentes na mesma coleção.

O nome físico da coleção combina `COLLECTION_NAME` com um hash do provedor e do modelo de embeddings. Mudar apenas a LLM mantém os dados. Mudar o modelo de embeddings ou o provedor seleciona outra coleção, que precisa de nova ingestão. Mesmo dimensões iguais não tornam espaços de embeddings intercambiáveis.

`PGVector` compartilha uma tabela entre coleções. Este projeto usa a coluna `vector` sem dimensão fixa (`embedding_length` omitido), para permitir dimensões diferentes em coleções distintas. A busca é filtrada pela coleção. Isso evita o conflito de dimensão descrito no enunciado, sem misturar vetores de modelos diferentes. Não há índice ANN; a busca exata é suficiente para o PDF do desafio.

Se reaproveitar um banco criado por outra implementação com dimensão fixa, use um banco novo. Para apagar **todos os dados deste Compose** e recriar do zero (ação destrutiva):

```bash
docker compose down -v
docker compose up -d
python src/ingest.py
```

## Testes

Testes locais, sem chave e sem banco:

```bash
python -m unittest discover -s tests -v
```

Testes com PostgreSQL real e embeddings determinísticos (sem consumir API):

```bash
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/rag python -m unittest discover -s tests -v
```

Teste de integração real com banco e provedor configurados (consome API e substitui apenas uma coleção de teste temporária):

```bash
python tests/integration.py
```

O teste usa o PDF incluído, verifica persistência, reingestão sem duplicação, recuperação e respostas dentro/fora do contexto. A coleção temporária é apagada ao final. Consulte `VALIDACAO.md` para o que efetivamente foi executado.

## Solução de problemas

- **Banco indisponível**: confira `docker compose ps`, `docker compose logs postgres` e `DATABASE_URL`. O padrão é `postgresql+psycopg://postgres:postgres@localhost:5432/rag`.
- **Porta 5432 ocupada**: altere a porta do host no Compose e a mesma porta em `DATABASE_URL`.
- **Coleção vazia**: execute a ingestão usando o mesmo provedor, modelo de embeddings e `COLLECTION_NAME` do chat.
- **Erro de autenticação, limite ou modelo**: confira a chave, saldo/cota e acesso ao ID escolhido. O CLI imprime a classe da falha sem revelar a mensagem bruta do SDK, que pode conter dados sensíveis.
- **PDF alterado**: execute a ingestão novamente.
- **Tabela de PDF complexa**: a extração de texto pode perder relações entre colunas; inspecione o texto extraído para documentos diferentes do exemplo.

## Documentação consultada

Modelos e APIs verificados em 20/10/2026; IDs e acesso podem mudar.

- [OpenAI: embeddings](https://developers.openai.com/api/docs/guides/embeddings)
- [OpenAI: GPT-4.1 mini](https://developers.openai.com/api/docs/models/gpt-4.1-mini)
- [Google: Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)
- [Google: embeddings](https://ai.google.dev/gemini-api/docs/embeddings)
- [OpenRouter: embeddings](https://openrouter.ai/docs/api_reference/embeddings)
- [OpenRouter: DeepSeek V4 Flash](https://openrouter.ai/deepseek/deepseek-v4-flash)
- [LangChain: PGVector](https://docs.langchain.com/oss/python/integrations/vectorstores/pgvector)
