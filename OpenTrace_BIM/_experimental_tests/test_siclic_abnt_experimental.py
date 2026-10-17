"""Isolated non-Qt tests for SICLIC preview and ABNT spreadsheet support."""
import csv
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from zipfile import ZipFile, ZIP_DEFLATED

from OpenTrace_BIM.siclic_bsdd_access import download_siclic_preview
from OpenTrace_BIM.official_classification_import import import_publisher_catalogue
from OpenTrace_BIM.project_setup import merge_classification_catalogues


class MockResponse:
    def __init__(self, data):
        self.data = io.BytesIO(json.dumps(data).encode())
    def __enter__(self): return self
    def __exit__(self, *_): self.data.close()
    def read(self, n): return self.data.read(n)


def opener_for(items, total=None, *, fail_at=None):
    def openit(req, timeout):
        assert timeout >= 5
        assert req.get_header('Accept') == 'application/json'
        q = parse_qs(urlsplit(req.full_url).query)
        assert q['Uri'] == ['https://identifier.buildingsmart.org/uri/DEMO/SICLIC/0.1.2']
        off = int(q['Offset'][0]); limit = int(q['Limit'][0])
        if fail_at is not None and off >= fail_at:
            raise TimeoutError('simulated network failure')
        return MockResponse({'classes': items[off:off+limit], 'classesTotalCount': len(items) if total is None else total})
    return openit

class TestSiclic(unittest.TestCase):
    def test_single_page_and_no_invented_correspondences(self):
        rows = [{'referenceCode': '3E.10.20', 'name': 'Elemento exemplar',
                 'uri': 'https://identifier.buildingsmart.org/dummy'},
                {'referenceCode': '2C.30.20', 'name': 'Produto exemplar'},
                {'referenceCode': 'unknown', 'name': 'Outro'}]
        cat = download_siclic_preview(opener=opener_for(rows))
        self.assertEqual(len(cat['classifications']), 2)
        self.assertEqual(cat['table_counts'], {'3E': 1, '2C': 1})
        self.assertTrue(cat['preview'])
        self.assertEqual(cat['classifications']['ABNT NBR 15965 · 3E.10.20']['matches'], [])
        self.assertEqual(cat['classifications']['ABNT NBR 15965 · 3E.10.20']['ifc_classes'], [])
    def test_pagination_complete(self):
        rows = [{'referenceCode': f'3E.{x:05d}', 'name': f'Exemplo {x}'} for x in range(650)]
        pages=[]
        cat = download_siclic_preview(opener=opener_for(rows), progress=lambda *x: pages.append(x))
        self.assertEqual(len(cat['classifications']), 650)
        self.assertEqual(len(pages), 2)
    def test_network_failure_rejects_partial_data(self):
        rows = [{'referenceCode': f'3E.{x:05d}', 'name': f'Exemplo {x}'} for x in range(650)]
        with self.assertRaises(TimeoutError):
            download_siclic_preview(opener=opener_for(rows, fail_at=500))
    def test_empty_demo_never_reports_success(self):
        with self.assertRaisesRegex(ValueError, 'Nenhum código'):
            download_siclic_preview(opener=opener_for([]))
    def test_unknown_response_rejected(self):
        with self.assertRaisesRegex(ValueError, 'lista de classes'):
            download_siclic_preview(opener=lambda *_a,**_kw: MockResponse({'anything': []}))
    def test_merge_sources(self):
        c = download_siclic_preview(opener=opener_for([{'code':'3E.20.10','name':'Exemplo'}]))
        merged=merge_classification_catalogues([c])
        self.assertEqual(len(merged['classifications']),1)
        self.assertIn('ABNT NBR 15965',merged['sources'][0]['system'])
        self.assertIn('bSDD',merged['sources'][0]['source_file'])

class TestAbntImporter(unittest.TestCase):
    def test_portuguese_codigo_termo_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ABNT_3E.csv'
            path.write_text('Código;Termo\n3E.10.20;Parede de exemplo\n2C.30.20;Janela de exemplo\n',encoding='utf-8')
            cat=import_publisher_catalogue(path,'ABNT NBR 15965',edition='Teste')
            self.assertEqual(len(cat['classifications']), 2)
            self.assertIn('ABNT NBR 15965 · 3E.10.20',cat['classifications'])
    def test_portuguese_xlsx_codigo_termo(self):
        xml=('<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        '<row r="1"><c r="A1" t="inlineStr"><is><t>Código</t></is></c><c r="B1" t="inlineStr"><is><t>Termo</t></is></c></row>'
        '<row r="2"><c r="A2" t="inlineStr"><is><t>3E.10.20</t></is></c><c r="B2" t="inlineStr"><is><t>Parede de exemplo</t></is></c></row>'
        '</sheetData></worksheet>')
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'ABNT.xlsx'
            with ZipFile(path,'w',ZIP_DEFLATED) as z:
                z.writestr('xl/worksheets/sheet1.xml',xml)
            cat=import_publisher_catalogue(path,'ABNT NBR 15965',edition='Teste')
            self.assertEqual(len(cat['classifications']),1)
    def test_uniclass_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'Uniclass.csv'
            path.write_text('Code,Title\nSs_25_10,Testing\n',encoding='utf-8')
            cat=import_publisher_catalogue(path,'Uniclass 2015')
            self.assertEqual(len(cat['classifications']),1)

if __name__=='__main__': unittest.main()

class TestAbntProjectPersistence(unittest.TestCase):
    def test_new_project_and_reopening_keep_abnt(self):
        from OpenTrace_BIM.project_setup import configure_new_project, catalogue_from_document, empty_template
        from OpenTrace_BIM.classification_assignments import add_reference, extend_project_catalogue
        abnt = download_siclic_preview(opener=opener_for([{'referenceCode': '3E.10.20', 'name': 'Termo teste'}]))
        merged = merge_classification_catalogues([abnt])
        project = configure_new_project({}, empty_template(), merged, ifc_schema='IFC4',
                                        primary_system='ABNT NBR 15965')
        reopened = json.loads(json.dumps(project))
        self.assertEqual(reopened['project_setup']['primary_classification_system'], 'ABNT NBR 15965')
        self.assertEqual(len(catalogue_from_document(reopened)['classifications']), 1)
        m = {'guid': 'immutable-identifier', 'psets': {'p': {'value': 1}}}
        updated = add_reference(m, abnt['classifications']['ABNT NBR 15965 · 3E.10.20'])
        self.assertEqual(updated['guid'], m['guid'])
        self.assertEqual(updated['psets'], m['psets'])
        self.assertFalse('classifications' in m)
        extra = {'id': 'manual', 'name': 'manual', 'system': 'ABNT NBR 15965',
                 'classifications': {'ABNT NBR 15965 · 3E.11': {'system': 'ABNT NBR 15965', 'code': '3E.11', 'name':'Outro'}}}
        ext = extend_project_catalogue(project, extra)
        self.assertEqual(len(catalogue_from_document(ext)['classifications']),2)
        self.assertEqual(len(catalogue_from_document(project)['classifications']),1)
