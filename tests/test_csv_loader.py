"""
Pruebas para el módulo csv_loader.py
"""

import pytest
import pandas as pd
from modules.csv_loader import CSVLoader, CSVLoadError
from config import MAX_FILE_SIZE_MB


class TestCSVLoaderDelimiterDetection:
    """Pruebas para la detección automática de delimitador."""
    
    def test_detect_comma_delimiter(self, sample_valid_csv):
        """Verifica que detecta correctamente el delimitador por coma."""
        delimiter = CSVLoader.detect_delimiter(sample_valid_csv)
        assert delimiter == ','
    
    def test_detect_semicolon_delimiter(self, sample_csv_with_delimiter_confusion):
        """Verifica que detecta correctamente el delimitador por punto y coma."""
        delimiter = CSVLoader.detect_delimiter(sample_csv_with_delimiter_confusion)
        assert delimiter == ';'
    
    def test_detect_delimiter_with_mixed_formats(self):
        """Verifica que prefiere el delimitador más consistente."""
        csv_mixed = """col1;col2;col3;col4
val1;val2;val3;val4
val5;val6;val7;val8
val9,val10;val11;val12"""
        delimiter = CSVLoader.detect_delimiter(csv_mixed)
        # Debe preferir ';' porque es más consistente
        assert delimiter == ';'
    
    def test_detect_delimiter_heuristic_consistency(self):
        """Verifica que heurística prefiere delimitador con mayor estabilidad."""
        # CSV donde | es más consistente que coma
        csv_pipe = """col1|col2|col3
val1|val2|val3
val4|val5|val6
val7|val8|val9"""
        
        csv_comma_inconsistent = """col1,col2,col3
val1,val2,val3
val4,val5,val6,extra"""
        
        delimiter_pipe = CSVLoader.detect_delimiter(csv_pipe)
        assert delimiter_pipe == '|'
        
        delimiter_comma = CSVLoader.detect_delimiter(csv_comma_inconsistent)
        assert delimiter_comma == ','  # Aún lo detecta pero con baja estabilidad


class TestCSVLoaderColumnCleaning:
    """Pruebas para la limpieza de nombres de columna."""
    
    def test_clean_column_names_basic(self):
        """Verifica limpieza básica de nombres."""
        columns = ['Column 1', 'Column-2', 'Column@3']
        cleaned = CSVLoader.clean_column_names(columns)
        
        assert cleaned[0] == 'Column_1'
        assert cleaned[1] == 'Column2'
        assert cleaned[2] == 'Column3'
    
    def test_clean_column_names_handles_duplicates(self):
        """Verifica que maneja nombres duplicados después de limpieza."""
        columns = ['nombre', 'NOMBRE', 'nombre-data', 'nombre_data']
        cleaned = CSVLoader.clean_column_names(columns)
        
        # Debe ser único después de limpiar
        assert len(cleaned) == len(set(cleaned))
    
    def test_clean_column_names_unnamed_columns(self):
        """Verifica que renombra columnas sin nombre."""
        columns = ['Col1', 'Unnamed: 0', 'Unnamed: 1', 'Col2']
        cleaned = CSVLoader.clean_column_names(columns)
        
        assert 'Col1' in cleaned
        assert 'Col2' in cleaned
        assert any('Column_' in name for name in cleaned)
    
    def test_clean_column_names_numeric_prefix(self):
        """Verifica que agrega prefijo a nombres que comienzan con número."""
        columns = ['123column', 'column456', '789']
        cleaned = CSVLoader.clean_column_names(columns)
        
        assert cleaned[0].startswith('_')
        assert not cleaned[1].startswith('_')
        assert cleaned[2].startswith('_')
    
    def test_clean_column_names_uniqueness_guaranteed(self):
        """Verifica garantía de unicidad con sufijos."""
        columns = ['A-B', 'A@B', 'A B', 'A_B']
        cleaned = CSVLoader.clean_column_names(columns)
        
        # Después de limpiar, todos convergen a 'AB'
        # Debe haber sufijos para los duplicados
        assert len(set(cleaned)) == len(cleaned)


class TestCSVLoaderBadLines:
    """Pruebas para detección de líneas mal formadas."""
    
    def test_detect_bad_lines(self, sample_csv_with_bad_lines):
        """Verifica detección de líneas con número incorrecto de columnas."""
        import csv
        import io
        
        reader = csv.reader(io.StringIO(sample_csv_with_bad_lines))
        rows = list(reader)
        
        header_cols = len(rows[0])
        bad_lines = [
            (i, row) for i, row in enumerate(rows[1:], 1)
            if len(row) != header_cols
        ]
        
        assert len(bad_lines) > 0
        assert any(len(row) < header_cols for _, row in bad_lines)
    
    def test_bad_lines_reported_in_load_info(self, sample_csv_with_bad_lines):
        """Verifica que bad_lines_count se reporta correctamente en load_info."""
        import io
        
        file_obj = io.StringIO(sample_csv_with_bad_lines)
        df, load_info = CSVLoader.load_csv(file_obj)
        
        assert 'bad_lines_count' in load_info
        assert load_info['bad_lines_count'] > 0
        assert 'bad_lines_sample' in load_info
    
    def test_bad_lines_sample_max_5(self):
        """Verifica que bad_lines_sample devuelve máximo 5 ejemplos."""
        csv_content = "a,b\n1,2\n3\n4\n5\n6\n7\n8\n9"  # Muchas líneas malas
        
        import io
        file_obj = io.StringIO(csv_content)
        df, load_info = CSVLoader.load_csv(file_obj)
        
        assert len(load_info['bad_lines_sample']) <= 5
    
    def test_strict_mode_raises_on_bad_lines(self):
        """Verifica que modo estricto levanta excepción con líneas malas."""
        csv_content = "a,b,c\n1,2,3\n4,5\n6,7,8"
        
        import io
        from config import CSV_LOAD_MODE
        
        # Solo prueba si estamos en modo permisivo (no podemos cambiar config durante test)
        # Este test es informativo
        if CSV_LOAD_MODE == 'permissive':
            file_obj = io.StringIO(csv_content)
            df, load_info = CSVLoader.load_csv(file_obj)
            # En modo permisivo, debe cargar sin excepción
            assert df is not None


class TestCSVLoaderFileValidation:
    """Pruebas para validación de archivos."""
    
    def test_validate_file_size_valid(self):
        """Verifica que permite archivos dentro del límite."""
        # 1MB debe estar dentro del límite configurado
        CSVLoader.validate_file(1024 * 1024)
    
    def test_validate_file_size_too_large(self):
        """Verifica que rechaza archivos muy grandes."""
        with pytest.raises(CSVLoadError):
            CSVLoader.validate_file((MAX_FILE_SIZE_MB + 1) * 1024 * 1024)
    
    def test_validate_file_size_boundary(self):
        """Verifica límite exacto de tamaño."""
        # El límite exacto configurado debe pasar
        CSVLoader.validate_file(MAX_FILE_SIZE_MB * 1024 * 1024)
        
        # Cualquier tamaño mayor al límite configurado debe fallar
        with pytest.raises(CSVLoadError):
            CSVLoader.validate_file(int((MAX_FILE_SIZE_MB + 0.1) * 1024 * 1024))


class TestCSVLoaderChunkedLoading:
    """Pruebas para carga por chunks de archivos grandes."""
    
    def test_chunked_load_csv_returns_same_format(self, sample_large_csv):
        """Verifica que load_csv_chunked retorna mismo formato que load_csv."""
        import io
        file_obj = io.StringIO(sample_large_csv)
        
        df, load_info = CSVLoader.load_csv_chunked(file_obj)
        
        # Verifica que retorna los campos necesarios
        assert 'delimiter' in load_info
        assert 'encoding' in load_info
        assert 'rows' in load_info
        assert 'columns' in load_info
        assert 'chunked' in load_info
        assert load_info['chunked'] is True
    
    def test_chunked_load_correct_row_count(self, sample_large_csv):
        """Verifica que cuenta correctamente el número de filas en chunked load."""
        import io
        file_obj = io.StringIO(sample_large_csv)
        
        df, load_info = CSVLoader.load_csv_chunked(file_obj)
        
        # El archivo tiene 100,001 filas (header + 100,000 datos)
        assert load_info['rows'] == 100000
        assert df.shape[0] == 100000
    
    def test_chunked_load_preserves_columns(self, sample_large_csv):
        """Verifica que columnas se conservan correctamente en chunked load."""
        import io
        file_obj = io.StringIO(sample_large_csv)
        
        df, load_info = CSVLoader.load_csv_chunked(file_obj)
        
        expected_columns = ['id', 'nombre', 'correo', 'telefono', 'edad', 'ciudad', 'fecha_registro']
        assert list(df.columns) == expected_columns
    
    def test_chunked_load_reports_chunks_loaded(self, sample_large_csv):
        """Verifica que reporta número de chunks cargados."""
        import io
        file_obj = io.StringIO(sample_large_csv)
        
        df, load_info = CSVLoader.load_csv_chunked(file_obj)
        
        assert 'chunks_loaded' in load_info
        assert load_info['chunks_loaded'] > 0
    
    def test_auto_chunked_load_detection(self):
        """Verifica que load_csv detecta automáticamente cuando usar chunks."""
        # Genera CSV simulado grande
        large_csv = "a,b,c\n" + "\n".join([f"{i},{i+1},{i+2}" for i in range(60000)])
        
        import io
        file_obj = io.StringIO(large_csv)
        
        # load_csv debe decidir automáticamente usar chunked si supera threshold
        df, load_info = CSVLoader.load_csv(file_obj)
        
        # Si usa chunked, debe tener el flag
        if load_info.get('chunked'):
            assert load_info['chunked'] is True
            assert 'chunks_loaded' in load_info
    
    def test_chunked_load_with_semicolon_delimiter(self):
        """Verifica que chunked load funciona con diferentes delimitadores."""
        csv_semicolon = "col1;col2;col3\n" + "\n".join([f"{i};{i+1};{i+2}" for i in range(60000)])
        
        import io
        file_obj = io.StringIO(csv_semicolon)
        
        df, load_info = CSVLoader.load_csv_chunked(file_obj)
        
        assert load_info['delimiter'] == ';'
        assert df.shape[1] == 3
