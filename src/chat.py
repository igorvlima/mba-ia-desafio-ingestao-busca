"""Chat de terminal sem histórico: cada pergunta consulta novamente o PDF."""
import sys
from search import search_prompt


def main():
    try:
        service = search_prompt()
    except ValueError as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Não foi possível iniciar ({type(exc).__name__}). Verifique o banco e o .env.", file=sys.stderr)
        return 1
    print("Faça sua pergunta (digite sair para encerrar):")
    while True:
        try:
            question = input("PERGUNTA: ").strip()
            if question.lower() in {"sair", "exit", "quit"}:
                return 0
            if not question:
                continue
            print(f"RESPOSTA: {service.answer(question)}\n")
        except (EOFError, KeyboardInterrupt):
            print("\nAté logo!")
            return 0
        except Exception as exc:
            print(f"Falha na consulta ({type(exc).__name__}). Verifique conexão, chave, modelo e saldo.", file=sys.stderr)


if __name__ == "__main__":
    sys.exit(main())
