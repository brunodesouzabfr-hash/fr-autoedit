# CARD_STYLE — sistema visual v2

O arquivo continua aceitando os campos 3.4.0. O bloco novo é opcional; quando
ausente, o compositor legado permanece utilizável.

```json
{
  "schema_version": 4,
  "design_system": {
    "id": "fr_quiet_engineering_atelier_v2",
    "version": "2.0.0",
    "enabled": true,
    "legacy_v1": false,
    "texture_seed": 4072026
  }
}
```

Regras:

- `enabled=true` ativa F1–F6 em artboards de pelo menos 480 px;
- `legacy_v1=true` tem precedência e oferece rollback visual;
- o seed é fixo para microtextura determinística;
- paleta e fontes continuam validadas pelos campos existentes;
- `material_backgrounds` fica vazio no v2: mármore não é base institucional;
- 1:1 é remontagem própria, não corte do 9:16;
- assets oficiais são indexados por SHA-256 e normalizados em cópias separadas.

CLI:

```bash
fr-autoedite cards --projeto /PROJETO --sistema-v2
fr-autoedite cards --projeto /PROJETO --legacy-v1
```

