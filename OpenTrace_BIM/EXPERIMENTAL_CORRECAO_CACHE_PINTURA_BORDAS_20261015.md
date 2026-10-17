# OpenTrace BIM — Correção da aplicação de materiais nas bordas

**PACOTE EXPERIMENTAL ISOLADO — NÃO PUBLICAR OU INTEGRAR SEM AUTORIZAÇÃO.**

Base: `OpenTrace_BIM-EXPERIMENTAL-ISOLADO-ACABAMENTO-BORDAS-PREVIA-ISO.zip`.
Não há alterações no GitHub, nos documentos externos ou no código instalado do IngeTrazo.

## Defeito efetivamente localizado no código

O comando `PaintWallEdgeFinishes` mudava o dicionário `face.attrs` das faces `start`, `end`, `top` e `bottom` e incrementava `scene.version`, mas **não marcava as malhas como tendo atributos alterados**. O renderizador do IngeTrazo pode reutilizar os buffers gráficos do grupo quando o serial geométrico (`_mut_serial`) é igual e `_attrs_dirty` é falso. Por isso o acabamento podia ficar salvo em propriedades, mas **não aparecer na viewport**. Os testes antigos utilizavam faces fictícias e verificavam apenas os dicionários, não o estado de invalidação do cache gráfico.

Referência técnica usada apenas para leitura: `ingelibre/ingetrazo`, `views/viewport.py`, método `_group_chunk()` (cache/reuso do VBO).

## Correções

1. `wall_edge_finishes.py`: após alterar as faces, marca `child.mesh._attrs_dirty = True` e `child.mesh._chunk_dirty = True`. Não muda `_mut_serial`, coordenadas, vértices, encontros ou espessuras.
2. `commands.py`: ao restaurar atributos em Desfazer/Refazer, invalida novamente o cache de cada malha filha. Continua sendo uma operação de histórico, sem recalcular a geometria.
3. `wall_edge_finishes.py` e `commands.py`: o material escolhido é resolvido antes de alterar faces/metadados. Um nome de material indisponível produz erro, sem remover os materiais anteriores silenciosamente.
4. `ui.py`: exibe também mensagens de erro de resolução do material, em vez de aparentar que foi aplicado.

## Verificações realizadas

- **64 testes automatizados passaram**, incluindo 5 novas verificações para o cache gráfico, aplicação nas faces corretas, reversão e material ausente.
- Compilação Python e integridade do ZIP conferidas.
- Não foi possível executar a viewport real Qt/OpenGL no ambiente de testes (PySide6/IngeTrazo indisponíveis). O teste visual no Windows ainda é **obrigatório**: não declarar o defeito resolvido no host antes de confirmar.

## Teste de aceite no Windows

1. Abra uma parede simples e selecione `Wall top` com um material de cor muito diferente da parede. Observe o topo na viewport **sem modificar qualquer dimensão**.
2. Escolha outro material em `Start end`. Confira a extremidade visível; o material deve aparecer imediatamente, sem selecionar outra ferramenta.
3. Repita em parede composta. Verifique que as faces longas e os vãos continuam com os materiais anteriores.
4. Desfaça e refaça; a aparência deve mudar de volta a cada operação.
5. Salve o `.igz`, reabra e mude a altura: os acabamentos devem persistir e acompanhar a parede.
6. Deixe uma face em `Use layer material`; a aparência da composição nessa face deve voltar.

Se os campos mudarem mas o desenho não, capture os textos da barra de status e uma imagem das bordas com o seletor aberto. Não usar este ZIP para trabalho de produção até o aceite visual.
