"""
Funciones auxiliares y de utilidad para el análisis de datos.
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os


class DataFrameHelper:
    """Contiene métodos auxiliares para trabajar con DataFrames."""
    
    @staticmethod
    def get_memory_usage(df):
        """
        Calcula el uso de memoria del DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame a analizar
        
        Returns:
            float: Uso de memoria en MB
        """
        return df.memory_usage(deep=True).sum() / (1024 ** 2)
    
    @staticmethod
    def get_duplicates_info(df):
        """
        Obtiene información sobre filas duplicadas.
        
        Args:
            df (pd.DataFrame): DataFrame a analizar
        
        Returns:
            dict: Información sobre duplicados
        """
        total_duplicates = df.duplicated().sum()
        duplicates_by_column = {}
        
        for col in df.columns:
            col_duplicates = df[col].duplicated().sum()
            if col_duplicates > 0:
                duplicates_by_column[col] = col_duplicates
        
        return {
            'total_duplicates': total_duplicates,
            'by_column': duplicates_by_column,
            'duplicates_percent': (total_duplicates / len(df) * 100) if len(df) > 0 else 0
        }
    
    @staticmethod
    def get_null_info(df):
        """
        Obtiene información detallada sobre valores nulos.
        
        Args:
            df (pd.DataFrame): DataFrame a analizar
        
        Returns:
            dict: Información sobre valores nulos
        """
        null_counts = df.isnull().sum()
        null_percents = (null_counts / len(df) * 100).round(2)
        
        return {
            'by_column': null_counts.to_dict(),
            'by_column_percent': null_percents.to_dict(),
            'total_null_cells': null_counts.sum(),
            'total_cells': df.shape[0] * df.shape[1]
        }
    
    @staticmethod
    def get_complete_rows_info(df):
        """
        Obtiene información sobre filas completamente limpias (sin nulos).
        
        Args:
            df (pd.DataFrame): DataFrame a analizar
        
        Returns:
            dict: Información sobre filas completas
        """
        total_rows = len(df)
        complete_rows = df.dropna().shape[0]
        complete_rows_percent = (complete_rows / total_rows * 100) if total_rows > 0 else 0
        
        return {
            'complete_rows': complete_rows,
            'total_rows': total_rows,
            'complete_rows_percent': round(complete_rows_percent, 2)
        }
    
    @staticmethod
    def get_column_utilization(df):
        """
        Calcula el porcentaje de utilidad para cada columna.
        Utilidad = (Valores no nulos / Total de filas) × 100
        
        Args:
            df (pd.DataFrame): DataFrame a analizar
        
        Returns:
            dict: {column_name: utilization_percent}
        """
        total_rows = len(df)
        if total_rows == 0:
            return {}
        
        utilization = {}
        for col in df.columns:
            non_null_count = df[col].notna().sum()
            utilization_percent = (non_null_count / total_rows * 100)
            utilization[col] = round(utilization_percent, 2)
        
        return utilization
    
    @staticmethod
    def get_empty_string_info(df):
        """
        Identifica columnas con cadenas vacías o solo espacios.
        
        Args:
            df (pd.DataFrame): DataFrame a analizar
        
        Returns:
            dict: Información sobre cadenas vacías
        """
        empty_info = {}
        
        for col in df.select_dtypes(include=['object']).columns:
            empty_count = (df[col].astype(str).str.strip() == '').sum()
            if empty_count > 0:
                empty_info[col] = {
                    'count': empty_count,
                    'percent': (empty_count / len(df) * 100).round(2)
                }
        
        return empty_info
    
    @staticmethod
    def infer_column_types(df):
        """
        Infiere el tipo de dato más probable para cada columna.
        
        Args:
            df (pd.DataFrame): DataFrame a analizar
        
        Returns:
            dict: Tipos inferidos por columna
        """
        inferred_types = {}
        
        for col in df.columns:
            dtype = str(df[col].dtype)
            
            if 'int' in dtype:
                inferred_types[col] = 'Entero'
            elif 'float' in dtype:
                inferred_types[col] = 'Flotante'
            elif 'datetime' in dtype:
                inferred_types[col] = 'Fecha'
            elif 'bool' in dtype:
                inferred_types[col] = 'Booleano'
            else:
                inferred_types[col] = 'Texto'
        
        return inferred_types


class StringHelper:
    """Métodos auxiliares para procesamiento de texto."""
    
    @staticmethod
    def clean_string(text):
        """Limpia una cadena removiendo espacios extra."""
        if not isinstance(text, str):
            return text
        return ' '.join(text.split())
    
    @staticmethod
    def truncate_string(text, max_length=50):
        """Trunca una cadena a una longitud máxima."""
        if isinstance(text, str) and len(text) > max_length:
            return text[:max_length] + '...'
        return text
    
    @staticmethod
    def get_cardinality_ratio(series):
        """
        Calcula la proporción de valores únicos en una serie.
        
        Args:
            series (pd.Series): Serie a analizar
        
        Returns:
            float: Proporción de valores únicos
        """
        if len(series) == 0:
            return 0
        return len(series.unique()) / len(series)


class ReportHelper:
    """Métodos auxiliares para generación de reportes."""
    
    @staticmethod
    def create_output_directory():
        """Crea el directorio de salida si no existe."""
        if not os.path.exists('./output/'):
            os.makedirs('./output/')
    
    @staticmethod
    def get_timestamp():
        """Retorna un timestamp formateado."""
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    @staticmethod
    def get_report_filename(report_type='reporte'):
        """
        Genera un nombre de archivo único para el reporte.
        
        Args:
            report_type (str): Tipo de reporte
        
        Returns:
            str: Nombre del archivo
        """
        timestamp = ReportHelper.get_timestamp()
        return f'{report_type}_{timestamp}'


class ValidationHelper:
    """Métodos auxiliares para validaciones."""
    
    @staticmethod
    def is_numeric(value):
        """Verifica si un valor es numérico."""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def is_in_range(value, min_val, max_val):
        """Verifica si un valor está dentro de un rango."""
        try:
            num = float(value)
            return min_val <= num <= max_val
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def count_special_characters(text):
        """Cuenta caracteres especiales en un texto."""
        if not isinstance(text, str):
            return 0
        special_count = sum(1 for c in text if not c.isalnum() and c != ' ')
        return special_count
