# SPDX-License-Identifier: GPL-3.0-or-later
"""English presentation of built-in library names, without editing user data.

Object IDs, IFC classification codes, material references and saved library
recipes are intentionally left untouched. Imported/user-defined names stay
exactly as their authors supplied them.
"""
from __future__ import annotations

FOLDER_EN = {
    'Paredes': 'Walls', 'Lajes': 'Slabs', 'Vigas': 'Beams',
    'Pilares': 'Columns', 'Portas': 'Doors', 'Janelas': 'Windows',
    'Perfis complexos': 'Complex profiles', 'Objetos': 'Objects',
    'Esquadrias': 'Doors and windows', 'Materiais': 'Materials',
    'Pessoais': 'Personal', 'Meus presets': 'My presets',
    'Pessoal': 'Personal', 'Favoritas': 'Favorites',
    'Diversos': 'Miscellaneous', 'Outros': 'Other',
    'Cimentos e Argamassas': 'Cement & Mortars',
    'Blocos ou Tijolos': 'Blocks & Bricks',
    'Revestimentos': 'Finishes & Cladding',
    'Metais': 'Metals', 'Pinturas': 'Paints & Colors',
    'Pinturas / Cores RAL': 'Paints / RAL Colors',
    'Pedras': 'Stone', 'Madeiras e Laminados': 'Wood & Laminates',
    'Vidros e Espelhos': 'Glass & Mirrors',
    'Estampas e Tecidos': 'Patterns & Fabrics',
    'Arquitetura': 'Architecture', 'Básica': 'Basic',
    'Padrão': 'Standard', 'Estrutura': 'Structure',
    'Essencial': 'Essential', 'Acervo completo': 'Full library',
    'Alvenaria': 'Masonry', 'Alvenaria revestida': 'Clad masonry',
    'Genéricas': 'Generic', 'Estruturais': 'Structural',
    'Pisos': 'Floors', 'Áreas molhadas': 'Wet areas',
    'Coberturas': 'Roofs', 'Concreto armado': 'Reinforced concrete',
    'Concreto': 'Concrete', 'Madeira': 'Timber', 'Aço': 'Steel',
    'Estruturais': 'Structural', 'Arquitetônicos': 'Architectural',
    'Rodapés': 'Baseboards', 'Faixas & Molduras': 'Trims & Moldings',
    'Corrimãos': 'Handrails', 'Parede': 'Wall',
}

_PACK_EN = {
    'ot:arq:basica': 'Architecture · Basic',
    'ot:arq:padrao': 'Architecture · Standard',
    'ot:estrutural': 'Structure · Essential',
    'ot:consulta:completa': 'Full library · selectable',
    'ot:arq:completa': 'Architecture · Complete',
}

_EXACT_BUILTIN_EN = {
    'Genérica · 10 cm': 'Generic · 10 cm',
    'Genérica · 12 cm': 'Generic · 12 cm',
    'Bloco cerâmico 9 + reboco': 'Clay block 9 + render',
    'Bloco cerâmico 11,5 + reboco': 'Clay block 11.5 + render',
    'Bloco cerâmico 14 + reboco': 'Clay block 14 + render',
    'Bloco de concreto 9 + reboco': 'Concrete block 9 + render',
    'Bloco de concreto 14 + reboco': 'Concrete block 14 + render',
    'Bloco cerâmico 9 + cerâmica em 1 face': 'Clay block 9 + tile on one side',
    'Bloco cerâmico 14 + cerâmica nas 2 faces': 'Clay block 14 + tile on both sides',
    'Drywall duplo 120 mm': 'Double drywall 120 mm',
    'Concreto armado aparente · 12 cm': 'Exposed reinforced concrete · 12 cm',
    'Concreto 10 + contrapiso + porcelanato': 'Concrete 10 + screed + porcelain tile',
    'Concreto 12 + contrapiso + porcelanato': 'Concrete 12 + screed + porcelain tile',
    'Concreto 12 + acústica + madeira': 'Concrete 12 + acoustic layer + timber floor',
    'Área molhada impermeabilizada': 'Waterproofed wet area',
    'Cobertura impermeabilizada': 'Waterproofed roof',
    'Cobertura invertida com isolamento': 'Insulated inverted roof',
    'Cobertura verde básica': 'Basic green roof',
    'Rodapé 100 × 15 mm': 'Baseboard 100 × 15 mm',
    'Rodapé 150 × 15 mm': 'Baseboard 150 × 15 mm',
    'Faixa / Moldura 50 × 20 mm': 'Trim / Molding 50 × 20 mm',
    'Corrimão redondo Ø42,4 mm': 'Round handrail Ø42.4 mm',
    'Corrimão retangular 40 × 60 mm': 'Rectangular handrail 40 × 60 mm',
    'Cimalha / faixa de parede 150 × 30 mm': 'Wall cap / trim 150 × 30 mm',
}

_PREFIXES = (
    ('Concreto armado · ', 'Reinforced concrete · '),
    ('Concreto · ', 'Concrete · '),
    ('Madeira · ', 'Timber · '),
    ('Aço · ', 'Steel · '),
)


def folder_label(raw: str) -> str:
    """Display a known built-in category in English, preserve custom ones."""
    return FOLDER_EN.get(str(raw), str(raw))


def builtin_name(raw: str) -> str:
    """Translate a known built-in recipe, not user-authored descriptions."""
    name = str(raw)
    if name in _EXACT_BUILTIN_EN:
        return _EXACT_BUILTIN_EN[name]
    for old, new in _PREFIXES:
        if name.startswith(old):
            return new + name[len(old):]
    return name


def library_label(pack: dict) -> str:
    return _PACK_EN.get(str(pack.get('id', '')), str(pack.get('name', '')))


def resource_label(rec: dict) -> str:
    name = str(rec.get('name', ''))
    # Do not silently translate personal or third-party object names.
    if str(rec.get('source') or '') in ('builtin', 'opentrace:bundled') or (
        str(rec.get('id', '')).startswith('builtin:') and
        str(rec.get('source') or '').startswith('opentrace:')
    ):
        return builtin_name(name)
    return name
