from __future__ import annotations
from dataclasses import dataclass, field
from importlib import metadata, util
from pathlib import Path
import shutil
import subprocess
from typing import Any, Callable


class AdapterError(RuntimeError): pass
class AdapterUnavailable(AdapterError): pass
class AdapterDeferred(AdapterError): pass


@dataclass(frozen=True)
class Request:
    operation: str
    source: Path | None = None
    destination: Path | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Result:
    backend: str
    operation: str
    data: Any
    fallback_used: bool = False
    warnings: tuple[str, ...] = ()


@dataclass
class Adapter:
    name: str
    tier: int
    executable: str | None = None
    module: str | None = None
    distribution: str | None = None
    purpose: str = ''
    operations: dict[str, Callable[[Request], Any]] = field(default_factory=dict)
    fallback_handler: Callable[[Request], Result] | None = None
    state: str = 'planned'
    version_args: tuple[str, ...] = ('--version',)

    def is_available(self) -> bool:
        try:
            if self.executable: return shutil.which(self.executable) is not None
            if self.module: return util.find_spec(self.module) is not None
            return False
        except (ImportError, AttributeError, ValueError, OSError):
            return False

    def version(self) -> str | None:
        if not self.is_available(): return None
        try:
            if self.distribution: return metadata.version(self.distribution)
            if self.tier == 3: return None  # Tier 3 nunca inicia binário, mesmo --version.
            if self.executable:
                result = subprocess.run([shutil.which(self.executable), *self.version_args],
                    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    timeout=8, check=False, text=True)
                return result.stdout.splitlines()[0][:240] if result.returncode == 0 and result.stdout else None
        except (metadata.PackageNotFoundError, OSError, subprocess.SubprocessError):
            return None
        return None

    def capabilities(self) -> set[str]:
        # Não anunciar execução quando há somente interface/descoberta.
        return set(self.operations) if self.state == 'implemented' and self.tier != 3 else set()

    def run(self, request: Request) -> Result:
        if not isinstance(request, Request): raise TypeError('Use Request tipada.')
        if self.tier == 3 or self.state != 'implemented':
            raise AdapterDeferred(f'{self.name}: execução não implementada nesta etapa; somente diagnóstico.')
        if request.operation not in self.operations:
            raise AdapterError(f'{self.name}: operação não suportada: {request.operation}')
        if not self.is_available(): raise AdapterUnavailable(f'{self.name} não instalado.')
        try:
            value = self.operations[request.operation](request)
        except (OSError, subprocess.SubprocessError, ImportError) as exc:
            raise AdapterError(f'{self.name}: falha na execução: {type(exc).__name__}') from exc
        return Result(self.name, request.operation, value)

    def fallback(self): return self.fallback_handler

    def smoke_test(self) -> bool:
        """Teste mínimo explícito, não confundir presença com teste funcional."""
        if self.state != 'implemented' or self.tier == 3: return False
        if not self.is_available(): return False
        try:
            return bool(self.run(Request('self_test')).data) if 'self_test' in self.operations else False
        except (AdapterError, ValueError, TypeError): return False
