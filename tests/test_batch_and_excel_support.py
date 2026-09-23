import pandas as pd
import io

import modules.analysis_service as analysis_service
from modules.analysis_service import analyze_uploaded_files, analyze_uploaded_workbook, summarize_batch_results, analyze_dataframe
from modules.csv_loader import CSVLoader
from modules.report_generator import ReportGenerator


def test_summarize_batch_results_returns_comparison_table():
    r1 = analyze_dataframe(pd.DataFrame({'a': [1, 2]}), source_name='a.csv')
    r2 = analyze_dataframe(pd.DataFrame({'a': [1, 2, 3, 4]}), source_name='b.csv')

    summary = summarize_batch_results([r1, r2])

    assert {'source_name', 'rows', 'columns', 'total_null_cells'}.issubset(set(summary.columns))
    assert len(summary) == 2


def test_csv_loader_load_file_supports_excel(tmp_path):
    path = tmp_path / 'demo.xlsx'
    data = pd.DataFrame({'nombre': ['Ana', 'Luis'], 'edad': [25, 30]})
    data.to_excel(path, index=False)

    with open(path, 'rb') as f:
        df, info = CSVLoader.load_file(f, file_name='demo.xlsx')

    assert list(df.columns) == ['nombre', 'edad']
    assert info['source_type'] == 'excel'
    assert info['rows'] == 2


def test_csv_loader_loads_selected_excel_sheet(tmp_path):
    path = tmp_path / 'multi_sheet.xlsx'
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({'valor': [1]}).to_excel(writer, sheet_name='Resumen', index=False)
        pd.DataFrame({'valor': [2, 3]}).to_excel(writer, sheet_name='Detalle', index=False)

    with open(path, 'rb') as file_object:
        assert CSVLoader.list_excel_sheets(file_object, 'multi_sheet.xlsx') == ['Resumen', 'Detalle']

    with open(path, 'rb') as file_object:
        dataframe, info = CSVLoader.load_file(
            file_object,
            file_name='multi_sheet.xlsx',
            sheet_name='Detalle',
        )

    assert dataframe['valor'].tolist() == [2, 3]
    assert info['sheet_name'] == 'Detalle'


def test_analyze_workbook_returns_one_result_per_sheet(tmp_path):
    path = tmp_path / 'workbook.xlsx'
    with pd.ExcelWriter(path) as writer:
        pd.DataFrame({'valor': [1, 2]}).to_excel(writer, sheet_name='Ventas', index=False)
        pd.DataFrame({'valor': [3]}).to_excel(writer, sheet_name='Devoluciones', index=False)

    file_object = io.BytesIO(path.read_bytes())
    file_object.name = 'workbook.xlsx'
    results = analyze_uploaded_workbook(file_object)

    assert [result['source_name'] for result in results] == [
        'workbook.xlsx :: Ventas',
        'workbook.xlsx :: Devoluciones',
    ]
    assert results[0]['load_info']['sheet_name'] == 'Ventas'
    assert results[1]['load_info']['sheet_name'] == 'Devoluciones'
    assert results[0]['df'] is not None
    assert results[1]['df'] is None


def test_batch_detects_delimiter_independently_and_releases_extra_dataframes():
    comma_file = io.StringIO('id,nombre\n1,Ana\n2,Luis\n')
    comma_file.name = 'ventas_coma.csv'
    semicolon_file = io.StringIO('id;nombre\n3;Marta\n4;Luis\n')
    semicolon_file.name = 'ventas_punto_coma.csv'

    results = analyze_uploaded_files([comma_file, semicolon_file])

    assert len(results) == 2
    assert results[0]['load_info']['delimiter'] == ','
    assert results[1]['load_info']['delimiter'] == ';'
    assert results[0]['df'] is not None
    assert results[1]['df'] is None


def test_batch_keeps_processing_when_one_file_fails(monkeypatch):
    first = io.StringIO('id,nombre\n1,Ana\n')
    first.name = 'correcto.csv'
    second = io.StringIO('contenido no valido')
    second.name = 'incorrecto.csv'
    original = analysis_service.analyze_uploaded_file

    def analyze_with_one_failure(uploaded_file, **kwargs):
        if uploaded_file.name == 'incorrecto.csv':
            raise ValueError('delimitador no detectable')
        return original(uploaded_file, **kwargs)

    monkeypatch.setattr(analysis_service, 'analyze_uploaded_file', analyze_with_one_failure)
    results = analyze_uploaded_files([first, second])
    summary = summarize_batch_results(results)

    assert [result['status'] for result in results] == ['ok', 'error']
    assert summary.loc[summary['source_name'] == 'incorrecto.csv', 'error'].iloc[0] == 'delimitador no detectable'


def test_workbook_keeps_processing_when_one_sheet_fails(monkeypatch):
    workbook = io.BytesIO(b'placeholder')
    workbook.name = 'ventas.xlsx'
    monkeypatch.setattr(analysis_service.CSVLoader, 'list_excel_sheets', lambda *_: ['OK', 'FALLA'])

    def analyze_with_one_failure(uploaded_file, sheet_name=0, **kwargs):
        if sheet_name == 'FALLA':
            raise ValueError('hoja ilegible')
        return analyze_dataframe(pd.DataFrame({'valor': [1]}), source_name='ventas.xlsx')

    monkeypatch.setattr(analysis_service, 'analyze_uploaded_file', analyze_with_one_failure)
    results = analyze_uploaded_workbook(workbook)

    assert [result['status'] for result in results] == ['ok', 'error']
    assert results[1]['error'] == 'hoja ilegible'


def test_batch_excel_report_contains_summary_and_aggregate_metrics(tmp_path, monkeypatch):
    summary = pd.DataFrame({
        'source_name': ['a.csv', 'b.csv'],
        'rows': [2, 3],
        'columns': [2, 2],
        'total_null_cells': [1, 0],
        'duplicate_rows': [0, 1],
        'critical_issues': [0, 1],
        'severe_issues': [1, 0],
    })
    monkeypatch.chdir(tmp_path)

    filepath = ReportGenerator.generate_batch_excel_report(summary, filename='lote_prueba')
    workbook = pd.ExcelFile(filepath)

    assert set(workbook.sheet_names) == {'RESUMEN_LOTE', 'METRICAS_AGREGADAS'}
    metrics = pd.read_excel(filepath, sheet_name='METRICAS_AGREGADAS')
    assert metrics.loc[metrics['Métrica'] == 'Filas totales', 'Valor'].iloc[0] == 5
