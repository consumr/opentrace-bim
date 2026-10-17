OpenTrace BIM EXPERIMENTAL / ISOLADO — catálogos de equivalências

1. table_families.json: comparação conceitual e verificável entre AS TABELAS de
   Uniclass 2015, OmniClass e ABNT NBR 15965. Não contém códigos de classes.
   NÃO serve como relação de equivalência normativa e NÃO é lido pelo motor de
   migração. Nenhuma migração automática é gerada desse arquivo.

2. crosswalk_template.csv: molde de relações entre códigos efetivos. Preencha
   códigos reais com nome exato de sistema. Uma linha pode ser exact, similar,
   broader, narrower ou related. A relação 'exact' só vira proposta automática
   quando evidence_status=verified, evidence_uri e evidence_edition existem
   e não há propostas concorrentes. 'verified' representa declaração do autor
   do catálogo importado, NÃO um selo oficial do OpenTrace.

3. equivalences_unverified_empty.json: modelo de catálogo JSON (sem linhas
   normativas inventadas). Para adicionar um catálogo de equivalências, use a
   seleção de arquivo na criação do projeto ou na migração BIM. Ele ficará
   guardado NO .igz por versão, independente dos arquivos CSV/JSON originais.

FONTE DAS FAMÍLIAS:
- Uniclass NBS: https://uniclass.thenbs.com/download (Julho 2026)
- OmniClass CSI: https://www.csiresources.org/standards/omniclass/standards-omniclass-about
- SICLIC FAU-USP (referência ABNT): https://siclic.fau.usp.br/busca

NÃO fazemos cópias das tabelas originais, NÃO atribuímos códigos normativos
por semelhança de nomes, e NÃO prometemos homologação nem uso autorizado de
conteúdo restrito. Não distribuímos este pacote fora do experimento.
