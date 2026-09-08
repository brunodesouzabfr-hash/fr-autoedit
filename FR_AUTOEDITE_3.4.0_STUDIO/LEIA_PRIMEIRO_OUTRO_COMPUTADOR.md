# Instalar o FR AutoEdite em outro computador

Este pacote contém o **FR AutoEdite Studio 3.4.0** completo. Ele foi preparado
para **Parrot OS, Debian e Ubuntu** em computadores de 64 bits com acesso a um
terminal e permissão para instalar programas.

## Instalação mais fácil

1. Copie o ZIP completo para o outro computador.
2. Descompacte o ZIP.
3. Abra a pasta extraída `FR_AUTOEDITE_3.4.0_STUDIO`.
4. Clique com o botão direito numa área vazia e escolha **Abrir no terminal**.
5. Execute exatamente:

```bash
chmod +x INSTALAR_EM_OUTRO_COMPUTADOR.sh
./INSTALAR_EM_OUTRO_COMPUTADOR.sh
```

O instalador verifica dependências, instala o programa, preserva uma versão
anterior, testa a geração de cards e abre o Studio no navegador.

Na lateral do painel deve aparecer:

```text
STUDIO 3.4.0 · ROTEIRO ISOLADO
```

## Instalar também os recursos opcionais

Para instalar QR Code, narração local, cofre de credenciais, integração por
`rclone` e gravação de datas do Google Takeout com ExifTool, use:

```bash
./INSTALAR_EM_OUTRO_COMPUTADOR.sh --com-opcionais
```

## Executar uma validação completa

O teste completo cria mídias sintéticas temporárias e valida preparação,
cards circulares, Google Takeout, time-lapse, renderizações, Reels, lotes e
auditoria:

```bash
./INSTALAR_EM_OUTRO_COMPUTADOR.sh --teste-completo
```

Ele demora mais que o teste rápido. Não usa fotos ou vídeos pessoais.

## Instalar sem abrir o navegador

```bash
./INSTALAR_EM_OUTRO_COMPUTADOR.sh --sem-abrir
```

Para abrir posteriormente:

```bash
fr-autoedite studio
```

Se o terminal não reconhecer `fr-autoedite`, use:

```bash
~/.local/bin/fr-autoedite studio
```

## Onde ficam os arquivos

- Programa instalado: `~/.local/share/fr-autoedite/`
- Comando: `~/.local/bin/fr-autoedite`
- Projetos: `~/FR-AutoEdite/Studio/`
- Contexto para auditoria por IA:
  `~/.local/share/fr-autoedite/CONTEXTO_PARA_IA_AUDITORIA_E_AUTOMACAO.md`
- Versões anteriores: `~/.local/share/fr-autoedite.backup.DATA-HORA/`

## Requisitos e limites reais

- Sistema suportado automaticamente: Parrot OS, Debian ou Ubuntu.
- Espaço livre recomendado: pelo menos duas vezes o tamanho do ZIP de mídias,
  além do espaço das renderizações.
- O funcionamento principal é local e gratuito.
- APIs são opcionais e podem gerar cobrança se o usuário ativá-las.
- O Google Drive exige autorização própria pelo `rclone`.
- O Google Takeout deve ser solicitado e baixado pelo usuário; o Studio recebe
  esse ZIP, lê os JSONs e cria um ZIP normalizado sem alterar o original.
- Nenhuma automação substitui assistir integralmente à master e aos Reels.

## Entregar o projeto a uma IA técnica

Envie à IA:

1. o ZIP desta aplicação;
2. `CONTEXTO_PARA_IA_AUDITORIA_E_AUTOMACAO.md`;
3. se houver um erro real, o texto completo exibido no Studio e o log técnico;
4. somente mídias sintéticas ou um projeto autorizado para testes.

Peça que a IA siga integralmente o contexto e devolva um novo ZIP testado,
sem apagar originais, sem enfraquecer testes e sem inserir chaves de API.
