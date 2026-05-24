"""
Módulo de generador de recomendaciones.
Genera recomendaciones de limpieza y validación basadas en los análisis realizados.
"""

import pandas as pd
from config import NULL_THRESHOLD_PERCENT, UNIQUE_VALUES_THRESHOLD


class RecommendationGenerator:
    """Genera recomendaciones de limpieza y validación de datos."""
    
    def __init__(self, profile, validation_results):
        """
        Inicializa el generador de recomendaciones.
        
        Args:
            profile (dict): Perfil del DataFrame
            validation_results (dict): Resultados de validaciones
        """
        self.profile = profile
        self.validation_results = validation_results
        self.recommendations = []
    
    def generate_all_recommendations(self):
        """
        Genera todas las recomendaciones.
        
        Returns:
            dict: Recomendaciones organizadas por categoría
        """
        recommendations = {
            'cleaning': self._generate_cleaning_recommendations(),
            'database_rules': self._generate_database_rules(),
            'normalization': self._generate_normalization_recommendations(),
            'quality': self._generate_quality_recommendations()
        }
        
        return recommendations
    
    def _generate_cleaning_recommendations(self):
        """Genera recomendaciones para limpieza de datos."""
        recommendations = []
        
        # Análisis de valores nulos
        for col, info in self.profile['null_analysis']['problematic_columns'].items():
            null_percent = info['null_percent']
            
            if null_percent >= 80:
                recommendations.append({
                    'severity': 'CRÍTICO',
                    'column': col,
                    'recommendation': f'La columna "{col}" tiene {null_percent:.1f}% de valores nulos. '
                                    'Se recomienda ELIMINAR esta columna del análisis.',
                    'action': 'DROP_COLUMN',
                    'details': {
                        'null_count': info['null_count'],
                        'null_percent': null_percent
                    }
                })
            elif null_percent >= NULL_THRESHOLD_PERCENT:
                recommendations.append({
                    'severity': 'GRAVE',
                    'column': col,
                    'recommendation': f'La columna "{col}" tiene más del {NULL_THRESHOLD_PERCENT}% de valores nulos '
                                    '({:.1f}%). Se recomienda evaluar si debe ser obligatoria o eliminarse.'.format(null_percent),
                    'action': 'REVIEW_COLUMN',
                    'details': {
                        'null_count': info['null_count'],
                        'null_percent': null_percent
                    }
                })
        
        # Análisis de cadenas vacías
        for col, info in self.profile['empty_strings']['columns_with_empty'].items():
            empty_percent = info['percent']
            
            if empty_percent > 0:
                recommendations.append({
                    'severity': 'AVISO',
                    'column': col,
                    'recommendation': f'La columna "{col}" contiene {info["count"]} cadenas vacías o solo espacios '
                                    '({:.1f}%). Se recomienda aplicar TRIM y reemplazar con valores nulos.'.format(empty_percent),
                    'action': 'CLEAN_WHITESPACE',
                    'details': {
                        'empty_count': info['count'],
                        'empty_percent': empty_percent
                    }
                })
        
        # Análisis de duplicados
        if self.profile['duplicates']['total_duplicates'] > 0:
            recommendations.append({
                'severity': 'GRAVE',
                'column': 'FILAS_COMPLETAS',
                'recommendation': f'Se detectaron {self.profile["duplicates"]["total_duplicates"]} filas duplicadas '
                                f'({self.profile["duplicates"]["duplicates_percent"]:.1f}%). '
                                'Se recomienda definir una CLAVE ÚNICA o aplicar DISTINCT.',
                'action': 'REMOVE_DUPLICATES',
                'details': {
                    'duplicate_count': self.profile['duplicates']['total_duplicates'],
                    'duplicate_percent': self.profile['duplicates']['duplicates_percent']
                }
            })
        
        # Análisis de mezcla de tipos
        for col, issues in self.profile['data_type_issues'].items():
            if issues['is_problematic']:
                recommendations.append({
                    'severity': 'GRAVE',
                    'column': col,
                    'recommendation': f'La columna "{col}" contiene una mezcla de tipos de datos: '
                                    f'{str(issues["detected_types"])}. '
                                    'Se recomienda convertir a un tipo único o dividir en columnas.',
                    'action': 'STANDARDIZE_TYPE',
                    'details': {
                        'detected_types': issues['detected_types']
                    }
                })
        
        return recommendations
    
    def _generate_database_rules(self):
        """Genera reglas sugeridas para la base de datos."""
        rules = []
        
        # Regla NOT NULL
        for col, info in self.profile['null_analysis']['by_column'].items():
            if info['percent'] == 0:
                rules.append({
                    'rule_type': 'NOT NULL',
                    'column': col,
                    'sql_constraint': f'ALTER TABLE tabla ADD CONSTRAINT nn_{col} CHECK ({col} IS NOT NULL);',
                    'reason': f'La columna "{col}" nunca contiene valores nulos.'
                })
        
        # Regla UNIQUE
        for col, profile_col in self.profile['column_profiles'].items():
            if profile_col['cardinality_ratio'] >= 0.95 and profile_col['non_null_count'] > 0:
                rules.append({
                    'rule_type': 'UNIQUE',
                    'column': col,
                    'sql_constraint': f'ALTER TABLE tabla ADD CONSTRAINT uk_{col} UNIQUE ({col});',
                    'reason': f'La columna "{col}" tiene {profile_col["unique_count"]} valores únicos '
                             f'({profile_col["cardinality_ratio"]*100:.1f}%), lo que sugiere ser clave única.'
                })
        
        # Regla CHECK para valores numéricos
        for col, info in self.validation_results.get('numeric_validation', {}).items():
            if info['is_problematic'] and info['negative_count'] > 0:
                rules.append({
                    'rule_type': 'CHECK (NO NEGATIVOS)',
                    'column': col,
                    'sql_constraint': f'ALTER TABLE tabla ADD CONSTRAINT ck_{col}_positive CHECK ({col} >= 0);',
                    'reason': f'La columna "{col}" contiene {info["negative_count"]} valores negativos que deben ser validados.'
                })
        
        # Reglas de validación de correos
        for col, info in self.validation_results.get('email_validation', {}).items():
            if info['is_problematic']:
                rules.append({
                    'rule_type': 'VALIDATION',
                    'column': col,
                    'description': f'Validar formato de email en {col}',
                    'reason': f'La columna "{col}" contiene {info["invalid_count"]} emails inválidos.'
                })
        
        # Reglas de validación de teléfono
        for col, info in self.validation_results.get('phone_validation', {}).items():
            if info['is_problematic']:
                rules.append({
                    'rule_type': 'VALIDATION',
                    'column': col,
                    'description': f'Validar formato de teléfono en {col}',
                    'reason': f'La columna "{col}" contiene {info["invalid_count"]} teléfonos inválidos.'
                })
        
        return rules
    
    def _generate_normalization_recommendations(self):
        """Genera recomendaciones de normalización."""
        recommendations = []
        
        # Whitespace normalization
        for col, info in self.profile['empty_strings']['columns_with_empty'].items():
            if info['count'] > 0:
                recommendations.append({
                    'type': 'WHITESPACE_TRIM',
                    'column': col,
                    'operation': 'TRIM()',
                    'reason': f'Remover espacios al inicio/final en "{col}"',
                    'examples': 'Convierte "  Juan  " → "Juan"'
                })
        
        # Case normalization para ciertos tipos
        for col, profile_col in self.profile['column_profiles'].items():
            type_hint = profile_col['type_hint']
            
            if type_hint in ['Email', 'URL']:
                recommendations.append({
                    'type': 'LOWERCASE',
                    'column': col,
                    'operation': 'LOWER()',
                    'reason': f'Normalizar mayúsculas en "{col}" ({type_hint})',
                    'examples': 'Convierte "JUAN@EXAMPLE.COM" → "juan@example.com"'
                })
        
        # Standardization de fechas
        for col, info in self.validation_results.get('date_validation', {}).items():
            if info.get('format_inconsistencies'):
                recommendations.append({
                    'type': 'DATE_STANDARDIZATION',
                    'column': col,
                    'operation': 'TO_DATE()',
                    'reason': f'Estandarizar formatos de fecha en "{col}"',
                    'inconsistencies_found': len(info['format_inconsistencies'])
                })
        
        # Numeric standardization
        for col, info in self.validation_results.get('numeric_validation', {}).items():
            if info.get('negative_count', 0) > 0:
                recommendations.append({
                    'type': 'RANGE_NORMALIZATION',
                    'column': col,
                    'operation': 'ABS() o FILTER',
                    'reason': f'Valores negativos encontrados en "{col}"',
                    'suggestion': 'Convertir a positivos o filtrar registros inválidos'
                })
        
        return recommendations
    
    def _generate_quality_recommendations(self):
        """Genera recomendaciones generales de calidad."""
        recommendations = []
        
        # Cardinalidad alta
        for col, profile_col in self.profile['column_profiles'].items():
            if profile_col['cardinality_ratio'] >= UNIQUE_VALUES_THRESHOLD:
                recommendations.append({
                    'severity': 'AVISO',
                    'type': 'HIGH_CARDINALITY',
                    'column': col,
                    'recommendation': f'La columna "{col}" tiene {profile_col["cardinality_ratio"]*100:.1f}% de valores únicos. '
                                    'Esto puede ser esperado (si es ID) o indicar problemas en la captura de datos.',
                    'action': 'REVIEW_COLUMN'
                })
        
        # Revisar columnas sin nombre
        for col in self.profile['general_info']['column_names']:
            if col.startswith('Column_') or col == 'Unnamed':
                recommendations.append({
                    'severity': 'AVISO',
                    'type': 'MISSING_COLUMN_NAME',
                    'column': col,
                    'recommendation': f'La columna "{col}" no tiene nombre descriptivo. '
                                    'Se recomienda definir un nombre apropiado.',
                    'action': 'RENAME_COLUMN'
                })
        
        # Resumen de calidad general
        null_percent_overall = self.profile['null_analysis']['null_percent_overall']
        if null_percent_overall > 30:
            recommendations.append({
                'severity': 'GRAVE',
                'type': 'OVERALL_QUALITY',
                'recommendation': f'El dataset tiene un {null_percent_overall:.1f}% de valores nulos en general. '
                                'La calidad general es BAJA. Se recomienda revisar el proceso de captura.',
                'action': 'REVIEW_PROCESS'
            })
        
        return recommendations
    
    def get_summary_recommendations(self):
        """Genera un resumen ejecutivo de recomendaciones."""
        all_recs = self.generate_all_recommendations()
        
        summary = {
            'critical_issues': len([
                r for recs in all_recs.values() for r in recs
                if r.get('severity') == 'CRÍTICO'
            ]),
            'serious_issues': len([
                r for recs in all_recs.values() for r in recs
                if r.get('severity') == 'GRAVE'
            ]),
            'warnings': len([
                r for recs in all_recs.values() for r in recs
                if r.get('severity') == 'AVISO'
            ]),
            'total_recommendations': sum(len(recs) for recs in all_recs.values()),
            'categories': list(all_recs.keys())
        }
        
        return summary
