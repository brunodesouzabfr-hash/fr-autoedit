"""Frame-aware joins. Masters render only two transition inputs at a time."""
from pathlib import Path
from types import SimpleNamespace


def join_segments(env, segments, target, definitions=None, transition_duration=.32, quality=None, draft=None):
    c = SimpleNamespace(**env)
    target = Path(target)
    if not segments:
        raise c.AutoEditeError("Não há segmentos para unir.")
    # Todo draft explícito privilegia resposta rápida e previsível. Chamadas
    # legadas sem transições mantêm o atalho apenas para timelines longas.
    if draft is True or (len(segments) > 24 and transition_duration <= .20 and draft is None and not any("transition" in s for s in definitions or [])):
        c._concat_copy_segments_with_progress(segments, target)
        return
    if len(segments) < 2 or not definitions or len(definitions) != len(segments):
        c._concat_copy_segments(segments, target)
        return
    if all(s.get("transition", "fade") == "cut" or float(s.get("transition_duration_sec", transition_duration)) == 0 for s in definitions[1:]):
        c._concat_copy_segments(segments, target)
        return
    infos = [c.parse_probe(p, c.ffprobe(p)) for p in segments]
    fps = float(infos[0].get("fps") or 24)
    durations = [round(float(v.get("duration_sec") or 0)*fps)/fps for v in infos]
    overlaps = [0.0]
    for i in range(1, len(segments)):
        s = definitions[i]
        raw = 0 if s.get("transition", "fade") == "cut" else max(0, float(s.get("transition_duration_sec", transition_duration)))
        overlaps.append(round(min(raw, durations[i-1]*.25, durations[i]*.25)*fps)/fps)
    quality = quality or {}
    codec = ["-c:v", "libx264", "-preset", "veryfast", "-crf", str(int(quality.get("video_crf",18))),
             "-pix_fmt", "yuv420p", "-r", str(fps), "-c:a", "aac", "-b:a", str(int(quality.get("audio_bitrate_kbps",192)))+"k",
             "-ac", "2", "-ar", "48000", "-movflags", "+faststart", "-threads", "2"]
    def encode(inputs, graph, dest):
        dest.parent.mkdir(parents=True, exist_ok=True)
        partial = dest.with_name(dest.stem + ".partial.mp4")
        cmd = ["ffmpeg", "-y", "-nostdin", "-hide_banner", "-loglevel", "error", "-filter_complex_threads", "1"]
        for p in inputs:
            cmd += ["-i", str(p)]
        try:
            command = [
                *cmd, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
                *codec, str(partial),
            ]
            for attempt in range(2):
                partial.unlink(missing_ok=True)
                result = c.run(
                    command, capture=True, check=False,
                    operation="junção de segmentos",
                )
                if result.returncode == 0:
                    break
                details = (result.stderr or result.stdout or "").strip()
                retryable = (
                    "Could not open encoder before EOF" in details
                    or "Nothing was written into output file" in details
                )
                if attempt == 0 and retryable:
                    c.warning(f"Junção curta sem saída completa; repetindo {dest.name} uma vez.")
                    continue
                raise c.AutoEditeError(
                    f"Falha ao executar ffmpeg (código {result.returncode}).\n{details[-1800:]}"
                )
            c.validate_rendered_media(partial)
            partial.replace(dest)
        finally:
            partial.unlink(missing_ok=True)
    # Bodies plus overlapping tails/heads; bounded memory, O(n) decoding.
    root = target.parent / ("." + target.stem + "_joins")
    chunks=[]
    for i,p in enumerate(segments):
        head = overlaps[i]
        tail = overlaps[i+1] if i+1 < len(segments) else 0
        end = durations[i]-tail
        body = root/f"{i:05d}_body.mp4"
        graph=(f"[0:v]trim=start={head:.6f}:end={end:.6f},settb=AVTB,setpts=PTS-STARTPTS,fps={fps:.6f}[v];"
               f"[0:a]apad=pad_dur={durations[i]:.6f},atrim=start={head:.6f}:end={end:.6f},asetpts=PTS-STARTPTS[a]")
        encode([p],graph,body)
        chunks.append(body)
        if tail:
            effect=c.TRANSITION_MAP[definitions[i+1].get("transition","fade")]
            boundary=root/f"{i:05d}_transition.mp4"
            graph=(f"[0:v]trim=start={end:.6f}:end={durations[i]:.6f},settb=AVTB,setpts=PTS-STARTPTS,fps={fps:.6f}[x];"
                   f"[1:v]trim=start=0:end={tail:.6f},settb=AVTB,setpts=PTS-STARTPTS,fps={fps:.6f}[y];"
                   f"[x][y]xfade=transition={effect}:duration={tail:.6f}:offset=0[v];"
                   f"[0:a]apad=pad_dur={durations[i]:.6f},atrim=start={end:.6f}:end={durations[i]:.6f},asetpts=PTS-STARTPTS[ax];"
                   f"[1:a]apad=pad_dur={durations[i+1]:.6f},atrim=start=0:end={tail:.6f},asetpts=PTS-STARTPTS[ay];"
                   f"[ax][ay]acrossfade=d={tail:.6f}:c1=tri:c2=tri[a]")
            encode([p,segments[i+1]],graph,boundary)
            chunks.append(boundary)
        c.info(f"Junções da master {i+1}/{len(segments)}")
    c._concat_copy_segments(chunks,target)
    expected=sum(durations)-sum(overlaps)
    measured=float(c.parse_probe(target,c.ffprobe(target)).get("duration_sec") or 0)
    if abs(measured-expected) > max(.35, len(segments)*.03):
        raise c.AutoEditeError(f"Duração das junções divergente: {measured:.3f}s obtidos; {expected:.3f}s previstos.")
