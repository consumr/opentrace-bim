# OpenTrace BIM — MERGE EXPERIMENTAL ISOLADO (410 + 420)

**NÃO É RELEASE. NÃO PUBLICAR. NÃO FAZER MERGE, PUSH, PR, ATUALIZAÇÃO DE CADERNOS OU PROMOÇÃO AUTOMÁTICA.**

Pacote exclusivamente local, gerado em 14/10/2026 a partir de dois ZIPs enviados pelo responsável:
- `OpenTrace_BIM-TEST-410-LOCAL(2).zip`, SHA256 `f35f95bfca96f1e6731a8b203d0cf48c9dcf1b9963852ceac60c72b12c704c31`;
- `OpenTrace_BIM-TEST-420(2).zip`, SHA256 `5cbb83fd5f624c2f2e788014c6362c141143f4940416ec7a0b03dd2fcb27f96b`.

Nenhuma operação Git foi realizada. Nenhuma branch ou repositório foi criado ou modificado. Foi consultado em **somente leitura** o código público do host IngeTrazo para conferir a API nativa de arquivos `.igz`. Todas as alterações estão dentro **desta cópia experimental local**. O recurso de atualização do pacote foi desativado neste build. A pasta interna deve continuar chamada `OpenTrace_BIM` para compatibilidade de importações do host. Instale somente em ambiente de teste isolado, **nunca substituindo a instalação que você deseja preservar sem backup**.

## Merge aplicado

- **Base 410**: navegação, barra contextual, Home, propriedades de objetos, sincronização e os modos `Porta` / `Vão de porta` preservados do pacote 410 LOCAL. PDF de maquetes usado como referência visual, sem redesenho da interface.
- **Motor de folhas da 420**: `door_leaf_grid.py`, `door_leaf_editor.py` e o contrato de folha em `door_window_core.py`, `door_window_geometry.py`, `door_window_properties.py`.
- **Traduções**: adicionadas chaves novas do motor de folhas, preservando as da 410.
- **Vão de porta**: preservado o fluxo existente em `wall_opening_place.py`, `contextual_bar.py`, `tool_row.py` da 410, que edita a parede sem criar folha ou batente. **A aparência, seleção e Undo no Windows ainda precisam de aceite.**
- **Editor de folha**: o editor tabular da 420 foi incorporado; a prévia frontal 2D gráfica permanece como bloco futuro, fora do escopo.

## Template + classificação — seleções independentes

O Home tem a ação **`Configurar projeto novo · template + catálogo`**, habilitada apenas em documento novo, ainda sem caminho de arquivo salvo, sem alterações e sem metadados anteriores OpenTrace. Não há diálogo compulsório ao abrir arquivos `.igz` antigos.

**Escolhas de template:**
1. `Padrão OpenTrace (novo projeto vazio)`: mantém a cena recém-criada, prepara metadados BIM e registra o catálogo. O usuário salva depois normalmente como `.igz`.
2. `Meu projeto .igz como template completo…`: escolhe o **arquivo existente de origem** e, depois, outro **arquivo de destino novo**. Copia bytes com criação exclusiva (`xb`) e **recusa sobrescrever qualquer `.igz` existente**. Abre a cópia usando `MainWindow.open_path` e grava alterações usando `MainWindow._do_save` — APIs nativas públicas em leitura de código do host. É o caminho de preservação dos objetos, geometria, layers e demais dados do documento. O original nunca é aberto para escrita e nunca é regravado. A identificação do template é o hash SHA256. **A integração com o host não foi executada de fato no IngeTrazo Windows nesta rodada.**
3. `Meu modelo de configurações (.json)…`: usa um arquivo exportado pelo OpenTrace no formato `opentrace-project-settings-template`. Exportação disponível no Home em **`Salvar minhas configurações como template…`**. Carrega apenas dados BIM do projeto, exportação, georreferência e biblioteca, sem geometria/layers da cena.

**Escolhas de catálogo:**
- IFC4 incorporado: usa o catálogo real de classes IFC4 já disponível no plugin (`bim_library.builtin_classifications()`), sem importar classificações externas, com esquema de exportação `IFC4`.
- IFC4 + meu catálogo CSV/JSON: aceita dados reais com `system` + `code` (exemplo CSV: `system;code;name;description`). Importa registros até o limite de 20.000 classificações e armazena snapshot local no registro BIM do projeto. **Não são inventados códigos NBR/Uniclass/OmniClass** e **não são feitas correspondências automáticas**.

Escolhas e classificações locais são registradas por `ExtensionApp.set_document_data`, mecanismo já existente; reabrir não gera novo diálogo nem exige o CSV/JSON original. No template `.igz`, a cópia nova é salva pelo mecanismo nativo após a escolha. No template vazio ou JSON, o **usuário deve salvar o novo projeto no IngeTrazo** para persistir no disco.

A leitura de projetos antigos não exige migração nem escolha compulsória. Não foi criada uma grande rotina de migração especulativa; o normalizador BIM existente conserva campos desconhecidos. **Troca de catálogo em projeto já iniciado**: implementada como experimento nesta revisão isolada, com prévia, resolução manual, pendências e Undo; consulte a seção adicional abaixo. Validação na interface real permanece pendente.

## Verificações e limites

- Código Python: `compileall` sem erros de sintaxe.
- Testes automatizados do motor de folha e módulo de configuração, incluindo cópia de `.igz` sem sobrescrita e preservação de metadados: resultados registrados localmente no momento de montagem deste pacote.
- **Não validado no Windows/IngeTrazo** nesta execução: PySide6 e host gráfico não estavam disponíveis. Não há aceite visual ou confirmação prática do fluxo `.igz`, da sincronização pós-merge nem do Undo da folha/porta. Testes host-neutros **não substituem** essa validação.
- O ZIP inclui apenas o plugin, sem modificar documentos de produto externos ou repositórios.

**Não incorporar ao GitHub nem às documentações oficiais sem autorização explícita do responsável.**


## REVISÃO EXPERIMENTAL ISOLADA — layers + migração IFC (14/10/2026)

**Esta revisão substitui apenas o conteúdo do pacote experimental anterior, sem tocar em
repositórios, branches, projetos do usuário ou documentos externos. Não autoriza publicação.**

### Layers individuais

- O seletor já existente em `ObjectProperties` e na barra contextual foi preservado.
- O **toolbar inferior de Layer Combinations incorporado ao OpenTrace** agora exibe
  **`Camada:`** ao lado de **`Combinação de Camadas:`**. São seletores diferentes:
  combinação controla estados de visibilidade/bloqueio/interseção; camada controla
  a associação dos objetos selecionados ou o destino de criação.
- Sem ferramenta ou seleção, o layer ativo da sessão serve como padrão para os
  próximos objetos OpenTrace; o padrão específico de uma ferramenta tem prioridade.
- A aplicação da layer nas ferramentas já passa pelo mecanismo nativo do host
  `core.layers.assign_layer` e, nos objetos existentes, por `AssignLayerCommand`.
- **Limitação:** se estiver instalada uma versão externa independente do plugin
  `layer_combinations`, o OpenTrace respeita essa instalação e não substitui sua
  barra; a nova opção do toolbar se aplica à versão incorporada.

### Propriedades IFC na criação

- As ferramentas de parede, laje, pilar, viga, porta e janela continuam gerando
  grupos com classe IFC, identidade IFC4 e layer pela rotina existente.
- Catálogos externos podem incluir as colunas `ifc_class`/`ifc_classes` para
  *vincular explicitamente* um código a uma classe `IfcDoor`, `IfcWall` etc.
  Se houver exatamente um código mapeado à classe IFC, objetos novos recebem
  automaticamente essa classificação. Com 0 ou >1 correspondência, mantêm a
  identificação interna IFC4 sem **inventar** código de classificação nacional.
- O registro de escolha e snapshot das definições (`project_setup.catalogue_keys`)
  é salvo no .igz e lido novamente ao reabrir o projeto; arquivos CSV de origem
  não são exigidos para classificar novos objetos após reabrir.

### Propriedades BIM → Migrar catálogo IFC…

- O botão aparece tanto na página **BIM / IFC** quanto em **Layer / BIM / IFC**.
  Ambos abrem o mesmo fluxo, não criam duas bibliotecas.
- Seleciona o destino **IFC4 interno** ou importa CSV/JSON de um sistema real,
  por exemplo ABNT ou Uniclass (o catálogo deve ser fornecido pelo usuário).
- Preview por classe e classificação atual: total de objetos, correspondência
  automática *exata* ou explicitamente informada, conflitos e pendências.
- Cada linha pode ser direcionada a um código da lista real de destino. Sem
  correspondência, permite reter classificação existente com pendência registrada,
  ou impedir a operação até tudo estar mapeado. Confirmação final obrigatória.
- Metadados IFC são alterados numa operação única com Undo/Redo, com os dados de
  projeto e catálogo. IDs IFC, objetos, geometria, layers, parâmetros, materiais,
  biblioteca de tipos e favoritos NÃO são substituídos.
- Quando a biblioteca antiga contém a mesma chave com outra definição, ambas
  versões são preservadas em entradas diferentes; não se sobrescreve o original.
- A prévia é invalidada se os metadados dos objetos forem alterados antes de aplicar.

Formato CSV estendido opcional:

```csv
system;code;name;ifc_class;matches
SistemaAutorizado;123;Tipo de porta;IfcDoor;OutroSistema · Antigo123
```

`matches` aceita uma ou várias correspondências `Sistema · Código` separadas
por `;` (ou `|` em CSV para não interferir no delimitador). No JSON,
`ifc_classes` e `matches` podem ser arrays de strings. **Exemplos acima são
ilustrativos; não representam códigos da ABNT ou do Uniclass.**

**Pendente:** empacotar bases **oficiais completas** ABNT/Uniclass, com licença,
versão e códigos verificados. Nenhum nome de sistema foi usado para fingir
que existem classificações oficiais prontas onde só existe IFC4 interno.

### Validação

- 13 testes Python host-neutros passaram: 7 preservados do merge 410+420 e
  6 novos para mapeamento, prévia/Undo, conflitos, persistência, colisões
  de biblioteca e prevenção contra aplicação sobre dados desatualizados.
- Compilação sintática (`compileall`) dos `.py` passou.
- **Não realizado**: teste de interface PySide6 e execução real no Windows,
  teste visual das maquetes, abertura/gravação real do `.igz` pelo IngeTrazo,
  teste nativo de Undo/Redo e checagem na máquina do responsável.

**NÃO IMPORTAR AO GITHUB, DOCUMENTOS, CADERNOS OU RELEASES sem autorização
explícita do responsável.**
