# OpenTrace BIM — CORREÇÃO EXPERIMENTAL ABNT / SICLIC

**Status:** pacote EXCLUSIVAMENTE EXPERIMENTAL, isolado. Não promover para GitHub, branches oficiais, releases ou cadernos do projeto sem autorização expressa.

## Diagnóstico da falha de uso

Na entrega `CATALOGOS-OPERACIONAIS`, Uniclass possuía instalação em um clique. ABNT tinha apenas link externo e importação local (CSV/XLSX/ZIP), sem acesso direto ao catálogo. O importador também não reconhecia o par de cabeçalhos **Código/Termo** (usado na estrutura das tabelas brasileiras), aceitando Código/Descrição ou Code/Title.

## Alterações desta revisão

1. **ABNT/SICLIC no gerenciador:** botão **Instalar SICLIC / ABNT via bSDD — prévia DEMO 0.1.2**. Consulta a fonte que o próprio SICLIC referencia: `https://identifier.buildingsmart.org/uri/DEMO/SICLIC/0.1.2`, pela API pública de leitura `https://api.bsdd.buildingsmart.org/api/Dictionary/v1/Classes`, com paginação e limites de segurança. É acionado SOMENTE pelo usuário; não há download automático ao abrir projetos.
2. **Aviso indispensável:** o dicionário público **DEMO 0.1.2 NÃO é a ABNT NBR 15965 completa ou homologada**. Se a API não oferecer classes, a operação retorna um erro claro. Nenhum catálogo vazio/parcial é instalado como se fosse completo. Os códigos reais obtidos são preservados com fonte e versão, sem fabricar equivalências Uniclass/OmniClass/IFC.
3. **Importador de planilhas brasileiras:** cabeçalhos `Código/Termo`, `Código/Termo padronizado` e outros comuns agora são reconhecidos em `.csv` e `.xlsx` (além de `.zip`). Identifica as famílias ABNT 0M, 0P, 1F, 1S, 1D, 2C, 2N, 2Q, 3E, 3R, 4U, 4A e 5I.
4. **Alternativa sem download:** botão **Cadastrar código ABNT consultado…**, exigindo código válido e descrição informados pelo usuário, explicitamente sem validação normativa automática.
5. **Persistência:** entradas ABNT usam a mesma biblioteca BIM do projeto e o mesmo mecanismo de atribuição de classificações aos objetos. Objetos e geometrias não são alterados pela instalação.
6. **Evita instalações repetidas** da mesma edição e preserva conflitos de definições para revisão, sem substituir os dados antigos.

## Como testar no Windows

- Faça backup da versão experimental atual e use uma instalação experimental separada.
- Na janela **Configurar projeto novo** → **Gerenciar catálogos**, escolha **Instalar SICLIC / ABNT via bSDD** e confirme o aviso. O número de códigos e famílias detectados deve aparecer. Se falhar, registre a mensagem completa — o servidor ou dicionário pode não estar acessível.
- Alternativamente clique **Importar tabela original CSV/XLSX/ZIP**, selecione **ABNT NBR 15965** e escolha uma tabela obtida na fonte que contenha **Código** e **Termo**.
- Para uso pontual, escolha **Cadastrar código ABNT consultado…**.
- Confirme **Usar catálogos selecionados**, selecione o sistema principal conforme desejado e grave o projeto. Selecione um objeto → **Propriedades BIM** → classificar → pesquise por código/descrição.

## Testes e limites

- **10 testes de lógica passaram**: importação CSV/XLSX Código/Termo, Uniclass sem regressão, paginação simulada do bSDD, rede interrompida sem instalar dados parciais, estrutura inesperada, conflitos, persistência e classificação sem mudar identidade/atributos IFC.
- Compilação sintática completa do pacote realizada.
- **Pendente:** consulta REAL ao bSDD de produção, testes visuais na interface Qt/Windows e confirmação da abrangência do dicionário DEMO 0.1.2. Não foi possível acessar essa API de rede neste ambiente.
- **Não incluído:** conteúdo integral da ABNT NBR 15965, correspondências homologadas entre ABNT/Uniclass/OmniClass, ou qualquer promessa de equivalência exata automática.
- A API e o dicionário de demonstração não substituem as edições normativas disponíveis junto à ABNT/SICLIC.

## Isolamento

Nenhum repositório/branch, caderno ou documento fora deste pacote foi alterado. O ZIP anterior permanece intacto. O trabalho foi feito a partir de uma cópia local do ZIP fornecido pelo usuário.
