"""
Configuración global de la aplicación.
Define constantes, límites y configuraciones para la plataforma de análisis CSV.
"""

# Configuración de carga de archivos
MAX_FILE_SIZE_MB = 50  # Tamaño máximo del archivo en MB
SUPPORTED_ENCODINGS = ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252', 'utf-16']
COMMON_DELIMITERS = [',', ';', '\t', '|', ':']

# Umbrales para detección de problemas
NULL_THRESHOLD_PERCENT = 40  # % mínimo de nulos para marcar como problemático
UNIQUE_VALUES_THRESHOLD = 0.8  # Proporción de valores únicos para marcar como problemático
CARDINALITY_WARNING_PERCENT = 95  # % de valores únicos que generan advertencia

# Configuración de validaciones
MIN_PASSWORD_LENGTH = 8
PHONE_MIN_LENGTH = 7
PHONE_MAX_LENGTH = 15

# Validaciones de rango numérico
COMMON_AGE_RANGE = (0, 120)
COMMON_YEAR_RANGE = (1900, 2100)

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
