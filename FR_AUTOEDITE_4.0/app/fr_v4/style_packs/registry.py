from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from ..core.config import SERVICES, STYLE_PACK_ID, DESIGN_VERSION


class AssetError(ValueError): pass


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): hasher.update(block)
    return hasher.hexdigest()


def confined(root: Path, relative: str) -> Path:
    part = Path(relative)
    if not relative or part.is_absolute() or '..' in part.parts:
        raise AssetError('Caminho relativo inválido: '+str(relative))
    target = (root/part).resolve()
    if not target.is_relative_to(root.resolve()): raise AssetError('Asset fora da raiz autorizada.')
    return target


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, name = tempfile.mkstemp(prefix='.fr-index-', dir=path.parent)
    try:
        with os.fdopen(handle, 'w', encoding='utf-8') as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name): os.unlink(name)


def normalize(source: Path, target: Path, canvas_size=2048, apparent_size=1740) -> dict:
    """Canvas transparente; nunca remove pixels opacos, fundo, aro ou monograma.

    alpha bbox alinha ativos transparentes. Em RGB, o canvas inteiro é identidade:
    a estimativa de diâmetro aparente exige revisão, não segmentação automática.
    """
    from PIL import Image, ImageOps
    if source.resolve() == target.resolve(): raise AssetError('Original não pode ser sobrescrito.')
    before = digest(source)
    with Image.open(source) as opened:
        image = ImageOps.exif_transpose(opened).convert('RGBA')
        alpha = image.getchannel('A')
        box = alpha.getbbox()
        if box is None: raise AssetError('Asset inteiramente transparente.')
        opaque = alpha.getextrema() == (255, 255)
        artwork = image.crop(box)  # Remove somente margem alpha=0.
        artwork = ImageOps.contain(artwork, (apparent_size, apparent_size), Image.Resampling.LANCZOS)
        result = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
        result.alpha_composite(artwork, ((canvas_size-artwork.width)//2, (canvas_size-artwork.height)//2))
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name('.' + target.name + '.partial.png')
        temporary.unlink(missing_ok=True)
        try:
            # Compressão PNG não altera pixels. Nível moderado evita que um
            # lote de 13 ativos 2048² aparente travamento em máquinas locais.
            result.save(temporary, format='PNG', compress_level=3)
            if digest(source) != before: raise AssetError('Original mudou durante normalização.')
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
    return {'sha256': digest(target), 'dimensions': [canvas_size, canvas_size],
            'apparent_target_px': apparent_size, 'original_sha256': before,
            'opaque_background_preserved': opaque,
            'normalization': 'alpha_bbox_contain_v1', 'visual_review_required': True}


def index_assets(app_root: Path) -> dict:
    """Reindexação explícita. Falha em vez de substituir arquivo original diferente."""
    app_root = app_root.resolve()
    pack_dir = app_root/'assets/style_packs'/STYLE_PACK_ID
    normalized_dir = app_root/'assets/service-medallions/normalized'
    if normalized_dir.is_dir():
        for stale in normalized_dir.glob('.*.partial.png'):
            stale.unlink(missing_ok=True)
        for stale in normalized_dir.glob('.fr-normalize-*.png'):
            stale.unlink(missing_ok=True)
    assets = {}
    for service in SERVICES:
        original_rel = f'assets/service-medallions/original/{service.key}.png'
        normalized_rel = f'assets/service-medallions/normalized/{service.key}.png'
        original = confined(app_root, original_rel)
        received = confined(app_root, f'assets/services/{service.key}.png')
        entry = {'asset_id': f'medallion_{service.key}', 'tipo': 'medallion',
                 'servico': service.key, 'caminho': original_rel, 'path': original_rel,
                 'status': 'pending_asset', 'sha256': None, 'dimensoes': None,
                 'fallback': 'medallion_placeholder_tecnico', 'publicavel': False}
        if received.is_file() and original.is_file() and digest(received) != digest(original):
            raise AssetError(f'{service.key}: cópia original diverge do recebido; revisão necessária.')
        if not original.exists() and received.is_file():
            original.parent.mkdir(parents=True, exist_ok=True)
            with received.open('rb') as src, original.open('xb') as dst: shutil.copyfileobj(src, dst)
        if original.is_file():
            normalized = normalize(original, confined(app_root, normalized_rel))
            from PIL import Image
            with Image.open(original) as image: dimensions = list(image.size)
            entry.update(status='installed_requires_review', sha256=digest(original),
                         dimensoes=dimensions, normalized_path=normalized_rel,
                         normalized=normalized)
        assets[entry['asset_id']] = entry
    logo_rel = 'assets/franco-romeu-logo.png'
    logo = confined(app_root, logo_rel)
    assets['logo_primary'] = {'asset_id': 'logo_primary', 'tipo': 'logo', 'path': logo_rel,
        'status': 'installed_requires_review' if logo.is_file() else 'pending_asset',
        'sha256': digest(logo) if logo.is_file() else None, 'publicavel': False}
    manifest = {'schema_version': 2, 'style_pack_id': STYLE_PACK_ID,
        'design_version': DESIGN_VERSION, 'root_basis': 'application',
        'assets': assets, 'generated_timestamp': None,
        'identity_policy': 'original_bytes_preserved', 'review_policy': 'manual_before_publish'}
    atomic_json(pack_dir/'manifest.json', manifest)
    if normalized_dir.is_dir():
        for stale in normalized_dir.glob('.*.partial.png'):
            stale.unlink(missing_ok=True)
        for stale in normalized_dir.glob('.fr-normalize-*.png'):
            stale.unlink(missing_ok=True)
    return manifest


def load(app_root: Path) -> dict:
    path = app_root/'assets/style_packs'/STYLE_PACK_ID/'manifest.json'
    if not path.is_file(): raise AssetError('Execute scripts/indexar_assets_v2.py antes de gerar v2.')
    manifest = json.loads(path.read_text(encoding='utf-8'))
    if manifest.get('style_pack_id') != STYLE_PACK_ID: raise AssetError('Style Pack incompatível.')
    return manifest


def resolve(app_root: Path, asset_id: str, *, normalized=True) -> tuple[Path | None, dict]:
    entry = load(app_root).get('assets', {}).get(asset_id)
    if not entry: raise AssetError('asset_id não declarado: '+asset_id)
    if entry['status'] == 'pending_asset': return None, entry
    original = confined(app_root, entry['path'])
    if not original.is_file() or digest(original) != entry['sha256']:
        raise AssetError('Asset alterado/ausente; reindexe e revise: '+asset_id)
    if normalized and entry.get('normalized_path'):
        path = confined(app_root, entry['normalized_path'])
        if not path.is_file() or digest(path) != entry['normalized']['sha256']:
            raise AssetError('Normalizado alterado/ausente: '+asset_id)
        return path, entry
    return original, entry


def signature(app_root: Path, plan: dict, style: dict) -> str:
    payload = {'plan': plan, 'style': style, 'manifest': load(app_root), 'renderer': DESIGN_VERSION}
    hasher = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, allow_nan=False).encode())
    for asset_id in sorted(payload['manifest']['assets']):
        entry = payload['manifest']['assets'][asset_id]
        for field in ('path', 'normalized_path'):
            if not entry.get(field): continue
            path = confined(app_root, entry[field])
            hasher.update(asset_id.encode()+field.encode())
            hasher.update(digest(path).encode() if path.is_file() else b'MISSING')
    for font in sorted((app_root/'assets/fonts').glob('*.ttf')):
        hasher.update(font.name.encode()+digest(font).encode())
    return hasher.hexdigest()
