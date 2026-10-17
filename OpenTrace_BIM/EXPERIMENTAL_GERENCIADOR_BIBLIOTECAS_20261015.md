# OpenTrace BIM — GERENCIADOR DE BIBLIOTECAS · EXCLUSIVAMENTE EXPERIMENTAL

**NÃO PUBLICAR. NÃO PROMOVER PARA BRANCH OFICIAL. NÃO ATUALIZAR CADERNOS OU OUTROS REPOSITÓRIOS.**

## Implementado nesta revisão local

- O botão **Gerenciar bibliotecas** abre uma janela própria do OpenTrace, independentemente de já existir `project_setup`. O diálogo antigo que orientava usar o assistente foi eliminado.
- Biblioteca inicial com coleções Arquitetura Básica, Arquitetura Padrão e Estrutura Essencial. Catálogo completo somente ao pressionar `Consultar acervo completo`.
- Navegação em árvore por biblioteca > pasta > subpasta > objeto; pesquisa e filtro por tipo. Prévia esquemática 2D carregada ao selecionar, sem construção de malhas.
- Importação individual de presets de paredes, lajes, vigas, pilares e perfis; exportação unitária `.otitem`, leitura de `.otitem` e `.apreset` legado.
- Importação e exportação de bibliotecas `.otlib`, exportação de subpastas, criação de novas coleções a partir da seleção e exportação dos favoritos pessoais. Gravador usa criação exclusiva para nunca sobrescrever sem que o usuário tome outra ação.
- O projeto atual pode escolher seus conjuntos sem abrir assistente. A lista rápida das ferramentas reflete as bibliotecas selecionadas sem apagar objetos existentes.
- Painel de ferramentas mostra botões `Importar parede`, `Exportar parede`, etc. A importação abre o navegador próprio do OpenTrace filtrado ao tipo de recurso.
- Portas e janelas: botões **Salvar esquadria na biblioteca** e **Usar favorito** no painel de propriedades da instância selecionada; a aplicação usa o comando histórico da esquadria e não copia IDs da parede, abertura ou objeto.
- Materiais do seletor OpenTrace organizados em categorias virtuais (Cimentos e Argamassas, Blocos ou Tijolos, Revestimentos, Metais, Pinturas, Pedras, Madeiras e Laminados, Vidros e Espelhos, Estampas e Tecidos, Diversos), busca textual e miniatura da textura ou cor quando disponível. A classificação por nome/arquivo é heurística de navegação, não classificação IFC.
- Aviso em destaque: `ATENÇÃO: CATÁLOGOS DE CLASSIFICAÇÃO E EQUIVALÊNCIAS PODEM DEIXAR A CRIAÇÃO DOS OBJETOS MAIS LENTA.` Com explicação do índice e custo adicional.

## Limites e precauções

- A prévia de perfis e presets é 2D esquemática. Não representa um render do objeto colocado na cena.
- A coleção registra **configurações paramétricas** e receitas de materiais; ela não equivale a copiar automaticamente todos os objetos desenhados como malhas. Para exportar a geometria completa, use o **template completo `.ottemplate`**.
- Portas e janelas possuem favoritos salváveis e aplicáveis a instâncias selecionadas. A escolha de favoritos automaticamente **antes de criar uma nova esquadria** ainda não está integrada ao motor.
- Materiais com texturas de arquivos locais em `.otlib` referenciam o arquivo original: não há empacotamento da textura binária neste formato. A prévia mostra uma amostra neutra se a imagem não está presente; para uma biblioteca verdadeiramente portátil de texturas, será preciso criar pacote de assets com paths relativos e validação.
- `Novo Window` abrindo automaticamente o configurador ainda depende do ciclo de documento do host e não foi alterado nesta revisão.
- Não foi executado o IngeTrazo real Windows nesta sessão: somente testes lógicos automatizados, análise de sintaxe e integridade do ZIP.
- Não alterar o materializador de `scene.materials`, a geometria nem os perfis de exportação IFC existentes sem novo aceite.

## Roteiro de teste no Windows

1. Abrir IngeTrazo + OpenTrace; Home > Gerenciar bibliotecas. Deve mostrar a árvore, sem janela dizendo para usar assistente.
2. `Consultar acervo completo`, buscar `parede`, clicar em um recurso; verificar prévia; `Importar objeto para o projeto` e confirmar presença na lista de presets de parede.
3. Selecionar uma pasta de paredes, `Exportar biblioteca / pasta…` para arquivo novo `.otlib`; fechar e `Importar biblioteca…`; verificar a estrutura preservada.
4. Em parede selecionada, `Salvar como…` para criar preset; voltar ao gerenciador e confirmar na consulta ao acervo completo. Exportar o favorito em `.otitem` e importar em outro projeto.
5. Selecionar uma porta hospedada; salvar favorito, modificar parâmetros e aplicar o favorito; confirmar resultados e Undo/Redo.
6. Testar lista de materiais com busca por `cimento`, `madeira`, `pedra` e nomes de texturas existentes. Confirmar miniaturas; aplicar material e verificar no modelo.
7. Criar projeto com Uniclass/ABNT, observar aviso de desempenho IFC; criar paredes e lajes sem recarregar catálogo a cada objeto.
8. Confirmar que arquivo fonte de template, bibliotecas e modelos abertos não foram sobrescritos.

## Testes

36 testes de regressão e extensão passaram localmente. Compilação Python e integridade ZIP devem constar na entrega final. Sem validação gráfica no Windows.
