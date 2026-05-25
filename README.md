# 📊 Analizador de Calidad de Datos CSV

Herramienta local para analizar archivos CSV e identificar posibles problemas de calidad de datos. Diseñada como apoyo preliminar y referencia dentro de procesos ETL, requiere validación posterior mediante controles formales y revisión humana.

## 🎯 Características

### Identificación de Posibles Problemas
- ✅ Registros nulos y campos vacíos
- ✅ Filas potencialmente duplicadas (completas y parciales)
- ✅ Tipos de datos inferidos por columna
- ✅ Columnas con posible mezcla de tipos de datos
- ✅ Valores fuera de rango numérico esperado
- ✅ Fechas con formatos inconsistentes o inválidos
- ✅ Formato de correos electrónicos potencialmente inválidos
- ✅ Formato de teléfonos potencialmente inválidos
- ✅ Texto con caracteres especiales anómalos
- ✅ Columnas con cardinalidad inusual
- ✅ Columnas con exceso de valores faltantes

### Generación de Reportes Preliminares
- 📊 Información general del dataset
- 📈 Análisis estadístico descriptivo
- ❌ Análisis de valores nulos
- 🔄 Detección de duplicados
- ✅ Validaciones preliminares (email, teléfono, fecha, etc.)
- 💡 Recomendaciones iniciales de limpieza
- 🗄️ Reglas sugeridas para base de datos (NOT NULL, UNIQUE, CHECK, etc.)
- 🔧 Sugerencias de normalización
- 📥 Exportación en Excel y HTML

---

## ⚠️ Alcance y Limitaciones

### 🎯 ¿Qué es esta herramienta?

Este proyecto es una **aplicación local de análisis preliminar** diseñada como herramienta de **consulta y referencia** dentro de procesos ETL/Big Data. Su propósito es ayudarte a:

- 🔍 **Identificar posibles problemas** de calidad en archivos CSV antes de ingestión
- 📊 **Servir como segunda opinión** en análisis de datos exploratorio
- 💡 **Generar recomendaciones iniciales** que requieren validación posterior

### ❌ Lo que **NO es** esta herramienta

- ❌ **NO** es un sistema de validación formal o certificado
- ❌ **NO** debe usarse como fuente única de verdad para decisiones críticas  
- ❌ **NO** reemplaza controles ETL formales ni validaciones en base de datos
- ❌ **NO** garantiza detección exhaustiva de todos los problemas
- ❌ **NO** es adecuada para tomar decisiones automáticas sobre datos de producción

### 🧪 Naturaleza de las validaciones

Las validaciones empleadas son **heurísticas y básicas**:
- Pueden generar **falsos positivos** (alertar problemas que no existen)
- Pueden generar **falsos negativos** (perder problemas reales)
- Usan patrones simples y reglas predeterminadas, no análisis estadístico avanzado

### ✅ Uso recomendado

1. **Análisis Exploratorio**: Entender la estructura y calidad general de un CSV
2. **Validación Preliminar**: Identificar problemas obvios antes de procesos más rigurosos
3. **Documentación de Descubrimientos**: Usar como base para investigaciones posteriores
4. **Apoyo a Procesos ETL**: Complementar (no reemplazar) reglas ETL formales

### 🔒 Decisiones que requieren validación adicional

Antes de proceder con cualquiera de estas acciones, **valida con herramientas especializadas o revisión humana**:

- Rechazo o eliminación de datos
- Transformaciones automáticas en masa
- Carga a sistemas de producción
- Cambios en reglas de negocio basados en los hallazgos

### 📌 Responsabilidad

La responsabilidad de validar datos y tomar decisiones críticas **recae en el usuario**, no en esta herramienta. Los resultados son indicativos y deben ser contrastados con:
- Reglas ETL formales del proceso
- Validaciones en base de datos (constraints, triggers)
- Revisión manual o auditoría humana
- Herramientas especializadas en calidad de datos

---

## 📋 Requisitos Previos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)

## 🚀 Instalación

### 1. Clonar o descargar el proyecto

```bash
# Si tienes Git
git clone <repositorio>
cd csv-data-analyzer

# O simplemente descarga los archivos del proyecto
```

### 2. Crear un entorno virtual (recomendado)

```bash
# En Windows
python -m venv venv
venv\Scripts\activate

# En macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar dependencias

```bash
pip install -r requirements.txt
```

**Dependencias incluidas:**
- `streamlit==1.40.0` - Framework web para la interfaz
- `pandas==2.2.0` - Procesamiento y análisis de datos
- `openpyxl==3.11.0` - Exportación a Excel
- `email-validator==2.1.0` - Validación de emails
- `python-dateutil==2.8.2` - Procesamiento de fechas
- `numpy==1.24.3` - Operaciones numéricas

## 📖 Uso

### Ejecutar la aplicación

```bash
streamlit run app.py
```

La aplicación se abrirá en tu navegador (generalmente en `http://localhost:8501`)

### Flujo de Uso

#### 1. **Cargar Archivo** 📥
   - Ve a la pestaña "Cargar Archivo"
   - Selecciona tu archivo CSV
   - Opcionalmente, especifica el delimitador y codificación
   - El sistema detectará automáticamente las características del archivo

#### 2. **Análisis** 📈
   - La pestaña "Análisis" muestra un resumen completo:
     - Información general (filas, columnas, memoria)
     - Análisis de valores nulos
     - Detección de duplicados
     - Identificación de cadenas vacías
     - Mezcla de tipos de datos
     - Cardinalidad de columnas

#### 3. **Validaciones** ✅
   - Revisa validaciones específicas:
     - Emails válidos/inválidos
     - Teléfonos válidos/inválidos
     - Fechas válidas/inválidas
     - Valores numéricos fuera de rango
     - Texto con caracteres especiales
     - URLs válidas/inválidas

#### 4. **Recomendaciones** 💡
   - Obtén sugerencias de limpieza
   - Reglas para base de datos (SQL)
   - Operaciones de normalización

#### 5. **Datos Problemáticos** 📋
   - Visualiza ejemplos de datos con problemas
   - Filas duplicadas
   - Columnas problemáticas

#### 6. **Descargar Reporte** 📥
   - Genera reportes en Excel o HTML
   - Los reportes incluyen todas las pestañas de análisis
   - Se guardan automáticamente en la carpeta `output/`

## 📊 Estructura del Proyecto

```
csv-data-analyzer/
├── app.py                    # Aplicación principal (Streamlit)
├── config.py                 # Configuración global
├── requirements.txt          # Dependencias
├── README.md                 # Este archivo
│
├── modules/                  # Módulos principales
│   ├── __init__.py
│   ├── csv_loader.py         # Carga y validación de CSV
│   ├── data_profiler.py      # Análisis y perfilado de datos
│   ├── validators.py         # Validaciones específicas
│   ├── recommendations.py    # Generador de recomendaciones
│   └── report_generator.py   # Exportación de reportes
│
├── utils/                    # Utilidades
│   ├── __init__.py
│   ├── helpers.py            # Funciones auxiliares
│   └── patterns.py           # Patrones y expresiones regex
│
└── output/                   # Reportes generados
    └── (archivos generados automáticamente)
```

## 📚 Módulos y Funciones Clave

### `csv_loader.py` - Carga de Archivos
```python
from modules.csv_loader import CSVLoader

# Cargar CSV con detección automática
df, info = CSVLoader.load_csv(file_object)

# Información devuelta
# {
#     'delimiter': ',',
#     'encoding': 'utf-8',
#     'rows': 1000,
#     'columns': 15
# }
```

### `data_profiler.py` - Análisis de Datos
```python
from modules.data_profiler import DataProfiler

profiler = DataProfiler(df)
profile = profiler.generate_profile()

# Accede a diferentes análisis
nulos = profile['null_analysis']
duplicados = profile['duplicates']
columnas = profile['column_profiles']
```

### `validators.py` - Validaciones
```python
from modules.validators import DataValidator

validator = DataValidator(df)
results = validator.validate_all()

# Contiene validaciones para:
# - Emails
# - Teléfonos
# - Fechas
# - Números
# - Texto
# - URLs
```

### `recommendations.py` - Recomendaciones
```python
from modules.recommendations import RecommendationGenerator

rec_gen = RecommendationGenerator(profile, validation_results)
recommendations = rec_gen.generate_all_recommendations()

# Devuelve:
# {
#     'cleaning': [...],
#     'database_rules': [...],
#     'normalization': [...],
#     'quality': [...]
# }
```

### `report_generator.py` - Reportes
```python
from modules.report_generator import ReportGenerator

report_gen = ReportGenerator(df, profile, validation_results, recommendations)

# Generar Excel
excel_path = report_gen.generate_excel_report('nombre_reporte')

# Generar HTML
html_path = report_gen.generate_html_report('nombre_reporte')
```

## 🔍 Ejemplos de Uso

### Ejemplo 1: Análisis Básico
```bash
# 1. Instala dependencias
pip install -r requirements.txt

# 2. Ejecuta la aplicación
streamlit run app.py

# 3. Carga tu CSV
# - Haz clic en "Cargar Archivo"
# - Selecciona tu CSV
# - Ve automáticamente al análisis
```

### Ejemplo 2: CSV con Problemas Comunes
```
# Dataset con problemas:
# - Columna con 60% de nulos
# - Emails con formato inválido
# - Fechas en diferentes formatos
# - Filas completamente duplicadas

# La aplicación detectará:
✓ 60% de nulos en columna 'teléfono' → GRAVE
✓ 15% de emails inválidos → AVISO
✓ 3 formatos de fecha diferentes → GRAVE
✓ 50 filas duplicadas → GRAVE

# Recomendaciones generadas:
→ Evaluar si columna 'teléfono' debe ser obligatoria
→ Validar formato de emails antes de insertar
→ Estandarizar formato de fechas
→ Eliminar filas duplicadas o aplicar DISTINCT
```

## 🛠️ Solución de Problemas

### Error: "Archivo demasiado grande"
- **Solución:** Los archivos están limitados a 50MB por defecto
- Edita `config.py` y aumenta `MAX_FILE_SIZE_MB`

### Error: "No se pudo detectar el delimitador"
- **Solución:** Especifica manualmente en la barra lateral
- Opciones: `,` `;` `\t` `|` `:`

### Error: "Codificación incorrecta"
- **Solución:** Especifica la codificación manualmente
- Opciones: `utf-8`, `latin-1`, `iso-8859-1`, `cp1252`

### Error: "La aplicación se ejecuta lentamente"
- **Solución:** El dataset es muy grande
- Prueba con un subset del archivo primero
- Aumenta `MAX_FILE_SIZE_MB` en `config.py` si es necesario

## 📝 Ejemplo de Reporte Generado

### Resumen Ejecutivo
```
Métrica                  | Valor
Total de Filas          | 10,000
Total de Columnas       | 25
Valores Nulos           | 5,234 (2.09%)
Filas Duplicadas        | 145 (1.45%)
Columnas Problemáticas  | 8
```

### Recomendaciones
```
🔴 CRÍTICO
- Columna 'ciudad' tiene 85% nulos → ELIMINAR COLUMNA

🟠 GRAVE
- Columna 'email' tiene 25 emails inválidos → VALIDAR ANTES DE BD
- Se detectaron 145 filas duplicadas → APLICAR DISTINCT

🟡 AVISO
- Columna 'edad' tiene valores negativos → REVISAR RANGO
```

### Reglas para Base de Datos
```sql
-- NOT NULL
ALTER TABLE tabla ADD CONSTRAINT nn_nombre CHECK (nombre IS NOT NULL);

-- UNIQUE
ALTER TABLE tabla ADD CONSTRAINT uk_email UNIQUE (email);

-- CHECK
ALTER TABLE tabla ADD CONSTRAINT ck_edad_positive CHECK (edad >= 0);

-- Validar emails
ALTER TABLE tabla ADD CONSTRAINT ck_email_format 
  CHECK (email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$');
```

## 🎓 Conceptos Educativos

Este proyecto es ideal para estudiantes de Ingeniería en Tecnologías de la Información porque:

1. **Estructura Modular** - Código organizado en componentes reutilizables
2. **Validación de Datos** - Patrones de validación comunes en desarrollo
3. **Análisis Estadístico** - Uso de pandas y numpy
4. **Interfaz Web** - Aplicación interactiva con Streamlit
5. **Generación de Reportes** - Exportación de datos a múltiples formatos
6. **Manejo de Errores** - Excepciones personalizadas y validación
7. **Patrones de Diseño** - Clases y métodos bien estructurados
8. **Expresiones Regulares** - Validación con regex

## 📖 Interpretación del Reporte

### ¿Qué significa cada indicador?

**% Nulos:**
- 0-10% → ✅ Aceptable
- 10-40% → ⚠️ Revisar
- 40-80% → 🔴 Grave
- >80% → 🔴 Crítico (considerar eliminar)

**Cardinalidad:**
- <10% → Pocos valores únicos (catálogo)
- 10-80% → Normal
- >80% → Muchos valores únicos (posible ID)

**Duplicados:**
- 0% → ✅ Sin duplicados
- 0-5% → ⚠️ Pocos duplicados
- >5% → 🔴 Necesita limpieza

## 🔐 Validaciones Incluidas

- **Emails:** Formato RFC estándar
- **Teléfonos:** Longitud y caracteres válidos
- **Fechas:** Múltiples formatos (ISO, DD/MM/YYYY, etc.)
- **URLs:** Protocolo y estructura válida
- **Números:** Rango y tipo de dato

## 🚀 Mejoras Futuras

- [ ] Conexión directa a base de datos
- [ ] Aplicar automáticamente transformaciones
- [ ] Machine Learning para detección de anomalías
- [ ] Interfaz gráfica avanzada
- [ ] Historial de análisis
- [ ] Comparación entre versiones
- [ ] Exportación a JSON

## 📞 Soporte

Para reportar problemas o sugerencias:
1. Revisa el archivo `config.py` para ajustar umbrales
2. Consulta la documentación de cada módulo
3. Verifica que todas las dependencias estén instaladas

## 📄 Licencia

Este proyecto es de código abierto para uso educativo.

## ✨ Autor

Desarrollado como plataforma educativa para análisis de calidad de datos.

---

**¡Buena suerte con tu análisis de datos!** 🎉
