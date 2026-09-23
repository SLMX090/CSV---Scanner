import pandas as pd
import io

from modules.analysis_service import analyze_uploaded_files, summarize_batch_results, analyze_dataframe
from modules.csv_loader import CSVLoader


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
