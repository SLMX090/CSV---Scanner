import io

from modules.analysis_service import analyze_dataframe, analyze_uploaded_file


def test_analyze_dataframe_returns_all_sections():
    df = __import__('pandas').DataFrame(
        {
            'nombre': ['Ana', 'Luis', 'Ana'],
            'email': ['ana@test.com', 'mail-invalido', 'ana@test.com'],
            'edad': [25, -5, 30],
        }
    )

    result = analyze_dataframe(df, source_name='demo.csv')

    assert result['source_name'] == 'demo.csv'
    assert 'load_info' in result
    assert 'profile' in result
    assert 'validation_results' in result
    assert 'recommendations' in result
    assert 'severity_issues' in result


def test_analyze_uploaded_file_handles_csv_string():
    content = "nombre,email,edad\nAna,ana@test.com,25\nLuis,mail-invalido,-5\n"

    uploaded = io.StringIO(content)
    uploaded.name = 'demo.csv'

    result = analyze_uploaded_file(uploaded, delimiter=',', encoding='utf-8')

    assert result['df'] is not None
    assert result['source_name'] == 'demo.csv'
    assert result['profile']['general_info']['total_rows'] == 2
    assert 'email_validation' in result['validation_results']
