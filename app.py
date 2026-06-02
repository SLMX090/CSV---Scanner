"""
Aplicación Principal de Análisis de Calidad de Datos CSV
=========================================================

Herramienta local para analizar archivos CSV e identificar posibles problemas de calidad 
de datos que requieren validación posterior mediante controles ETL formales.

Autor: Sistema de Análisis de Datos
Versión: 1.0.0
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Importa módulos personalizados
from modules.csv_loader import CSVLoader, CSVLoadError
from modules.data_profiler import DataProfiler
from modules.validators import DataValidator
from modules.recommendations import RecommendationGenerator
from modules.report_generator import ReportGenerator
from modules.severity_analyzer import SeverityAnalyzer
from modules.sql_filter_suggestions import SQLFilterSuggestions


# Configuración de la página
st.set_page_config(
    page_title="Analizador de Datos CSV",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos personalizados
st.markdown("""
<style>
    .main-title {
        color: #2c3e50;
        text-align: center;
        margin-bottom: 30px;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border: 1px solid #ffc107;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .error-box {
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Título principal
st.markdown("# 📊 Analizador de Calidad de Datos CSV", unsafe_allow_html=True)
st.markdown("""
Herramienta local para analizar archivos CSV e identificar posibles problemas de calidad de datos 
que requieren validación posterior.
""")

# Aviso sobre carácter preliminar de la herramienta
st.info(
    "ℹ️ **Importante**: Este análisis es **orientativo y preliminar**. "
    "Los resultados no reemplazan validaciones formales de ETL ni controles de base de datos. "
    "Revisa con herramientas especializadas antes de tomar decisiones críticas.",
    icon="⚠️"
)

st.divider()

# Barra lateral de configuración
with st.sidebar:
    st.header("⚙️ Configuración")
    
    st.subheader("Opciones de Carga")
    delimiter_manual = st.checkbox("Especificar delimitador manualmente", value=False)
    delimiter = None
    if delimiter_manual:
        delimiter = st.selectbox(
            "Selecciona el delimitador:",
            [',', ';', '\t', '|', ':'],
            index=0
        )
    
    encoding_manual = st.checkbox("Especificar codificación manualmente", value=False)
    encoding = None
    if encoding_manual:
        encoding = st.selectbox(
            "Selecciona la codificación:",
            ['utf-8', 'latin-1', 'iso-8859-1', 'cp1252'],
            index=0
        )
    
    st.divider()
    
    st.divider()
    st.info("""
    **Consejos de Uso:**
    - Carga un archivo CSV pequeño primero para probar
    - Si el análisis es lento, el archivo puede ser muy grande
    - Revisa todas las pestañas del reporte
    """)


# Sección principal
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📥 Cargar Archivo",
    "📈 Análisis",
    "✅ Validaciones",
    "💡 Recomendaciones",
    "📋 Datos Problemáticos",
    "📥 Descargar Reporte"
])

# ============================================================================
# TAB 1: CARGA DE ARCHIVO
# ============================================================================
with tab1:
    st.header("Carga de Archivo CSV")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Selecciona un archivo CSV",
            type=['csv'],
            help="Soporta archivos CSV con diferentes delimitadores y codificaciones"
        )
    
    with col2:
        if uploaded_file:
            st.metric("Tamaño", f"{uploaded_file.size / 1024:.2f} KB")
    
    if uploaded_file:
        st.divider()
        
        # Intenta cargar el archivo
        spinner_msg = "Cargando archivo..."
        if uploaded_file.size > 100 * 1024 * 1024:  # > 100MB
            spinner_msg = "⏳ Cargando archivo grande por chunks..."
        
        with st.spinner(spinner_msg):
            try:
                df, load_info = CSVLoader.load_csv(
                    uploaded_file,
                    delimiter=delimiter,
                    encoding=encoding
                )
                
                # Guarda en sesión
                st.session_state.df = df
                st.session_state.load_info = load_info
                
                # Muestra información de carga
                st.markdown('<div class="success-box">', unsafe_allow_html=True)
                if load_info.get('chunked'):
                    st.success("✅ Archivo grande cargado por chunks")
                else:
                    st.success("✅ Archivo cargado correctamente")
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Muestra información de carga con adaptaciones para chunked
                cols = st.columns(4)
                with cols[0]:
                    st.metric("Filas", f"{load_info['rows']:,}")
                with cols[1]:
                    st.metric("Columnas", load_info['columns'])
                with cols[2]:
                    st.metric("Delimitador", f"'{load_info['delimiter']}'")
                with cols[3]:
                    if load_info.get('chunked'):
                        st.metric("Modo", f"Chunks ({load_info.get('chunks_loaded', 0)})")
                    else:
                        st.metric("Modo", load_info.get('load_mode', 'permissive'))
                
                # Advertencia si es carga chunked (es una muestra)
                if load_info.get('chunked'):
                    st.markdown('<div class="info-box">', unsafe_allow_html=True)
                    st.info(
                        f"ℹ️ **Carga por Chunks**: Archivo grande ({uploaded_file.size / (1024*1024):.1f} MB) "
                        f"cargado en {load_info.get('chunks_loaded', 1)} chunk(s). "
                        "El análisis se realiza sobre el archivo completo. "
                        "Algunos cálculos de estadísticas pueden ser aproximados."
                    )
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Muestra advertencia si hay líneas problemáticas
                if load_info.get('bad_lines_count', 0) > 0:
                    st.markdown('<div class="warning-box">', unsafe_allow_html=True)
                    st.warning(
                        f"⚠️ **Pérdida de Datos Detectada**: Se omitieron {load_info['bad_lines_count']} línea(s) "
                        f"({load_info['bad_lines_count'] / (load_info['rows'] + load_info['bad_lines_count']) * 100:.1f}% del total). "
                        "Estas líneas no coincidían con el número esperado de columnas.\n\n"
                        "**Recomendación**: Revisa los detalles de las líneas problemáticas y considera "
                        "investigar la causa raíz en el archivo original."
                    )
                    
                    # Muestra ejemplos y opción de descarga
                    if load_info.get('bad_lines_sample'):
                        col1, col2 = st.columns([3, 1])
                        
                        with col1:
                            with st.expander(f"📋 Ver detalles ({len(load_info['bad_lines_sample'])} de {load_info['bad_lines_count']} problemas):"):
                                st.markdown("**Líneas problemáticas detectadas:**")
                                for bad_line in load_info['bad_lines_sample']:
                                    st.code(
                                        f"Línea {bad_line['line_number']}: "
                                        f"{bad_line['actual_columns']} col. (esperaba {bad_line['expected_columns']})\n"
                                        f"Contenido: {bad_line['content']}...",
                                        language='text'
                                    )
                        
                        with col2:
                            # Crea CSV descargable con los detalles de líneas problemáticas
                            try:
                                import pandas as pd
                                bad_lines_df = pd.DataFrame(load_info['bad_lines_sample'])
                                csv_bytes = bad_lines_df.to_csv(index=False).encode()
                                st.download_button(
                                    label="⬇️ Descargar\nDetalles",
                                    data=csv_bytes,
                                    file_name="lineas_problematicas.csv",
                                    mime="text/csv",
                                    help="Descarga un CSV con los detalles de las líneas omitidas"
                                )
                            except Exception:
                                pass  # Si falla la descarga, continúa sin error
                    
                    st.markdown('</div>', unsafe_allow_html=True)
                
                # Muestra vista previa
                st.subheader("Vista Previa de Datos")
                st.dataframe(
                    df.head(10),
                    use_container_width=True,
                    height=300
                )
                
            except CSVLoadError as e:
                st.markdown('<div class="error-box">', unsafe_allow_html=True)
                st.error(f"❌ Error al cargar el archivo:\n{str(e)}")
                st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e:
                st.markdown('<div class="error-box">', unsafe_allow_html=True)
                st.error(f"❌ Error inesperado:\n{str(e)}")
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("👆 Carga un archivo CSV para comenzar el análisis")


# ============================================================================
# TAB 2: ANÁLISIS
# ============================================================================
with tab2:
    if 'df' not in st.session_state:
        st.info("⚠️ Primero carga un archivo en la pestaña 'Cargar Archivo'")
    else:
        st.header("Análisis de Calidad de Datos")
        
        df = st.session_state.df
        
        with st.spinner("Generando perfil de datos..."):
            # Genera el perfil
            profiler = DataProfiler(df)
            profile = profiler.generate_profile()
            st.session_state.profile = profile
            
            # Información General
            st.subheader("📊 Información General")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total de Filas", profile['general_info']['total_rows'])
            with col2:
                st.metric("Total de Columnas", profile['general_info']['total_columns'])
            with col3:
                st.metric("Total de Celdas", profile['general_info']['total_cells'])
            with col4:
                st.metric("Memoria Usada", f"{profile['memory_usage']:.2f} MB")
            
            # Análisis de Nulos
            st.subheader("❌ Análisis de Valores Nulos")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(
                    "Celdas Nulas Totales",
                    profile['null_analysis']['total_null_cells']
                )
            with col2:
                st.metric(
                    "% Nulos Global",
                    f"{profile['null_analysis']['null_percent_overall']:.2f}%"
                )
            with col3:
                st.metric(
                    "Columnas Problemáticas",
                    len(profile['null_analysis']['problematic_columns'])
                )
            
            # Detalle de nulos por columna
            if profile['null_analysis']['by_column']:
                null_df = pd.DataFrame([
                    {
                        'Columna': col,
                        'Nulos': info['count'],
                        '% Nulos': f"{info['percent']:.2f}%"
                    }
                    for col, info in profile['null_analysis']['by_column'].items()
                    if info['count'] > 0
                ]).sort_values('Nulos', ascending=False)
                
                st.dataframe(null_df, use_container_width=True)
            
            # Análisis de Duplicados
            st.subheader("🔄 Análisis de Duplicados")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(
                    "Filas Duplicadas",
                    profile['duplicates']['total_duplicates']
                )
            with col2:
                st.metric(
                    "% Duplicados",
                    f"{profile['duplicates']['duplicates_percent']:.2f}%"
                )
            
            # Análisis de Strings Vacíos
            st.subheader("⚫ Cadenas Vacías o Solo Espacios")
            if profile['empty_strings']['columns_with_empty']:
                empty_df = pd.DataFrame([
                    {
                        'Columna': col,
                        'Cantidad': info['count'],
                        '% Vacías': f"{info['percent']:.2f}%"
                    }
                    for col, info in profile['empty_strings']['columns_with_empty'].items()
                ]).sort_values('Cantidad', ascending=False)
                
                st.dataframe(empty_df, use_container_width=True)
            else:
                st.success("✅ No se detectaron cadenas vacías o solo espacios")
            
            # Mezcla de Tipos de Datos
            st.subheader("🔀 Columnas con Mezcla de Tipos")
            if profile['data_type_issues']:
                st.warning("⚠️ Se detectaron columnas con múltiples tipos de datos:")
                for col, issues in profile['data_type_issues'].items():
                    with st.expander(f"📋 {col}"):
                        st.write("Tipos detectados:", issues['detected_types'])
                        st.write("Problemático:", "SÍ" if issues['is_problematic'] else "NO")
            else:
                st.success("✅ Todos los datos de cada columna son del mismo tipo")
            
            # Cardinalidad de Columnas
            st.subheader("🎯 Cardinalidad de Columnas")
            high_cardinality = [
                {
                    'Columna': col,
                    'Únicos': profile['column_profiles'][col]['unique_count'],
                    'Cardinalidad %': f"{profile['column_profiles'][col]['cardinality_ratio']*100:.2f}%"
                }
                for col in profile['column_profiles']
                if profile['column_profiles'][col]['cardinality_ratio'] >= 0.80
            ]
            
            if high_cardinality:
                high_card_df = pd.DataFrame(high_cardinality).sort_values('Cardinalidad %', ascending=False)
                st.dataframe(high_card_df, use_container_width=True)
            else:
                st.info("ℹ️ Todas las columnas tienen cardinalidad moderada")


# ============================================================================
# TAB 3: VALIDACIONES
# ============================================================================
with tab3:
    if 'df' not in st.session_state:
        st.info("⚠️ Primero carga un archivo en la pestaña 'Cargar Archivo'")
    else:
        st.header("Validaciones de Datos")
        
        df = st.session_state.df
        
        # Validación por Dominio (NUEVA FEATURE)
        with st.expander("🎯 Validación por Dominio (Opcional)", expanded=False):
            st.markdown("""
            Selecciona un dominio para validar tus datos contra reglas predefinidas.
            **Esto es referencia, no validación formal. Requiere revisión posterior.**
            """)
            
            domains = {
                'healthcare': 'Sector Sanitario',
                'ecommerce': 'E-Commerce y Retail',
                'hr': 'Recursos Humanos',
                'finance': 'Finanzas',
                'government': 'Gobierno y Datos Públicos'
            }
            
            domain_choice = st.selectbox(
                "Selecciona un dominio:",
                options=list(domains.keys()),
                format_func=lambda x: f"{x.upper()} - {domains[x]}",
                key='domain_selector'
            )
            
            if domain_choice:
                # Carga reglas del dominio
                import yaml
                try:
                    with open('./config/domain_templates.yaml', 'r', encoding='utf-8') as f:
                        all_domain_rules = yaml.safe_load(f)
                    
                    domain_rules = all_domain_rules.get(domain_choice, {})
                    
                    if domain_rules:
                        # Aplica validación
                        domain_validation = DataValidator.validate_against_domain_rules(
                            df, domain_choice, domain_rules
                        )
                        
                        if domain_validation['columns_checked']:
                            st.markdown(f"✅ **Dominio**: {domain_choice.upper()}")
                            st.markdown(f"**Columnas con reglas**: {', '.join(domain_validation['columns_checked'])}")
                            
                            # Muestra resultados
                            for col, validation in domain_validation['validations'].items():
                                col1, col2, col3 = st.columns(3)
                                
                                with col1:
                                    st.metric(
                                        f"{col}",
                                        f"{validation['violations_count']} violaciones"
                                    )
                                
                                with col2:
                                    pct = validation['violation_percent']
                                    color = "🔴" if pct > 5 else "🟡" if pct > 0 else "🟢"
                                    st.metric(f"Porcentaje", f"{color} {pct}%")
                                
                                with col3:
                                    rule_info = f"Regla: {validation['rule_name']}"
                                    if validation['rule_type'] == 'numeric':
                                        rule_info += f"\nRango: {validation['min']}-{validation['max']}"
                                    st.metric("Tipo", validation['rule_type'])
                                
                                if validation['comment']:
                                    st.caption(f"ℹ️ {validation['comment']}")
                        else:
                            st.warning(f"No se encontraron columnas coincidentes para dominio '{domain_choice}'")
                    else:
                        st.warning(f"No hay reglas definidas para dominio '{domain_choice}'")
                
                except FileNotFoundError:
                    st.error("⚠️ Archivo de reglas no encontrado (config/domain_templates.yaml)")
                except yaml.YAMLError as e:
                    st.error(f"❌ Error al leer reglas YAML: {e}")
        
        with st.spinner("Ejecutando validaciones..."):
            # Realiza validaciones
            validator = DataValidator(df)
            validation_results = validator.validate_all()
            st.session_state.validation_results = validation_results
            
            # Validación de Emails
            if validation_results['email_validation']:
                st.subheader("📧 Validación de Emails")
                for col, info in validation_results['email_validation'].items():
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(f"{col} - Válidos", info['valid_count'])
                    with col2:
                        st.metric(f"{col} - Inválidos", info['invalid_count'])
                    with col3:
                        status = "🔴 PROBLEMA" if info['is_problematic'] else "🟢 OK"
                        st.metric(f"{col} - Estado", status)
                    
                    if info['examples_invalid']:
                        with st.expander(f"Ver ejemplos inválidos de {col}"):
                            st.dataframe(pd.DataFrame(info['examples_invalid']))
            
            # Validación de Teléfonos
            if validation_results['phone_validation']:
                st.subheader("📱 Validación de Teléfonos")
                for col, info in validation_results['phone_validation'].items():
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(f"{col} - Válidos", info['valid_count'])
                    with col2:
                        st.metric(f"{col} - Inválidos", info['invalid_count'])
                    with col3:
                        status = "🔴 PROBLEMA" if info['is_problematic'] else "🟢 OK"
                        st.metric(f"{col} - Estado", status)
                    
                    if info['examples_invalid']:
                        with st.expander(f"Ver ejemplos inválidos de {col}"):
                            st.dataframe(pd.DataFrame(info['examples_invalid']))
            
            # Validación de Fechas
            if validation_results['date_validation']:
                st.subheader("📅 Validación de Fechas")
                for col, info in validation_results['date_validation'].items():
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(f"{col} - Válidas", info['valid_count'])
                    with col2:
                        st.metric(f"{col} - Inválidas", info['invalid_count'])
                    with col3:
                        status = "🔴 PROBLEMA" if info['is_problematic'] else "🟢 OK"
                        st.metric(f"{col} - Estado", status)
                    
                    if info['examples_invalid']:
                        with st.expander(f"Ver ejemplos inválidos de {col}"):
                            st.dataframe(pd.DataFrame(info['examples_invalid']))
            
            # Validación Numérica
            if validation_results['numeric_validation']:
                st.subheader("🔢 Validación Numérica")
                for col, info in validation_results['numeric_validation'].items():
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(f"{col} - Mín", f"{info['min']:.2f}")
                    with col2:
                        st.metric(f"{col} - Máx", f"{info['max']:.2f}")
                    with col3:
                        if info['negative_count'] > 0:
                            st.metric(f"{col} - Negativos", info['negative_count'])
            
            # Validación de Texto
            if validation_results['text_validation']:
                st.subheader("📝 Validación de Texto")
                for col, info in validation_results['text_validation'].items():
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric(
                            f"{col} - Caract. Especiales",
                            info['special_chars_count']
                        )
                    with col2:
                        st.metric(
                            f"{col} - Espacios Inicio/Final",
                            info['leading_trailing_spaces']
                        )
                    
                    if info['examples']:
                        with st.expander(f"Ver ejemplos de {col}"):
                            st.dataframe(pd.DataFrame(info['examples']))
            
            # URLs
            if validation_results['url_validation']:
                st.subheader("🌐 Validación de URLs")
                for col, info in validation_results['url_validation'].items():
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric(f"{col} - Válidas", info['valid_count'])
                    with col2:
                        st.metric(f"{col} - Inválidas", info['invalid_count'])
                    with col3:
                        status = "🔴 PROBLEMA" if info['is_problematic'] else "🟢 OK"
                        st.metric(f"{col} - Estado", status)


# ============================================================================
# TAB 4: RECOMENDACIONES
# ============================================================================
with tab4:
    if 'df' not in st.session_state:
        st.info("⚠️ Primero carga un archivo en la pestaña 'Cargar Archivo'")
    else:
        st.header("Recomendaciones Preliminares")
        
        st.info(
            "💡 Estas recomendaciones son **sugerencias preliminares** basadas en análisis heurístico. "
            "**Requieren validación posterior** con reglas ETL formales y consideraciones del negocio.",
            icon="ℹ️"
        )
        
        if 'profile' not in st.session_state or 'validation_results' not in st.session_state:
            st.warning("⚠️ Ejecuta primero el análisis en las pestañas anteriores")
        else:
            df = st.session_state.df
            profile = st.session_state.profile
            validation_results = st.session_state.validation_results
            
            with st.spinner("Generando recomendaciones..."):
                # Analiza severidad dinámicamente
                severity_issues = SeverityAnalyzer.analyze_severity(profile, validation_results)
                severity_counts = SeverityAnalyzer.get_severity_counts(severity_issues)
                
                # Genera recomendaciones
                rec_gen = RecommendationGenerator(profile, validation_results)
                recommendations = rec_gen.generate_all_recommendations()
                st.session_state.recommendations = recommendations
                
                # Resumen de severidad (dinámico, no placeholders)
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("🔴 Críticos", severity_counts['critical'])
                with col2:
                    st.metric("🟠 Graves", severity_counts['severe'])
                with col3:
                    st.metric("🟡 Advertencias", severity_counts['warnings'])
                with col4:
                    total_issues = (severity_counts['critical'] + severity_counts['severe'] + 
                                   severity_counts['warnings'])
                    st.metric("📋 Total", total_issues)
                
                # Muestra detalles de problemas detectados
                st.divider()
                st.subheader("⚠️ Problemas Detectados por Severidad")
                
                # Problemas críticos
                if severity_issues['critical']:
                    st.markdown("#### 🔴 CRÍTICOS")
                    for issue in severity_issues['critical']:
                        st.error(f"**{issue['type']}** en columna `{issue['column']}`: {issue['description']}")
                
                # Problemas graves
                if severity_issues['severe']:
                    st.markdown("#### 🟠 GRAVES")
                    for issue in severity_issues['severe']:
                        st.warning(f"**{issue['type']}** en columna `{issue['column']}`: {issue['description']}")
                
                # Advertencias
                if severity_issues['warnings']:
                    st.markdown("#### 🟡 ADVERTENCIAS")
                    for issue in severity_issues['warnings']:
                        st.info(f"**{issue['type']}** en columna `{issue['column']}`: {issue['description']}")
                
                if not severity_issues['critical'] and not severity_issues['severe'] and not severity_issues['warnings']:
                    st.success("✅ No se detectaron problemas de severidad")
                
                st.divider()
                
                # Recomendaciones de Limpieza
                st.subheader("🧹 Recomendaciones de Limpieza")
                cleaning_recs = recommendations['cleaning']
                if cleaning_recs:
                    for rec in cleaning_recs:
                        severity_color = {
                            'CRÍTICO': '🔴',
                            'GRAVE': '🟠',
                            'AVISO': '🟡'
                        }.get(rec['severity'], '⚪')
                        
                        with st.expander(f"{severity_color} {rec['column']} - {rec['severity']}"):
                            st.write(f"**Recomendación:** {rec['recommendation']}")
                            st.write(f"**Acción:** {rec['action']}")
                            st.write(f"**Detalles:** {rec['details']}")
                else:
                    st.success("✅ No hay problemas de limpieza detectados")
                
                st.divider()
                
                # Reglas para Base de Datos
                st.subheader("🗄️ Reglas Sugeridas para Base de Datos")
                db_rules = recommendations['database_rules']
                if db_rules:
                    for rule in db_rules[:15]:
                        with st.expander(f"📌 {rule.get('rule_type', '')} - {rule.get('column', '')}"):
                            st.write(f"**Razón:** {rule.get('reason', '')}")
                            if 'sql_constraint' in rule:
                                st.code(rule['sql_constraint'], language='sql')
                            if 'description' in rule:
                                st.write(f"**Descripción:** {rule['description']}")
                else:
                    st.info("ℹ️ No hay reglas sugeridas en este momento")
                
                st.divider()
                
                # Normalización
                st.subheader("🔧 Recomendaciones de Normalización")
                norm_recs = recommendations['normalization']
                if norm_recs:
                    for rec in norm_recs:
                        with st.expander(f"🔨 {rec['type']} - {rec['column']}"):
                            st.write(f"**Operación:** `{rec['operation']}`")
                            st.write(f"**Razón:** {rec['reason']}")
                            if 'examples' in rec:
                                st.write(f"**Ejemplo:** {rec['examples']}")
                else:
                    st.success("✅ No se requieren normalizaciones especiales")
                
                st.divider()
                
                # Sugerencias de Filtros SQL
                st.subheader("🔍 Sugerencias de Filtros SQL")
                st.write("Queries SQL que pueden utilizarse para limpiar y validar los datos:")
                
                sql_suggester = SQLFilterSuggestions(profile, validation_results, df)
                sql_suggestions = sql_suggester.generate_all_suggestions()
                
                # Agrupa por categoría
                for category, filters_list in sql_suggestions.items():
                    if filters_list:
                        category_name = category.replace('_', ' ').title()
                        st.markdown(f"#### {category_name}")
                        
                        for filter_item in filters_list[:5]:  # Máximo 5 por categoría
                            severity = filter_item.get('severity', 'AVISO')
                            severity_icon = {
                                'CRÍTICO': '🔴',
                                'GRAVE': '🟠',
                                'AVISO': '🟡'
                            }.get(severity, '⚪')
                            
                            column = filter_item.get('column', 'GENERAL')
                            problem = filter_item.get('problem', '')
                            
                            with st.expander(f"{severity_icon} {column} - {problem}"):
                                # SQL principal
                                filter_sql = filter_item.get('filter_sql', filter_item.get('filter_sql_simple', 'N/A'))
                                st.code(filter_sql, language='sql')
                                
                                # Descripción
                                description = filter_item.get('description', '')
                                if description:
                                    st.write(f"**Descripción:** {description}")
                                
                                # Impacto
                                impact = filter_item.get('impact', '')
                                if impact:
                                    st.write(f"**Impacto:** {impact}")
                                
                                # Alternativas
                                if 'filter_type_2' in filter_item:
                                    st.write("**Alternativa:**")
                                    st.code(filter_item['filter_type_2'], language='sql')
                                
                                if 'alternative' in filter_item:
                                    st.write("**Alternativa avanzada:**")
                                    st.code(filter_item['alternative'], language='sql')
                                
                                if 'cleanup_sql' in filter_item:
                                    st.write("**Para limpiar datos:**")
                                    st.code(filter_item['cleanup_sql'], language='sql')
                        
                        st.divider()
                
                # Nota final
                st.info("💡 **Nota:** Estos filtros SQL son sugerencias basadas en los problemas detectados. Ajústalos según tu base de datos específica y requiere antes su validación.")


# ============================================================================
# TAB 5: DATOS PROBLEMÁTICOS
# ============================================================================
with tab5:
    if 'df' not in st.session_state:
        st.info("⚠️ Primero carga un archivo en la pestaña 'Cargar Archivo'")
    else:
        st.header("Muestras de Datos Problemáticos")
        
        df = st.session_state.df
        
        if 'profile' not in st.session_state:
            st.warning("⚠️ Ejecuta primero el análisis")
        else:
            profile = st.session_state.profile
            
            # Filas Duplicadas
            if profile['duplicates']['examples']:
                st.subheader("🔄 Filas Duplicadas (Ejemplos)")
                dup_df = pd.DataFrame(profile['duplicates']['examples'])
                st.dataframe(dup_df, use_container_width=True)
            else:
                st.success("✅ No se encontraron filas duplicadas")
            
            st.divider()
            
            # Columnas con muchos nulos
            st.subheader("❌ Columnas Problemáticas por Nulos")
            problematic_cols = profile['null_analysis']['problematic_columns']
            if problematic_cols:
                for col, info in problematic_cols.items():
                    st.warning(
                        f"**{col}**: {info['null_count']} nulos "
                        f"({info['null_percent']:.1f}%) - Estado: {info['status']}"
                    )
            else:
                st.success("✅ No hay columnas problemáticas por nulos")
            
            st.divider()
            
            # Columnas con mezcla de tipos
            st.subheader("🔀 Columnas con Mezcla de Tipos")
            type_issues = profile['data_type_issues']
            if type_issues:
                for col, issues in type_issues.items():
                    st.warning(f"**{col}**: {issues['detected_types']}")
            else:
                st.success("✅ Todas las columnas tienen tipos de datos consistentes")


# ============================================================================
# TAB 6: DESCARGAR REPORTE
# ============================================================================
with tab6:
    st.header("Descarga de Reportes")
    
    if 'df' not in st.session_state:
        st.info("⚠️ Primero carga un archivo en la pestaña 'Cargar Archivo'")
    elif 'profile' not in st.session_state:
        st.warning("⚠️ Ejecuta primero el análisis en las pestañas anteriores")
    else:
        st.success("✅ Todos los análisis completados. Puedes descargar los reportes.")
        
        df = st.session_state.df
        profile = st.session_state.profile
        validation_results = st.session_state.validation_results
        recommendations = st.session_state.recommendations
        
        # Genera nombre del archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_base = f"reporte_datos_{timestamp}"
        
        # Generador de reportes
        report_gen = ReportGenerator(df, profile, validation_results, recommendations)
        
        col1, col2 = st.columns(2)
        
        # Exportar Excel
        with col1:
            if st.button("📊 Generar Reporte Excel", key="excel_btn", use_container_width=True):
                with st.spinner("Generando reporte Excel..."):
                    try:
                        filepath = report_gen.generate_excel_report(filename_base)
                        
                        # Lee el archivo para descargar
                        with open(filepath, 'rb') as f:
                            excel_data = f.read()
                        
                        st.download_button(
                            label="⬇️ Descargar Excel",
                            data=excel_data,
                            file_name=f"{filename_base}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                        
                        st.success(f"✅ Reporte guardado en: {filepath}")
                    except Exception as e:
                        st.error(f"❌ Error al generar Excel: {str(e)}")
        
        # Exportar HTML
        with col2:
            if st.button("🌐 Generar Reporte HTML", key="html_btn", use_container_width=True):
                with st.spinner("Generando reporte HTML..."):
                    try:
                        filepath = report_gen.generate_html_report(filename_base)
                        
                        # Lee el archivo para descargar
                        with open(filepath, 'r', encoding='utf-8') as f:
                            html_data = f.read()
                        
                        st.download_button(
                            label="⬇️ Descargar HTML",
                            data=html_data,
                            file_name=f"{filename_base}.html",
                            mime="text/html"
                        )
                        
                        st.success(f"✅ Reporte guardado en: {filepath}")
                    except Exception as e:
                        st.error(f"❌ Error al generar HTML: {str(e)}")
        
        st.divider()
        st.info("💾 Los reportes se guardan en la carpeta `output/` del proyecto")


# ============================================================================
# FOOTER
# ============================================================================
st.divider()
st.markdown("""
---
**Analizador de Calidad de Datos CSV** | Versión 1.0.0
Desarrollado para análisis de datos antes de cargar a base de datos
""")
