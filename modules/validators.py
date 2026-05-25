"""
Módulo de validadores.
Realiza validaciones específicas en datos como emails, teléfonos, fechas, etc.
"""

import pandas as pd
import re
from datetime import datetime
from dateutil import parser as date_parser
from utils.patterns import ValidationPatterns
from utils.helpers import ValidationHelper
from config import (
    CONTENT_DETECTION_THRESHOLD, 
    SAMPLE_SIZE_FOR_CONTENT_DETECTION,
    ALLOWED_DATE_FORMATS,
    DEFAULT_DAYFIRST,
    DATE_FORMAT_CONSISTENCY_THRESHOLD
)


class DataValidator:
    """Clase para validar diferentes tipos de datos."""
    
    def __init__(self, df):
        """
        Inicializa el validador con un DataFrame.
        
        Args:
            df (pd.DataFrame): DataFrame a validar
        """
        self.df = df
        self.validation_results = {}
    
    def validate_all(self):
        """
        Ejecuta todas las validaciones.
        
        Returns:
            dict: Resultados de todas las validaciones
        """
        # Detecta tipos de dato por contenido
        content_types = self._detect_column_types_by_content()
        
        self.validation_results = {
            'email_validation': self._validate_emails(content_types),
            'phone_validation': self._validate_phones(content_types),
            'date_validation': self._validate_dates(content_types),
            'numeric_validation': self._validate_numerics(),
            'text_validation': self._validate_text(),
            'url_validation': self._validate_urls(content_types),
        }
        
        return self.validation_results
    
    def _detect_column_types_by_content(self):
        """
        Detecta tipos de dato basándose en el análisis del contenido de las columnas.
        
        Analiza una muestra de valores no nulos en cada columna y determina qué tipo
        de dato es más probable según el porcentaje de valores que coinciden con
        patrones de email, teléfono, fecha, URL, etc.
        
        Returns:
            dict: {
                'column_name': 'detected_type' o None,
                ...
            }
        """
        detected_types = {}
        
        for col in self.df.columns:
            # Obtiene una muestra de valores no nulos
            sample = self.df[col].dropna().head(SAMPLE_SIZE_FOR_CONTENT_DETECTION)
            
            if len(sample) == 0:
                continue
            
            type_counts = {
                'email': 0,
                'phone': 0,
                'date': 0,
                'url': 0,
                'numeric': 0,
                'other': 0
            }
            
            # Analiza cada valor en la muestra
            for value in sample:
                value_str = str(value).strip()
                
                # Verifica qué tipo es más probable
                if ValidationPatterns.is_valid_email(value_str):
                    type_counts['email'] += 1
                elif ValidationPatterns.is_valid_phone(value_str):
                    type_counts['phone'] += 1
                elif ValidationPatterns.is_valid_url(value_str):
                    type_counts['url'] += 1
                elif ValidationPatterns.is_valid_date_format(value_str):
                    type_counts['date'] += 1
                elif ValidationPatterns.is_float(value_str):
                    type_counts['numeric'] += 1
                else:
                    type_counts['other'] += 1
            
            # Calcula porcentajes
            total_values = len(sample)
            type_percentages = {
                k: v / total_values for k, v in type_counts.items()
            }
            
            # Encuentra el tipo más común que supere el umbral
            best_type = None
            best_percent = 0
            for data_type, percentage in type_percentages.items():
                if percentage >= CONTENT_DETECTION_THRESHOLD and percentage > best_percent:
                    best_type = data_type
                    best_percent = percentage
            
            detected_types[col] = best_type if best_type else None
        
        return detected_types
    
    def _validate_emails(self, content_types=None):
        """Valida columnas de email."""
        if content_types is None:
            content_types = {}
        email_results = {}
        
        # Detecta columnas de email por nombre
        email_columns_by_name = [
            col for col in self.df.columns
            if any(x in col.lower() for x in ['email', 'correo', 'mail'])
        ]
        
        # Detecta columnas de email por contenido
        email_columns_by_content = [
            col for col, detected_type in content_types.items()
            if detected_type == 'email'
        ]
        
        # Combina ambas listas (evita duplicados)
        email_columns = list(set(email_columns_by_name + email_columns_by_content))
        
        for col in email_columns:
            invalid_emails = []
            valid_count = 0
            invalid_count = 0
            
            for idx, value in enumerate(self.df[col].items()):
                if pd.isna(value[1]):
                    continue
                
                if ValidationPatterns.is_valid_email(value[1]):
                    valid_count += 1
                else:
                    invalid_count += 1
                    if len(invalid_emails) < 5:
                        invalid_emails.append({
                            'row': idx + 1,
                            'value': str(value[1])[:50]
                        })
            
            email_results[col] = {
                'valid_count': valid_count,
                'invalid_count': invalid_count,
                'invalid_percent': (
                    (invalid_count / (valid_count + invalid_count) * 100)
                    if (valid_count + invalid_count) > 0 else 0
                ),
                'examples_invalid': invalid_emails,
                'is_problematic': invalid_count > 0,
                'detected_by_content': col in email_columns_by_content
            }
        
        return email_results
    
    def _validate_phones(self, content_types=None):
        """Valida columnas de teléfono."""
        if content_types is None:
            content_types = {}
        
        phone_results = {}
        
        # Detecta columnas de teléfono por nombre
        phone_columns_by_name = [
            col for col in self.df.columns
            if any(x in col.lower() for x in ['telefono', 'phone', 'celular', 'mobile'])
        ]
        
        # Detecta columnas de teléfono por contenido
        phone_columns_by_content = [
            col for col, detected_type in content_types.items()
            if detected_type == 'phone'
        ]
        
        # Combina ambas listas (evita duplicados)
        phone_columns = list(set(phone_columns_by_name + phone_columns_by_content))
        
        for col in phone_columns:
            invalid_phones = []
            valid_count = 0
            invalid_count = 0
            
            for idx, value in enumerate(self.df[col].items()):
                if pd.isna(value[1]):
                    continue
                
                if ValidationPatterns.is_valid_phone(value[1]):
                    valid_count += 1
                else:
                    invalid_count += 1
                    if len(invalid_phones) < 5:
                        invalid_phones.append({
                            'row': idx + 1,
                            'value': str(value[1])[:50]
                        })
            
            phone_results[col] = {
                'valid_count': valid_count,
                'invalid_count': invalid_count,
                'invalid_percent': (
                    (invalid_count / (valid_count + invalid_count) * 100)
                    if (valid_count + invalid_count) > 0 else 0
                ),
                'examples_invalid': invalid_phones,
                'is_problematic': invalid_count > 0,
                'detected_by_content': col in phone_columns_by_content
            }
        
        return phone_results
    
    def _validate_dates(self, content_types=None):
        """Valida columnas de fecha con detección de formato inconsistente."""
        if content_types is None:
            content_types = {}
        
        date_results = {}
        
        # Detecta columnas de fecha por nombre
        date_columns_by_name = [
            col for col in self.df.columns
            if any(x in col.lower() for x in ['fecha', 'date', 'time', 'hora', 'timestamp'])
        ]
        
        # Detecta columnas de fecha por contenido
        date_columns_by_content = [
            col for col, detected_type in content_types.items()
            if detected_type == 'date'
        ]
        
        # Combina ambas listas (evita duplicados)
        date_columns = list(set(date_columns_by_name + date_columns_by_content))
        
        for col in date_columns:
            invalid_dates = []
            valid_dates = []
            format_patterns = {}  # Rastrear qué formato usa cada fecha
            ambiguous_dates = []  # Fechas que podrían ser DD/MM o MM/DD
            invalid_count = 0
            
            for idx, value in enumerate(self.df[col].items()):
                if pd.isna(value[1]):
                    continue
                
                value_str = str(value[1]).strip()
                
                # Intenta parsear la fecha
                try:
                    parsed_date = date_parser.parse(value_str, dayfirst=DEFAULT_DAYFIRST)
                    
                    # Intenta detectar el formato usado
                    detected_format = None
                    for fmt in ALLOWED_DATE_FORMATS:
                        try:
                            datetime.strptime(value_str, fmt)
                            detected_format = fmt
                            break
                        except ValueError:
                            continue
                    
                    if detected_format:
                        format_patterns[detected_format] = format_patterns.get(detected_format, 0) + 1
                        valid_dates.append({
                            'value': value_str,
                            'format': detected_format,
                            'parsed': parsed_date
                        })
                    else:
                        # Fecha válida pero formato no estándar
                        format_patterns['<formato_no_estándar>'] = format_patterns.get('<formato_no_estándar>', 0) + 1
                        
                        # Detecta ambigüedad potencial (p.ej., 03/04/2024 podría ser 3-abr o 4-mar)
                        if '-' in value_str or '/' in value_str:
                            parts = re.split('[/-]', value_str)
                            if len(parts) >= 2 and int(parts[0]) <= 12 and int(parts[1]) <= 12:
                                ambiguous_dates.append({
                                    'row': idx + 1,
                                    'value': value_str,
                                    'issue': 'Ambiguo: podría ser DD/MM o MM/DD'
                                })
                        
                        valid_dates.append({
                            'value': value_str,
                            'format': '<no_estándar>',
                            'parsed': parsed_date
                        })
                
                except Exception:
                    invalid_count += 1
                    if len(invalid_dates) < 5:
                        invalid_dates.append({
                            'row': idx + 1,
                            'value': value_str[:50]
                        })
            
            # Calcula consistencia de formato como proporción (0.0-1.0)
            if format_patterns:
                most_common_format = max(format_patterns, key=format_patterns.get)
                most_common_count = format_patterns[most_common_format]
                total_valid = len(valid_dates)
                format_consistency = (most_common_count / total_valid) if total_valid > 0 else 0.0
            else:
                format_consistency = 0.0
                most_common_format = None
            
            date_results[col] = {
                'valid_count': len(valid_dates),
                'invalid_count': invalid_count,
                'invalid_percent': (
                    (invalid_count / (len(valid_dates) + invalid_count) * 100)
                    if (len(valid_dates) + invalid_count) > 0 else 0
                ),
                'detected_formats': format_patterns,
                'format_consistency': format_consistency,
                'most_common_format': most_common_format,
                'ambiguous_dates': ambiguous_dates,
                'examples_invalid': invalid_dates,
                'is_problematic': (
                    invalid_count > 0 or 
                    format_consistency < DATE_FORMAT_CONSISTENCY_THRESHOLD or
                    len(ambiguous_dates) > 0
                ),
                'detected_by_content': col in date_columns_by_content
            }
        
        return date_results
    
    def _validate_numerics(self):
        """Valida columnas numéricas."""
        numeric_results = {}
        
        for col in self.df.select_dtypes(include=['int64', 'float64']).columns:
            out_of_range = []
            negative_values = 0
            zero_values = 0
            
            # Detecta valores fuera de rango
            for idx, value in enumerate(self.df[col].items()):
                if pd.isna(value[1]):
                    continue
                
                if value[1] < 0:
                    negative_values += 1
                    
                    # Si parece ser una edad
                    if 'edad' in col.lower() and len(out_of_range) < 5:
                        out_of_range.append({
                            'row': idx + 1,
                            'value': value[1],
                            'issue': 'Valor negativo'
                        })
                
                if value[1] == 0:
                    zero_values += 1
            
            numeric_results[col] = {
                'min': float(self.df[col].min()),
                'max': float(self.df[col].max()),
                'negative_count': int(negative_values),
                'zero_count': int(zero_values),
                'examples_out_of_range': out_of_range,
                'is_problematic': len(out_of_range) > 0
            }
        
        return numeric_results
    
    def _validate_text(self):
        """Valida columnas de texto."""
        text_results = {}
        
        for col in self.df.select_dtypes(include=['object']).columns:
            special_chars_count = 0
            leading_trailing_spaces = 0
            long_values = 0
            examples = []
            
            for idx, value in enumerate(self.df[col].items()):
                if pd.isna(value[1]):
                    continue
                
                value_str = str(value[1])
                
                # Detecta caracteres especiales
                if ValidationPatterns.has_special_chars(value_str):
                    special_chars_count += 1
                    if len(examples) < 3:
                        examples.append({
                            'row': idx + 1,
                            'value': value_str[:50],
                            'issue': 'Caracteres especiales'
                        })
                
                # Detecta espacios al inicio/final
                if ValidationPatterns.has_leading_trailing_spaces(value_str):
                    leading_trailing_spaces += 1
                
                # Detecta valores muy largos (posibles errores)
                if len(value_str) > 500:
                    long_values += 1
            
            total_values = self.df[col].notna().sum()
            
            text_results[col] = {
                'special_chars_count': int(special_chars_count),
                'leading_trailing_spaces': int(leading_trailing_spaces),
                'long_values_count': int(long_values),
                'examples': examples,
                'is_problematic': special_chars_count > 0 or leading_trailing_spaces > 0
            }
        
        return text_results
    
    def _validate_urls(self, content_types=None):
        """Valida columnas de URL."""
        if content_types is None:
            content_types = {}
        
        url_results = {}
        
        # Detecta columnas de URL por nombre
        url_columns_by_name = [
            col for col in self.df.columns
            if any(x in col.lower() for x in ['url', 'website', 'web', 'link'])
        ]
        
        # Detecta columnas de URL por contenido
        url_columns_by_content = [
            col for col, detected_type in content_types.items()
            if detected_type == 'url'
        ]
        
        # Combina ambas listas (evita duplicados)
        url_columns = list(set(url_columns_by_name + url_columns_by_content))
        
        for col in url_columns:
            invalid_urls = []
            valid_count = 0
            invalid_count = 0
            
            for idx, value in enumerate(self.df[col].items()):
                if pd.isna(value[1]):
                    continue
                
                if ValidationPatterns.is_valid_url(value[1]):
                    valid_count += 1
                else:
                    invalid_count += 1
                    if len(invalid_urls) < 5:
                        invalid_urls.append({
                            'row': idx + 1,
                            'value': str(value[1])[:50]
                        })
            
            url_results[col] = {
                'valid_count': valid_count,
                'invalid_count': invalid_count,
                'invalid_percent': (
                    (invalid_count / (valid_count + invalid_count) * 100)
                    if (valid_count + invalid_count) > 0 else 0
                ),
                'examples_invalid': invalid_urls,
                'is_problematic': invalid_count > 0,
                'detected_by_content': col in url_columns_by_content
            }
        
        return url_results
    
    def get_validation_summary(self):
        """Genera un resumen de las validaciones."""
        summary = {
            'total_issues_found': 0,
            'columns_with_issues': [],
            'issues_by_type': {}
        }
        
        for validation_type, results in self.validation_results.items():
            if results:
                summary['issues_by_type'][validation_type] = len(
                    [col for col, data in results.items() if data.get('is_problematic', False)]
                )
                for col, data in results.items():
                    if data.get('is_problematic', False):
                        if col not in summary['columns_with_issues']:
                            summary['columns_with_issues'].append(col)
                        summary['total_issues_found'] += 1
        
        return summary
