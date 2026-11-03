"""Login no Garmin a partir do token guardado (sem senha).

O token vem da variável de ambiente GARMIN_TOKENS (o JSON gerado por
make_token.py, guardado como Secret no GitHub). Se TOKENS_OUT estiver
definida, o token renovado é gravado nesse arquivo para o workflow
atualizar o Secret.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from garminconnect import Garmin


def login() -> Garmin:
    tokens = os.getenv("GARMIN_TOKENS", "").strip()
    if not tokens:
        sys.exit("GARMIN_TOKENS não definido. Rode scripts/make_token.py e salve o resultado como Secret.")
    client = Garmin()
    client.login(tokens)
    out = os.getenv("TOKENS_OUT")
    if out:
        p = Path(out)
        p.write_text(client.client.dumps(), encoding="utf-8")
        p.chmod(0o600)
    return client
