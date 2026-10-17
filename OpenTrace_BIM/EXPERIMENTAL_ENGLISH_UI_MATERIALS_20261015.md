# OpenTrace BIM — pacote experimental isolado: interface em inglês

**Data:** 2026-10-15. **Não publicar nem integrar sem autorização explícita.**

Base: `OpenTrace_BIM-EXPERIMENTAL-ISOLADO-GERENCIADOR-BIBLIOTECAS-PREVIAS-IFC.zip`.

## Ajustes realizados

- Gerenciador de bibliotecas e objetos: botões, pesquisa, títulos, mensagens, tipos e pastas apresentados em inglês.
- Seletor de materiais: títulos, pesquisa, categorias e descrição de prévia em inglês.
- Painel OpenTrace: `Detailed properties`, Home, textos de configuração e atalhos visíveis em inglês.
- Presets incorporados de parede, laje, pilar e viga: nomes/grupos em inglês (`Concrete`, `Reinforced concrete`, `Timber`, `Steel` etc.).
- Perfis estruturais e arquitetônicos incorporados: nomes e pastas de exibição em inglês.
- Bibliotecas básicas distribuídas com o plugin: nomes em inglês sem alterar os IDs das coleções.
- Leitura de bibliotecas antigas: um tradutor estritamente visual apresenta títulos de presets incorporados em inglês, sem reescrever registros pessoais.
- Mensagens de erro e confirmação dos recursos individuais corrigidas em inglês.

## Materiais: separação de responsabilidades

- O **IngeTrazo** mantém o motor e o registro de materiais, incluindo nomes, cores, texturas e escala.
- O **OpenTrace** organiza e pesquisa materiais existentes, exibe miniaturas e disponibiliza sua aplicação em elementos paramétricos.
- Categorias como `Cement & Mortars`, `Blocks & Bricks`, `Paints & Colors`, `Stone`, `Patterns & Fabrics` são **pastas virtuais** do OpenTrace: não alteram o material original no IngeTrazo.
- Os nomes pessoais de materiais e os nomes autorais de presets permanecem intocados, mesmo quando foram criados em português. IDs, referências IFC e vínculos não são traduzidos.
- Criar uma textura nova *pela interface do OpenTrace*, com cadastro direto no registro nativo, ainda **não** faz parte desta entrega.

## Verificação

- **41 testes automatizados aprovados**, incluindo 5 casos novos de idioma/identidade.
- `compileall` Python aprovado; integridade ZIP verificada.
- **Sem execução Qt/PySide6 no Windows neste ambiente.** Verificação visual no IngeTrazo ainda pendente.
- Nenhuma alteração em GitHub, branches, cadernos ou documentos externos.
