# OpenTrace BIM v0.44.0 — instalação e atualizações

## Instalação no IngeTrazo

1. Feche o IngeTrazo.
2. Abra a pasta de plugins (no Windows, normalmente `%APPDATA%\ingetrazo\plugins\`).
3. Faça uma cópia de segurança da pasta `OpenTrace_BIM` que já existir.
4. Extraia este ZIP **mantendo a pasta `OpenTrace_BIM`** diretamente dentro de `plugins`.
5. Abra novamente o IngeTrazo e confirme que o plugin informa `0.44.0` na tela Home.

**Não copie apenas `updater.py`; o pacote é uma extensão completa.** Não renomeie `OpenTrace_BIM`, pois a verificação da atualização exige o nome correto.

## Atualização independente

Na aba **Home**, pressione **Check for updates**. A partir da v0.44.0, a busca é feita em
`https://api.github.com/repos/lelopes05/opentrace-bim/releases?per_page=30`;
não há consulta ao catálogo de extensões do IngeTrazo. O botão apenas consulta;
o arquivo ZIP só é baixado e instalado após confirmação do usuário.
O atualizador confere versão, nome do pacote, SHA-256 oficial do asset,
segurança dos caminhos do ZIP e compilação sintática dos arquivos Python.
Reinicie o IngeTrazo após a instalação.

A caixa **Automatically check for updates** é opt-in. Quando marcada, faz uma verificação na abertura; não baixa nem instala sem autorização.

## Importante para as instalações antigas

- **v0.12.9:** o botão que já está instalado foi programado para consultar `ingelibre/ingetrazo-extensions/main/catalog.json`. Nenhum pacote novo consegue mudar esse código remotamente. Para aparecer a v0.44.0 naquele botão, a equipe do catálogo precisa atualizar sua entrada de `opentrace_bim`; alternativa: instalar este ZIP uma vez manualmente.
- **v0.42.0 e v0.42.1:** vieram com o botão desativado. Instale este ZIP uma vez manualmente.
- **v0.42.2:** já consulta GitHub, mas só encontrará a v0.44.0 **após a v0.44.0 ter sua Release e asset publicados**.
- **v0.44.0:** pronto para consultar Releases futuras sem intervenção do catálogo do IngeTrazo.

## Status de validação

Os testes locais verificaram sintaxe, integridade e operação do atualizador em simulação Python. A interface gráfica e a aplicação do update **ainda exigem teste real no IngeTrazo Windows**. O ZIP local **não foi publicado no GitHub**.
