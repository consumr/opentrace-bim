# OpenTrace BIM — TEST-409 LOCAL (base TEST-408)

**Origem:** pacote fornecido pelo usuário `OpenTrace_BIM-TEST-408(1).zip`.
**Escopo:** somente edição local. Nenhum push, commit, branch, PR ou modificação no GitHub.
**Estado:** pré-teste; NÃO validado no Windows/IngeTrazo.

## Mudanças deste pacote

1. **Laje:** os três modos existentes do `SlabTool` ficam acessíveis pela barra contextual: retângulo por diagonal, três pontos (base e largura) e polígono livre. Troca sincronizada com o mesmo motor da paleta radial.
2. **Pilar:** seletor de seção retangular/quadrada, circular ou perfil complexo; seletor de perfil da biblioteca original; largura e comprimento da seção empilhados; diâmetro se circular; grade de nove pontos de ancoragem. Altura e base preservadas.
3. **Viga:** as mesmas opções de seção (largura e altura na seção transversal, diâmetro para círculo, seletor de perfil complexo), grade completa 3×3 ancorada na seção; os antigos três botões laterais foram retirados da barra. O extrudado horizontal existente não foi substituído.
4. **Porta:** opção `Porta` ou `Vão de porta` na barra da ferramenta. A segunda cria apenas a abertura retangular, sem folha/batente, por `EditWall` com Undo. A finalidade `purpose=door` é preservada pelo normalizador; a exportação permanece como `IfcOpeningElement` sem `IfcDoor` fictícia.
5. **Painel:** Layer + BIM/IFC em um único bloco de uma linha quando recolhido; o bloco integra o scroll de `Propriedades detalhadas` em cada página, sem criar cópia do editor compartilhado. O seletor de Layer permanece na barra flutuante.
6. **Classificações:** biblioteca inicial com os **776 nomes reais de entidades da estrutura IFC4** já embarcada no pacote e descrições originais, pesquisável por parte do nome. Seleção inicial automática para a classe nativa do objeto; opção explícita de não classificar e códigos externos/pessoais preservados. Os novos objetos recebem metadados IFC4 mesmo que o usuário não abra o inspector.

**Limite normativo importante:** `OpenTrace BIM / IFC4` é a identificação interna pela classe de entidade IFC4. **Não é** classificação ABNT NBR 15965, Uniclass, OmniClass nem validação de normas. Seus catálogos completos não estão neste pacote; bibliotecas externas continuam dependentes de dados oficiais válidos/usuário. Nunca use `IfcWall` como se fosse um código NBR 15965.

## Verificações executadas neste ambiente

- Análise sintática (`ast.parse` e `compileall`) de todos os arquivos Python: **PASSOU**.
- Catálogo offline: carregou **776** entidades IFC4 e 776 entradas internas; mesclou uma classificação pessoal fictícia, preservando-a: **PASSOU**.
- Normalizador real de aberturas: `purpose=door` preservado e aberturas retangulares existentes sem alteração do campo: **PASSOU**.
- Ligações estáticas dos controles aos modos existentes do motor, perfis e grade de nove âncoras: **PASSOU**.
- **NÃO TESTADO aqui:** PySide6, renderização visual, host IngeTrazo, Undo real, modelagem 3D em Windows e export IFC de cenário completo (dependências ausentes).

## Roteiro de aceite no Windows

- Faça backup da pasta `OpenTrace_BIM` anterior **fora da pasta de plugins**, feche o IngeTrazo e substitua a pasta inteira; confirme que o caminho termina em `plugins/OpenTrace_BIM/__init__.py`. Não instale uma pasta aninhada.
- **Laje:** ative a ferramenta e faça, separadamente, retângulo por diagonal, retângulo por três pontos (base e largura) e polígono; confira estados selecionados da barra.
- **Pilar:** alterne entre retangular e circular; confira se campos largura/comprimento ou diâmetro aparecem adequadamente; teste âncora em canto, centro e outro canto; escolha um perfil complexo já existente.
- **Viga:** alterne as mesmas seções e grade 3×3; confira que o perfil extruda no eixo da viga e o topo continua correto; Undo/Redo depois de mudar âncora.
- **Porta:** no modo `Vão de porta`, insira vão em parede e confirme ausência de esquadria, corte correto, seleção e Undo/Redo; volte a `Porta` e confirme que a porta completa continua sendo criada.
- **IFC/Layer:** expanda/recolha `Propriedades detalhadas` e `Layer / BIM / IFC`; crie objetos sem tocar no menu e confira identificação IFC4 sugerida. Teste código personalizado, desmarcação explícita (`Sem classificação`) e troca de Layer da criação e do selecionado.
- Abra projeto salvo e reinicie IngeTrazo para identificar problemas de persistência.

**Não substituir sua instalação estável sem backup.** Teste primeiro em projeto descartável.
