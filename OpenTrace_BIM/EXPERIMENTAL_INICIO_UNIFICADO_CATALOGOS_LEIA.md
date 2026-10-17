# OPENTRACE BIM — EXPERIMENTAL ISOLADO — CONFIGURAÇÃO INICIAL UNIFICADA

**Data:** 14/10/2026. **NÃO OFICIAL. NÃO PUBLICAR, MERGEAR, TRANSFERIR PARA BRANCH OFICIAL OU SINCRONIZAR CADERNOS SEM AUTORIZAÇÃO EXPRESSA.**

Este pacote é uma cópia local do experimento `IFC43-EQUIVALENCIAS`. Não contém alterações externas ou acesso de escrita a repositórios.

## Interface inicial

- Em projeto **novo, ainda sem nome e não salvo**, o gatilho que antes abria somente `Escolher Template de Layers` agora abre `EXPERIMENTAL · Configuração inicial do projeto`.
- A antiga janela inicial de layers deixa de ser chamada pelo **gerenciador de layers incorporado** neste pacote; continua disponível a janela de gerenciamento dos templates depois da criação.
- Configurações independentes na mesma janela: (1) template do projeto (.igz completo / JSON / vazio), (2) **Conjunto de Combinação de Layers** completo, essencial ou pessoal (ou preservado), (3) IFC4 / IFC4X3_ADD2 experimental, (4) catálogos de classificação selecionados, catálogo principal e equivalências, (5) área de bibliotecas disponíveis (internas e espaços para futuras fontes externas).
- Template `.igz` escolhido origina **cópia com nome diferente**, nunca sobrescreve a origem. Por padrão, mantém os layers do `.igz` se a pessoa não pedir conjunto diferente.
- Se projeto já tem configuração ou é `.igz` existente, a inicialização não reapresenta a janela. O `.igz` salvo contém IDs, seleção dos catálogos, proveniência, tipo de template, conjunto de layers e referências de bibliotecas.
- Página Home mantém entrada manual somente para um projeto novo ainda não configurado.

**OBSERVAÇÃO DE COMPATIBILIDADE:** se houver outra instalação **independente** de `layer_combinations` no diretório de plugins do IngeTrazo, o OpenTrace, por segurança, não a substitui. Essa extensão separada pode continuar abrindo seu próprio assistente, fora do controle deste ZIP. Verifique isso no Windows antes de considerar a substituição da janela antiga validada.

## Classificação sem fabricar códigos

- Importação direta de arquivos `.csv`, `.xlsx` e `.zip` com planilhas/tabelas, sem conversões manuais e sem dependência de `openpyxl` no runtime.
- Seleção permite Uniclass 2015, OmniClass, ABNT NBR 15965, MasterFormat, UniFormat, CoClass e sistemas adicionais de nome livre. Múltiplas fontes podem coexistir. Sistema, código, descrição e hash SHA-256 de arquivo-fonte são preservados no projeto.
- Catálogos reais **não passam a ser automaticamente equivalentes à entidade IFC**. Sem correspondência explícita, objeto retém classe/propriedades IFC, e seus códigos normativos são atribuídos pelo usuário.
- Correspondências código-a-código permanecem importáveis através dos catálogos de equivalências versionados existentes. Relações apenas entre famílias de tabelas (`classification_crosswalks/table_families.json`) **não** geram migrações de códigos.
- As **bases completas oficiais Uniclass 2026, OmniClass e ABNT NÃO ESTÃO EMBUTIDAS** neste ZIP. Não foi possível baixar arquivos oficiais na execução isolada. Por respeito a licenças, versões e procedência, não foram criadas tabelas fictícias.
- Para Uniclass, obter arquivos originais na NBS; o importador já aceita o ZIP, XLSX ou CSV. Para OmniClass e ABNT, usar apenas fonte e licença que autorizem o uso, sem redistribuí-las com o plugin.

## Fontes conferidas nesta revisão

- Uniclass 2015, tabelas de julho/2026 (NBS): https://uniclass.thenbs.com/download — publicação trimestral; CC BY-ND 4.0.
- OmniClass, 15 tabelas (CSI): https://www.csiresources.org/standards/omniclass/standards-omniclass-about
- Restrições explícitas de reprodução, incorporação e divulgação de mapeamentos no contrato OmniClass: https://www.csiresources.org/csistore/oc-eula
- ABNT NBR 15965 e correspondências IFC via SICLIC FAU-USP: https://siclic.fau.usp.br/busca — SICLIC avisa estar em desenvolvimento e que os campos IFC não integram a norma original.
- buildingSMART IFC4.3.2.0: https://technical.buildingsmart.org/standards/ifc/ifc-schema-specifications/

## Testes e limites

- **29 testes automatizados** passaram na execução local, incluindo 23 anteriores, importação CSV/XLSX/ZIP sintéticos, persistência e ligação simulada entre controles de layers e BIM.
- Compilação sintática de todos os módulos Python e integridade ZIP conferidas.
- **NÃO VALIDADO** no IngeTrazo Windows, em PySide6 real, tampouco a conformidade formal IFC4.3 em validador externo. A renderização do novo diálogo e a coexistência com instalações antigas de Layer Combinations requerem ensaio real.
- A área das bibliotecas externas é **reservada**, não carrega automaticamente objetos, portas, materiais ou perfis externos. Seleção funcional neste pacote para as bibliotecas incorporadas.
- Mudanças estritamente isoladas no pacote: `project_setup_dialog.py`, `project_setup.py`, `layer_combinations/__init__.py`, `official_classification_import.py` e este documento. Revisão do arquivo de referências conceituais de tabelas.
