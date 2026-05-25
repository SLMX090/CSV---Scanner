# Pruebas Automatizadas

Conjunto completo de pruebas unitarias para validar la funcionalidad del analizador de datos CSV.

## Estructura de Pruebas

```
tests/
├── __init__.py              # Inicializador del paquete
├── conftest.py              # Fixtures compartidas entre pruebas
├── test_csv_loader.py       # Pruebas para carga y procesamiento de CSV
├── test_validators.py       # Pruebas para validadores de datos
├── test_data_profiler.py    # Pruebas para perfilado de datos
└── test_patterns.py         # Pruebas para patrones y expresiones regulares
```

## Instalación de Dependencias

Para ejecutar las pruebas, instala pytest:

```bash
pip install pytest pytest-cov
```

O instala desde requirements.txt:

```bash
pip install -r requirements.txt
```

## Ejecutar Pruebas

### Ejecutar todas las pruebas

```bash
pytest
```

### Ejecutar con modo verbose

```bash
pytest -v
```

### Ejecutar un archivo específico de pruebas

```bash
pytest tests/test_csv_loader.py
```

### Ejecutar una clase específica de pruebas

```bash
pytest tests/test_validators.py::TestEmailValidation
```

### Ejecutar una prueba específica

```bash
pytest tests/test_validators.py::TestEmailValidation::test_validate_emails_by_name
```

### Ejecutar con cobertura de código

```bash
pytest --cov=modules --cov=utils --cov-report=html
```

Esto genera un reporte HTML en `htmlcov/index.html`

### Ejecutar pruebas rápidas (excluyendo pruebas lentas)

```bash
pytest -m "not slow"
```

## Cobertura de Pruebas

Las pruebas cubren:

### 1. **test_csv_loader.py** - Carga y Procesamiento de CSV
- ✅ Detección automática de delimitador (coma, punto y coma, etc.)
- ✅ Limpieza de nombres de columna
- ✅ Manejo de duplicados en nombres después de limpieza
- ✅ Detección de líneas mal formadas
- ✅ Validación de tamaño de archivo

### 2. **test_validators.py** - Validadores de Datos
- ✅ Validación de emails (por nombre y por contenido)
- ✅ Validación de teléfonos (por nombre y por contenido)
- ✅ Validación de fechas (formatos, consistencia, ambigüedad)
- ✅ Validación de URLs
- ✅ Detección de tipo de dato por contenido de columna

### 3. **test_data_profiler.py** - Perfilado de Datos
- ✅ Información general del perfil
- ✅ Análisis de valores nulos
- ✅ Detección de filas duplicadas
- ✅ Perfiles individuales de columnas
- ✅ Cálculo de uso de memoria

### 4. **test_patterns.py** - Patrones y Expresiones Regulares
- ✅ Validación de emails con regex
- ✅ Validación de teléfonos
- ✅ Validación de URLs
- ✅ Validación de formatos de fecha
- ✅ Inferencia de tipo de dato
- ✅ Detección de caracteres especiales
- ✅ Sugerencias de tipo basadas en nombre de columna

## Fixtures Disponibles

Las fixtures en `conftest.py` proporcionan datos de prueba:

- `sample_valid_csv()` - CSV válido y bien formado
- `sample_csv_with_bad_lines()` - CSV con líneas mal formadas
- `sample_csv_mixed_dates()` - CSV con fechas en diferentes formatos
- `sample_dataframe()` - DataFrame de pandas para pruebas
- `sample_csv_file()` - Archivo CSV temporal
- Y más...

## Resultado Esperado

Todas las pruebas deben pasar sin errores:

```
================================ 60 passed in 2.34s ================================
```

## Integración Continua

Para integración continua, usa:

```bash
pytest --cov=modules --cov=utils --cov-report=xml
```

Esto genera `coverage.xml` compatible con servicios como Codecov.

## Solución de Problemas

### Si las pruebas fallan con "No module named 'modules'"

Asegúrate de estar ejecutando pytest desde el directorio raíz del proyecto:

```bash
cd /ruta/a/proyecto
pytest
```

### Si pytest no se encuentra

Instala pytest:

```bash
pip install pytest
```

### Si hay errores de importación

Verifica que `__init__.py` existe en los directorios:
- `modules/`
- `utils/`
- `tests/`
