"""
Módulo de perfilado de datos.
Realiza análisis estadístico y perfilado del DataFrame.
"""

import pandas as pd
import numpy as np
from utils.helpers import DataFrameHelper, StringHelper
from utils.patterns import ValidationPatterns, get_column_type_hints
from config import NULL_THRESHOLD_PERCENT, UNIQUE_VALUES_THRESHOLD, CARDINALITY_WARNING_PERCENT


class DataProfiler:
    """Clase para realizar el perfilado completo de un DataFrame."""
    
    def __init__(self, df):
        """
        Inicializa el perfilador con un DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame a analizar
        """
        self.df = df
        self.profile = {}
    
    def generate_profile(self):
        """
        Genera un perfil completo del DataFrame.
        
        Returns:
            dict: Perfil completo
        """
        self.profile = {
            'general_info': self._get_general_info(),
            'null_analysis': self._analyze_nulls(),
            'empty_strings': self._analyze_empty_strings(),
            'duplicates': self._analyze_duplicates(),
            'column_profiles': self._profile_columns(),
            'data_type_issues': self._detect_type_issues(),
            'memory_usage': DataFrameHelper.get_memory_usage(self.df),
        }
        
        return self.profile
    
    def _get_general_info(self):
        """Obtiene información general del DataFrame."""
        return {
            'total_rows': len(self.df),
            'total_columns': len(self.df.columns),
            'total_cells': len(self.df) * len(self.df.columns),
            'column_names': list(self.df.columns),
            'data_types': self.df.dtypes.astype(str).to_dict()
        }
    
    def _analyze_nulls(self):
        """Analiza valores nulos en el DataFrame."""
        null_info = DataFrameHelper.get_null_info(self.df)
        
        # Obtiene información de filas completas
        complete_rows_info = DataFrameHelper.get_complete_rows_info(self.df)
        
        # Obtiene utilidad por columna
        column_utilization = DataFrameHelper.get_column_utilization(self.df)
        
        # Identifica columnas problemáticas
        problematic_columns = {}
        for col, null_count in null_info['by_column'].items():
            null_percent = null_info['by_column_percent'][col]
            if null_percent >= NULL_THRESHOLD_PERCENT:
                problematic_columns[col] = {
                    'null_count': int(null_count),
                    'null_percent': float(null_percent),
                    'utilization_percent': column_utilization.get(col, 0),
                    'status': 'CRÍTICO' if null_percent >= 80 else 'GRAVE'
                }
        
        return {
            'total_null_cells': int(null_info['total_null_cells']),
            'null_percent_overall': float(
                (null_info['total_null_cells'] / null_info['total_cells'] * 100)
                if null_info['total_cells'] > 0 else 0
            ),
            'complete_rows': complete_rows_info['complete_rows'],
            'complete_rows_percent': complete_rows_info['complete_rows_percent'],
            'by_column': {
                col: {
                    'count': int(count),
                    'percent': float(null_info['by_column_percent'][col]),
                    'utilization_percent': column_utilization.get(col, 0)
                }
                for col, count in null_info['by_column'].items()
                if count > 0
            },
            'column_utilization': column_utilization,
            'problematic_columns': problematic_columns
        }
    
    def _analyze_empty_strings(self):
        """Analiza cadenas vacías o solo espacios."""
        empty_info = DataFrameHelper.get_empty_string_info(self.df)
        
        return {
            'columns_with_empty': empty_info,
            'total_empty_cells': sum(
                info['count'] for info in empty_info.values()
            ) if empty_info else 0
        }
    
    def _analyze_duplicates(self):
        """Analiza filas duplicadas."""
        dup_info = DataFrameHelper.get_duplicates_info(self.df)
        
        # Obtiene ejemplos de duplicados
        if dup_info['total_duplicates'] > 0:
            duplicate_rows = self.df[self.df.duplicated(keep=False)].head(5)
            examples = duplicate_rows.to_dict('records')
        else:
            examples = []
        
        return {
            'total_duplicates': int(dup_info['total_duplicates']),
            'duplicates_percent': float(dup_info['duplicates_percent']),
            'by_column': dup_info['by_column'],
            'examples': examples
        }
    
    def _profile_columns(self):
        """Genera perfil de cada columna."""
        column_profiles = {}
        
        for col in self.df.columns:
            column_profiles[col] = {
                'dtype': str(self.df[col].dtype),
                'type_hint': get_column_type_hints(col),
                'non_null_count': int(self.df[col].notna().sum()),
                'null_count': int(self.df[col].isna().sum()),
                'null_percent': float(
                    (self.df[col].isna().sum() / len(self.df) * 100)
                    if len(self.df) > 0 else 0
                ),
                'unique_count': int(self.df[col].nunique()),
                'cardinality_ratio': float(
                    StringHelper.get_cardinality_ratio(self.df[col])
                ),
                'stats': self._get_column_stats(col)
            }
        
        return column_profiles
    
    def _get_column_stats(self, col):
        """Obtiene estadísticas para una columna específica."""
        stats = {}
        
        try:
            # Estadísticas para columnas numéricas
            if pd.api.types.is_numeric_dtype(self.df[col]):
                stats['min'] = float(self.df[col].min())
                stats['max'] = float(self.df[col].max())
                stats['mean'] = float(self.df[col].mean())
                stats['median'] = float(self.df[col].median())
                stats['std'] = float(self.df[col].std())
        except Exception:
            pass
        
        try:
            # Valores más comunes
            most_common = self.df[col].value_counts().head(3)
            stats['most_common'] = {
                str(k): int(v) for k, v in most_common.items()
            }
        except Exception:
            pass
        
        return stats
    
    def _detect_type_issues(self):
        """Detecta columnas con mezcla de tipos de datos."""
        type_issues = {}
        
        for col in self.df.select_dtypes(include=['object']).columns:
            type_distribution = {}
            
            # Infiere tipos en la columna
            for value in self.df[col].dropna().unique()[:100]:
                inferred = ValidationPatterns.infer_data_type(value)
                type_distribution[inferred] = type_distribution.get(inferred, 0) + 1
            
            # Si hay mezcla de tipos
            if len(type_distribution) > 1:
                type_issues[col] = {
                    'detected_types': type_distribution,
                    'is_problematic': len(type_distribution) > 2
                }
        
        return type_issues
    
    def get_problematic_columns(self):
        """
        Retorna lista de columnas problemáticas.
        
        Returns:
            list: Columnas con problemas detectados
        """
        problematic = []
        
        # Columnas con muchos nulos
        for col, info in self.profile['null_analysis']['problematic_columns'].items():
            problematic.append({
                'column': col,
                'issue': 'Demasiados valores nulos',
                'severity': info['status'],
                'details': f"{info['null_percent']:.1f}% nulos"
            })
        
        # Columnas con mezcla de tipos
        for col, info in self.profile['data_type_issues'].items():
            problematic.append({
                'column': col,
                'issue': 'Mezcla de tipos de datos',
                'severity': 'GRAVE' if info['is_problematic'] else 'AVISO',
                'details': str(info['detected_types'])
            })
        
        # Columnas con demasiados valores únicos
        for col, profile in self.profile['column_profiles'].items():
            cardinality = profile['cardinality_ratio']
            if cardinality >= UNIQUE_VALUES_THRESHOLD:
                problematic.append({
                    'column': col,
                    'issue': 'Demasiados valores únicos',
                    'severity': 'AVISO',
                    'details': f"{cardinality*100:.1f}% valores únicos"
                })
        
        return problematic
