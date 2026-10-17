# OpenTrace BIM — Correção experimental: material imediato da parede

**ISOLADO. Não integrar, publicar, alterar GitHub, branches, cadernos ou documentos externos sem autorização explícita do proprietário.**

## Causa e mudança

A versão anterior mudou o rótulo do botão para `Apply preset`, mas o seletor `Material` da parede simples continuava roteado para `defaults_changed -> apply_changes -> EditWall`, um comando que regenera toda a geometria, mesmo quando somente a aparência muda. O formulário ainda podia privilegiar o estado da ferramenta de desenho em vez de uma parede selecionada. Esses caminhos misturavam alteração de propriedades com aplicação de presets.

Nesta revisão, `Material.currentIndexChanged` aciona `wall_material_changed`, dedicado à mudança de aparência de paredes simples **selecionadas**. O novo `PaintWallBodyMaterial` atualiza as faces nativas e `material_name` na parede existente, preservando os materiais opcionais de bordas, posição, IFC, UID, comprimento, camadas e geometria. Marca o cache visual da malha como inválido e suporta Desfazer/Refazer, incluindo a aparência anterior. Paredes compostas continuam usando os controles de materiais por camada; mudanças geométricas continuam usando `EditWall`.

A seleção de `Apply preset` continua explícita e efetivamente aciona a aplicação do preset, independente da edição de propriedades. Adicionada orientação textual na seção de presets. Uma seleção de material inválido retorna erro e reverte a interface para o valor persistido, em vez de aparentar aplicação.

## Testes locais

- 79 testes automatizados passaram (74 antigos + 5 novos).
- Teste de pintura real das `Face.attrs` em faces de uma parede simples simulada (não apenas alteração do texto selecionado).
- Persistência da referência de material, Desfazer/Refazer, preservação dos acabamentos independentes, invalidação do cache e garantia de não reconstrução das faces no caminho testado.
- Verificação estática da ligação do seletor a `PaintWallBodyMaterial` e da separação da ação `Apply preset`.
- Sintaxe Python e integridade ZIP verificadas.

**Pendente:** funcionamento visual no IngeTrazo no Windows e possíveis particularidades da cache do viewport real. Sem PySide6/host gráfico neste ambiente; não declarar aceite visual antecipadamente.

## Roteiro mínimo no Windows

1. Selecione uma parede simples já desenhada.
2. Em `Geometry and properties > Material`, escolha duas cores/texturas bem contrastantes, uma após a outra. A parede deve mudar imediatamente, sem clicar em `Apply preset`.
3. Em `Edge finishes`, escolha `Start end = Aluminium`, depois um material bem contrastante. Observe especificamente a extremidade inicial da linha de referência (não a face longa).
4. Pressione Ctrl+Z e Ctrl+Y; a aparência e os nomes selecionados devem acompanhar o histórico.
5. Só depois selecione outro item em `Library · Wall` e clique `Apply preset` para substituir o tipo. O uso do seletor de material não deve alterar a geometria.
6. Repita com uma parede composta, alterando material em uma de suas camadas; esse caminho continua usando o motor de camadas e deve permanecer sob verificação visual.
