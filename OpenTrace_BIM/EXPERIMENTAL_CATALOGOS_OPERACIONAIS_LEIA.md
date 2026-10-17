**ATENÇÃO — esta nota descreve a ENTREGA ANTERIOR. Para a correção ABNT da entrega atual, leia `EXPERIMENTAL_ABNT_SICLIC_CORRECAO.md`.**

# OpenTrace BIM — EXPERIMENTAL ISOLADO — catálogos operacionais

**Somente para testes. NÃO publicar, NÃO integrar com a branch oficial e NÃO promover automaticamente decisões a outros cadernos.**

## Base e isolamento

Esta variante parte apenas do ZIP local `OpenTrace_BIM-EXPERIMENTAL-ISOLADO-SETUP-UNIFICADO-CATALOGOS.zip`. Não foi feito push, commit, criação de branch nem edição de documentação externa. O pacote experimental anterior foi mantido intacto.

## Funcionamento novo

- **Projeto novo:** a janela unificada mantém template, Conjunto de Combinação de Layers, IFC4/IFC4.3 experimental, classificações e bibliotecas separados; botão **Instalar Uniclass pronto / gerenciar catálogos**.
- **Uniclass 2015:** botão para instalar **uma edição histórica arquivada (janeiro de 2022, 12 tabelas)** a partir de cópia pública de dados NBS em CSV. Download é iniciado SOMENTE pelo clique explícito, com checksum SHA-256 de cada tabela, arquivo cache atômico e reabertura offline. Edição **não é de 2026**. A fonte original NBS contém 15 tabelas na edição atual de julho de 2026; o usuário pode importar a edição atual em ZIP/XLSX/CSV.
- **BIM/IFC:** botão para instalar outros catálogos após a criação do projeto, sem refazer layers/objetos. Outro botão permite pesquisar classificações por código/descrição, atribuir muitas ao mesmo objeto, definir a principal e inserir códigos manuais explicitamente. A gravação do objeto usa o histórico nativo, logo é desfeita/refeita pelo host.
- **ABNT NBR 15965 / OmniClass / outros:** fontes oficiais acessíveis pelos botões de referência; importar arquivo obtido legitimamente pelo usuário ou referenciar manualmente código validado na origem. Nenhuma tabela completa proprietária fica embutida neste ZIP e nenhum download automatizado dessas fontes ocorre.
- **Migração:** catálogos carregados no projeto são destinos selecionáveis. A tabela de revisão usa busca/completar em vez de milhares de itens repetidos. Classificações secundárias e outros sistemas ativos são preservados. Referências verificadas podem ser registradas manualmente com URI, edição e revisão; sugestões por semelhança não são aplicadas automaticamente.
- **Exportação:** utiliza `IfcClassification` e `IfcRelAssociatesClassification` já presentes no motor, permitindo várias classificações no mesmo objeto. IFC4 continua padrão; IFC4.3 ADD2 continua experimental e NÃO certificado. Perfis de exportação anteriores intocados.

## Obtenção e direitos

- Fonte editorial Uniclass (versão atual): https://uniclass.thenbs.com/download — licença NBS CC BY-ND 4.0 https://creativecommons.org/licenses/by-nd/4.0/.
- Arquivo histórico opcional 2022 espelhado: https://github.com/buildig/uniclass-2015 — não confundir com versão oficial corrente.
- ABNT (consulta SICLIC/FAU-USP): https://siclic.fau.usp.br/busca ; verificar códigos/termos com a norma antes de usá-los como definitivos.
- OmniClass / licença CSI: https://www.csiresources.org/csistore/oc-eula — não incorporar automaticamente base restrita.

## Verificações e limitações

- Sintaxe Python: conferida; ZIP: verificar integridade depois do empacotamento.
- 34 testes automatizados foram executados com resultado positivo (29 anteriores + 5 novos). Os novos cobrem instalação completa de 12 tabelas **com rede simulada**, falha atômica, reabertura offline, referências múltiplas, idempotência e conflito de códigos. Exportação IFC em IFC4/IFC4.3 verificada em teste anterior do pacote por geração de arquivos sintéticos.
- **Ainda NÃO foi validado:** acesso HTTP efetivo ao espelho no Windows; visual Qt no IngeTrazo; leitura da planilha oficial atual de julho/2026; validação IFC4.3 em aplicação externa; equivalências específicas entre ABNT, OmniClass e Uniclass. Não há equivalências código a código normativamente homologadas nesta entrega.
- Nenhuma linha de tabela foi inventada para simular um catálogo oficial. Os dados arquivados não estão embutidos neste ZIP; são transferidos pelo instalador opt-in quando houver internet.

## Teste recomendado no Windows

1. Instale em ambiente/cópia isolada, sem substituir a 410 nem a 420.
2. Abra projeto novo → **Gerenciar catálogos** → **Instalar Uniclass 2022** (necessita internet); confira número de códigos. Alternativamente importe ZIP/XLSX/CSV da edição corrente NBS.
3. Crie uma porta, selecione-a → BIM → **Pesquisar e associar códigos** → procure código existente; associe uma segunda classificação manualmente.
4. Salve `.igz` e reabra, confira associações, layers e fontes do catálogo. Exporte em IFC4, confira relações; só então experimente IFC4.3 e validador externo.
5. BIM → **Migrar catálogo IFC** → escolha catálogo previamente carregado, revise e teste Desfazer.
