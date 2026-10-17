# OpenTrace BIM — EXPERIMENTAL ISOLADO — Ctrl+N, bibliotecas e templates

**Não integrar na branch oficial, não publicar e não atualizar os cadernos do projeto sem autorização.**
Este documento só acompanha o ZIP de testes. Base: pacote experimental local de correções ABNT, informações e assistente.

## Alterações deste experimento

1. **Novo documento:** observa a ação *File > New* (Ctrl+N) nativa do IngeTrazo e reabre a configuração para um novo documento ainda não configurado. O host reutiliza a mesma cena, razão pela qual o controle anterior por identidade de `scene` falhava. Um documento salvo reaberto não é tratado como novo.
2. **Botão da Home:** sempre habilitado; permite iniciar outro projeto deliberadamente. Ao confirmar *Criar projeto*, utiliza o mecanismo nativo de arquivo novo do IngeTrazo, incluindo a confirmação de salvar/descartar/cancelar quando aplicável. Projetos de origem não são sobrescritos.
3. **Desempenho:** cache transitório de aplicabilidade IFC por classe; reutiliza a carga em cada objeto criado. O painel BIM evita decodificar e normalizar novamente todos os códigos em alterações exclusivamente geométricas, graças à identidade do registro imutável de `plugin_data` fornecido pelo IngeTrazo. A geometria e as atribuições normativas permanecem distintas.
4. **Bibliotecas hierárquicas:** exemplos de Arquitetura Básica, Arquitetura Padrão e Estrutura Essencial, contendo recursos reais do catálogo preexistente (paredes, lajes, vigas, pilares, perfis estruturais). São índices com configurações, não novas geometrias. Pastas/subpastas, pesquisa, importação e exportação de coleções `.otlib`/`.json`, pastas externas e consulta do acervo completo sob demanda. Recursos pessoais podem ser importados individualmente.
5. **Lista rápida:** presets existentes são filtrados pelas coleções escolhidas no projeto novo, **somente se o projeto optar pelo novo modo de bibliotecas**. Projetos antigos continuam com a lista anterior. O catálogo mestre é preservado. Materiais e perfis já associados a geometria não são apagados.
6. **Materiais:** os campos do OpenTrace de parede, laje, viga, pilar, compositor de camadas e materiais de portas/janelas usam um seletor com pesquisa e pastas de materiais. A biblioteca nativa continua disponível e o material só é registrado na cena quando utilizado. A bandeja nativa de Materiais do IngeTrazo não foi modificada.
7. **Templates completos:** na janela de configuração há **Salvar template completo deste projeto…**. O formato `.ottemplate` armazena `scene.igz` (geometria, layers e recursos reais salvos pelo IngeTrazo) e `resources.json` (coleções selecionadas e presets/perfis pessoais). Na criação de projeto há opção de usar `.ottemplate`, gerando nova cópia `.igz` independente. O arquivo de origem nunca é sobrescrito; um destino existente é recusado.
8. **Home → Gerenciar bibliotecas:** agora abre navegador de bibliotecas, permite importar uma receita individual, e alterar os conjuntos carregados em um projeto configurado. No projeto novo, a etapa 4 também oferece esse gerenciamento.

## Limitações importantes

- **Windows/IngeTrazo/PySide6 não está disponível no ambiente de testes:** confirmação visual do assistente, atalhos, persistência do pacote `.ottemplate` e do seletor de materiais dependem de teste no host real.
- **Portas e janelas:** o motor atual não oferece o mesmo contrato de *preset favorito global* que os catálogos de parede, laje, viga e pilar. O sistema de coleções já aceita `door`/`window` como categorias, mas não implementa ainda importação/aplicação de favoritos de portas/janelas. Portas/janelas efetivamente modeladas em uma cena `.igz` são conservadas pelo template nativo. Não se deve anunciar essa etapa como concluída.
- **Perfis:** continuam com toda a biblioteca disponível para a resolução segura de referências já existentes. Os exemplos selecionados acompanham o template; restringir semântica de todos os seletores de perfis requer teste do host.
- **Materiais:** o seletor por pastas é implementado nos componentes OpenTrace, não substitui a bandeja global do host. As listas nativas completas continuam acessíveis; a filtragem por favoritos de materiais em todos os seletores do host permanece futura.
- **`.otlib` é JSON validado, não é um ZIP de texturas.** Pacotes importados contêm receitas/metadados; texturas externas referenciadas por caminhos não são incorporadas automaticamente. O `.igz` é responsável pelos materiais de cena. Diretórios externos são referências, não cópias de arquivos.
- **Catálogos IFC4/IFC4.3, Uniclass, ABNT e equivalências:** não modificados neste bloco, exceto o custo da consulta de classificação no instante da criação.
- **Não há prova de melhora na renderização/geometria no Windows:** benchmark sintético de 15.363 classificações no ambiente local deu cerca de 10 ms por varredura anterior; com índice, ~1 ms de preparação e ~0,003 ms por consulta quente. Isso não mede o tempo total da ferramenta.

## Verificação manual sugerida no Windows

1. Começar no IngeTrazo e confirmar que a janela aparece uma vez, não reaparecendo ao desenhar.
2. Executar Ctrl+N com o programa já aberto e confirmar que a janela retorna; cancelar salvamento de um documento modificado e garantir que o projeto antigo continua intacto.
3. Confirmar que o botão da Home permanece ativo mesmo sem trocar abas e, após *Criar projeto*, inicia efetivamente outro documento.
4. Abrir **Gerenciar bibliotecas**, navegar Arquitetura Básica/Padrão, importar e exportar `.otlib`, e carregar um único preset a partir do acervo completo.
5. Usar materiais de paredes, lajes e portas; conferir pastas e pesquisa; testar material não utilizado até a aplicação.
6. Salvar um `.ottemplate` a partir de um projeto com objetos, layers e perfis pessoais; criar outro projeto a partir dele e verificar objetos, layers, propriedades e favoritos.
7. Instalar ABNT, criar várias paredes/lajes seguidas, e comparar responsividade com/sem catálogo. Desfazer/refazer e exportação IFC não devem sofrer regressões.

## Testes neste ambiente

28 testes automatizados (18 pré-existentes + 10 novos), compilação Python e integridade do ZIP. Nenhuma interface do host Windows foi executada.
