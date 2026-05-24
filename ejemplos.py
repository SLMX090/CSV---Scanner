"""
EJEMPLOS DE USO DE CADA MÓDULO
==============================

Este archivo contiene ejemplos de cómo usar cada módulo independientemente
de la interfaz de Streamlit. Útil para aprender cómo funciona internamente.
"""

# ============================================================================
# EJEMPLO 1: Carga de CSV
# ============================================================================

print("=" * 70)
print("EJEMPLO 1: CARGANDO UN ARCHIVO CSV")
print("=" * 70)

from modules.csv_loader import CSVLoader, CSVLoadError

# Opción 1: Cargar un archivo
try:
    # Abre el archivo
    with open('ejemplo_datos_problematicos.csv', 'rb') as file:
        df, info = CSVLoader.load_csv(file)
    
    print(f"✅ Archivo cargado exitosamente")
    print(f"   Filas: {info['rows']}")
    print(f"   Columnas: {info['columns']}")
    print(f"   Delimitador: '{info['delimiter']}'")
    print(f"   Codificación: {info['encoding']}")
    
except CSVLoadError as e:
    print(f"❌ Error: {e}")
except Exception as e:
    print(f"❌ Error inesperado: {e}")


# ============================================================================
# EJEMPLO 2: Perfilado de Datos
# ============================================================================

print("\n" + "=" * 70)
print("EJEMPLO 2: ANALIZANDO LOS DATOS (PROFILING)")
print("=" * 70)

from modules.data_profiler import DataProfiler

# Asumiendo que ya cargamos el DataFrame
if 'df' in locals():
    # Crear el perfilador
    profiler = DataProfiler(df)
    
    # Generar el perfil completo
    profile = profiler.generate_profile()
    
    # Mostrar información general
    print("\n📊 INFORMACIÓN GENERAL:")
    print(f"   Total de filas: {profile['general_info']['total_rows']}")
    print(f"   Total de columnas: {profile['general_info']['total_columns']}")
    print(f"   Total de celdas: {profile['general_info']['total_cells']}")
    print(f"   Memoria usada: {profile['memory_usage']:.2f} MB")
    
    # Mostrar información sobre nulos
    print("\n❌ ANÁLISIS DE VALORES NULOS:")
    print(f"   Total nulos: {profile['null_analysis']['total_null_cells']}")
    print(f"   % Nulos global: {profile['null_analysis']['null_percent_overall']:.2f}%")
    print(f"   Columnas problemáticas: {len(profile['null_analysis']['problematic_columns'])}")
    
    for col, info in profile['null_analysis']['problematic_columns'].items():
        print(f"   - {col}: {info['null_count']} nulos ({info['null_percent']:.1f}%)")
    
    # Mostrar información sobre duplicados
    print("\n🔄 ANÁLISIS DE DUPLICADOS:")
    print(f"   Total duplicados: {profile['duplicates']['total_duplicates']}")
    print(f"   % Duplicados: {profile['duplicates']['duplicates_percent']:.2f}%")
    
    # Mostrar información sobre cadenas vacías
    print("\n⚫ CADENAS VACÍAS O SOLO ESPACIOS:")
    if profile['empty_strings']['columns_with_empty']:
        for col, info in profile['empty_strings']['columns_with_empty'].items():
            print(f"   - {col}: {info['count']} cadenas vacías ({info['percent']:.1f}%)")
    else:
        print("   ✅ No hay cadenas vacías")
    
    # Mostrar información sobre tipos de datos
    print("\n🔀 MEZCLA DE TIPOS DE DATOS:")
    if profile['data_type_issues']:
        for col, issues in profile['data_type_issues'].items():
            print(f"   - {col}: {issues['detected_types']}")
    else:
        print("   ✅ Todos los datos son consistentes")


# ============================================================================
# EJEMPLO 3: Validaciones
# ============================================================================

print("\n" + "=" * 70)
print("EJEMPLO 3: VALIDANDO DATOS ESPECÍFICOS")
print("=" * 70)

from modules.validators import DataValidator

if 'df' in locals():
    # Crear validador
    validator = DataValidator(df)
    
    # Ejecutar todas las validaciones
    validation_results = validator.validate_all()
    
    # Mostrar resultados de emails
    print("\n📧 VALIDACIÓN DE EMAILS:")
    if validation_results['email_validation']:
        for col, info in validation_results['email_validation'].items():
            print(f"   Columna: {col}")
            print(f"   - Válidos: {info['valid_count']}")
            print(f"   - Inválidos: {info['invalid_count']}")
            print(f"   - % Inválidos: {info['invalid_percent']:.2f}%")
            
            if info['examples_invalid']:
                print("   - Ejemplos de inválidos:")
                for example in info['examples_invalid'][:3]:
                    print(f"     • Fila {example['row']}: {example['value']}")
    else:
        print("   Sin columnas de email")
    
    # Mostrar resultados de teléfonos
    print("\n📱 VALIDACIÓN DE TELÉFONOS:")
    if validation_results['phone_validation']:
        for col, info in validation_results['phone_validation'].items():
            print(f"   Columna: {col}")
            print(f"   - Válidos: {info['valid_count']}")
            print(f"   - Inválidos: {info['invalid_count']}")
            print(f"   - % Inválidos: {info['invalid_percent']:.2f}%")
    else:
        print("   Sin columnas de teléfono")
    
    # Mostrar resultados de fechas
    print("\n📅 VALIDACIÓN DE FECHAS:")
    if validation_results['date_validation']:
        for col, info in validation_results['date_validation'].items():
            print(f"   Columna: {col}")
            print(f"   - Válidas: {info['valid_count']}")
            print(f"   - Inválidas: {info['invalid_count']}")
            if info['format_inconsistencies']:
                print(f"   - Formatos encontrados: {info['format_inconsistencies']}")
    else:
        print("   Sin columnas de fecha")
    
    # Mostrar validación numérica
    print("\n🔢 VALIDACIÓN NUMÉRICA:")
    if validation_results['numeric_validation']:
        for col, info in validation_results['numeric_validation'].items():
            print(f"   Columna: {col}")
            print(f"   - Mínimo: {info['min']:.2f}")
            print(f"   - Máximo: {info['max']:.2f}")
            if info['negative_count'] > 0:
                print(f"   - Valores negativos: {info['negative_count']}")
    else:
        print("   Sin columnas numéricas")


# ============================================================================
# EJEMPLO 4: Recomendaciones
# ============================================================================

print("\n" + "=" * 70)
print("EJEMPLO 4: GENERANDO RECOMENDACIONES")
print("=" * 70)

from modules.recommendations import RecommendationGenerator

if 'profile' in locals() and 'validation_results' in locals():
    # Crear generador de recomendaciones
    rec_gen = RecommendationGenerator(profile, validation_results)
    
    # Generar todas las recomendaciones
    recommendations = rec_gen.generate_all_recommendations()
    
    # Mostrar resumen
    summary = rec_gen.get_summary_recommendations()
    print(f"\n📋 RESUMEN DE RECOMENDACIONES:")
    print(f"   Críticas: {summary['critical_issues']}")
    print(f"   Graves: {summary['serious_issues']}")
    print(f"   Advertencias: {summary['warnings']}")
    print(f"   Total: {summary['total_recommendations']}")
    
    # Mostrar recomendaciones de limpieza
    print(f"\n🧹 RECOMENDACIONES DE LIMPIEZA:")
    for rec in recommendations['cleaning'][:5]:  # Primeras 5
        severity_emoji = {
            'CRÍTICO': '🔴',
            'GRAVE': '🟠',
            'AVISO': '🟡'
        }.get(rec['severity'], '⚪')
        
        print(f"\n   {severity_emoji} [{rec['severity']}] {rec['column']}")
        print(f"      {rec['recommendation']}")
        print(f"      Acción: {rec['action']}")
    
    # Mostrar reglas de BD
    print(f"\n🗄️ REGLAS SUGERIDAS PARA BASE DE DATOS:")
    for rule in recommendations['database_rules'][:3]:  # Primeras 3
        print(f"\n   {rule['rule_type']} - {rule['column']}")
        print(f"      Razón: {rule['reason']}")
        if 'sql_constraint' in rule:
            print(f"      SQL: {rule['sql_constraint'][:80]}...")
    
    # Mostrar normalización
    print(f"\n🔧 RECOMENDACIONES DE NORMALIZACIÓN:")
    for rec in recommendations['normalization'][:3]:  # Primeras 3
        print(f"\n   {rec['type']} - {rec['column']}")
        print(f"      Operación: {rec['operation']}")
        print(f"      Razón: {rec['reason']}")


# ============================================================================
# EJEMPLO 5: Generación de Reportes
# ============================================================================

print("\n" + "=" * 70)
print("EJEMPLO 5: GENERANDO REPORTES")
print("=" * 70)

from modules.report_generator import ReportGenerator

if 'df' in locals() and 'profile' in locals():
    print("\n📊 Generando reportes...")
    
    # Crear generador de reportes
    report_gen = ReportGenerator(df, profile, validation_results, recommendations)
    
    # Generar reporte Excel
    try:
        excel_path = report_gen.generate_excel_report('ejemplo_reporte')
        print(f"✅ Reporte Excel generado: {excel_path}")
    except Exception as e:
        print(f"⚠️ Error al generar Excel: {e}")
    
    # Generar reporte HTML
    try:
        html_path = report_gen.generate_html_report('ejemplo_reporte')
        print(f"✅ Reporte HTML generado: {html_path}")
    except Exception as e:
        print(f"⚠️ Error al generar HTML: {e}")


# ============================================================================
# EJEMPLO 6: Patrones de Validación
# ============================================================================

print("\n" + "=" * 70)
print("EJEMPLO 6: USANDO PATRONES DE VALIDACIÓN")
print("=" * 70)

from utils.patterns import ValidationPatterns

print("\n✉️ VALIDAR EMAILS:")
emails = [
    "juan@gmail.com",
    "maria@hotmail.com",
    "invalid.email@",
    "usuario@invalid.com.es"
]

for email in emails:
    is_valid = ValidationPatterns.is_valid_email(email)
    status = "✅" if is_valid else "❌"
    print(f"   {status} {email}")

print("\n📱 VALIDAR TELÉFONOS:")
phones = [
    "+34912345678",
    "666777888",
    "123",
    "+34 912 345 678"
]

for phone in phones:
    is_valid = ValidationPatterns.is_valid_phone(phone)
    status = "✅" if is_valid else "❌"
    print(f"   {status} {phone}")

print("\n🌐 VALIDAR URLs:")
urls = [
    "https://www.google.com",
    "https://github.com/usuario/repo",
    "not_a_url",
    "http://invalid"
]

for url in urls:
    is_valid = ValidationPatterns.is_valid_url(url)
    status = "✅" if is_valid else "❌"
    print(f"   {status} {url}")

print("\n📅 VALIDAR FECHAS:")
dates = [
    "2023-01-15",
    "15/01/2023",
    "2023/01/15",
    "invalid-date"
]

for date in dates:
    is_valid = ValidationPatterns.is_valid_date_format(date)
    status = "✅" if is_valid else "❌"
    print(f"   {status} {date}")


# ============================================================================
# EJEMPLO 7: Funciones Auxiliares
# ============================================================================

print("\n" + "=" * 70)
print("EJEMPLO 7: USANDO FUNCIONES AUXILIARES")
print("=" * 70)

from utils.helpers import DataFrameHelper, StringHelper

if 'df' in locals():
    print("\n📊 INFORMACIÓN DEL DATAFRAME:")
    memory = DataFrameHelper.get_memory_usage(df)
    print(f"   Memoria usada: {memory:.2f} MB")
    
    duplicates = DataFrameHelper.get_duplicates_info(df)
    print(f"   Duplicados totales: {duplicates['total_duplicates']}")
    print(f"   % Duplicados: {duplicates['duplicates_percent']:.2f}%")
    
    nulls = DataFrameHelper.get_null_info(df)
    print(f"   Células nulas totales: {nulls['total_null_cells']}")
    
    print("\n📝 LIMPIEZA DE TEXTO:")
    text = "   Esto   es   un   ejemplo   "
    cleaned = StringHelper.clean_string(text)
    print(f"   Original: '{text}'")
    print(f"   Limpio: '{cleaned}'")
    
    print("\n✂️ TRUNCADO DE TEXTO:")
    long_text = "Este es un texto muy largo que excede la longitud máxima permitida"
    truncated = StringHelper.truncate_string(long_text, 30)
    print(f"   Original ({len(long_text)} chars): {long_text}")
    print(f"   Truncado: {truncated}")


# ============================================================================
# FIN DE EJEMPLOS
# ============================================================================

print("\n" + "=" * 70)
print("✨ FIN DE EJEMPLOS")
print("=" * 70)
print("""
Para ejecutar este archivo:
    python ejemplos.py

Para usar en tu propio código:
    from modules import csv_loader, data_profiler, validators
    from modules import recommendations, report_generator
    from utils import helpers, patterns
""")
