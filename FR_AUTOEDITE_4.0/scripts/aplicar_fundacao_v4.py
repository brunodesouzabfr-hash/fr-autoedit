"""Aplica somente arquivos novos da fundação, após conferir hashes da base.

Não instala dependências, não troca VERSION, não altera Studio, não executa
Git. Por padrão apenas descreve; --aplicar realiza a cópia verificada.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile


def sha256(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''): result.update(chunk)
    return result.hexdigest()


def safe(root,relative):
    part=Path(relative)
    if part.is_absolute() or '..' in part.parts: raise ValueError('Caminho inseguro no manifesto.')
    result=(root/part).resolve()
    if not result.is_relative_to(root.resolve()):raise ValueError('Caminho fora da raiz.')
    if any(p in {'Studio','originais','.git','.env'} for p in part.parts):raise ValueError('Destino protegido.')
    return result


def plan(package: Path, destination: Path):
    manifest=json.loads((package/'PATCH_MANIFEST.json').read_text(encoding='utf-8'))
    if manifest.get('mode')!='additive_foundation_only':raise ValueError('Manifesto de aplicação incompatível.')
    for relative,expected in manifest['base_sha256'].items():
        path=safe(destination,relative)
        if not path.is_file() or sha256(path)!=expected:
            raise ValueError(f'Base difere do ZIP auditado: {relative}. Não aplicar sobre código diferente.')
    additions=[]
    for relative,expected in manifest['new_files_sha256'].items():
        source=safe(package/'source',relative);target=safe(destination,relative)
        if not source.is_file() or sha256(source)!=expected:raise ValueError('Pacote corrompido: '+relative)
        if target.exists():
            if not target.is_file() or sha256(target)!=expected:
                raise ValueError('Arquivo existente seria alterado: '+relative)
        else:additions.append((source,target,expected))
    return additions


def apply(additions):
    published=[]
    try:
        for source,target,expected in additions:
            target.parent.mkdir(parents=True,exist_ok=True)
            # Criação exclusiva: nem concorrência pode sobrescrever arquivo existente.
            with source.open('rb') as src,target.open('xb') as dst:
                published.append((target,expected))
                shutil.copyfileobj(src,dst);dst.flush();os.fsync(dst.fileno())
            if sha256(target)!=expected:raise ValueError('Falha de integridade: '+str(target))
    except BaseException:
        for target,expected in reversed(published):
            if target.is_file() and sha256(target)==expected:target.unlink()
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino',type=Path,required=True,help='diretório que contém VERSION, app/ e fr-autoedite')
    parser.add_argument('--aplicar',action='store_true')
    args=parser.parse_args()
    package=Path(__file__).resolve().parent
    try:
        additions=plan(package,args.destino.resolve())
        if args.aplicar:apply(additions)
        print(json.dumps({'applied':args.aplicar,'new_files':[str(p) for _,p,_ in additions],
                          'cli_changed':False,'studio_changed':False,'version_changed':False},ensure_ascii=False,indent=2))
        return 0
    except (OSError,ValueError) as exc:
        print(json.dumps({'applied':False,'error':str(exc)},ensure_ascii=False))
        return 2


if __name__=='__main__':raise SystemExit(main())
