"""
Módulo para generar código SQL completo de limpieza y carga de datos a base de datos.
Genera scripts SQL listos para insertar datos limpios en una nueva tabla.
"""

from datetime import datetime
from utils.helpers import StringHelper


class DatabaseCodeGenerator:
    """Genera código SQL para limpiar, transformar y cargar datos a BD."""
    
    def __init__(self, df, profile, validation_results, table_name='datos_limpios'):
        """
        Inicializa el generador de código SQL.
        
        Args:
            df (pd.DataFrame): DataFrame con datos
            profile (dict): Perfil del DataFrame
            validation_results (dict): Resultados de validaciones
            table_name (str): Nombre de la tabla en BD
        """
        self.df = df
        self.profile = profile
        self.validation_results = validation_results
        self.table_name = table_name
    
    def generate_complete_script(self):
        """
        Genera un script SQL completo y listo para usar.
        
        Returns:
            str: Script SQL completo
        """
        sections = []
        
        # 1. Tabla limpia temporal
        sections.append(self._generate_create_table_statement())
        sections.append('')
        
        # 2. CTE para limpiar datos
        sections.append(self._generate_data_cleaning_cte())
        sections.append('')
        
        # 3. Insert con todas las transformaciones
        sections.append(self._generate_insert_statement())
        sections.append('')
        
        # 4. Validaciones finales
        sections.append(self._generate_validation_queries())
        
        return '\n'.join(sections)
    
    def _generate_create_table_statement(self):
        """Genera statement CREATE TABLE con tipos de datos sugeridos."""
        lines = [
            f"-- Crear tabla limpia para {self.table_name}",
            f"-- Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            f"CREATE TABLE IF NOT EXISTS {self.table_name} (",
        ]
        
        column_defs = []
        for col, profile_col in self.profile['column_profiles'].items():
            dtype = self._get_sql_type(profile_col)
            constraints = self._get_constraints(col)
            
            line = f"  {col} {dtype}"
            if constraints:
                line += f" {constraints}"
            column_defs.append(line + ",")
        
        # Remove trailing comma from last column
        if column_defs:
            column_defs[-1] = column_defs[-1].rstrip(',') + ','
        
        lines.extend(column_defs)
        
        # Primary key
        id_cols = [c for c in self.profile['general_info']['column_names'] 
                   if 'id' in c.lower() or 'codigo' in c.lower()]
        if id_cols:
            lines.append(f"  PRIMARY KEY ({', '.join(id_cols)})")
        else:
            lines[-1] = lines[-1].rstrip(',')
        
        lines.append(");")
        lines.append('')
        
        return '\n'.join(lines)
    
    def _get_sql_type(self, profile_col):
        """Determina el tipo SQL adecuado basado en el perfil."""
        type_hint = profile_col.get('type_hint', 'TEXT')
        dtype = profile_col.get('dtype', 'object')
        
        # Mapeo de tipos
        type_mapping = {
            'Integer': 'INT',
            'Float': 'DECIMAL(15,2)',
            'Date': 'DATE',
            'DateTime': 'TIMESTAMP',
            'Email': 'VARCHAR(255)',
            'Phone': 'VARCHAR(20)',
            'URL': 'TEXT',
            'Boolean': 'BOOLEAN',
            'Text': 'VARCHAR(255)',
        }
        
        return type_mapping.get(type_hint, 
                               type_mapping.get(dtype, 'VARCHAR(255)'))
    
    def _get_constraints(self, col):
        """Determina constraints SQL para una columna."""
        constraints = []
        null_info = self.profile['null_analysis']['by_column'].get(col, {})
        
        # NOT NULL si nunca tiene nulos
        if null_info.get('percent', 0) == 0 and null_info.get('count', 0) > 0:
            constraints.append('NOT NULL')
        
        # UNIQUE si tiene cardinalidad alta
        col_profile = self.profile['column_profiles'].get(col, {})
        if col_profile.get('cardinality_ratio', 0) >= 0.95:
            constraints.append('UNIQUE')
        
        # DEFAULT para timestamps
        if 'fecha' in col.lower() or 'date' in col.lower():
            constraints.append('DEFAULT CURRENT_TIMESTAMP')
        
        return ' '.join(constraints)
    
    def _generate_data_cleaning_cte(self):
        """Genera CTE con transformaciones de limpieza de datos."""
        col_transforms = []
        
        for col in self.profile['general_info']['column_names'][:20]:  # Primeras 20
            profile_col = self.profile['column_profiles'].get(col, {})
            type_hint = profile_col.get('type_hint', 'Text')
            
            # Limpieza básica
            transform = f"TRIM({col}) AS {col}_clean"
            
            # Transformaciones específicas por tipo
            if type_hint == 'Integer':
                transform = f"TRY_CAST(TRIM({col}) AS INT) AS {col}_clean"
            elif type_hint == 'Float':
                transform = f"TRY_CAST(REGEXP_REPLACE(TRIM({col}), '[^0-9,.]', '') AS DECIMAL) AS {col}_clean"
            elif type_hint == 'Date':
                transform = f"TRY_CAST(TRIM({col}) AS DATE) AS {col}_clean"
            elif type_hint == 'Email':
                transform = f"LOWER(TRIM({col})) AS {col}_clean"
            
            col_transforms.append(f"  {transform}")
        
        script = [
            "-- CTE para limpiar y transformar datos",
            "WITH cleaned_data AS (",
            "  SELECT",
        ]
        
        # Agregar transformaciones
        script.extend(col_transforms[:-1])
        script.append(col_transforms[-1].rstrip(',') if col_transforms else "")
        
        script.append("  FROM source_table")
        script.append("  WHERE 1=1")
        
        # Filtros automáticos
        script.extend(self._generate_where_filters())
        
        script.append(")")
        
        return '\n'.join(script)
    
    def _generate_where_filters(self):
        """Genera clausulas WHERE para filtrar filas problemáticas."""
        filters = []
        
        # Eliminar nulos en columnas críticas
        critical_cols = [col for col, info in self.profile['null_analysis']['by_column'].items()
                        if info.get('percent', 0) == 0]
        if critical_cols:
            filters.append(f"  AND {' IS NOT NULL AND '.join(critical_cols)} IS NOT NULL")
        
        # Filtrar emails válidos si existen
        for col, info in self.validation_results.get('email_validation', {}).items():
            if info.get('is_problematic'):
                filters.append(f"  AND ({col} LIKE '%@%' OR {col} IS NULL)")
        
        # Filtrar teléfonos válidos
        for col, info in self.validation_results.get('phone_validation', {}).items():
            if info.get('is_problematic'):
                filters.append(f"  AND (LENGTH({col}) >= 7 OR {col} IS NULL)")
        
        return filters
    
    def _generate_insert_statement(self):
        """Genera statement INSERT con todas las transformaciones."""
        cols = self.profile['general_info']['column_names'][:20]
        clean_cols = [f"{col}_clean" for col in cols]
        
        # Renombrar back a original
        select_cols = [f"{col}_clean AS {col}" for col in cols]
        
        script = [
            f"-- Insertar datos limpios en {self.table_name}",
            f"INSERT INTO {self.table_name} ({', '.join(cols)})",
            "SELECT",
            "  " + (',\n  '.join(select_cols)),
            "FROM cleaned_data",
            "WHERE 1=1",
        ]
        
        # Agregar deduplicación si hay duplicados
        if self.profile['duplicates']['total_duplicates'] > 0:
            script.append("  -- Evitar duplicados")
            script.append(f"  AND ROW_NUMBER() OVER (PARTITION BY {', '.join(cols[:3])} ORDER BY 1) = 1")
        
        script.append(";")
        
        return '\n'.join(script)
    
    def _generate_validation_queries(self):
        """Genera queries de validación para el resultado."""
        queries = [
            "-- Validaciones del resultado",
            f"-- Verificar registros cargados",
            f"SELECT COUNT(*) as registros_cargados FROM {self.table_name};",
            "",
            f"-- Verificar nulos por columna",
            f"SELECT",
            f"  'Análisis de Nulos' as verificacion,",
        ]
        
        cols = self.profile['general_info']['column_names'][:10]
        null_checks = [f"  SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) as {col}" 
                       for col in cols]
        
        queries.extend(null_checks[:-1])
        if null_checks:
            queries.append(null_checks[-1] + ",")
        queries.append(f"FROM {self.table_name};")
        
        queries.extend([
            "",
            f"-- Verificar duplicados",
            f"SELECT",
            f"  {', '.join(cols[:3])},",
            f"  COUNT(*) as count_duplicates",
            f"FROM {self.table_name}",
            f"GROUP BY {', '.join(cols[:3])}",
            f"HAVING COUNT(*) > 1;",
        ])
        
        return '\n'.join(queries)
    
    def generate_python_cleanup_code(self):
        """Genera código Python para limpiar datos antes de BD."""
        script = [
            "# Código Python para limpiar datos antes de insertar en BD",
            "import pandas as pd",
            "import numpy as np",
            "from datetime import datetime",
            "",
            "def cleanup_data(df):",
            "    \"\"\"Limpia el DataFrame antes de insertar en BD.\"\"\"",
            "    df_clean = df.copy()",
            "",
        ]
        
        # Eliminar duplicados
        if self.profile['duplicates']['total_duplicates'] > 0:
            script.append("    # 1. Eliminar duplicados")
            script.append("    df_clean = df_clean.drop_duplicates(keep='first')")
            script.append("")
        
        # Eliminar nulos en columnas críticas
        critical_cols = [col for col, info in self.profile['null_analysis']['by_column'].items()
                        if info.get('percent', 0) == 0]
        if critical_cols:
            script.append("    # 2. Eliminar filas con nulos en columnas críticas")
            script.append(f"    df_clean = df_clean.dropna(subset={critical_cols})")
            script.append("")
        
        # Limpiar espacios
        script.append("    # 3. Limpiar espacios en blanco")
        for col in self.profile['general_info']['column_names'][:10]:
            script.append(f"    df_clean['{col}'] = df_clean['{col}'].str.strip() if df_clean['{col}'].dtype == 'object' else df_clean['{col}']")
        
        script.extend([
            "",
            "    # 4. Estandarizar tipos de datos",
        ])
        
        # Conversión de tipos
        for col, profile_col in list(self.profile['column_profiles'].items())[:10]:
            type_hint = profile_col.get('type_hint')
            if type_hint == 'Integer':
                script.append(f"    df_clean['{col}'] = pd.to_numeric(df_clean['{col}'], errors='coerce').astype('Int64')")
            elif type_hint == 'Float':
                script.append(f"    df_clean['{col}'] = pd.to_numeric(df_clean['{col}'], errors='coerce')")
            elif type_hint == 'Date':
                script.append(f"    df_clean['{col}'] = pd.to_datetime(df_clean['{col}'], errors='coerce')")
            elif type_hint == 'Email':
                script.append(f"    df_clean['{col}'] = df_clean['{col}'].str.lower()")
        
        script.extend([
            "",
            "    return df_clean",
            "",
            "# Uso:",
            "# df_cleaned = cleanup_data(df)",
            "# df_cleaned.to_sql('datos_limpios', con=engine, if_exists='append', index=False)",
        ])
        
        return '\n'.join(script)
    
    def generate_config_yaml(self):
        """Genera archivo YAML con configuración de validación personalizada."""
        yaml_config = [
            "# Configuración personalizada de validación de datos",
            f"# Generada: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            "",
            "database:",
            f"  table_name: {self.table_name}",
            "  charset: utf8mb4",
            "  collate: utf8mb4_unicode_ci",
            "",
            "columns:",
        ]
        
        for col, profile_col in list(self.profile['column_profiles'].items())[:20]:
            null_percent = self.profile['null_analysis']['by_column'].get(col, {}).get('percent', 0)
            
            yaml_config.extend([
                f"  {col}:",
                f"    type: {profile_col.get('type_hint', 'TEXT')}",
                f"    nullable: {null_percent > 0}",
                f"    unique: {profile_col.get('cardinality_ratio', 0) >= 0.95}",
            ])
            
            # Validaciones específicas
            validations = []
            if 'email' in col.lower():
                validations.append("email")
            if 'phone' in col.lower() or 'telefono' in col.lower():
                validations.append("phone")
            if 'fecha' in col.lower() or 'date' in col.lower():
                validations.append("date")
            
            if validations:
                yaml_config.append(f"    validations: [{', '.join(validations)}]")
            
            yaml_config.append("")
        
        yaml_config.extend([
            "cleaning:",
            "  trim_whitespace: true",
            "  remove_duplicates: true",
            "  handle_nulls: 'remove'  # opciones: remove, fill_default, keep",
            "  standardize_case: true",
            "",
            "validation_rules:",
            "  min_rows: 10",
            "  max_null_percent: 30",
            "  email_valid: true",
            "  phone_valid: true",
        ])
        
        return '\n'.join(yaml_config)
    
    def export_scripts(self, output_dir='./output'):
        """Exporta todos los scripts generados como archivos."""
        import os
        
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        files_created = {}
        
        # 1. SQL completo
        sql_file = f"{output_dir}/script_limpieza_{timestamp}.sql"
        with open(sql_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_complete_script())
        files_created['sql'] = sql_file
        
        # 2. Python
        py_file = f"{output_dir}/cleanup_data_{timestamp}.py"
        with open(py_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_python_cleanup_code())
        files_created['python'] = py_file
        
        # 3. YAML config
        yaml_file = f"{output_dir}/config_validacion_{timestamp}.yaml"
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write(self.generate_config_yaml())
        files_created['config'] = yaml_file
        
        return files_created
