"""
Módulo de perfilado de datos.
Realiza análisis estadístico y perfilado del DataFrame.
"""

import pandas as pd
import numpy as np
from utils.helpers import DataFrameHelper, StringHelper
from utils.patterns import ValidationPatterns, get_column_type_hints
from config import NULL_THRESHOLD_PERCENT, UNIQUE_VALUES_THRESHOLD, CARDINALITY_WARNING_PERCENT


class MemoryUsage(float):
    """Valor compatible: se formatea como float y también expone detalles por llave."""

    def __new__(cls, total_mb, by_column=None):
        obj = float.__new__(cls, total_mb)
        obj.total_mb = total_mb
        obj.by_column = by_column or {}
        return obj

    def __getitem__(self, key):
        if key == 'total_mb':
            return self.total_mb
        if key == 'by_column':
            return self.by_column
        raise KeyError(key)

    def __contains__(self, key):
        return key in {'total_mb', 'by_column'}

    def keys(self):
        return ['total_mb', 'by_column']

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default


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
            'memory_usage': self._get_memory_usage(),
        }
        
        return self.profile

    @classmethod
    def generate_profile_from_chunks(cls, chunks, sample_rows=10000):
        """Genera un perfil sin concatenar todos los chunks en memoria.

        Las métricas de filas, nulos, vacíos y duplicados se acumulan sobre
        todo el archivo. Las estadísticas detalladas de columnas se calculan
        sobre una muestra acotada y quedan identificadas como aproximadas.
        """
        total_rows = 0
        total_memory_bytes = 0
        null_counts = None
        empty_counts = None
        complete_rows = 0
        duplicate_hashes = set()
        duplicate_count = 0
        sample_parts = []
        sampled_rows = 0
        column_names = None
        data_types = {}

        for chunk in chunks:
            if chunk is None or chunk.empty:
                continue

            if column_names is None:
                column_names = list(chunk.columns)
                null_counts = pd.Series(0, index=chunk.columns, dtype='int64')
                empty_counts = pd.Series(0, index=chunk.columns, dtype='int64')

            total_rows += len(chunk)
            total_memory_bytes += int(chunk.memory_usage(deep=True).sum())
            null_counts = null_counts.add(chunk.isna().sum(), fill_value=0)
            complete_rows += int(chunk.notna().all(axis=1).sum())

            object_columns = chunk.select_dtypes(include=['object', 'string']).columns
            if len(object_columns):
                empty_counts = empty_counts.add(
                    chunk[object_columns].apply(
                        lambda column: column.fillna('').astype(str).str.strip().eq('').sum()
                    ),
                    fill_value=0,
                )

            row_hashes = pd.util.hash_pandas_object(chunk, index=False)
            new_hashes = set(row_hashes.tolist())
            duplicate_count += len(row_hashes) - len(new_hashes - duplicate_hashes)
            duplicate_hashes.update(new_hashes)

            if sampled_rows < sample_rows:
                sample = chunk.head(sample_rows - sampled_rows)
                sample_parts.append(sample.copy())
                sampled_rows += len(sample)

            if not data_types:
                data_types = chunk.dtypes.astype(str).to_dict()

        if not column_names:
            return cls(pd.DataFrame()).generate_profile()

        sample_df = pd.concat(sample_parts, ignore_index=True) if sample_parts else pd.DataFrame(columns=column_names)
        profile = cls(sample_df).generate_profile()
        total_cells = total_rows * len(column_names)
        null_counts = null_counts.astype(int)
        null_total = int(null_counts.sum())
        null_percentages = (null_counts / total_rows * 100) if total_rows else null_counts * 0

        by_column = {
            col: {
                'count': int(null_counts[col]),
                'percent': float(null_percentages[col]),
                'utilization_percent': float(100 - null_percentages[col]),
            }
            for col in column_names
            if null_counts[col] > 0
        }
        column_utilization = {
            col: float(100 - null_percentages[col]) for col in column_names
        }
        problematic_columns = {
            col: {
                'null_count': info['count'],
                'null_percent': info['percent'],
                'utilization_percent': info['utilization_percent'],
                'status': 'CRÍTICO' if info['percent'] >= 80 else 'GRAVE',
            }
            for col, info in by_column.items()
            if info['percent'] >= NULL_THRESHOLD_PERCENT
        }

        profile['general_info'].update({
            'total_rows': total_rows,
            'total_columns': len(column_names),
            'total_cells': total_cells,
            'column_names': column_names,
            'data_types': data_types,
            'memory_usage_mb': total_memory_bytes / (1024 ** 2),
        })
        profile['null_analysis'].update({
            'total_null_cells': null_total,
            'null_percent_overall': (null_total / total_cells * 100) if total_cells else 0,
            'complete_rows': complete_rows,
            'complete_rows_percent': (complete_rows / total_rows * 100) if total_rows else 0,
            'by_column': by_column,
            'column_utilization': column_utilization,
            'problematic_columns': problematic_columns,
            'total_null_count': null_total,
            'total_null_percent': (null_total / total_cells * 100) if total_cells else 0,
            'columns_with_nulls': by_column,
        })
        profile['empty_strings'] = {
            'columns_with_empty': {
                col: {
                    'count': int(empty_counts.get(col, 0)),
                    'percent': float(empty_counts.get(col, 0) / total_rows * 100) if total_rows else 0,
                }
                for col in column_names
                if empty_counts.get(col, 0) > 0
            },
            'total_empty_cells': int(empty_counts.sum()),
        }
        duplicate_percent = duplicate_count / total_rows * 100 if total_rows else 0
        profile['duplicates'].update({
            'total_duplicates': int(duplicate_count),
            'total_duplicate_rows': int(duplicate_count),
            'duplicates_percent': float(duplicate_percent),
            'examples': [],
        })
        profile['memory_usage'] = MemoryUsage(total_memory_bytes / (1024 ** 2))
        profile['incremental'] = {
            'enabled': True,
            'sample_rows': sampled_rows,
            'sample_limit': sample_rows,
            'column_statistics_approximate': sampled_rows < total_rows,
        }
        return profile
    
    def _get_general_info(self):
        """Obtiene información general del DataFrame."""
        memory_usage_mb = DataFrameHelper.get_memory_usage(self.df)
        return {
            'total_rows': len(self.df),
            'total_columns': len(self.df.columns),
            'total_cells': len(self.df) * len(self.df.columns),
            'column_names': list(self.df.columns),
            'data_types': self.df.dtypes.astype(str).to_dict(),
            # Alias de compatibilidad para pruebas/documentación previa
            'memory_usage_mb': memory_usage_mb
        }


    def _get_memory_usage(self):
        """Obtiene uso de memoria total y por columna con compatibilidad float/dict."""
        total_mb = DataFrameHelper.get_memory_usage(self.df)
        by_column = {
            col: float(self.df[col].memory_usage(deep=True) / (1024 ** 2))
            for col in self.df.columns
        }
        return MemoryUsage(total_mb, by_column)

    
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
        
        total_null_cells = int(null_info['total_null_cells'])
        null_percent_overall = float(
            (null_info['total_null_cells'] / null_info['total_cells'] * 100)
            if null_info['total_cells'] > 0 else 0
        )

        by_column = {
            col: {
                'count': int(count),
                'percent': float(null_info['by_column_percent'][col]),
                'utilization_percent': column_utilization.get(col, 0)
            }
            for col, count in null_info['by_column'].items()
            if count > 0
        }

        columns_with_nulls = {
            col: {
                'null_count': info['count'],
                'null_percent': info['percent'],
                'utilization_percent': info['utilization_percent']
            }
            for col, info in by_column.items()
        }

        return {
            'total_null_cells': total_null_cells,
            'null_percent_overall': null_percent_overall,
            'complete_rows': complete_rows_info['complete_rows'],
            'complete_rows_percent': complete_rows_info['complete_rows_percent'],
            'by_column': by_column,
            'column_utilization': column_utilization,
            'problematic_columns': problematic_columns,
            # Alias de compatibilidad para pruebas/documentación previa
            'total_null_count': total_null_cells,
            'total_null_percent': null_percent_overall,
            'columns_with_nulls': columns_with_nulls
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
        
        duplicate_columns = []
        columns = list(self.df.columns)
        for i, col_a in enumerate(columns):
            for col_b in columns[i + 1:]:
                try:
                    if self.df[col_a].equals(self.df[col_b]):
                        duplicate_columns.append({'column_a': col_a, 'column_b': col_b})
                except Exception:
                    continue

        total_duplicates = int(dup_info['total_duplicates'])
        return {
            'total_duplicates': total_duplicates,
            'duplicates_percent': float(dup_info['duplicates_percent']),
            'by_column': dup_info['by_column'],
            'examples': examples,
            # Alias/extra para pruebas/documentación previa
            'total_duplicate_rows': total_duplicates,
            'duplicate_columns': duplicate_columns
        }
    
    def _profile_columns(self):
        """Genera perfil de cada columna."""
        column_profiles = {}
        
        for col in self.df.columns:
            stats = self._get_column_stats(col)
            cardinality_ratio = float(StringHelper.get_cardinality_ratio(self.df[col]))
            col_profile = {
                'dtype': str(self.df[col].dtype),
                'data_type': str(self.df[col].dtype),
                'type_hint': get_column_type_hints(col),
                'non_null_count': int(self.df[col].notna().sum()),
                'null_count': int(self.df[col].isna().sum()),
                'null_percent': float(
                    (self.df[col].isna().sum() / len(self.df) * 100)
                    if len(self.df) > 0 else 0
                ),
                'unique_count': int(self.df[col].nunique()),
                'unique_percent': cardinality_ratio * 100,
                'cardinality_ratio': cardinality_ratio,
                'stats': stats
            }
            # Alias top-level para estadísticas numéricas usadas por pruebas previas
            col_profile.update({k: v for k, v in stats.items() if k in ['min', 'max', 'mean', 'median', 'std']})
            column_profiles[col] = col_profile
        
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
