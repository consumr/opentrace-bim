# OpenTrace BIM — TEST-410 LOCAL

**Base:** TEST-409-LOCAL enviado ao usuário. **Entrega:** ZIP local de teste, sem qualquer operação de escrita no GitHub. **Validação no Windows/IngeTrazo:** ainda pendente.

## Ajustes desta rodada

1. **Alinhamento da barra contextual:** todas as páginas de ferramentas agora mantêm os grupos alinhados à esquerda; espaço excedente é reservado ao final, sem espalhar os grupos pela largura disponível.
2. **Modos com ícones:** no Pilar e na Viga, a seleção de seção retangular, circular ou perfil complexo usa ícones existentes (`opening_rect`, `opening_circle`, `profile`) sem palavras nos botões; há tooltips e nomes acessíveis. A lista de perfis complexos permanece quando o modo correspondente está selecionado. Os três métodos da Laje já usam os ícones do motor existente e foram preservados.
3. **Vão de porta sem esquadria:** além dos dois modos com ícones na barra contextual da Porta, o botão Porta na fileira superior ganhou uma seta de menu com `Porta completa` e `Vão de porta (sem folha e batente)`. Ambos usam o mesmo motor e QAction já registrados no host: o modo vão produz somente o recorte; não adiciona folha nem batente.
4. **Home:** retirados os botões repetidos de ferramentas, perfil complexo, alinhar/distribuir e BIM/IFC. A Home apresenta instruções iniciais, **o formulário original de Informações do Projeto** (não duplicado; mantém as ligações de salvar do controlador BIM), botão desabilitado `Gerenciar bibliotecas`, resumo das bibliotecas/layer combinations e bloco original de atualização.
5. **Informações do Projeto:** botão `ⓘ` do cabeçalho e comando de menu direcionam à seção incorporada na Home. As abas BIM e Perfis, assim como as ferramentas na fileira superior, continuam disponíveis.
6. **Propriedades detalhadas/IFC/Layer:** preservada a estrutura funcional validada no TEST-409.

## Verificações neste ambiente

- Sintaxe de todos os 86 módulos Python e `compileall`: **OK**.
- Ligações estáticas com o motor de portas, seleção dos perfis e controles de construção: **OK**.
- Modelo de vão de porta: a normalização mantém `purpose=door` sem preencher com uma porta: **OK**.
- Catálogo IFC4 de 776 entidades permanece disponível: **OK**.
- **Sem testes visuais/integração aqui:** PySide6 e IngeTrazo não estão instalados. Os resultados acima não comprovam desenho, Undo, estado dos menus nem disposição final no Windows.

## Seu roteiro de teste Windows

1. **Barra:** ative Parede, Laje, Pilar, Viga e Porta. Confira os grupos desde a esquerda, sem larguras vazias entre eles.
2. **Laje:** com os três ícones (cantos opostos, três pontos, polígono livre), crie uma peça de cada tipo.
3. **Pilar/Viga:** clique nos ícones retangular, circular, complexo; confira as medidas, a grade de nove âncoras e o seletor de perfil complexo.
4. **Porta:** na seta à direita de Porta, selecione `Vão de porta`; clique em uma parede. Deve recortar sem folha ou batente. Volte ao menu e selecione `Porta completa`; confirme a esquadria. Compare também os botões de inserção da barra inferior. Teste desfazer/refazer.
5. **Home:** verifique boas-vindas; edite Nome do Projeto (e reabra para conferir persistência); confira botão inativo `Gerenciar bibliotecas`, resumo e controles de atualização. Botão `ⓘ` deve posicionar a Home nas informações do projeto.
6. **Regressão:** menu Layer/IFC e propriedades recolhíveis; testes essenciais de parede/porta/laje do pacote 409.

**Instale em projeto descartável, depois de fazer backup da pasta do plugin 409; substitua a pasta inteira e reinicie o IngeTrazo.**
