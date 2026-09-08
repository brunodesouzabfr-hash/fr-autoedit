#!/usr/bin/env bash
set -euo pipefail

fr_test_dir="$(mktemp -d)"
fr_app_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

cleanup() {
  rm -rf -- "$fr_test_dir"
}
trap cleanup EXIT

python3 -m py_compile \
  "$fr_app_dir/app/fr_autoedite.py" \
  "$fr_app_dir/app/local_analysis.py" \
  "$fr_app_dir/app/copilot.py" \
  "$fr_app_dir/app/studio.py"
python3 "$fr_app_dir/tests/studio_http_test.py"
python3 "$fr_app_dir/tests/card_circle_test.py"
python3 "$fr_app_dir/tests/ai_brief_window_test.py"
python3 "$fr_app_dir/tests/preparation_resume_test.py"
python3 "$fr_app_dir/tests/studio_job_recovery_test.py"
fr_answers="$(python3 "$fr_app_dir/tests/make_fixture.py" "$fr_test_dir" "$fr_app_dir")"

"$fr_app_dir/fr-autoedite" importar-takeout \
  --arquivo "$fr_test_dir/fr autoedite.zip" \
  --projeto "$fr_test_dir/takeout-project"
test -s "$fr_test_dir/takeout-project/_ENTRADA/FR_AUTOEDITE_ENTRADA.zip"
test -s "$fr_test_dir/takeout-project/RELATORIO_GOOGLE_TAKEOUT.json"
python3 - "$fr_test_dir/takeout-project/RELATORIO_GOOGLE_TAKEOUT.json" <<'PY'
import json
import sys
from pathlib import Path

report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert report["summary"]["media_total"] >= 5
assert report["summary"]["dates_restored_from_json"] >= 2
PY

"$fr_app_dir/fr-autoedite" preparar --respostas "$fr_answers"
fr_project="$fr_test_dir/workspace/teste-automatizado"

test -s "$fr_project/MANIFESTO_MEDIA.json"
test -s "$fr_project/EDIT_PLAN.json"
test -s "$fr_project/CONTEXTO_PROJETO.md"
test -s "$fr_project/CARD_STYLE.json"
test -s "$fr_project/SOCIAL_PLAN.json"
test -s "$fr_project/ROTEIRO_MESTRE_PARA_IA.md"
test -s "$fr_project/_EDITAR/04_ROTEIRO_MESTRE_PARA_IA.md"
test -s "$fr_project/_ENVIAR_IA/00_COMECE_AQUI_O_QUE_EDITAR_E_ENVIAR.md"
test -s "$fr_project/_ENVIAR_IA/01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md"
test -s "$fr_project/_ENVIAR_IA/02_NAO_EDITAR_APENAS_ENVIAR_PROMPT.md"
test -s "$fr_project/_ENVIAR_IA/03_NAO_EDITAR_LISTA_DE_LOTES.txt"
test -s "$fr_project/PROMPT_PRONTO_PARA_CHATGPT.md"
test -s "$fr_project/pacote_chatgpt/FR_AUTOEDITE_LOTE_001.zip"
test -s "$fr_project/CONTATO_GERAL_CODEX.jpg"
test -d "$fr_project/originais_organizados"
test -d "$fr_project/selects"
python3 - "$fr_project/MANIFESTO_MEDIA.json" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert manifest["schema_version"] == 3
assert manifest["summary"]["duplicates_marked"] >= 1
assert manifest["summary"]["scene_clips"] >= 1
assert any(row.get("parent_video") for row in manifest["media"])
PY
python3 - "$fr_project/QUESTIONARIO_RESPONDIDO.json" <<'PY'
import json
import sys
from pathlib import Path

answers = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert answers["edition"]["quality_preset"] == "custom"
assert len(answers["visual_effects"]["transitions"]) >= 5
assert answers["cards"]["show_contact_icons"] is True
assert answers["cloud_export"]["provider"] == "google_drive_rclone"
assert answers["service_intro"]["service_key"] == "iluminacao"
PY
python3 - "$fr_project/EDIT_PLAN.json" "$fr_project/social/planos/REEL_8S.json" <<'PY'
import json
import sys
from pathlib import Path

main = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
reel = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
assert any(item.get("card_kind") == "service" and item.get("service_key") == "iluminacao" for item in main["segments"])
assert any(item.get("external_role") == "intro" for item in main["segments"])
timelapses = [item for item in main["segments"] if item.get("editorial_timelapse")]
assert len(timelapses) == 1
assert timelapses[0]["media_type"] == "video"
assert timelapses[0]["playback_speed"] == 4.0
roles = {item.get("coverage_role") for item in reel["segments"] if item.get("type") == "media" and not item.get("external_asset")}
assert "inicio" in roles and "fim" in roles
PY
"$fr_app_dir/fr-autoedite" aplicar-roteiro-ia \
  --projeto "$fr_project" \
  --arquivo "$fr_project/_ENVIAR_IA/01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE_IA.md"
test -s "$fr_project/RELATORIO_APLICACAO_ROTEIRO_IA.json"
unzip -tq "$fr_project/pacote_chatgpt/FR_AUTOEDITE_LOTE_001.zip" >/dev/null
while IFS= read -r -d '' fr_lot; do
  test "$(stat -c %s "$fr_lot")" -lt $((150 * 1024 * 1024))
  unzip -tq "$fr_lot" >/dev/null
done < <(find "$fr_project/pacote_chatgpt" -maxdepth 1 -type f -name 'FR_AUTOEDITE_LOTE_*.zip' -print0)

"$fr_app_dir/fr-autoedite" render --projeto "$fr_project" --usar-proxies

fr_branded="$fr_project/entrega/FR_TESTE_AUTOMATIZADO_INSTITUCIONAL_FR.mp4"
fr_clean="$fr_project/entrega/FR_TESTE_AUTOMATIZADO_LIMPO.mp4"
test -s "$fr_branded"
test -s "$fr_clean"

for fr_video in "$fr_branded" "$fr_clean"; do
  fr_dimensions="$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$fr_video")"
  test "$fr_dimensions" = "360x640"
  ffmpeg -v error -i "$fr_video" -f null -
done

"$fr_app_dir/fr-autoedite" social --projeto "$fr_project" --usar-proxies

for fr_seconds in 6 8 10; do
  fr_reel="$fr_project/entrega/FR_TESTE_AUTOMATIZADO_REEL_${fr_seconds}S_INSTITUCIONAL_FR.mp4"
  test -s "$fr_reel"
  ffmpeg -v error -i "$fr_reel" -f null -
done

test -s "$fr_project/social/stories/FR_TESTE_AUTOMATIZADO_STORY_01.mp4"
test -s "$fr_project/social/capas/CAPA_REEL_8S.jpg"
test "$(find "$fr_project/social/carrossel" -type f -name 'CARROSSEL_*.jpg' | wc -l)" -ge 4

"$fr_app_dir/fr-autoedite" draft --projeto "$fr_project" --somente branded
fr_draft="$fr_project/entrega/FR_TESTE_AUTOMATIZADO_RASCUNHO_480P_INSTITUCIONAL_FR.mp4"
test -s "$fr_draft"
test "$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$fr_draft")" = "480x854"

"$fr_app_dir/fr-autoedite" replanejar --projeto "$fr_project" --modo alfabetico --duracao-media 2
python3 - "$fr_project/EDIT_PLAN.json" <<'PY'
import json
import sys
from pathlib import Path

plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert plan["schema_version"] == 3
assert plan["order_mode"] == "alfabetico"
PY

"$fr_app_dir/fr-autoedite" replanejar --projeto "$fr_project" --modo aleatorio --seed 123456 --duracao-media 2
python3 - "$fr_project/EDIT_PLAN.json" "$fr_test_dir/random-one.json" <<'PY'
import json
import sys
from pathlib import Path

plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert plan["schema_version"] == 3
assert plan["order_mode"] == "aleatorio"
assert plan["random_seed"] == 123456
stable = [{key: item.get(key) for key in ("type", "media_id", "start_sec", "duration_sec", "phase_order", "transition", "image_animation")} for item in plan["segments"]]
Path(sys.argv[2]).write_text(json.dumps(stable, sort_keys=True), encoding="utf-8")
PY
"$fr_app_dir/fr-autoedite" replanejar --projeto "$fr_project" --modo aleatorio --seed 123456 --duracao-media 2
python3 - "$fr_project/EDIT_PLAN.json" "$fr_test_dir/random-one.json" <<'PY'
import json
import sys
from pathlib import Path

plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
stable = [{key: item.get(key) for key in ("type", "media_id", "start_sec", "duration_sec", "phase_order", "transition", "image_animation")} for item in plan["segments"]]
assert json.dumps(stable, sort_keys=True) == Path(sys.argv[2]).read_text(encoding="utf-8")
PY

"$fr_app_dir/fr-autoedite" auditar --projeto "$fr_project"
test -s "$fr_project/RELATORIO_AUDITORIA.md"

HOME="$fr_test_dir/home" "$fr_app_dir/fr-autoedite" codex-config --provider ollama --model llava
test -s "$fr_test_dir/home/.fr_autoedite/creds.json"

fr_context="$fr_test_dir/contexto-universal.md"
printf '%s\n' \
  '# Projeto Universal FR' \
  '' \
  '1. ANTES | mostrar o estado inicial e a preparação' \
  '2. EXECUÇÃO | mostrar montagem e decisões técnicas' \
  '3. RESULTADO | mostrar a entrega concluída' \
  > "$fr_context"

"$fr_app_dir/fr-autoedite" novo \
  --zip "$fr_test_dir/fr autoedite.zip" \
  --contexto "$fr_context" \
  --modo cronologico \
  --duracao-longa 12 \
  --duracao-media 2 \
  --reels 6 \
  --workspace-root "$fr_test_dir/universal"

fr_universal="$fr_test_dir/universal/projeto-universal-fr"
test -s "$fr_universal/CONTEXTO_PROJETO.md"
test -s "$fr_universal/fontes_contexto/contexto-universal.md"
python3 - "$fr_universal/EDIT_PLAN.json" <<'PY'
import json
import sys
from pathlib import Path

plan = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
assert plan["order_mode"] == "cronologico"
titles = [item["title"] for item in plan["segments"] if item.get("card_kind") == "phase"]
assert titles == ["ANTES", "EXECUÇÃO", "RESULTADO"]
PY

echo "SMOKE TEST OK"
