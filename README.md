# 📊 Analizador de Calidad de Datos CSV - v3.3

![Python](https://img.shields.io/badge/python-3.8+-blue) ![Status](https://img.shields.io/badge/status-active-green)

Herramienta para analizar archivos CSV y Excel, identificar problemas de calidad de datos y producir artefactos útiles para limpieza, validación y carga a base de datos. La versión actual incluye análisis por lote, detección inteligente de problemas, generación de SQL/Python y exportación de reportes estructurados con soporte multidialecto.

## 🎯 Características Principales

### 📊 Análisis Completo de Datos
- ✅ Detección de nulos, duplicados, tipos mixtos
- ✅ Análisis estadístico y perfilado automático
- ✅ Validación de emails, teléfonos, fechas, URLs
- ✅ Detección de anomalías y outliers
- ✅ Cardinalidad y distribución de valores

### 💡 Recomendaciones Inteligentes
- ✅ Sugerencias de limpieza específicas
- ✅ Reglas SQL automáticas (NOT NULL, UNIQUE, CHECK)
- ✅ Recomendaciones de normalización
- ✅ **Filtros SQL listos para usar**

### 🗄️ ✨ Generación de Código SQL/Python (NUEVO)
**Novedades de la versión 3.x:**

- ✅ **Motor Jinja2 con soporte multidialecto** (PostgreSQL, MySQL, Snowflake, BigQuery). El script se ajusta automáticamente al dialecto elegido.
- ✅ **Inferencia de tipos inteligente**: se calcula precisión y escala de números para usar `NUMERIC/DECIMAL(precision,scale)` en lugar de `VARCHAR` por defecto.
- ✅ **Tabla de cuarentena**: los registros con errores de tipo o formato se insertan en una tabla secundaria con información detallada (`columna_erronea`, `categoria_error`, `valor_original`).
- ✅ **Selector de dialecto en la interfaz**: elige el motor SQL deseado antes de generar el script.
- ✅ Código Python de limpieza con pandas.
- ✅ Estandarización automática de fechas y monedas.
- ✅ Eliminación de duplicados y nulos.
- ✅ Queries de validación final.

### ⚙️ ✨ Configuración Personalizada (NUEVO)
- ✅ Carga configuración YAML/JSON propia
- ✅ Validaciones personalizadas por dominio
- ✅ Reglas de negocio específicas

### 📥 ✨ Reportes Mejorados (NUEVO)
- ✅ Excel con análisis completo en múltiples hojas
- ✅ HTML con información interactiva
- ✅ Incluye código SQL/Python generado
- ✅ Configuración YAML exportada

---

## 🚀 Instalación y Uso Rápido

```bash
# 1. Clonar/descargar proyecto
git clone <repositorio>
cd csv-data-analyzer

# 2. Crear entorno virtual
python -m venv venv
venv\\Scripts\\activate  # Windows
source venv/bin/activate  # macOS/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar
streamlit run app.py
```

Accede a `http://localhost:8501` en tu navegador.

---

## 📱 Interfaz de Usuario - 8 Pestañas

| # | Pestaña | Descripción |
|----|---------|----------|
| 1️⃣ | 📥 Cargar Archivo | Sube CSV, configura delimitador/codificación |
| 2️⃣ | 📈 Análisis | Nulos, duplicados, tipos, estadísticas |
| 3️⃣ | ✅ Validaciones | Email, teléfono, fecha, URL, dominio |
| 4️⃣ | 💡 Recomendaciones | Limpieza, reglas SQL, normalización, **filtros SQL** |
| 5️⃣ | 📋 Datos Problemáticos | Ejemplos de filas con problemas |
| 6️⃣ | 💾 Código SQL/Python | **Script SQL + Python + YAML generado** ✨ *(ahora con selector de dialecto)* |
| 7️⃣ | ⚙️ Configuración | **Carga tu YAML/JSON personalizado** ✨ |
| 8️⃣ | 📥 Descargar Reporte | Excel (14 hojas) + HTML |

---

## 💾 Nuevo: Generación Automática de Código

### Script SQL Generado Automáticamente
```sql
-- CREATE TABLE automático con tipos inferidos
CREATE TABLE IF NOT EXISTS datos_limpios (
  id INT PRIMARY KEY,
  nombre VARCHAR(255) NOT NULL,
  email VARCHAR(255) UNIQUE,
  fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- INSERT con limpieza, estandarización y filtros
WITH cleaned_data AS (
  SELECT
    TRIM(id) AS id_clean,
    LOWER(TRIM(email)) AS email_clean,
    TRY_CAST(TRIM(fecha) AS DATE) AS fecha_clean
  FROM source_table
  WHERE email LIKE '%@%'
    AND TRIM(email) IS NOT NULL
)
INSERT INTO datos_limpios (id, email, fecha)
SELECT id_clean, email_clean, fecha_clean
FROM cleaned_data
WHERE ROW_NUMBER() OVER (PARTITION BY id ORDER BY 1) = 1;
```

**Desde la versión 3.x el script SQL se genera mediante plantillas Jinja2 y soporta múltiples dialectos**. A modo ilustrativo se muestra un ejemplo simplificado para PostgreSQL; el script final adaptará los tipos y funciones de cast según el motor seleccionado.

### Código Python Generado Automáticamente
```python
def cleanup_data(df):
    df_clean = df.copy()
    
    # Eliminar duplicados
    df_clean = df_clean.drop_duplicates(keep='first')
    
    # Limpiar espacios
    df_clean = df_clean.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    
    # Estandarizar tipos
    df_clean['id'] = pd.to_numeric(df_clean['id'], errors='coerce').astype('Int64')
    df_clean['email'] = df_clean['email'].str.lower()
    df_clean['fecha'] = pd.to_datetime(df_clean['fecha'], errors='coerce')
    
    return df_clean
```

---

## 📊 Contenido del Reporte Excel

La exportación actual del proyecto organiza la información en varias hojas temáticas para facilitar la revisión del análisis.

| # | Hoja | Contenido |
|---|------|----------|
| 1 | **RESUMEN_EJECUTIVO** | Métricas clave y conteos |
| 2 | **INFO_GENERAL** | Información básica del dataset |
| 3 | **ANALISIS_NULOS** | Valores nulos por columna |
| 4 | **FILAS_Y_UTILIDAD** | Filas completas y utilidad |
| 5 | **DUPLICADOS** | Registros duplicados |
| 6 | **PERFIL_COLUMNAS** | Tipos de datos y cardinalidad |
| 7 | **VALIDACIONES** | Resultados de validaciones |
| 8 | **LIMPIEZA** | Recomendaciones de limpieza |
| 9 | **REGLAS_BD** | Reglas SQL sugeridas |
| 10 | **NORMALIZACION** | Transformaciones recomendadas |
| 11 | **FILTROS_SQL** | Filtros SQL por problema |
| 12 | **CODIGO_SQL** | ✨ **Script SQL completo** |
| 13 | **CODIGO_PYTHON** | ✨ **Script Python** |
| 14 | **CONFIG_YAML** | ✨ **Configuración YAML exportada** |

La generación SQL incorpora el manejo de cuarentena y validación de errores dentro del script, mientras que el libro exportado mantiene una estructura clara para revisión humana y análisis posterior.

---

## ⚙️ Configuración Personalizada YAML

```yaml
database:
  table_name: datos_limpios
  charset: utf8mb4

columns:
  email:
    type: VARCHAR(255)
    nullable: false
    unique: true
    validations: [email]
  
  edad:
    type: INT
    nullable: false

cleaning:
  trim_whitespace: true
  remove_duplicates: true
  handle_nulls: remove

validation_rules:
  min_rows: 100
  max_null_percent: 20
```

**Cómo usar:**
1. Ve a pestaña "⚙️ Configuración"
2. Carga tu archivo YAML/JSON
3. Las validaciones se personalizan automáticamente

---

## 📈 Validación por Dominio

Reglas predefinidas para sectores:

| Dominio | Ejemplo |
|---------|---------|
| Healthcare | Edad: 0-120, Temp: 36-41°C, Presión: 60-200 |
| E-Commerce | Precio ≥ 0, Stock ≥ 0, Descuento 0-100% |
| HR | Edad: 18-75, Salario > 500 |
| Finance | Tasa: 0-100%, IBAN válido |
| Gobierno | ZIP: 5 dígitos, NIF válido |

---

## ⚠️ Notas Importantes

### Alcance
- ✅ **SÍ es**: Análisis exploratorio, validación preliminar
- ❌ **NO es**: Sistema formal certificado

### Antes de Producción
- Valida código SQL con tu DBA
- Prueba con datos de ejemplo
- Ajusta según tu contexto específico
- Responsabilidad del usuario

---

## 📚 Estructura del Proyecto

```
.
├── app.py                           # App principal Streamlit
├── config.py                        # Configuración global
├── modules/
│   ├── csv_loader.py               # Carga de archivos
│   ├── data_profiler.py            # Perfilado
│   ├── validators.py               # Validaciones
│   ├── recommendations.py          # Recomendaciones
│   ├── report_generator.py         # Reportes
│   ├── severity_analyzer.py        # Análisis severidad
│   ├── sql_filter_suggestions.py   # Filtros SQL
│   └── db_code_generator.py        # ✨ Generador SQL/Python
├── utils/
│   ├── helpers.py
│   └── patterns.py
└── tests/                           # Tests unitarios (85+ tests)
```

---

## 🧪 Pruebas

```bash
# Ejecutar todos los tests
pytest

# Archivo específico
pytest tests/test_validators.py -v
```

La suite principal del proyecto cubre la validación de carga, perfilado, validaciones, patrones, lote y generación de SQL/Python, y se puede usar como referencia para comprobar cambios en la lógica del analizador.

---

## 💾 Archivos Grandes

Soporte automático para archivos **> 100 MB**:

```
Tamaño          Método
< 100 MB        Carga completa
100 MB - 1 GB   Chunks automático (50K filas/chunk)
```

---

## 📝 Versión y Licencia

**Versión:** 3.2.0  
**Última actualización:** Junio 2026  
**Licencia:** MIT

---

**Hecha con ❤️ para simplificar análisis de calidad de datos**

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
