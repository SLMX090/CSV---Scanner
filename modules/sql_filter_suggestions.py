"""
Módulo para generar sugerencias de filtros SQL basadas en los problemas detectados.
Proporciona queries SQL específicas que pueden usarse para limpiar y filtrar datos.
"""


class SQLFilterSuggestions:
    """Genera sugerencias de filtros SQL para limpiar y validar datos."""
    
    def __init__(self, profile, validation_results, df):
        """
        Inicializa el generador de sugerencias SQL.
        
        Args:
            profile (dict): Perfil del DataFrame
            validation_results (dict): Resultados de validaciones
            df (pd.DataFrame): DataFrame original
        """
        self.profile = profile
        self.validation_results = validation_results
        self.df = df
    
    def generate_all_suggestions(self):
        """
        Genera todas las sugerencias de filtros SQL.
        
        Returns:
            dict: Sugerencias organizadas por categoría
        """
        suggestions = {
            'null_filters': self._generate_null_filters(),
            'duplicates_filters': self._generate_duplicates_filters(),
            'type_standardization': self._generate_type_filters(),
            'validation_filters': self._generate_validation_filters(),
            'cleanup_filters': self._generate_cleanup_filters(),
            'data_quality_filters': self._generate_quality_filters()
        }
        
        return suggestions
    
    def _generate_null_filters(self):
        """Genera filtros para eliminar o manejar valores nulos."""
        filters = []
        
        # Filtros para columnas con nulos problemáticos
        for col, info in self.profile['null_analysis']['by_column'].items():
            if info['percent'] > 0:
                filters.append({
                    'column': col,
                    'type': 'NULL_ELIMINATION',
                    'severity': 'CRÍTICO' if info['percent'] >= 80 else 'GRAVE' if info['percent'] >= 40 else 'AVISO',
                    'problem': f"Columna con {info['percent']:.1f}% de nulos",
                    'filter_type_1': f"WHERE {col} IS NOT NULL",
                    'filter_type_2': f"WHERE {col} IS NOT NULL AND TRIM({col}) != ''",
                    'description': f'Elimina filas donde "{col}" es nulo',
                    'impact': f"Reducirá {info['percent']:.1f}% del dataset"
                })
        
        return filters
    
    def _generate_duplicates_filters(self):
        """Genera filtros para eliminar duplicados."""
        filters = []
        
        if self.profile['duplicates']['total_duplicates'] > 0:
            dup_percent = self.profile['duplicates']['duplicates_percent']
            
            # Opción 1: DISTINCT
            filters.append({
                'type': 'REMOVE_DUPLICATES',
                'severity': 'GRAVE' if dup_percent > 5 else 'AVISO',
                'problem': f'{self.profile["duplicates"]["total_duplicates"]} filas duplicadas ({dup_percent:.1f}%)',
                'filter_sql': 'SELECT DISTINCT * FROM tabla',
                'description': 'Elimina todas las filas duplicadas manteniendo la primera ocurrencia',
                'impact': f'Reducirá {dup_percent:.1f}% del dataset',
                'columns_affected': 'Todas',
                'alternative': 'SELECT * FROM tabla WHERE id IN (SELECT MIN(id) FROM tabla GROUP BY all_columns)'
            })
            
            # Opción 2: ROW_NUMBER para mantener primeros duplicados
            all_cols = ', '.join([f'"{col}"' for col in self.profile['general_info']['column_names']])
            filters.append({
                'type': 'REMOVE_DUPLICATES_ADVANCED',
                'severity': 'GRAVE',
                'problem': 'Opción avanzada: mantener solo primer duplicado',
                'filter_sql': f'SELECT * FROM (SELECT *, ROW_NUMBER() OVER (PARTITION BY {all_cols} ORDER BY rownum ASC) as rn FROM tabla) WHERE rn = 1',
                'description': 'Mantiene la primera ocurrencia de cada duplicado',
                'note': 'Requiere campo de ordenamiento (rownum o ID)',
                'columns_affected': 'Todas'
            })
        
        return filters
    
    def _generate_type_filters(self):
        """Genera filtros para estandarizar tipos de datos."""
        filters = []
        
        for col, issues in self.profile['data_type_issues'].items():
            if issues['is_problematic']:
                detected_types = issues['detected_types']
                
                filters.append({
                    'column': col,
                    'type': 'TYPE_STANDARDIZATION',
                    'severity': 'GRAVE',
                    'problem': f'Columna con tipos mixtos: {detected_types}',
                    'filter_sql': f'CAST({col} AS VARCHAR)',
                    'alternative': f'CAST({col} AS NUMERIC) -- Si principalmente es numérica',
                    'description': f'Estandariza el tipo de datos en "{col}"',
                    'detected_types': detected_types,
                    'recommendation': 'Convertir a tipo texto si la columna tiene caracteres especiales'
                })
        
        return filters
    
    def _generate_validation_filters(self):
        """Genera filtros para datos que fallan validaciones."""
        filters = []
        
        # Validación de emails
        for col, info in self.validation_results.get('email_validation', {}).items():
            if info['is_problematic'] and info['invalid_count'] > 0:
                invalid_percent = (info['invalid_count'] / (info['valid_count'] + info['invalid_count'])) * 100
                filters.append({
                    'column': col,
                    'type': 'EMAIL_VALIDATION',
                    'severity': 'GRAVE' if invalid_percent > 10 else 'AVISO',
                    'problem': f'{info["invalid_count"]} emails inválidos ({invalid_percent:.1f}%)',
                    'filter_sql': f"""WHERE {col} LIKE '%@%' AND {col} LIKE '%.%' AND POSITION('@' IN {col}) > 1""",
                    'filter_sql_advanced': f"""WHERE {col} ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Z|a-z]{{2,}}$'""",
                    'description': f'Filtra emails válidos en "{col}"',
                    'impact': f'Elimina {invalid_percent:.1f}% de los registros'
                })
        
        # Validación de teléfonos
        for col, info in self.validation_results.get('phone_validation', {}).items():
            if info['is_problematic'] and info['invalid_count'] > 0:
                invalid_percent = (info['invalid_count'] / (info['valid_count'] + info['invalid_count'])) * 100
                filters.append({
                    'column': col,
                    'type': 'PHONE_VALIDATION',
                    'severity': 'GRAVE' if invalid_percent > 10 else 'AVISO',
                    'problem': f'{info["invalid_count"]} teléfonos inválidos ({invalid_percent:.1f}%)',
                    'filter_sql': f"""WHERE LENGTH(REGEXP_REPLACE({col}, '[^0-9]', '')) >= 7""",
                    'filter_sql_simple': f"""WHERE {col} LIKE '[0-9]%' AND LENGTH({col}) >= 7""",
                    'description': f'Filtra teléfonos válidos en "{col}" (mínimo 7 dígitos)',
                    'impact': f'Elimina {invalid_percent:.1f}% de los registros'
                })
        
        return filters
    
    def _generate_cleanup_filters(self):
        """Genera filtros para limpiar datos."""
        filters = []
        
        # Espacios en blanco
        for col, info in self.profile['empty_strings']['columns_with_empty'].items():
            if info['count'] > 0:
                empty_percent = info['percent']
                
                filters.append({
                    'column': col,
                    'type': 'WHITESPACE_CLEANUP',
                    'severity': 'AVISO',
                    'problem': f'{info["count"]} cadenas vacías o solo espacios ({empty_percent:.1f}%)',
                    'filter_sql': f"""WHERE TRIM({col}) IS NOT NULL AND TRIM({col}) != ''""",
                    'cleanup_sql': f"""UPDATE tabla SET {col} = TRIM({col}) WHERE {col} IS NOT NULL""",
                    'description': f'Elimina o limpia espacios en blanco en "{col}"',
                    'impact': f'Afecta {empty_percent:.1f}% de los registros'
                })
        
        # Caracteres especiales problemáticos
        for col in self.profile['general_info']['column_names'][:10]:
            col_data = self.df[col].astype(str)
            special_char_count = col_data.str.contains(r'[<>{}"\|\\^`~]', regex=True, na=False).sum()
            
            if special_char_count > 0:
                special_percent = (special_char_count / len(col_data)) * 100
                
                if special_percent > 0.5:  # Solo si afecta > 0.5%
                    filters.append({
                        'column': col,
                        'type': 'SPECIAL_CHARS_CLEANUP',
                        'severity': 'AVISO',
                        'problem': f'{special_char_count} registros con caracteres especiales ({special_percent:.2f}%)',
                        'filter_sql': f"""WHERE {col} NOT LIKE '%[<>{{}}"|\\^`~]%'""",
                        'cleanup_sql': f"""UPDATE tabla SET {col} = REGEXP_REPLACE({col}, '[<>{{}}"|\\\\^`~]', '') """,
                        'description': f'Elimina caracteres especiales en "{col}"',
                        'impact': f'Afecta {special_percent:.2f}% de los registros'
                    })
        
        return filters
    
    def _generate_quality_filters(self):
        """Genera filtros de calidad de datos general."""
        filters = []
        
        total_rows = self.profile['general_info']['total_rows']
        complete_rows = self.profile['null_analysis']['complete_rows']
        complete_percent = self.profile['null_analysis']['complete_rows_percent']
        
        # Filtro para filas completas
        filters.append({
            'type': 'COMPLETE_ROWS',
            'severity': 'GRAVE' if complete_percent < 50 else 'AVISO',
            'problem': f'Solo {complete_percent:.1f}% de filas están completas (sin nulos)',
            'filter_sql': 'WHERE ' + ' IS NOT NULL AND '.join([f'"{col}"' for col in self.profile['general_info']['column_names']]) + ' IS NOT NULL',
            'description': 'Filtra únicamente las filas sin ningún valor nulo',
            'impact': f'Mantiene solo {complete_percent:.1f}% del dataset ({complete_rows} de {total_rows} filas)',
            'columns_affected': 'Todas'
        })
        
        # Filtro conservador (filas usables)
        problematic_null_cols = self.profile['null_analysis']['problematic_columns']
        if problematic_null_cols:
            cols_to_check = ', '.join([f'"{col}"' for col in problematic_null_cols.keys()])
            filters.append({
                'type': 'EXCLUDE_PROBLEM_COLUMNS',
                'severity': 'AVISO',
                'problem': f'Excluir columnas problemáticas: {cols_to_check}',
                'filter_sql': 'SELECT * EXCEPT (' + ', '.join([f'"{col}"' for col in problematic_null_cols.keys()]) + ') FROM tabla',
                'description': 'Elimina columnas con demasiados nulos del análisis',
                'impact': f'Reduce a {len(self.profile["general_info"]["column_names"]) - len(problematic_null_cols)} columnas utilizables',
                'columns_affected': problematic_null_cols.keys()
            })
        
        return filters
    
    def get_summary_suggestions(self):
        """
        Retorna un resumen de sugerencias para mostrar rápidamente.
        
        Returns:
            list: Lista de sugerencias más críticas
        """
        all_suggestions = self.generate_all_suggestions()
        
        summary = []
        
        # Agregar una sugerencia crítica por categoría
        for category, suggestions_list in all_suggestions.items():
            if suggestions_list:
                # Ordenar por severidad
                sorted_sugg = sorted(
                    suggestions_list,
                    key=lambda x: {'CRÍTICO': 0, 'GRAVE': 1, 'AVISO': 2}.get(x.get('severity', 'AVISO'), 2)
                )
                if sorted_sugg:
                    summary.append(sorted_sugg[0])
        
        return summary
