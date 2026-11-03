"""Rode UMA vez no seu computador para gerar o token do Garmin.

    pip install "garminconnect[workout]" curl_cffi
    python scripts/make_token.py

Ele pede e-mail, senha e o código MFA (se você usa). A senha não é salva:
só o token é impresso, para você colar no Secret GARMIN_TOKENS do GitHub.
Trate esse token como uma senha.
"""
from getpass import getpass

from garminconnect import Garmin


def main() -> None:
    email = input("E-mail do Garmin: ").strip()
    password = getpass("Senha do Garmin: ")
    client = Garmin(email, password, prompt_mfa=lambda: input("Código MFA: ").strip())
    client.login()
    print("\nLogin OK. Copie TODO o texto abaixo para o Secret GARMIN_TOKENS:\n")
    print(client.client.dumps())


if __name__ == "__main__":
    main()
