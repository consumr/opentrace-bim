# OpenTrace BIM — Relatório técnico de continuidade: paredes

**Data:** 16/10/2026  
**Distribuição:** EXPERIMENTAL — ISOLADO  
**Base de trabalho:** `OpenTrace_BIM-EXPERIMENTAL-ISOLADO-MATERIAL-IMEDIATO-CORRECAO-REAL(1).zip` (anexo recebido)  
**Integração ao oficial:** nenhuma; sem GitHub, commits, pushes ou alterações no servidor.

## 1. Alterações feitas

### Simple / Composite
- O botão `Composite` da barra contextual compartilha o estado real do controle `structure` do editor; a escolha agora chega a um **comando `EditWall` no histórico nativo** quando uma parede está selecionada, em vez de atualizar apenas as opções da próxima parede.
- Menu da ferramenta de parede: ao existir uma única parede selecionada, alterna o tipo do **objeto selecionado** sem ativar a ferramenta de desenho nem limpar a seleção. Sem seleção, configura a **próxima parede**, preservando o fluxo de criação anterior.
- Simple → Composite: converte a parede para uma composição inicial com **uma camada core** da espessura e do material do objeto original. A partir daí, o editor de camadas permite inserir e editar mais camadas.
- Composite → Simple: produz corpo único com a espessura total; usa o material principal da parede, se existir, ou o material da camada core. A pilha de camadas é substituída (pode ser restaurada imediatamente com Undo).
- Atualização sincronizada de painel/controle/barra: quando há uma parede selecionada, ela prevalece sobre o modo de criação ainda ativo. A prévia de comprimento da próxima parede deixa de sobrescrever inadvertidamente o comprimento do objeto selecionado.
- Falha de conversão retorna erro e restaura o estado da UI a partir do objeto.

### Pintura de superfícies
- O seletor do material principal e os quatro seletores (`Start end`, `Finish end`, `Wall top`, `Wall bottom`) resolvem a **seleção do documento no instante da mudança**. Não dependem de um `target` que pode ter ficado nulo/desatualizado durante a sincronização da interface.
- Permanecem os comandos nativos `PaintWallBodyMaterial` e `PaintWallEdgeFinishes`, que pintam `Face.attrs` na cena real, registram estado anterior/posterior e invalidam cache visual sem reconstruir malhas.
- Criado `PaintWallLayerMaterials`: mudanças **somente de material** em camadas existentes de paredes compostas atualizam as faces nativas, preservando os acabamentos independentes de topo/bordas. Alterações de ordem, espessura, geometria e identidade das camadas seguem para o motor existente `EditWall`.
- A assinatura de junções ignora propriedades de aparência: pintar paredes ou camadas não provoca uma regeneração geométrica desnecessária por mudança no registro de materiais.
- Sem seleção, a escolha de material principal atualiza os parâmetros **da próxima parede** e não tenta editar uma seleção antiga.
- `Apply preset` permanece exclusivamente uma ação de substituição por preset salvo. Não foi reaproveitado como confirmação de pinturas/medidas.

## 2. Arquivos alterados

- `ui.py` — resolução da seleção, conversão, prioridade edição/criação, roteamento material e camadas, assinatura da regeneração de junções.
- `commands.py` — adição do comando `PaintWallLayerMaterials` com Desfazer/Refazer.
- `contextual_bar.py` — contexto de parede selecionada tem prioridade sobre ferramenta de desenho ociosa.
- `_experimental_tests/test_wall_edge_finishes_and_uv_preview.py` — assert antigo atualizado para a assinatura de junções expandida.
- `_experimental_tests/test_wall_immediate_material_real.py` — assert antigo atualizado para a resolução do alvo selecionado.
- `_experimental_tests/test_wall_direct_conversion_materials_20261016.py` — novos testes de efeitos reais dos comandos, com cenas e faces simuladas.
- Este relatório e `PACKAGE_MANIFEST.txt` — documentos de entrega **dentro do ZIP**, sem atualização de documentação externa.

Nenhum módulo de portas, janelas, bibliotecas, IFC, templates ou exportador foi reescrito.

## 3. Testes efetivamente executados neste ambiente

- `python -m pytest -q OpenTrace_BIM/_experimental_tests`: **91 testes aprovados** (79 herdados e 12 novos).
- `python -m compileall -q OpenTrace_BIM`: sintaxe Python verificada.
- Execução das **classes de comando verdadeiras** (`CreateWall`, `EditWall`, `PaintWallBodyMaterial`, `PaintWallEdgeFinishes`, `PaintWallLayerMaterials`) extraídas diretamente do código de produção, com **dublês da cena/malha/host**: registro real em `Face.attrs`, faces da parede simples e composta, pintura das quatro extremidades, preservação de pintura independente, persistência em `ext[KEY]` e Desfazer/Refazer.
- Execução dos **corpos verdadeiros** dos handlers `wall_material_changed`, `edge_finishes_changed` e `structure_changed` com histórico simulado: comprovada a chegada dos comandos às faces e à alteração dos metadados quando `target` está desatualizado.
- Regeneração/swap de filhos executados pelo `EditWall` de produção com gerador geométrico simulado, incluindo conversão nas duas direções, ajuste de altura, reaplicação das pinturas e Undo/Redo.
- Negativa para material inexistente validada sem gravar materiais ou pintura parcial.
- Integridade do novo ZIP validada por `ZipFile.testzip()`; lista de arquivos comparada com o pacote-base.

**Escopo honesto:** os testes acima executaram comandos e mutações de faces, não somente valores de controles, **mas usaram dublês para o motor geométrico e cache do IngeTrazo**. Não constituem validação da aplicação real.

## 4. Pendências e roteiro de aceite no IngeTrazo Windows

**Não testado aqui:** despacho efetivo dos sinais Qt, renderização OpenGL, aplicação visual de texturas na viewport, comportamento do histórico do host gráfico e compatibilidade em `.igz` real após salvar/reabrir.

Sugestão de aceite, em um arquivo de teste descartável:

1. Desenhar uma parede **Simple** e uma **Composite** com pelo menos duas camadas e materiais distintos. Em ambas, trocar sucessivamente `Start end`, `Finish end`, `Wall top`, `Wall bottom`. Observar a **malha na viewport sem pressionar Apply preset**.
2. Selecionar cada parede já existente (inclusive com a ferramenta de parede ativa), repetir as quatro pinturas e verificar que o objeto correto muda, mantendo material independente das demais faces. Testar `Use layer material`.
3. Na parede simples selecionada, trocar material principal duas vezes. Na composta, trocar material de cada camada; confirmar o efeito imediato no modelo e que a topologia não é reconstruída para alteração puramente visual.
4. Com objeto selecionado, clicar em **Composite**, observar nova estrutura/camadas no painel, e depois **Simple**. Desfazer/Refazer cada conversão. Sem objeto selecionado, alternar entre tipos e **criar novas paredes** para confirmar o resultado na viewport.
5. Com a pintura aplicada, mudar altura/espessura, trocar composições, editar um encontro e regenerar paredes; verificar que os acabamentos permanecem.
6. Aplicar um **preset diferente por Apply preset**, confirmar a mudança de tipo e depois voltar a editar materiais individualmente sem Apply. Salvar, fechar e reabrir `.igz` para testar persistência.
7. Repetir ao menos uma sequência de passos com Undo/Redo e dois tipos de materiais (cor sólida e textura) para capturar eventual cache visual residual.

**Critério de conclusão:** as superfícies e geometrias devem mudar **no IngeTrazo Windows**, não apenas em testes automatizados. Nenhum resultado visual do Windows foi declarado aprovado neste relatório.

## 5. Instrução de isolamento

Manter este ZIP como pacote experimental independente. Instalar apenas numa cópia do ambiente de testes e guardar o ZIP anterior. **Não publicar, integrar ou substituir a distribuição oficial sem autorização explícita.**
