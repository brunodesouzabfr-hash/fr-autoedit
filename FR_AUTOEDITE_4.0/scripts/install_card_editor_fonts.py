#!/usr/bin/env python3
"""Prepara o cache local de fontes do FR Card Editor Universal.

As fontes não são redistribuídas no release. Elas são obtidas, quando necessário,
do repositório oficial google/fonts no commit congelado em contracts/m9,
verificadas por SHA-256 e gravadas somente no cache local da instalação.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.parse
import urllib.request


class FontInstallError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()

    contract_path = Path(args.contract).expanduser().resolve()
    destination = Path(args.destination).expanduser().resolve()
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FontInstallError("Contrato de fontes M9 inválido ou ausente.") from exc
    repository = str(contract.get("repository") or "").rstrip("/")
    commit = str(contract.get("commit") or "")
    fonts = contract.get("fonts")
    if not repository.startswith("https://github.com/") or len(commit) < 12 or not isinstance(fonts, list):
        raise FontInstallError("Contrato de fontes M9 incompleto.")
    destination.mkdir(parents=True, exist_ok=True)

    installed = []
    for row in fonts:
        if not isinstance(row, dict):
            raise FontInstallError("Entrada inválida no contrato de fontes.")
        filename = str(row.get("file") or "")
        source_path = str(row.get("source_path") or "")
        expected = str(row.get("sha256") or "").lower()
        if not filename or "/" in filename or ".." in filename or len(expected) != 64:
            raise FontInstallError(f"Entrada de fonte inválida: {filename!r}.")
        target = destination / filename
        if target.is_file() and sha256(target) == expected:
            installed.append(filename)
            continue
        if args.offline:
            raise FontInstallError(
                f"Fonte local ausente: {filename}. Conecte-se à internet ou configure FR_CARD_EDITOR_FONT_HOME."
            )
        url = f"{repository}/raw/{commit}/{urllib.parse.quote(source_path, safe='/')}"
        request = urllib.request.Request(url, headers={"User-Agent": "FR-AutoEdite-4.5"})
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = response.read(16 * 1024 * 1024 + 1)
        except Exception as exc:
            raise FontInstallError(f"Falha ao obter fonte fixada {filename}: {exc}") from exc
        if len(payload) > 16 * 1024 * 1024:
            raise FontInstallError(f"Fonte excedeu limite de segurança: {filename}.")
        received = hashlib.sha256(payload).hexdigest()
        if received != expected:
            raise FontInstallError(
                f"Hash divergente para {filename}: esperado {expected}, recebido {received}."
            )
        with tempfile.NamedTemporaryFile(dir=destination, prefix=".font-", delete=False) as tmp:
            tmp.write(payload)
            tmp_path = Path(tmp.name)
        tmp_path.replace(target)
        installed.append(filename)

    print(f"Font-cache universal pronto: {destination} ({len(installed)} fontes verificadas)")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except FontInstallError as exc:
        print(f"ERRO: {exc}")
        raise SystemExit(2)
