"""
Módulo para generar código SQL completo de limpieza y carga de datos a base de datos.
Genera scripts SQL listos para insertar datos limpios en una nueva tabla.
"""

from datetime import datetime
from utils.helpers import StringHelper

# Nueva importación de Jinja2 para motor de plantillas
from jinja2 import Environment, BaseLoader

# Importamos configuración de dialectos SQL y dialecto predeterminado
from config import SQL_DIALECTS, DEFAULT_SQL_DIALECT


class DatabaseCodeGenerator:
    """
    Generador de código para scripts SQL y Python relacionados con la limpieza de datos.

    A partir de un DataFrame y su perfil, este generador produce un script SQL
    completo que crea una tabla limpia, una tabla de cuarentena, transforma los
    datos de forma segura utilizando funciones específicas del dialecto SQL y
    separa los registros válidos de los erróneos. Además, mantiene métodos
    auxiliares para generar código Python y configuraciones YAML compatibles
    con versiones anteriores.
    """

    def __init__(
        self,
        df,
        profile,
        validation_results,
        table_name: str = 'datos_limpios',
        dialect: str | None = None,
        source_table: str = 'source_table'
    ) -> None:
        """
        Inicializa el generador de código SQL.

        Args:
            df (pd.DataFrame): DataFrame con los datos analizados.
            profile (dict): Perfil obtenido mediante `DataProfiler`.
            validation_results (dict): Resultados de validaciones (emails, teléfonos, etc.).
            table_name (str): Nombre de la tabla limpia que se creará.
            dialect (str, opcional): Dialecto SQL a utilizar. Si no se especifica
                se tomará el valor de `DEFAULT_SQL_DIALECT` definido en `config.py`.
            source_table (str): Nombre de la tabla origen desde la cual se leerán
                los datos en el script SQL. Por defecto `source_table`.
        """
        self.df = df
        self.profile = profile
        self.validation_results = validation_results
        self.table_name = table_name
        # Determina el dialecto a usar para la generación SQL
        self.dialect_name = dialect or DEFAULT_SQL_DIALECT
        self.dialect_config = SQL_DIALECTS.get(self.dialect_name, SQL_DIALECTS[DEFAULT_SQL_DIALECT])
        self.source_table = source_table

        # Instancia un entorno Jinja2. BaseLoader permite cargar plantillas desde cadenas.
        self.jinja_env = Environment(loader=BaseLoader(), autoescape=False, trim_blocks=True, lstrip_blocks=True)
    
    # ----------------------------------------------------------------------
    # MÉTODOS PÚBLICOS
    # ----------------------------------------------------------------------
    def generate_complete_script(self, dialect: str | None = None) -> str:
        """
        Genera un script SQL completo usando plantillas Jinja2 y soporte para
        múltiples dialectos.

        Este método sustituye al enfoque previo basado en concatenación de
        cadenas. Toma en cuenta el dialecto seleccionado para adaptar las
        funciones de cast, parseo de fechas y tipos de datos. Si se pasa un
        dialecto distinto del definido en la inicialización, se usa ese valor
        únicamente para esta generación.

        Args:
            dialect (str, opcional): Dialecto específico para esta llamada.

        Returns:
            str: El script SQL completo listo para ejecutar.
        """
        # Permite sobreescribir el dialecto de instancia en la llamada
        if dialect:
            dialect_conf = SQL_DIALECTS.get(dialect, self.dialect_config)
        else:
            dialect_conf = self.dialect_config

        # Construye la lista de metadatos por columna
        columns_meta = self._build_columns_meta(dialect_conf)

        # Contexto para la plantilla
        context = {
            'now': datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
            'table_name': self.table_name,
            # Tabla de cuarentena fija, según especificación
            'quarantine_table': 'datos_cuarentena',
            'source_table': self.source_table,
            'columns': columns_meta,
            'primary_keys': self._get_primary_keys(),
            'dialect': dialect_conf,
        }

        # Renderiza y devuelve el script completo
        template = self.jinja_env.from_string(self._sql_template())
        return template.render(context)
    
    # ----------------------------------------------------------------------
    # MÉTODOS PRIVADOS DE APOYO
    # ----------------------------------------------------------------------
    def _sql_template(self) -> str:
        """
        Devuelve la plantilla Jinja2 que define el script SQL completo.

        La plantilla se estructura en las siguientes secciones:
        - Creación de la tabla limpia (`CREATE TABLE`)
        - Creación de la tabla de cuarentena
        - CTE `cleaned_data` para realizar cast y validación de columnas
        - Inserción en la tabla limpia
        - Inserción en la tabla de cuarentena para filas erróneas
        - Consultas de validación básicas al final

        Variables del contexto:
            now: fecha y hora actual
            table_name: nombre de la tabla limpia
            quarantine_table: nombre de la tabla de cuarentena
            source_table: tabla origen de los datos
            columns: lista de metadatos de cada columna (sql_type, clean_expr, flag_expr, error_category, original_expr)
            primary_keys: lista de columnas que serán clave primaria
            dialect: configuración específica del dialecto SQL
        """
        return """
-- Script generado el {{ now }}

-- ============================================================================
-- 1. Creación de tablas
-- ============================================================================
-- Tabla limpia principal
CREATE TABLE IF NOT EXISTS {{ table_name }} (
{%- for col in columns %}
    {{ col.name }} {{ col.sql_type }}{%- if not loop.last %},{% endif %}
{%- endfor %}
{%- if primary_keys %},
    PRIMARY KEY ({{ primary_keys | join(', ') }})
{%- endif %}
);

-- Tabla de cuarentena para almacenar registros rechazados
CREATE TABLE IF NOT EXISTS {{ quarantine_table }} (
    id BIGINT PRIMARY KEY,
    fecha_rechazo TIMESTAMP,
    columna_erronea TEXT,
    categoria_error TEXT,
    valor_original TEXT,
    fila_completa_json TEXT
);

-- ============================================================================
-- 2. CTE: Limpieza y validación de datos
-- ============================================================================
WITH cleaned_data AS (
    SELECT
{%- for col in columns %}
        {{ col.clean_expr }} AS {{ col.name }}_value,
        {{ col.flag_expr }} AS {{ col.name }}_ok{%- if not loop.last %},{% endif %}
{%- endfor %}
    FROM {{ source_table }}
)

-- ============================================================================
-- 3. Inserción de datos válidos
-- ============================================================================
INSERT INTO {{ table_name }} ({{ columns | map(attribute='name') | join(', ') }})
SELECT
{%- for col in columns %}
    {{ col.name }}_value{%- if not loop.last %},{% endif %}
{%- endfor %}
FROM cleaned_data
WHERE
{%- for col in columns %}
    {{ col.name }}_ok{%- if not loop.last %} AND{% endif %}
{%- endfor %}
;

-- ============================================================================
-- 4. Inserción de datos en cuarentena
-- ============================================================================
{%- for col in columns %}
INSERT INTO {{ quarantine_table }} (id, fecha_rechazo, columna_erronea, categoria_error, valor_original, fila_completa_json)
SELECT
    ROW_NUMBER() OVER () AS id,
    CURRENT_TIMESTAMP,
    '{{ col.name }}',
    '{{ col.error_category }}',
    {{ col.original_expr }},
    {{ dialect.json_func }}({{ source_table }})
FROM cleaned_data
WHERE NOT {{ col.name }}_ok;

{%- endfor %}
-- ============================================================================
-- 5. Consultas de validación
-- ============================================================================
-- Verificar cantidad de registros cargados
SELECT COUNT(*) AS registros_cargados FROM {{ table_name }};

-- Verificar nulos por columna en tabla limpia
SELECT
    'Análisis de Nulos' AS verificacion,
{%- for col in columns %}
    SUM(CASE WHEN {{ col.name }} IS NULL THEN 1 ELSE 0 END) AS {{ col.name }}{%- if not loop.last %},{% endif %}
{%- endfor %}
FROM {{ table_name }};

-- Verificar duplicados según primeras columnas
SELECT
    {{ columns[:3] | map(attribute='name') | join(', ') }},
    COUNT(*) AS count_duplicates
FROM {{ table_name }}
GROUP BY {{ columns[:3] | map(attribute='name') | join(', ') }}
HAVING COUNT(*) > 1;
"""

    def _build_columns_meta(self, dialect_conf: dict) -> list:
        """
        Construye metadatos para cada columna que serán usados en la plantilla SQL.

        Para cada columna se calcula:
        - sql_type: tipo de dato SQL inferido inteligentemente.
        - clean_expr: expresión para castear y limpiar el valor de la columna.
        - flag_expr: expresión que evalúa a TRUE si el valor es válido, FALSE si no.
        - error_category: categoría de error cuando el valor es inválido.
        - original_expr: expresión que representa el valor original (para cuarentena).

        Args:
            dialect_conf (dict): Configuración del dialecto seleccionado.

        Returns:
            list[dict]: Lista de diccionarios con metadatos por columna.
        """
        columns_meta: list[dict] = []
        for col in self.profile['general_info']['column_names']:
            profile_col = self.profile['column_profiles'].get(col, {})
            # Inferir tipo SQL inteligente
            sql_type = self._infer_sql_type(col, profile_col, dialect_conf)
            # Construir expresiones de limpieza y flag según el tipo
            clean_expr, flag_expr, error_category = self._build_clean_and_flag_expr(
                col, profile_col, sql_type, dialect_conf
            )
            # Valor original sin transformación
            original_expr = f"{col}"
            columns_meta.append({
                'name': col,
                'sql_type': sql_type,
                'clean_expr': clean_expr,
                'flag_expr': flag_expr,
                'error_category': error_category,
                'original_expr': original_expr
            })
        return columns_meta

    def _infer_sql_type(self, col: str, profile_col: dict, dialect_conf: dict) -> str:
        """
        Infere el tipo SQL óptimo para una columna basándose en el perfil y
        ajustándolo al dialecto seleccionado.

        Para columnas numéricas se determina la precisión y escala a partir
        de los datos presentes en el DataFrame. Si la columna es entera,
        se utiliza el tipo entero específico del dialecto; si es decimal,
        se calcula la cantidad de dígitos antes y después del punto decimal
        para definir un DECIMAL o equivalente.

        Args:
            col (str): Nombre de la columna.
            profile_col (dict): Perfil de la columna con hints y dtype.
            dialect_conf (dict): Configuración del dialecto.

        Returns:
            str: Tipo SQL con la forma adecuada (ej. NUMERIC(10,2)).
        """
        dtype = profile_col.get('dtype', 'object')
        type_hint = profile_col.get('type_hint', 'Text')

        # Boolean
        if type_hint == 'Boolean' or dtype == 'bool':
            return dialect_conf['boolean_type']

        # Fecha / Date
        if type_hint in ['Date', 'DateTime']:
            # Para las fechas se usa DATE o TIMESTAMP según sea necesario
            return 'DATE' if type_hint == 'Date' else 'TIMESTAMP'

        # Email, Phone, URL se tratan como texto largo
        if type_hint in ['Email', 'Phone', 'URL']:
            return dialect_conf['text_type']

        # Números: determinar si es int o decimal
        if type_hint in ['Integer', 'Float'] or dtype.startswith(('int', 'float')):
            series = self.df[col]
            # Si hay valores decimales
            if type_hint == 'Float' or 'float' in dtype:
                precision, scale = self._compute_numeric_precision_scale(series)
                base_type = dialect_conf.get('numeric_type', 'NUMERIC')
                return f"{base_type}({precision},{scale})"
            else:
                # Entero
                max_digits = self._compute_integer_digits(series)
                # Muchos motores aceptan diferentes tamaños; por simplicidad usamos int_type
                return dialect_conf.get('int_type', 'INT')

        # Texto genérico
        return dialect_conf['text_type']

    def _compute_numeric_precision_scale(self, series) -> tuple[int, int]:
        """
        Calcula la precisión total y la escala (número de decimales) de una serie
        numérica. La precisión total es el máximo número de dígitos contando
        enteros y decimales; la escala es la máxima cantidad de dígitos a la
        derecha del punto decimal.

        Args:
            series (pd.Series): Serie numérica.

        Returns:
            (int, int): Tupla de (precision, scale)
        """
        import pandas as pd
        s = pd.to_numeric(series, errors='coerce')
        s = s.dropna()
        max_int_digits = 1
        max_decimal_digits = 0
        for val in s:
            try:
                string_val = str(val)
                if 'e' in string_val or 'E' in string_val:
                    # Representación científica: convertir a decimal
                    from decimal import Decimal
                    string_val = format(Decimal(string_val), 'f')
                if '.' in string_val:
                    int_part, frac_part = string_val.split('.')
                    max_int_digits = max(max_int_digits, len(int_part.replace('-', '')))
                    max_decimal_digits = max(max_decimal_digits, len(frac_part.rstrip('0')))
                else:
                    max_int_digits = max(max_int_digits, len(string_val.replace('-', '')))
            except Exception:
                continue
        precision = max_int_digits + (max_decimal_digits if max_decimal_digits > 0 else 0)
        scale = max_decimal_digits
        # Asegurar al menos 1 dígito de escala para floats
        if scale == 0 and any('.' in str(v) for v in s.astype(str)):
            scale = 2
            precision = max_int_digits + scale
        return precision, scale

    def _compute_integer_digits(self, series) -> int:
        """
        Calcula el máximo número de dígitos de una serie de enteros.

        Args:
            series (pd.Series): Serie numérica entera.

        Returns:
            int: Número máximo de dígitos.
        """
        import pandas as pd
        s = pd.to_numeric(series, errors='coerce').dropna()
        max_digits = 1
        for val in s:
            try:
                digits = len(str(int(abs(val))))
                if digits > max_digits:
                    max_digits = digits
            except Exception:
                continue
        return max_digits

    def _build_clean_and_flag_expr(
        self, col: str, profile_col: dict, sql_type: str, dialect_conf: dict
    ) -> tuple[str, str, str]:
        """
        Construye las expresiones de limpieza y validación para una columna.

        Devuelve tanto la expresión de limpieza (`clean_expr`) como la expresión
        booleana que indica si el valor es válido (`flag_expr`). También se
        determina la categoría de error para la tabla de cuarentena.

        Args:
            col (str): Nombre de la columna.
            profile_col (dict): Perfil de la columna.
            sql_type (str): Tipo SQL inferido para la columna.
            dialect_conf (dict): Configuración del dialecto.

        Returns:
            (clean_expr, flag_expr, error_category)
        """
        type_hint = profile_col.get('type_hint', 'Text')
        try_cast = dialect_conf.get('try_cast', 'CAST')

        # Expresión de limpieza base: quita espacios
        trimmed = f"TRIM({col})"

        # Caso Fecha / Date
        if type_hint in ['Date', 'DateTime']:
            # Selecciona la función de parseo según dialecto. Por defecto: YYYY-MM-DD
            date_format = '%Y-%m-%d' if type_hint == 'Date' else '%Y-%m-%d %H:%M:%S'
            parse_expr_template = dialect_conf.get('date_parse')
            if parse_expr_template:
                parse_expr = parse_expr_template.replace('{expr}', trimmed).replace('{format}', date_format)
            else:
                parse_expr = f"{trimmed}"
            clean_expr = parse_expr
            flag_expr = f"({parse_expr}) IS NOT NULL"
            error_category = 'FORMATO_FECHA_INVALIDO'
            return clean_expr, flag_expr, error_category

        # Caso Email / Phone / URL: solo limpiar y castear a texto
        if type_hint in ['Email', 'Phone', 'URL']:
            clean_expr = trimmed
            flag_expr = 'TRUE'
            error_category = 'FORMATO_INVALIDO'
            return clean_expr, flag_expr, error_category

        # Caso Boolean
        if type_hint == 'Boolean' or profile_col.get('dtype') == 'bool':
            # Para booleanos, se intenta castear usando try_cast
            if try_cast.upper() != 'CAST':
                clean_expr = f"{try_cast}({trimmed} AS {sql_type})"
            else:
                clean_expr = f"CAST({trimmed} AS {sql_type})"
            flag_expr = f"({clean_expr}) IS NOT NULL"
            error_category = 'TIPO_DATO_BOOLEANO'
            return clean_expr, flag_expr, error_category

        # Caso numérico (entero o decimal)
        if type_hint in ['Integer', 'Float'] or profile_col.get('dtype', '').startswith(('int', 'float')):
            if try_cast.upper() != 'CAST':
                clean_expr = f"{try_cast}({trimmed} AS {sql_type})"
            else:
                clean_expr = f"CAST({trimmed} AS {sql_type})"
            flag_expr = f"({clean_expr}) IS NOT NULL"
            error_category = 'TIPO_DATO_NUMERICO'
            return clean_expr, flag_expr, error_category

        # Caso texto u otro tipo: no requiere cast
        clean_expr = trimmed
        flag_expr = 'TRUE'
        error_category = 'VALOR_INVALIDO'
        return clean_expr, flag_expr, error_category

    def _get_primary_keys(self) -> list[str]:
        """
        Obtiene las columnas que pueden funcionar como clave primaria.

        Se consideran columnas cuyo nombre contiene 'id' o 'codigo'.

        Returns:
            list[str]: Lista de nombres de columnas candidatas a clave primaria.
        """
        candidates = [
            col for col in self.profile['general_info']['column_names']
            if 'id' in col.lower() or 'codigo' in col.lower()
        ]
        return candidates
    
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
