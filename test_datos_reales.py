"""
Test con datos reales del archivo ejemplo_datos_problematicos.csv
"""

from modules.csv_loader import CSVLoader
from modules.data_profiler import DataProfiler
import sys

print("=" * 70)
print("ANÁLISIS DEL CSV PROBLEMÁTICO REAL")
print("=" * 70)

try:
    # Cargar CSV
    loader = CSVLoader()
    with open('ejemplo_datos_problematicos.csv', 'rb') as f:
        result = loader.load_csv(f)
    
    if isinstance(result, tuple):
        df, load_info = result
    else:
        df = result
    
    print(f"\n✅ CSV cargado exitosamente")
    print(f"   Filas: {len(df)}")
    print(f"   Columnas: {len(df.columns)}")
    
    # Perfilar datos
    profiler = DataProfiler(df)
    profile = profiler.generate_profile()
    
    # Mostrar información general
    general = profile['general_info']
    null_analysis = profile['null_analysis']
    
    print(f"\n📊 INFORMACIÓN GENERAL:")
    print(f"   Total de filas: {general['total_rows']}")
    print(f"   Total de columnas: {general['total_columns']}")
    print(f"   Total de celdas: {general['total_cells']}")
    
    # Resumen de nulos
    print(f"\n📈 RESUMEN DE NULOS:")
    print(f"   Celdas nulas totales: {null_analysis['total_null_cells']}")
    print(f"   % Nulos global: {null_analysis['null_percent_overall']:.2f}%")
    print(f"   Filas completamente limpias: {null_analysis['complete_rows']}")
    print(f"   % Filas completas: {null_analysis['complete_rows_percent']:.2f}%")
    
    # Utilidad por columna
    print(f"\n📊 UTILIDAD POR COLUMNA (% de datos válidos):")
    print("-" * 70)
    
    utilization = null_analysis['column_utilization']
    for col in sorted(utilization.keys()):
        util_pct = utilization[col]
        if util_pct >= 90:
            status = "✅ EXCELENTE"
        elif util_pct >= 80:
            status = "✅ ACEPTABLE"
        elif util_pct >= 50:
            status = "⚠️  BAJO"
        else:
            status = "❌ CRÍTICO"
        
        print(f"   {col:30s}: {util_pct:6.2f}% {status}")
    
    # Problematic columns
    if null_analysis['problematic_columns']:
        print(f"\n⚠️  COLUMNAS PROBLEMÁTICAS (< {null_analysis['problematic_columns'] or 'N/A'} % válidas):")
        print("-" * 70)
        for col, info in null_analysis['problematic_columns'].items():
            print(f"   {col:30s}: {info['null_percent']:.2f}% nulos | {info['utilization_percent']:.2f}% utilidad | {info['status']}")
    
    print(f"\n" + "=" * 70)
    print("✅ CONCLUSIÓN: Sistema funcionando correctamente con datos reales")
    print("=" * 70)

except FileNotFoundError:
    print("❌ Error: No se encontró el archivo 'ejemplo_datos_problematicos.csv'")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error durante análisis: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
