# Guia rápido — FR AutoEdite 3.4.0 Fase 2

Este passo a passo é para quem quer instalar, abrir o Studio e concluir o fluxo
de edição assistida por uma IA externa.

## 1. Abrir o terminal

No Linux, abra o aplicativo **Terminal**.

## 2. Baixar ou atualizar o código

Para a primeira instalação:

```bash
git clone https://github.com/brunodesouzabfr-hash/fr-autoedit.git
cd fr-autoedit
git switch main
```

Se o repositório já existe:

```bash
cd /CAMINHO/PARA/fr-autoedit
git switch main
git pull --ff-only origin main
```

Não execute `git pull` enquanto houver mudanças pessoais no código. Confira
antes com:

```bash
git status --short
```

## 3. Instalar dependências

```bash
sudo apt update
sudo apt install -y python3 python3-pil ffmpeg unzip zip xdg-utils
```

## 4. Instalar o FR AutoEdite

```bash
cd FR_AUTOEDITE_3.4.0_STUDIO
chmod +x install.sh fr-autoedite
./install.sh
fr-autoedite --versao
```

O resultado esperado é `FR AutoEdite 3.4.0`.

## 5. Abrir o Studio

```bash
fr-autoedite studio
```

Se o terminal não encontrar o comando:

```bash
~/.local/bin/fr-autoedite studio
```

## 6. Criar o projeto e inserir o ZIP

1. No Studio, crie um projeto.
2. Escreva apenas o contexto que você conhece e pode confirmar.
3. Selecione o ZIP com as fotos e vídeos.
4. Aguarde o envio terminar.
5. Não feche a janela durante uma tarefa em andamento.

O ZIP original é preservado no projeto local.

## 7. Gerar proxies e manifesto

Clique em **Preparar projeto**. A aplicação:

- extrai o ZIP com validação;
- cataloga as mídias;
- cria proxies e miniaturas;
- gera o manifesto;
- pode retomar itens já concluídos após uma interrupção.

## 8. Gerar o PACOTE_PARA_IA

Abra a área **MÍDIAS PARA A IA** e clique em
**Gerar/atualizar PACOTE_PARA_IA**.

Se já houver pacote, escolha conscientemente:

- `replace`: substituir o pacote gerado;
- `version` ou `history`: preservar a versão anterior;
- `cancel`: não alterar.

## 9. Enviar o material para a IA

Anexe à IA:

- `00_NAO_EDITAR_CONTEXTO_PROJETO.md`;
- `01_EDITAR_E_DEVOLVER_ROTEIRO_MESTRE.md`;
- `02_NAO_EDITAR_MANIFESTO_MEDIA.json`;
- `04_NAO_EDITAR_INSTRUCOES_PARA_IA.md`;
- todos os ZIPs de `03_NAO_EDITAR_LOTES_DE_PROXIES/`.

Copie para o chat o conteúdo do arquivo 04. Peça à IA que assista aos proxies,
edite somente o Roteiro Mestre e devolva apenas o Markdown completo.

## 10. Salvar a resposta

Copie a resposta integral para:

```text
PACOTE_PARA_IA/05_RESPOSTA_DA_IA_IMPORTAR_AQUI.md
```

Não remova os marcadores `FR_AUTOEDITE_JSON_BEGIN` e
`FR_AUTOEDITE_JSON_END`.

## 11. Importar e validar

No Studio:

1. selecione o Markdown respondido;
2. clique em **Enviar e validar resposta**;
3. leia os erros e avisos;
4. corrija o arquivo se houver erro bloqueante;
5. clique em **Aplicar decisões** somente após a validação.

Pedidos ainda não executáveis podem ficar preservados como metadados com aviso.
Isso não deve invalidar os demais trechos seguros.

## 12. Revisar cena por cena

Na **ETAPA 06 · FILME PRINCIPAL**:

- confira vídeo de origem e trecho usado;
- confira início, fim e duração;
- revise serviço, card e família visual;
- corrija conflitos;
- abra a prévia e percorra a timeline.

## 13. Gerar e assistir ao rascunho

Gere o rascunho por proxies. Assista ao vídeo inteiro e confira:

- ordem e ritmo;
- cortes e transições;
- textos, cards e balões;
- troca de serviço;
- locução e legenda;
- CTA;
- enquadramento e legibilidade.

## 14. Renderizar

Depois da revisão, selecione os originais como fonte da master e renderize.
Revise também Reels e Stories antes de entregar ou publicar.

## Segurança

Nunca envie ao GitHub `Studio/`, vídeos, proxies, ZIPs, originais, renders
reais, `.env`, tokens, chaves, credenciais ou logs pessoais.

Antes de qualquer commit:

```bash
git status --short
```

Consulte [README.md](README.md) e [UPGRADE_3.4.0.md](UPGRADE_3.4.0.md) para mais
detalhes.
