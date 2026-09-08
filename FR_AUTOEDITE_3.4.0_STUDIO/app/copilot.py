#!/usr/bin/env python3
"""Copiloto opcional do FR AutoEdite.

O programa permanece totalmente funcional sem este módulo. Nenhuma chamada
externa acontece sem `ai_copilot.enabled=true` e uma credencial configurada.
"""

from __future__ import annotations

import base64
import getpass
import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


class CopilotError(RuntimeError):
    pass


class CredentialStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path("~/.fr_autoedite").expanduser()
        self.path = self.root / "creds.json"

    def _read_metadata(self) -> dict[str, Any]:
        if not self.path.is_file():
            return {"providers": {}}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"providers": {}}

    def _write_metadata(self, data: dict[str, Any]) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.chmod(temporary, 0o600)
        temporary.replace(self.path)
        os.chmod(self.path, 0o600)

    def configure(self, provider: str, model: str, key: str | None = None) -> str:
        provider = provider.strip().lower()
        if provider not in {"openai", "anthropic", "ollama"}:
            raise CopilotError("Provider inválido. Use openai, anthropic ou ollama.")
        if provider == "ollama":
            key = ""
        elif key is None:
            key = getpass.getpass(f"Chave {provider} (não será exibida): ").strip()
        if provider != "ollama" and not key:
            raise CopilotError("Nenhuma chave foi informada.")

        metadata = self._read_metadata()
        providers = metadata.setdefault("providers", {})
        storage = "none"
        if provider != "ollama" and shutil.which("secret-tool"):
            result = subprocess.run(
                ["secret-tool", "store", "--label=FR AutoEdite Copilot", "service", "fr-autoedite", "provider", provider],
                input=key,
                text=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=False,
            )
            if result.returncode == 0:
                storage = "system_keyring"
        if provider != "ollama" and storage != "system_keyring":
            # Compatibilidade em sistemas sem cofre. Base64 é apenas ofuscação;
            # o arquivo recebe modo 0600 e a UI deixa isso explícito.
            storage = "local_0600_base64_obfuscation"
            providers.setdefault(provider, {})["encoded_key"] = base64.b64encode(key.encode("utf-8")).decode("ascii")
        providers[provider] = {
            **providers.get(provider, {}),
            "model": model,
            "storage": storage,
            "configured_at": int(time.time()),
        }
        metadata["active_provider"] = provider
        self._write_metadata(metadata)
        return storage

    def load(self, provider: str) -> tuple[str, str]:
        provider = provider.strip().lower()
        metadata = self._read_metadata()
        settings = metadata.get("providers", {}).get(provider, {})
        model = str(settings.get("model") or "")
        if provider == "ollama":
            return "", model or "llava"
        env_name = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
        if os.environ.get(env_name, "").strip():
            return os.environ[env_name].strip(), model
        if settings.get("storage") == "system_keyring" and shutil.which("secret-tool"):
            result = subprocess.run(
                ["secret-tool", "lookup", "service", "fr-autoedite", "provider", provider],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip(), model
        encoded = str(settings.get("encoded_key") or "")
        if encoded:
            try:
                return base64.b64decode(encoded).decode("utf-8"), model
            except Exception as exc:
                raise CopilotError("Credencial local inválida; configure novamente.") from exc
        raise CopilotError(f"Nenhuma credencial foi configurada para {provider}.")

    def status(self) -> dict[str, Any]:
        metadata = self._read_metadata()
        result: dict[str, Any] = {"active_provider": metadata.get("active_provider"), "providers": {}}
        for provider, settings in metadata.get("providers", {}).items():
            result["providers"][provider] = {
                "model": settings.get("model"),
                "storage": settings.get("storage"),
                "configured": provider == "ollama" or bool(settings.get("storage")),
            }
        return result


class CopilotManager:
    def __init__(self, project_dir: Path, config: dict[str, Any]) -> None:
        self.project_dir = project_dir
        self.config = config
        self.provider = str(config.get("provider") or "openai").lower()
        self.store = CredentialStore()
        self.cache_dir = project_dir / "copilot" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def cache_path(self) -> Path:
        return self.cache_dir / "CURADORIA_IA.json"

    def _curation_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "selections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "media_id": {"type": "string"},
                            "phase_order": {"type": "integer"},
                            "start_sec": {"type": "number"},
                            "duration_sec": {"type": "number"},
                            "reason": {"type": "string"},
                        },
                        "required": ["media_id", "phase_order", "start_sec", "duration_sec", "reason"],
                        "additionalProperties": False,
                    },
                },
                "warnings": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["summary", "selections", "warnings"],
            "additionalProperties": False,
        }

    def _prompt(self, context: str, manifest: dict[str, Any], strategy: str) -> str:
        simplified = []
        for row in manifest.get("media", []):
            if row.get("status") != "ok" or row.get("excluded_from_auto_edit"):
                continue
            simplified.append({
                "id": row.get("id"),
                "type": row.get("media_type"),
                "duration": row.get("duration_sec"),
                "capture_time": row.get("capture_time"),
                "quality_score": row.get("quality_score"),
                "parent_video": row.get("parent_video"),
                "scene_start_sec": row.get("scene_start_sec"),
                "needs_stabilization": row.get("needs_stabilization", False),
            })
        return (
            "Analise a prancha visual e o manifesto. Selecione os melhores clipes para representar "
            "cada etapa real do projeto. Não invente materiais, técnicas, resultados ou etapas. "
            "Retorne somente o JSON solicitado. Respeite os limites de duração e use apenas media_id existentes.\n\n"
            f"CONTEXTO:\n{context[:24000]}\n\n"
            f"DIRETRIZES FR:\n{strategy[:24000]}\n\n"
            f"MANIFESTO SIMPLIFICADO:\n{json.dumps(simplified, ensure_ascii=False)}"
        )

    def _image_data_url(self, board: Path) -> str:
        mime = "image/png" if board.suffix.lower() == ".png" else "image/jpeg"
        return f"data:{mime};base64,{base64.b64encode(board.read_bytes()).decode('ascii')}"

    def _request_json(self, request: urllib.request.Request, timeout: int = 180) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:1000]
            raise CopilotError(f"API respondeu HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise CopilotError(f"Copiloto indisponível: {exc}") from exc

    @staticmethod
    def _extract_openai_text(payload: dict[str, Any]) -> str:
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"]
        for output in payload.get("output", []):
            if output.get("type") != "message":
                continue
            for content in output.get("content", []):
                if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                    return content["text"]
        raise CopilotError("A resposta da OpenAI não continha JSON textual.")

    def _call_openai(self, key: str, model: str, prompt: str, board: Path) -> dict[str, Any]:
        body = {
            "model": model,
            "instructions": "Você é o curador técnico da Franco Romeu. Preserve verdade factual e autoridade humana.",
            "input": [{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {"type": "input_image", "image_url": self._image_data_url(board), "detail": "high"},
                ],
            }],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "fr_autoedite_curation",
                    "strict": True,
                    "schema": self._curation_schema(),
                }
            },
        }
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(body).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            method="POST",
        )
        return json.loads(self._extract_openai_text(self._request_json(request)))

    def _call_anthropic(self, key: str, model: str, prompt: str, board: Path) -> dict[str, Any]:
        media_type = "image/png" if board.suffix.lower() == ".png" else "image/jpeg"
        body = {
            "model": model,
            "max_tokens": 5000,
            "system": "Você é o curador técnico da Franco Romeu. Responda somente JSON válido.",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": base64.b64encode(board.read_bytes()).decode("ascii")}},
                    {"type": "text", "text": prompt + "\nJSON Schema:\n" + json.dumps(self._curation_schema())},
                ],
            }],
        }
        request = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps(body).encode("utf-8"),
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            method="POST",
        )
        payload = self._request_json(request)
        text = "".join(item.get("text", "") for item in payload.get("content", []) if item.get("type") == "text")
        return json.loads(text)

    def _call_ollama(self, model: str, prompt: str, board: Path) -> dict[str, Any]:
        body = {
            "model": model,
            "stream": False,
            "format": self._curation_schema(),
            "messages": [{
                "role": "user", "content": prompt,
                "images": [base64.b64encode(board.read_bytes()).decode("ascii")],
            }],
        }
        request = urllib.request.Request(
            "http://127.0.0.1:11434/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        payload = self._request_json(request)
        return json.loads(payload.get("message", {}).get("content", "{}"))

    def validate(self, result: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
        available = {row.get("id"): row for row in manifest.get("media", [])}
        valid = []
        for selection in result.get("selections", []):
            row = available.get(selection.get("media_id"))
            if not row or row.get("status") != "ok" or row.get("excluded_from_auto_edit"):
                continue
            duration = max(0.1, float(selection.get("duration_sec") or 0))
            source_duration = max(0.0, float(row.get("duration_sec") or 0))
            start = max(0.0, float(selection.get("start_sec") or 0))
            if row.get("media_type") == "video" and source_duration:
                start = min(start, max(0.0, source_duration - 0.1))
                duration = min(duration, max(0.1, source_duration - start))
            else:
                start = 0.0
            valid.append({
                "media_id": row["id"],
                "phase_order": max(1, int(selection.get("phase_order") or 1)),
                "start_sec": round(start, 3),
                "duration_sec": round(duration, 3),
                "reason": str(selection.get("reason") or "seleção visual do Copiloto"),
            })
        if not valid:
            raise CopilotError("A curadoria não retornou nenhuma seleção válida.")
        validated = {
            "provider": self.provider,
            "summary": str(result.get("summary") or "Curadoria visual opcional"),
            "selections": valid,
            "warnings": [str(value) for value in result.get("warnings", [])],
            "validated_at": int(time.time()),
        }
        temporary = self.cache_path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(validated, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(self.cache_path)
        return validated

    def curate(
        self, board: Path, context: str, manifest: dict[str, Any], strategy: str,
        *, use_cache: bool = True,
    ) -> dict[str, Any]:
        if use_cache and self.cache_path.is_file():
            try:
                return self.validate(json.loads(self.cache_path.read_text(encoding="utf-8")), manifest)
            except Exception:
                pass
        prompt = self._prompt(context, manifest, strategy)
        key, stored_model = self.store.load(self.provider)
        model = str(self.config.get("model") or stored_model or "").strip()
        if not model:
            raise CopilotError("Defina o modelo do Copiloto no Studio ou em codex-config.")
        if self.provider == "openai":
            result = self._call_openai(key, model, prompt, board)
        elif self.provider == "anthropic":
            result = self._call_anthropic(key, model, prompt, board)
        elif self.provider == "ollama":
            result = self._call_ollama(model, prompt, board)
        else:
            raise CopilotError(f"Provider não suportado: {self.provider}")
        return self.validate(result, manifest)

