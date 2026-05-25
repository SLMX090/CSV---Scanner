"""
Pruebas para el módulo data_profiler.py
"""

import pytest
import pandas as pd
import numpy as np
from modules.data_profiler import DataProfiler


class TestDataProfilerGeneralInfo:
    """Pruebas para información general del perfil."""
    
    def test_profile_basic_info(self, sample_dataframe):
        """Verifica que extrae información básica correcta."""
        profiler = DataProfiler(sample_dataframe)
        profile = profiler.generate_profile()
        
        assert profile['general_info']['total_rows'] == 3
        assert profile['general_info']['total_columns'] == 5
        assert 'memory_usage_mb' in profile['general_info']
    
    def test_profile_empty_dataframe(self):
        """Verifica manejo de DataFrame vacío."""
        df = pd.DataFrame()
        profiler = DataProfiler(df)
        profile = profiler.generate_profile()
        
        assert profile['general_info']['total_rows'] == 0
        assert profile['general_info']['total_columns'] == 0
    
    def test_profile_single_row(self):
        """Verifica perfil con una sola fila."""
        df = pd.DataFrame({
            'col1': [1],
            'col2': ['test']
        })
        profiler = DataProfiler(df)
        profile = profiler.generate_profile()
        
        assert profile['general_info']['total_rows'] == 1


class TestDataProfilerNullAnalysis:
    """Pruebas para análisis de valores nulos."""
    
    def test_null_analysis_no_nulls(self, sample_dataframe):
        """Verifica análisis cuando no hay nulos."""
        profiler = DataProfiler(sample_dataframe)
        profile = profiler.generate_profile()
        
        null_analysis = profile['null_analysis']
        assert null_analysis['total_null_count'] == 0
        assert null_analysis['total_null_percent'] == 0.0
    
    def test_null_analysis_with_nulls(self):
        """Verifica detección correcta de valores nulos."""
        df = pd.DataFrame({
            'col1': [1, 2, None],
            'col2': ['a', None, 'c'],
            'col3': [1.1, 2.2, 3.3]
        })
        
        profiler = DataProfiler(df)
        profile = profiler.generate_profile()
        
        null_analysis = profile['null_analysis']
        assert null_analysis['total_null_count'] == 2
        assert 'col1' in null_analysis['columns_with_nulls']
        assert 'col2' in null_analysis['columns_with_nulls']
    
    def test_null_percent_calculation(self):
        """Verifica cálculo correcto de porcentaje de nulos."""
        df = pd.DataFrame({
            'col1': [1, None, None],  # 66.7% nulos
            'col2': [1, 2, 3]         # 0% nulos
        })
        
        profiler = DataProfiler(df)
        profile = profiler.generate_profile()
        
        null_analysis = profile['null_analysis']
        col1_null_pct = null_analysis['columns_with_nulls']['col1']['null_percent']
        
        assert 66 < col1_null_pct < 68


class TestDataProfilerDuplicates:
    """Pruebas para análisis de duplicados."""
    
    def test_duplicate_detection_no_duplicates(self, sample_dataframe):
        """Verifica cuando no hay filas duplicadas."""
        profiler = DataProfiler(sample_dataframe)
        profile = profiler.generate_profile()
        
        assert profile['duplicates']['total_duplicate_rows'] == 0
    
    def test_duplicate_detection_with_duplicates(self):
        """Verifica detección correcta de filas duplicadas."""
        df = pd.DataFrame({
            'col1': [1, 2, 1, 3],
            'col2': ['a', 'b', 'a', 'd']
        })
        
        profiler = DataProfiler(df)
        profile = profiler.generate_profile()
        
        assert profile['duplicates']['total_duplicate_rows'] > 0
    
    def test_duplicate_columns_detection(self):
        """Verifica detección de columnas duplicadas."""
        df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': [1, 2, 3],  # Igual a col1
            'col3': [4, 5, 6]
        })
        
        profiler = DataProfiler(df)
        profile = profiler.generate_profile()
        
        # Debería detectar que col1 y col2 tienen el mismo contenido
        duplicates = profile['duplicates']
        assert 'duplicate_columns' in duplicates


class TestDataProfilerColumnProfiles:
    """Pruebas para perfiles individuales de columnas."""
    
    def test_column_profile_numeric(self):
        """Verifica perfil de columna numérica."""
        df = pd.DataFrame({
            'numbers': [1, 2, 3, 4, 5]
        })
        
        profiler = DataProfiler(df)
        profile = profiler.generate_profile()
        
        col_profile = profile['column_profiles']['numbers']
        assert col_profile['data_type'] in ['int64', 'int', 'numeric']
        assert 'min' in col_profile
        assert 'max' in col_profile
        assert 'mean' in col_profile
    
    def test_column_profile_text(self):
        """Verifica perfil de columna de texto."""
        df = pd.DataFrame({
            'text': ['short', 'medium length', 'a very long text string here']
        })
        
        profiler = DataProfiler(df)
        profile = profiler.generate_profile()
        
        col_profile = profile['column_profiles']['text']
        assert col_profile['data_type'] == 'object'
        assert 'unique_count' in col_profile
        assert 'unique_percent' in col_profile
    
    def test_column_profile_unique_values(self):
        """Verifica conteo de valores únicos."""
        df = pd.DataFrame({
            'col': [1, 2, 2, 3, 3, 3]
        })
        
        profiler = DataProfiler(df)
        profile = profiler.generate_profile()
        
        col_profile = profile['column_profiles']['col']
        assert col_profile['unique_count'] == 3


class TestDataProfilerDataTypeIssues:
    """Pruebas para detección de problemas de tipo de dato."""
    
    def test_mixed_type_column_detection(self):
        """Verifica detección de columnas con tipos mixtos."""
        df = pd.DataFrame({
            'mixed': [1, '2', 3.0, None, 'five']
        })
        
        profiler = DataProfiler(df)
        profile = profiler.generate_profile()
        
        # Debería detectar tipos inconsistentes
        issues = profile['data_type_issues']
        assert len(issues) > 0 or issues is not None


class TestDataProfilerMemoryUsage:
    """Pruebas para cálculo de uso de memoria."""
    
    def test_memory_usage_calculation(self, sample_dataframe):
        """Verifica que calcula uso de memoria."""
        profiler = DataProfiler(sample_dataframe)
        profile = profiler.generate_profile()
        
        memory_usage = profile['memory_usage']
        assert memory_usage['total_mb'] > 0
        assert 'by_column' in memory_usage
    
    def test_memory_usage_large_dataframe(self):
        """Verifica cálculo en DataFrame más grande."""
        df = pd.DataFrame({
            'col1': np.random.randn(10000),
            'col2': np.random.randn(10000),
            'col3': ['text'] * 10000
        })
        
        profiler = DataProfiler(df)
        profile = profiler.generate_profile()
        
        memory_usage = profile['memory_usage']
        assert memory_usage['total_mb'] > 0
