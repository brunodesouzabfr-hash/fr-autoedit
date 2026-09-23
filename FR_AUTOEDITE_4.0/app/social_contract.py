"""Render the explicit social lists supplied by the AI, without re-sampling."""
from pathlib import Path
from types import SimpleNamespace
import copy


def render(env, project, answers, use_proxies=False, only="all"):
    c = SimpleNamespace(**env)
    project = Path(project)
    result, rendered = [], {}
    social = answers.get("social", {})
    plan_dir = project / "social/planos"
    stories_path = plan_dir / "STORIES_PLAN.json"
    stories = c.read_json(stories_path) if stories_path.is_file() else {"enabled": False}
    wanted = set(str(v) for v in social.get("reel_durations_sec", [])) if only in {"all", "reels"} and social.get("reels_enabled") else set()
    if only in {"all", "stories"} and stories.get("enabled") and not stories.get("timeline"):
        wanted.add(str(stories["source_reel_sec"]))
    for key in sorted(wanted, key=int):
        path = plan_dir / f"REEL_{key}S.json"
        if not path.is_file():
            raise c.AutoEditeError("Reel solicitado não existe no roteiro ativo: " + key)
        items = c.render_plan(project, path, use_proxies=use_proxies, only="branded")
        rendered[key] = items[0]
        result.extend(items)
        if only != "stories" and social.get("create_reel_covers", True):
            cover=project/"social/capas"/f"CAPA_REEL_{key}S.jpg"
            cover.parent.mkdir(parents=True,exist_ok=True)
            c.render_reel_cover(project,c.read_json(path),cover)
            result.append(cover)
    if only in {"all","stories"} and stories.get("enabled"):
        if stories.get("timeline"):
            path=plan_dir/"STORIES_TIMELINE.json"
            c.write_json(path,stories["timeline"])
            source=c.render_plan(project,path,use_proxies=use_proxies,only="branded")[0]
            result.append(source)
        else:
            source=rendered[str(stories["source_reel_sec"])]
            story_name = answers.get("project", {}).get("slug") or answers.get("project", {}).get("name") or project.name
            story_prefix = "FR_" + c.slugify(story_name).upper().replace("-", "_")
            result.extend(c.split_story_video(source, project / "social/stories",
                                              stories.get("part_duration_sec", 15), story_prefix))
    if only in {"all","carrossel"} and social.get("carousel_enabled"):
        result.extend(render_carousel(env,project,plan_dir/"CARROSSEL_PLAN.json",use_proxies))
    publication=project/"PUBLICACAO_SOCIAL.md"
    copy_text=publication.read_text(encoding="utf-8") if publication.is_file() else c.social_copy(answers)
    c.write_text(project/"social/PACOTE_EDITORIAL.md",copy_text)
    c.write_text(project/"social/RELATORIO_SOCIAL.md","# Saídas sociais do roteiro\n\n"+"\n".join("- "+str(p.relative_to(project)) for p in result)+"\n")
    return result


def render_carousel(env,project,path,use_proxies=False):
    c=SimpleNamespace(**env)
    carousel=c.read_json(path)
    if carousel.get("enabled") is False:
        return []
    plan={"output":{**carousel.get("output",{"width":1080,"height":1350}),"fps":24,
                    "render_source":"proxies" if use_proxies else "originals"}}
    brand,style=c.load_brand(),c.load_card_style(project)
    outputs=[]
    for index,slide in enumerate(carousel.get("slides",[]),1):
        target=Path(project)/"social/carrossel"/f"CARROSSEL_{index:02d}.jpg"
        segment=copy.deepcopy(slide)
        segment.update(segment_id=f"C{index:03d}",type="card",card_kind="intro" if slide.get("kind")=="cover" else "outro" if slide.get("kind")=="outro" else "phase")
        if slide.get("kind")=="media" and not segment.get("visual"):
            row=next((r for r in c.read_json(Path(project)/"MANIFESTO_MEDIA.json").get("media",[]) if r.get("id")==slide.get("media_id")),{})
            if row:
                segment["visual"]={"media_id":row["id"],"time_sec":float(row.get("scene_start_sec") or 0),"time_basis":"absolute_parent_media"}
        c.card_image(target,segment,plan,brand,style,project)
        outputs.append(target)
    return outputs
