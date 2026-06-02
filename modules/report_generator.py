"""
Módulo de generador de reportes.
Genera reportes en Excel y HTML con análisis completo de datos.
"""

import pandas as pd
from datetime import datetime
import os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from utils.helpers import ReportHelper, StringHelper
from modules.severity_analyzer import SeverityAnalyzer


class ReportGenerator:
    """Genera reportes en Excel y HTML con los análisis realizados."""
    
    def __init__(self, df, profile, validation_results, recommendations):
        """
        Inicializa el generador de reportes.
        
        Args:
            df (pd.DataFrame): DataFrame original
            profile (dict): Perfil del DataFrame
            validation_results (dict): Resultados de validaciones
            recommendations (dict): Recomendaciones generadas
        """
        self.df = df
        self.profile = profile
        self.validation_results = validation_results
        self.recommendations = recommendations
        ReportHelper.create_output_directory()
    
    def generate_excel_report(self, filename=None):
        """
        Genera un reporte completo en Excel.
        
        Args:
            filename (str): Nombre del archivo (sin extensión)
        
        Returns:
            str: Ruta del archivo generado
        """
        if filename is None:
            filename = ReportHelper.get_report_filename('reporte_datos')
        
        filepath = f'./output/{filename}.xlsx'
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Hoja 1: Resumen Ejecutivo
            self._write_summary_sheet(writer)
            
            # Hoja 2: Información General
            self._write_general_info_sheet(writer)
            
            # Hoja 3: Análisis de Nulos
            self._write_null_analysis_sheet(writer)
            
            # Hoja 4: Análisis de Duplicados
            self._write_duplicates_sheet(writer)
            
            # Hoja 5: Perfil de Columnas
            self._write_column_profile_sheet(writer)
            
            # Hoja 6: Validaciones
            self._write_validation_sheet(writer)
            
            # Hoja 7: Recomendaciones de Limpieza
            self._write_cleaning_recommendations_sheet(writer)
            
            # Hoja 8: Reglas para Base de Datos
            self._write_database_rules_sheet(writer)
            
            # Hoja 9: Normalización
            self._write_normalization_sheet(writer)
            
            # Hoja 10: Muestras de Datos Problemáticos
            self._write_problem_samples_sheet(writer)
        
        return filepath
    
    def _write_summary_sheet(self, writer):
        """Escribe la hoja de resumen ejecutivo con métricas dinámicas."""
        # Calcula severidad dinámicamente
        severity_issues = SeverityAnalyzer.analyze_severity(
            self.profile,
            self.validation_results
        )
        severity_counts = SeverityAnalyzer.get_severity_counts(severity_issues)
        
        summary_data = {
            'Métrica': [
                'Fecha del Reporte',
                'Total de Filas',
                'Total de Columnas',
                'Total de Celdas',
                'Uso de Memoria',
                'Filas Completas (sin nulos)',
                '% Filas Completas',
                'Valores Nulos Totales',
                '% Nulos Global',
                'Filas Duplicadas',
                '% Duplicados',
                'Columnas Problemáticas',
                'Problemas Críticos',
                'Problemas Graves',
                'Advertencias'
            ],
            'Valor': [
                datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
                str(self.profile['general_info']['total_rows']),
                str(self.profile['general_info']['total_columns']),
                str(self.profile['general_info']['total_cells']),
                f"{self.profile['memory_usage']:.2f} MB",
                str(self.profile['null_analysis']['complete_rows']),
                f"{self.profile['null_analysis']['complete_rows_percent']:.2f}%",
                str(self.profile['null_analysis']['total_null_cells']),
                f"{self.profile['null_analysis']['null_percent_overall']:.2f}%",
                str(self.profile['duplicates']['total_duplicates']),
                f"{self.profile['duplicates']['duplicates_percent']:.2f}%",
                str(len(self.profile.get('data_type_issues', {}))),
                str(severity_counts['critical']),
                str(severity_counts['severe']),
                str(severity_counts['warnings'])
            ]
        }
        
        df_summary = pd.DataFrame(summary_data)
        df_summary.to_excel(writer, sheet_name='RESUMEN_EJECUTIVO', index=False)
    
    def _write_general_info_sheet(self, writer):
        """Escribe información general del dataset."""
        info_data = {
            'Información': [
                'Total de Filas',
                'Total de Columnas',
                'Columnas Identificadas',
            ],
            'Detalle': [
                self.profile['general_info']['total_rows'],
                self.profile['general_info']['total_columns'],
                ', '.join(self.profile['general_info']['column_names'][:10])
            ]
        }
        
        df_info = pd.DataFrame(info_data)
        df_info.to_excel(writer, sheet_name='INFO_GENERAL', index=False)
    
    def _write_null_analysis_sheet(self, writer):
        """Escribe análisis de valores nulos, asegurando que la hoja siempre existe."""
        null_data = []
        
        for col, info in self.profile['null_analysis']['by_column'].items():
            null_data.append({
                'Columna': col,
                'Nulos': info['count'],
                '% Nulos': f"{info['percent']:.2f}%",
                '% Utilidad': f"{info['utilization_percent']:.2f}%",
                'Estado': 'CRÍTICO' if info['percent'] >= 80 else 'GRAVE' if info['percent'] >= 40 else 'OK'
            })
        
        # Si no hay nulos, añade una fila indicando que no hay incidencias
        if not null_data:
            null_data.append({
                'Columna': 'N/A',
                'Nulos': 0,
                '% Nulos': '0.00%',
                '% Utilidad': '100.00%',
                'Estado': 'Sin incidencias detectadas'
            })
        
        df_nulls = pd.DataFrame(null_data)
        df_nulls.to_excel(writer, sheet_name='ANALISIS_NULOS', index=False)
        
        # Agregar hoja adicional con resumen de filas completas y utilidad por columna
        self._write_rows_and_utilization_sheet(writer)
    
    def _write_rows_and_utilization_sheet(self, writer):
        """Escribe análisis de filas completas y utilidad por columna."""
        # Datos de resumen de filas completas
        complete_rows_data = {
            'Métrica': [
                'Total de Filas',
                'Filas Completas (sin nulos)',
                '% Filas Completas',
                'Filas con al menos 1 nulo'
            ],
            'Valor': [
                str(self.profile['null_analysis'].get('complete_rows', 0) + 
                    (self.profile['general_info']['total_rows'] - 
                     self.profile['null_analysis'].get('complete_rows', 0))),
                str(self.profile['null_analysis'].get('complete_rows', 0)),
                f"{self.profile['null_analysis'].get('complete_rows_percent', 0):.2f}%",
                str(self.profile['general_info']['total_rows'] - 
                    self.profile['null_analysis'].get('complete_rows', 0))
            ]
        }
        
        df_complete = pd.DataFrame(complete_rows_data)
        df_complete.to_excel(writer, sheet_name='FILAS_Y_UTILIDAD', index=False, startrow=0)
        
        # Datos de utilidad por columna
        utilization_data = []
        for col, utilization_pct in self.profile['null_analysis'].get('column_utilization', {}).items():
            utilization_data.append({
                'Columna': col,
                '% Utilidad': f"{utilization_pct:.2f}%",
                'Estatus': 'CRÍTICO' if utilization_pct < 50 else 'BAJO' if utilization_pct < 80 else 'ACEPTABLE'
            })
        
        if utilization_data:
            df_utilization = pd.DataFrame(utilization_data)
            df_utilization.to_excel(writer, sheet_name='FILAS_Y_UTILIDAD', index=False, startrow=6)
    
    def _write_duplicates_sheet(self, writer):
        """Escribe análisis de duplicados."""
        dup_data = {
            'Aspecto': [
                'Total de Duplicados',
                '% de Duplicados',
                'Primeras Filas Duplicadas'
            ],
            'Detalle': [
                str(self.profile['duplicates']['total_duplicates']),
                f"{self.profile['duplicates']['duplicates_percent']:.2f}%",
                'Ver ejemplos en datos'
            ]
        }
        
        df_dups = pd.DataFrame(dup_data)
        df_dups.to_excel(writer, sheet_name='DUPLICADOS', index=False)
    
    def _write_column_profile_sheet(self, writer):
        """Escribe perfil detallado de columnas."""
        profile_data = []
        
        for col, prof in self.profile['column_profiles'].items():
            profile_data.append({
                'Columna': col,
                'Tipo': prof['dtype'],
                'Sugerencia': prof['type_hint'] or 'N/A',
                'No Nulos': prof['non_null_count'],
                'Nulos': prof['null_count'],
                '% Nulos': f"{prof['null_percent']:.2f}%",
                'Únicos': prof['unique_count'],
                'Cardinalidad': f"{prof['cardinality_ratio']*100:.2f}%"
            })
        
        df_profiles = pd.DataFrame(profile_data)
        df_profiles.to_excel(writer, sheet_name='PERFIL_COLUMNAS', index=False)
    
    def _write_validation_sheet(self, writer):
        """Escribe resultados de validaciones, asegurando que la hoja siempre existe."""
        validation_data = []
        
        # Validaciones de email
        for col, info in self.validation_results.get('email_validation', {}).items():
            validation_data.append({
                'Columna': col,
                'Tipo Validación': 'Email',
                'Válidos': info['valid_count'],
                'Inválidos': info['invalid_count'],
                '% Inválidos': f"{info['invalid_percent']:.2f}%",
                'Estado': 'PROBLEMÁTICO' if info['is_problematic'] else 'OK'
            })
        
        # Validaciones de teléfono
        for col, info in self.validation_results.get('phone_validation', {}).items():
            validation_data.append({
                'Columna': col,
                'Tipo Validación': 'Teléfono',
                'Válidos': info['valid_count'],
                'Inválidos': info['invalid_count'],
                '% Inválidos': f"{info['invalid_percent']:.2f}%",
                'Estado': 'PROBLEMÁTICO' if info['is_problematic'] else 'OK'
            })
        
        # Si no hay validaciones, añade una fila indicando que no hay incidencias
        if not validation_data:
            validation_data.append({
                'Columna': 'N/A',
                'Tipo Validación': 'N/A',
                'Válidos': 0,
                'Inválidos': 0,
                '% Inválidos': '0.00%',
                'Estado': 'Sin incidencias detectadas'
            })
        
        df_validations = pd.DataFrame(validation_data)
        df_validations.to_excel(writer, sheet_name='VALIDACIONES', index=False)
    
    def _write_cleaning_recommendations_sheet(self, writer):
        """Escribe recomendaciones de limpieza, asegurando que la hoja siempre existe."""
        cleaning_recs = self.recommendations.get('cleaning', [])
        
        clean_data = []
        if cleaning_recs:
            for rec in cleaning_recs:
                clean_data.append({
                    'Severidad': rec.get('severity', ''),
                    'Columna': rec.get('column', ''),
                    'Recomendación': StringHelper.truncate_string(rec.get('recommendation', ''), 100),
                    'Acción': rec.get('action', '')
                })
        
        # Si no hay recomendaciones, añade una fila indicando que no hay incidencias
        if not clean_data:
            clean_data.append({
                'Severidad': 'N/A',
                'Columna': 'N/A',
                'Recomendación': 'Sin incidencias detectadas',
                'Acción': 'N/A'
            })
        
        df_cleaning = pd.DataFrame(clean_data)
        df_cleaning.to_excel(writer, sheet_name='LIMPIEZA', index=False)
    
    def _write_database_rules_sheet(self, writer):
        """Escribe reglas sugeridas para base de datos, asegurando que la hoja siempre existe."""
        db_rules = self.recommendations.get('database_rules', [])
        
        rules_data = []
        if db_rules:
            for rule in db_rules:
                rules_data.append({
                    'Tipo de Regla': rule.get('rule_type', ''),
                    'Columna': rule.get('column', ''),
                    'SQL/Descripción': StringHelper.truncate_string(
                        rule.get('sql_constraint', rule.get('description', '')),
                        100
                    ),
                    'Razón': StringHelper.truncate_string(rule.get('reason', ''), 100)
                })
        
        # Si no hay reglas, añade una fila indicando que no hay incidencias
        if not rules_data:
            rules_data.append({
                'Tipo de Regla': 'N/A',
                'Columna': 'N/A',
                'SQL/Descripción': 'Sin incidencias detectadas',
                'Razón': 'N/A'
            })
        
        df_rules = pd.DataFrame(rules_data)
        df_rules.to_excel(writer, sheet_name='REGLAS_BD', index=False)
    
    def _write_normalization_sheet(self, writer):
        """Escribe recomendaciones de normalización, asegurando que la hoja siempre existe."""
        norm_recs = self.recommendations.get('normalization', [])
        
        norm_data = []
        if norm_recs:
            for rec in norm_recs:
                norm_data.append({
                    'Tipo': rec.get('type', ''),
                    'Columna': rec.get('column', ''),
                    'Operación': rec.get('operation', ''),
                    'Razón': StringHelper.truncate_string(rec.get('reason', ''), 100)
                })
        
        # Si no hay recomendaciones, añade una fila indicando que no hay incidencias
        if not norm_data:
            norm_data.append({
                'Tipo': 'N/A',
                'Columna': 'N/A',
                'Operación': 'Sin incidencias detectadas',
                'Razón': 'N/A'
            })
        
        df_norm = pd.DataFrame(norm_data)
        df_norm.to_excel(writer, sheet_name='NORMALIZACION', index=False)
    
    def _write_problem_samples_sheet(self, writer):
        """Escribe muestras de datos problemáticos."""
        # Primeras filas duplicadas si existen
        if self.profile['duplicates']['examples']:
            examples_df = pd.DataFrame(self.profile['duplicates']['examples'])
            examples_df.to_excel(writer, sheet_name='MUESTRAS_PROBLEMATICAS', index=False)
    
    def generate_html_report(self, filename=None):
        """
        Genera un reporte en HTML.
        
        Args:
            filename (str): Nombre del archivo (sin extensión)
        
        Returns:
            str: Ruta del archivo generado
        """
        if filename is None:
            filename = ReportHelper.get_report_filename('reporte_datos')
        
        filepath = f'./output/{filename}.html'
        
        html_content = self._build_html_report()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return filepath
    
    def _build_html_report(self):
        """Construye el contenido HTML del reporte."""
        timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
        
        html = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Reporte de Análisis de Datos CSV</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                }}
                .header {{
                    background-color: #2c3e50;
                    color: white;
                    padding: 20px;
                    border-radius: 5px;
                    margin-bottom: 20px;
                }}
                .section {{
                    background-color: white;
                    padding: 15px;
                    margin-bottom: 15px;
                    border-radius: 5px;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                }}
                .section h2 {{
                    color: #2c3e50;
                    border-bottom: 3px solid #3498db;
                    padding-bottom: 10px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin-top: 10px;
                }}
                th {{
                    background-color: #3498db;
                    color: white;
                    padding: 10px;
                    text-align: left;
                }}
                td {{
                    padding: 8px;
                    border-bottom: 1px solid #ddd;
                }}
                tr:hover {{
                    background-color: #f5f5f5;
                }}
                .critical {{ color: #e74c3c; font-weight: bold; }}
                .serious {{ color: #f39c12; font-weight: bold; }}
                .warning {{ color: #f1c40f; font-weight: bold; }}
                .ok {{ color: #27ae60; font-weight: bold; }}
                .metric {{
                    display: inline-block;
                    margin: 10px 20px 10px 0;
                }}
                .metric-value {{
                    font-size: 24px;
                    font-weight: bold;
                    color: #3498db;
                }}
                .metric-label {{
                    font-size: 12px;
                    color: #7f8c8d;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📊 Reporte de Análisis de Datos CSV</h1>
                <p>Generado: {timestamp}</p>
            </div>
            
            {self._build_summary_section()}
            {self._build_general_info_section()}
            {self._build_null_analysis_section()}
            {self._build_duplicates_section()}
            {self._build_column_profile_section()}
            {self._build_validation_section()}
            {self._build_recommendations_section()}
            
        </body>
        </html>
        """
        
        return html
    
    def _build_summary_section(self):
        """Construye sección de resumen."""
        summary = f"""
        <div class="section">
            <h2>📈 Resumen Ejecutivo</h2>
            <div class="metric">
                <div class="metric-value">{self.profile['general_info']['total_rows']}</div>
                <div class="metric-label">Filas</div>
            </div>
            <div class="metric">
                <div class="metric-value">{self.profile['general_info']['total_columns']}</div>
                <div class="metric-label">Columnas</div>
            </div>
            <div class="metric">
                <div class="metric-value">{self.profile['duplicates']['total_duplicates']}</div>
                <div class="metric-label">Duplicados</div>
            </div>
            <div class="metric">
                <div class="metric-value">{self.profile['null_analysis']['total_null_cells']}</div>
                <div class="metric-label">Celdas Nulas</div>
            </div>
        </div>
        """
        return summary
    
    def _build_general_info_section(self):
        """Construye sección de información general."""
        cols = ', '.join(self.profile['general_info']['column_names'][:15])
        
        return f"""
        <div class="section">
            <h2>ℹ️ Información General</h2>
            <table>
                <tr>
                    <th>Métrica</th>
                    <th>Valor</th>
                </tr>
                <tr>
                    <td>Total de Filas</td>
                    <td>{self.profile['general_info']['total_rows']}</td>
                </tr>
                <tr>
                    <td>Total de Columnas</td>
                    <td>{self.profile['general_info']['total_columns']}</td>
                </tr>
                <tr>
                    <td>Uso de Memoria</td>
                    <td>{self.profile['memory_usage']:.2f} MB</td>
                </tr>
            </table>
        </div>
        """
    
    def _build_null_analysis_section(self):
        """Construye sección de análisis de nulos."""
        null_info = self.profile['null_analysis']['by_column']
        
        rows = ''
        for col, info in null_info.items():
            status = 'critical' if info['percent'] >= 80 else 'serious' if info['percent'] >= 40 else 'ok'
            rows += f"""
            <tr>
                <td>{col}</td>
                <td>{info['count']}</td>
                <td class="{status}">{info['percent']:.2f}%</td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2>❌ Análisis de Valores Nulos</h2>
            <p>Total de celdas nulas: <strong>{self.profile['null_analysis']['total_null_cells']}</strong></p>
            <table>
                <tr>
                    <th>Columna</th>
                    <th>Cantidad</th>
                    <th>Porcentaje</th>
                </tr>
                {rows}
            </table>
        </div>
        """
    
    def _build_duplicates_section(self):
        """Construye sección de duplicados."""
        return f"""
        <div class="section">
            <h2>🔄 Análisis de Duplicados</h2>
            <p>Filas duplicadas: <strong class="critical">{self.profile['duplicates']['total_duplicates']}</strong></p>
            <p>Porcentaje: <strong>{self.profile['duplicates']['duplicates_percent']:.2f}%</strong></p>
        </div>
        """
    
    def _build_column_profile_section(self):
        """Construye sección de perfil de columnas."""
        rows = ''
        for col, prof in self.profile['column_profiles'].items():
            rows += f"""
            <tr>
                <td>{col}</td>
                <td>{prof['dtype']}</td>
                <td>{prof['unique_count']}</td>
                <td class="{'critical' if prof['null_percent'] >= 40 else 'ok'}">{prof['null_percent']:.2f}%</td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2>📋 Perfil de Columnas</h2>
            <table>
                <tr>
                    <th>Columna</th>
                    <th>Tipo</th>
                    <th>Únicos</th>
                    <th>% Nulos</th>
                </tr>
                {rows}
            </table>
        </div>
        """
    
    def _build_validation_section(self):
        """Construye sección de validaciones."""
        validation_info = []
        
        for col, info in self.validation_results.get('email_validation', {}).items():
            validation_info.append((col, 'Email', info['invalid_count'], info['invalid_percent']))
        
        for col, info in self.validation_results.get('phone_validation', {}).items():
            validation_info.append((col, 'Teléfono', info['invalid_count'], info['invalid_percent']))
        
        if not validation_info:
            return '<div class="section"><h2>✅ Validaciones</h2><p>No se detectaron validaciones requeridas.</p></div>'
        
        rows = ''
        for col, val_type, invalid, invalid_pct in validation_info:
            rows += f"""
            <tr>
                <td>{col}</td>
                <td>{val_type}</td>
                <td class="{'critical' if invalid > 0 else 'ok'}">{invalid}</td>
                <td>{invalid_pct:.2f}%</td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2>✅ Validaciones</h2>
            <table>
                <tr>
                    <th>Columna</th>
                    <th>Tipo</th>
                    <th>Inválidos</th>
                    <th>% Inválido</th>
                </tr>
                {rows}
            </table>
        </div>
        """
    
    def _build_recommendations_section(self):
        """Construye sección de recomendaciones."""
        cleaning_recs = self.recommendations.get('cleaning', [])
        
        if not cleaning_recs:
            return '<div class="section"><h2>💡 Recomendaciones</h2><p>No hay recomendaciones en este momento.</p></div>'
        
        rows = ''
        for rec in cleaning_recs[:10]:  # Primeras 10
            severity_class = 'critical' if rec.get('severity') == 'CRÍTICO' else 'serious' if rec.get('severity') == 'GRAVE' else 'warning'
            rows += f"""
            <tr>
                <td class="{severity_class}">{rec.get('severity', '')}</td>
                <td>{rec.get('column', '')}</td>
                <td>{StringHelper.truncate_string(rec.get('recommendation', ''), 50)}</td>
            </tr>
            """
        
        return f"""
        <div class="section">
            <h2>💡 Recomendaciones Principales</h2>
            <table>
                <tr>
                    <th>Severidad</th>
                    <th>Columna</th>
                    <th>Recomendación</th>
                </tr>
                {rows}
            </table>
        </div>
        """
