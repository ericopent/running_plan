"""Criptografa os JSON do painel com a senha do site (Secret SITE_PASSWORD).

AES-256-GCM com chave derivada por PBKDF2-SHA256. O navegador faz o caminho
inverso com WebCrypto (site/app.js). Sem SITE_PASSWORD, copia os JSON abertos.

    SITE_PASSWORD=... python scripts/encrypt_site_data.py data _site/data
"""
from __future__ import annotations

import base64
import json
import os
import shutil
import sys
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ITERATIONS = 310_000
FILES = ["plan.json", "activities.json", "pushed.json"]


def b64(b: bytes) -> str:
    return base64.b64encode(b).decode()


def main(src: str, dst: str) -> None:
    src_p, dst_p = Path(src), Path(dst)
    dst_p.mkdir(parents=True, exist_ok=True)
    password = os.getenv("SITE_PASSWORD", "")

    if not password:
        for f in FILES:
            if (src_p / f).exists():
                shutil.copy(src_p / f, dst_p / f)
        print("SITE_PASSWORD vazio: dados publicados sem criptografia.")
        return

    salt = os.urandom(16)
    key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS).derive(password.encode())
    aes = AESGCM(key)
    bundle = {"v": 1, "kdf": "PBKDF2-SHA256", "iterations": ITERATIONS, "salt": b64(salt), "files": {}}
    for f in FILES:
        path = src_p / f
        data = path.read_bytes() if path.exists() else b"{}"
        iv = os.urandom(12)
        bundle["files"][f] = {"iv": b64(iv), "ct": b64(aes.encrypt(iv, data, None))}
    (dst_p / "vault.json").write_text(json.dumps(bundle), encoding="utf-8")
    print(f"{len(FILES)} arquivos criptografados em {dst_p / 'vault.json'}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
