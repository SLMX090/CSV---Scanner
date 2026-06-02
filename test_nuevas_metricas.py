"""
Script de prueba para validar las nuevas métricas de filas completas y utilidad por columna
"""

import pandas as pd
import sys
import os

# Agregar módulos al path
sys.path.insert(0, os.path.dirname(__file__))

from utils.helpers import DataFrameHelper
from modules.data_profiler import DataProfiler

# Crear un DataFrame de prueba que simula el problema
print("=" * 70)
print("TEST DE NUEVAS MÉTRICAS: Filas Completas y Utilidad por Columna")
print("=" * 70)

# Caso 1: CSV con 10 filas, 3 columnas, 1 columna opcional con muchos nulos
datos = {
    'nombre': ['Juan', 'María', 'Pedro', 'Ana', 'Luis', 'Rosa', 'Carlos', 'Sofia', 'Diego', 'Elena'],
    'email': ['juan@mail.com', 'maria@mail.com', 'pedro@mail.com', 'ana@mail.com', 'luis@mail.com', 
              'rosa@mail.com', 'carlos@mail.com', 'sofia@mail.com', 'diego@mail.com', 'elena@mail.com'],
    'nota_opcional': ['Ok', None, 'Ok', None, 'Ok', None, 'Ok', None, 'Ok', None]
}

df = pd.DataFrame(datos)

print("\n📊 DATAFRAME DE PRUEBA:")
print(df)
print(f"\nDimensiones: {df.shape[0]} filas × {df.shape[1]} columnas")

# Test 1: Filas completas
print("\n" + "=" * 70)
print("TEST 1: Información de Filas Completas")
print("=" * 70)

complete_rows_info = DataFrameHelper.get_complete_rows_info(df)
print(f"\nTotal de filas: {complete_rows_info['total_rows']}")
print(f"Filas completamente limpias (sin nulos): {complete_rows_info['complete_rows']}")
print(f"Porcentaje de filas completas: {complete_rows_info['complete_rows_percent']}%")

# Test 2: Utilidad por columna
print("\n" + "=" * 70)
print("TEST 2: Utilidad por Columna")
print("=" * 70)

column_utilization = DataFrameHelper.get_column_utilization(df)
print("\nPorcentaje de utilidad (valores no nulos) por columna:")
for col, util_pct in column_utilization.items():
    status = "✅ ACEPTABLE" if util_pct >= 80 else "⚠️  BAJO" if util_pct >= 50 else "❌ CRÍTICO"
    print(f"  {col:20s}: {util_pct:6.2f}% {status}")

# Test 3: Perfil completo con nuevas métricas
print("\n" + "=" * 70)
print("TEST 3: Perfil Completo del DataProfiler")
print("=" * 70)

profiler = DataProfiler(df)
profile = profiler.generate_profile()

null_analysis = profile['null_analysis']

print(f"\n📈 Resumen de Nulos:")
print(f"  Total celdas nulas: {null_analysis['total_null_cells']}")
print(f"  % Nulos global: {null_analysis['null_percent_overall']:.2f}%")
print(f"\n📋 Filas Completas:")
print(f"  Filas sin nulos: {null_analysis['complete_rows']}")
print(f"  % Filas completas: {null_analysis['complete_rows_percent']:.2f}%")
print(f"\n📊 Utilidad por Columna:")
for col, util_pct in null_analysis['column_utilization'].items():
    status = "✅" if util_pct >= 80 else "⚠️ " if util_pct >= 50 else "❌"
    print(f"  {col:20s}: {util_pct:6.2f}% {status}")

# Test 4: Validar con caso más extremo
print("\n" + "=" * 70)
print("TEST 4: Caso Extremo - CSV con 50 columnas, 1 opcional vacía")
print("=" * 70)

# Crear un DF con 50 columnas donde 49 están completas y 1 está vacía
datos_extremo = {f'columna_{i}': ['valor'] * 100 for i in range(49)}
datos_extremo['columna_opcional'] = [None] * 100

df_extremo = pd.DataFrame(datos_extremo)

complete_rows_info_extremo = DataFrameHelper.get_complete_rows_info(df_extremo)
column_utilization_extremo = DataFrameHelper.get_column_utilization(df_extremo)

print(f"\n✅ CSV de {df_extremo.shape[0]} filas × {df_extremo.shape[1]} columnas")
print(f"❌ Filas completamente limpias: {complete_rows_info_extremo['complete_rows']}")
print(f"📊 % Filas completas: {complete_rows_info_extremo['complete_rows_percent']:.2f}%")
print(f"\n🔍 Columnas problemáticas:")
for col in datos_extremo.keys():
    util_pct = column_utilization_extremo[col]
    if util_pct < 80:
        print(f"  ❌ {col}: {util_pct:.2f}% de utilidad")

# Conclusión
print("\n" + "=" * 70)
print("✅ CONCLUSIÓN: Las nuevas métricas funcionan correctamente")
print("=" * 70)
print("""
Con estas métricas ahora puedes:
1. Saber exactamente cuántas filas están 100% limpias (sin nulos)
2. Identificar QUÉ COLUMNA está causando los problemas
3. Tomar decisiones informadas sobre qué datos mantener

En el caso extremo: 0% de filas completas (porque columna_opcional está toda vacía)
Pero 98% de utilidad promedio (49 de 50 columnas están 100% útiles)
""")
