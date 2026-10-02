# M7 — Proxy Integrity

**PRE-AUDIT ASSUMPTION:** `build_manifest` reutiliza proxy com source path/size/status e arquivo não vazio, `create_video_proxy` escreve partial→target, `create_chatgpt_package` varre `proxies/` por arquivo; M0 confirma versão local. M6 poderá chamar validador M7 quando pronto. Escopo: lineage, cobertura e bloqueio de pacote incompleto, não nova Media Intelligence Next.

Registrar `source_asset_id`, `source_hash`, `proxy_hash`, `source_duration`, `proxy_duration`, `coverage_start`, `coverage_end`, `generation_parameters` e status. Hashes são de arquivos **diferentes**. Determinar duração e range com FFprobe/decodificação amostral quando apropriado, tolerância técnica medida em fixtures (VFR, arredondamento de FPS, delay de áudio, imagem). Um proxy 0 bytes, faltante, ilegível ou truncado nunca passa pela simples presença. Mapeamento source↔proxy e lotes precisa usar manifesto corrente, inclusive split de proxy grande com cobertura das partes em ordem, sem omissões/duplicações. Invalidar cache quando source hash ou parâmetros mudarem. Mensagem de falha inclui ID e ação recuperável sem mexer no original.

Testes: vídeo sintético íntegro, truncado, fonte trocada mesmo tamanho, vídeo sem áudio, VFR e proxy dividido; registrar durations/ranges, estado do pacote, integridade do original. Não comparar `source_hash == proxy_hash`. Matriz M7.
