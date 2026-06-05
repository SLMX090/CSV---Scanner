"""
Configuración global de la aplicación.
Define constantes, límites y configuraciones para la plataforma de análisis CSV.
"""

# Configuración de carga de archivos
MAX_FILE_SIZE_MB = 1024  # Tamaño máximo del archivo en MB (1GB)
SUPPORTED_ENCODINGS = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-16']
COMMON_DELIMITERS = [',', ';', '\t', '|', ':']

# Configuración de carga por chunks (para archivos grandes)
CHUNKED_LOAD_THRESHOLD_MB = 100  # Archivos > 100MB se cargan por chunks
CHUNK_SIZE_ROWS = 50000  # Número de filas por chunk
MAX_CHUNKS_TO_ANALYZE = 10  # Máximo número de chunks a analizar para perfilado
ENABLE_CHUNKED_LOADING = True  # Activar carga por chunks automáticamente

# Modo de carga de CSV: 'strict' (detiene si hay errores) o 'permissive' (omite líneas malas con aviso)
CSV_LOAD_MODE = 'permissive'  # Cambiar a 'strict' para modo estricto
BAD_LINES_THRESHOLD_WARNING = 10  # Número de líneas malas para mostrar advertencia

# Umbrales para detección de problemas
NULL_THRESHOLD_PERCENT = 40  # % mínimo de nulos para marcar como problemático
UNIQUE_VALUES_THRESHOLD = 0.8  # Proporción de valores únicos para marcar como problemático
CARDINALITY_WARNING_PERCENT = 95  # % de valores únicos que generan advertencia

# Umbral para detección de contenido (análisis de tipo de dato basado en contenido)
CONTENT_DETECTION_THRESHOLD = 0.70  # Si >= 70% de valores en una columna son del tipo X, validar como tipo X
SAMPLE_SIZE_FOR_CONTENT_DETECTION = 100  # Máximo de valores a analizar para detección de contenido

# Configuración de validaciones
MIN_PASSWORD_LENGTH = 8
PHONE_MIN_LENGTH = 7
PHONE_MAX_LENGTH = 15

# Patrones de validación
EMAIL_PATTERN = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
PHONE_PATTERN = r'^\+?[1-9]\d{1,14}$|^[\d\s\-\(\)\.]{7,}$'
URL_PATTERN = r'^https?://[^\s/$.?#].[^\s]*$'

# Configuración de reportes
REPORT_OUTPUT_PATH = './output/'
REPORT_DATE_FORMAT = '%d/%m/%Y %H:%M:%S'

# Configuración de columnas especiales
DATETIME_KEYWORDS = ['fecha', 'date', 'time', 'hora', 'timestamp', 'created', 'updated', 'born']
EMAIL_KEYWORDS = ['email', 'correo', 'mail']
PHONE_KEYWORDS = ['telefono', 'phone', 'celular', 'mobile', 'whatsapp']
URL_KEYWORDS = ['url', 'website', 'web', 'link']
ID_KEYWORDS = ['id', 'codigo', 'code', 'identificador']

# ============================================================
# Configuración SQL v3.2: dialectos soportados
# ============================================================

DEFAULT_SQL_DIALECT = 'PostgreSQL'

SQL_DIALECTS = {
    'PostgreSQL': {
        'name': 'postgresql',
        'int_type': 'INTEGER',
        'numeric_type': 'NUMERIC',
        'float_type': 'NUMERIC',
        'boolean_type': 'BOOLEAN',
        'text_type': 'TEXT',
        'date_parse': "TO_DATE({expr}, '{format}')",
        'datetime_parse': "TO_TIMESTAMP({expr}, '{format}')",
        'try_cast': 'CAST',
        'json_func': 'to_json'
    },

    'MySQL': {
        'name': 'mysql',
        'int_type': 'INT',
        'numeric_type': 'DECIMAL',
        'float_type': 'DECIMAL',
        'boolean_type': 'BOOLEAN',
        'text_type': 'TEXT',
        'date_parse': "STR_TO_DATE({expr}, '{format}')",
        'datetime_parse': "STR_TO_DATE({expr}, '{format}')",
        'try_cast': 'CAST',
        'json_func': 'JSON_OBJECT'
    },

    'Snowflake': {
        'name': 'snowflake',
        'int_type': 'INT',
        'numeric_type': 'NUMBER',
        'float_type': 'FLOAT',
        'boolean_type': 'BOOLEAN',
        'text_type': 'VARCHAR',
        'date_parse': "TRY_TO_DATE({expr}, '{format}')",
        'datetime_parse': "TRY_TO_TIMESTAMP({expr}, '{format}')",
        'try_cast': 'TRY_CAST',
        'json_func': 'TO_JSON'
    },

    'BigQuery': {
        'name': 'bigquery',
        'int_type': 'INT64',
        'numeric_type': 'NUMERIC',
        'float_type': 'FLOAT64',
        'boolean_type': 'BOOL',
        'text_type': 'STRING',
        'date_parse': "PARSE_DATE('{format}', {expr})",
        'datetime_parse': "PARSE_TIMESTAMP('{format}', {expr})",
        'try_cast': 'SAFE_CAST',
        'json_func': 'TO_JSON_STRING'
    }
}

# Configuración de validación de fechas
ALLOWED_DATE_FORMATS = [
    '%Y-%m-%d',           # ISO 8601: 2024-01-15
    '%d/%m/%Y',           # Europeo: 15/01/2024
    '%m/%d/%Y',           # Estadounidense: 01/15/2024
    '%d-%m-%Y',           # Alternativo: 15-01-2024
    '%Y/%m/%d',           # Alternativo: 2024/01/15
    '%d.%m.%Y',           # Puntos: 15.01.2024
    '%Y%m%d',             # Compacto: 20240115
    '%d %b %Y',           # Mes abreviado: 15 Jan 2024
    '%d %B %Y',           # Mes completo: 15 January 2024
    '%b %d, %Y',          # US: Jan 15, 2024
    '%B %d, %Y',          # US: January 15, 2024
]
DEFAULT_DAYFIRST = True  # Interpreta 01/02/03 como día/mes/año (no mes/día/año)
DATE_FORMAT_CONSISTENCY_THRESHOLD = 0.95  # Proporción (0.0-1.0) de fechas que deben coincidir con el mismo formato
