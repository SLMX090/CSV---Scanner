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
from config import COMMON_AGE_RANGE, COMMON_YEAR_RANGE


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
        self.validation_results = {
            'email_validation': self._validate_emails(),
            'phone_validation': self._validate_phones(),
            'date_validation': self._validate_dates(),
            'numeric_validation': self._validate_numerics(),
            'text_validation': self._validate_text(),
            'url_validation': self._validate_urls(),
        }
        
        return self.validation_results
    
    def _validate_emails(self):
        """Valida columnas de email."""
        email_results = {}
        
        # Detecta columnas de email por nombre
        email_columns = [
            col for col in self.df.columns
            if any(x in col.lower() for x in ['email', 'correo', 'mail'])
        ]
        
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
                'is_problematic': invalid_count > 0
            }
        
        return email_results
    
    def _validate_phones(self):
        """Valida columnas de teléfono."""
        phone_results = {}
        
        # Detecta columnas de teléfono por nombre
        phone_columns = [
            col for col in self.df.columns
            if any(x in col.lower() for x in ['telefono', 'phone', 'celular', 'mobile'])
        ]
        
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
                'is_problematic': invalid_count > 0
            }
        
        return phone_results
    
    def _validate_dates(self):
        """Valida columnas de fecha."""
        date_results = {}
        
        # Detecta columnas de fecha por nombre
        date_columns = [
            col for col in self.df.columns
            if any(x in col.lower() for x in ['fecha', 'date', 'time', 'hora', 'timestamp'])
        ]
        
        for col in date_columns:
            invalid_dates = []
            valid_count = 0
            invalid_count = 0
            format_issues = {}
            
            for idx, value in enumerate(self.df[col].items()):
                if pd.isna(value[1]):
                    continue
                
                value_str = str(value[1]).strip()
                
                # Intenta parsear la fecha
                try:
                    date_parser.parse(value_str)
                    # Verifica si tiene formato consistente
                    if ValidationPatterns.is_valid_date_format(value_str):
                        valid_count += 1
                    else:
                        # Formato no estándar pero válido
                        format_issue = type(value_str).__name__
                        format_issues[format_issue] = format_issues.get(format_issue, 0) + 1
                        valid_count += 1
                except Exception:
                    invalid_count += 1
                    if len(invalid_dates) < 5:
                        invalid_dates.append({
                            'row': idx + 1,
                            'value': value_str[:50]
                        })
            
            date_results[col] = {
                'valid_count': valid_count,
                'invalid_count': invalid_count,
                'format_inconsistencies': format_issues,
                'invalid_percent': (
                    (invalid_count / (valid_count + invalid_count) * 100)
                    if (valid_count + invalid_count) > 0 else 0
                ),
                'examples_invalid': invalid_dates,
                'is_problematic': invalid_count > 0 or len(format_issues) > 1
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
    
    def _validate_urls(self):
        """Valida columnas de URL."""
        url_results = {}
        
        # Detecta columnas de URL por nombre
        url_columns = [
            col for col in self.df.columns
            if any(x in col.lower() for x in ['url', 'website', 'web', 'link'])
        ]
        
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
                'is_problematic': invalid_count > 0
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
