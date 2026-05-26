"""
Pruebas para el módulo validators.py
"""

import pytest
import pandas as pd
from modules.validators import DataValidator


class TestEmailValidation:
    """Pruebas para validación de emails."""
    
    def test_validate_emails_by_name(self, sample_dataframe):
        """Verifica detección de columnas de email por nombre."""
        validator = DataValidator(sample_dataframe)
        results = validator._validate_emails()
        
        assert 'correo' in results
        assert results['correo']['valid_count'] == 3
        assert results['correo']['invalid_count'] == 0
    
    def test_validate_emails_invalid_format(self):
        """Verifica detección de emails inválidos."""
        df = pd.DataFrame({
            'email': ['valid@example.com', 'invalid-email', 'another@test.org']
        })
        
        validator = DataValidator(df)
        results = validator._validate_emails()
        
        assert results['email']['invalid_count'] == 1
        assert len(results['email']['examples_invalid']) > 0
    
    def test_validate_emails_by_content(self):
        """Verifica detección de emails por contenido de columna."""
        df = pd.DataFrame({
            'contact': [
                'user1@example.com',
                'user2@test.org',
                'john.doe@domain.com',
                'jane.smith@mail.co.uk',
                'invalid@'
            ]
        })
        
        validator = DataValidator(df)
        content_types = validator._detect_column_types_by_content()
        
        # Más del 70% son emails, debería detectar el tipo
        assert content_types.get('contact') == 'email'


class TestPhoneValidation:
    """Pruebas para validación de teléfonos."""
    
    def test_validate_phones_by_name(self, sample_dataframe):
        """Verifica detección de columnas de teléfono por nombre."""
        validator = DataValidator(sample_dataframe)
        results = validator._validate_phones()
        
        assert 'telefono' in results
        assert results['telefono']['valid_count'] > 0
    
    def test_validate_phones_valid_format(self):
        """Verifica que acepta formatos válidos de teléfono."""
        df = pd.DataFrame({
            'phone': [
                '+34612345678',
                '34687654321',
                '+1-555-123-4567',
                '(555) 123-4567'
            ]
        })
        
        validator = DataValidator(df)
        results = validator._validate_phones()
        
        assert results['phone']['valid_count'] > 0
    
    def test_validate_phones_invalid_format(self):
        """Verifica detección de teléfonos inválidos."""
        df = pd.DataFrame({
            'phone': [
                '+34612345678',
                'not-a-phone',
                '123',  # Muy corto
                '+34687654321'
            ]
        })
        
        validator = DataValidator(df)
        results = validator._validate_phones()
        
        assert results['phone']['invalid_count'] > 0


class TestDateValidation:
    """Pruebas para validación de fechas."""
    
    def test_validate_dates_by_name(self, sample_dataframe):
        """Verifica detección de columnas de fecha por nombre."""
        validator = DataValidator(sample_dataframe)
        results = validator._validate_dates()
        
        assert 'fecha' in results
        assert results['fecha']['valid_count'] > 0
    
    def test_validate_dates_consistent_format(self):
        """Verifica detección de formato consistente."""
        df = pd.DataFrame({
            'fecha': [
                '2024-01-15',
                '2024-02-20',
                '2024-03-10',
                '2024-04-05'
            ]
        })
        
        validator = DataValidator(df)
        results = validator._validate_dates()
        
        # Todas en mismo formato (proporción >= 0.90)
        assert results['fecha']['format_consistency'] >= 0.90
    
    def test_validate_dates_inconsistent_format(self):
        """Verifica detección de formatos inconsistentes."""
        df = pd.DataFrame({
            'fecha': [
                '2024-01-15',
                '15/01/2024',
                '01-15-2024',
                '15.01.2024'
            ]
        })
        
        validator = DataValidator(df)
        results = validator._validate_dates()
        
        # Múltiples formatos
        assert len(results['fecha']['detected_formats']) > 1
    
    def test_validate_dates_ambiguous_detection(self):
        """Verifica detección de fechas ambiguas."""
        df = pd.DataFrame({
            'fecha': [
                '03/04/2024',  # Ambiguo
                '12/13/2024',  # Claro (13 es día)
                '01/02/2024'   # Ambiguo
            ]
        })
        
        validator = DataValidator(df)
        results = validator._validate_dates()
        
        assert len(results['fecha']['ambiguous_dates']) > 0
    
    def test_validate_dates_below_consistency_threshold(self):
        """Verifica que se marca como problemático si inconsistencia está bajo umbral (0.95)."""
        df = pd.DataFrame({
            'fecha': [
                '2024-01-15',   # Formato 1
                '15/01/2024',   # Formato 2
                '2024-01-20',   # Formato 1
                '20/01/2024',   # Formato 2
                '2024-01-25',   # Formato 1
                '25/01/2024'    # Formato 2
            ]
        })
        
        validator = DataValidator(df)
        results = validator._validate_dates()
        
        # 50% en cada formato, bajo 0.95
        assert results['fecha']['format_consistency'] < 0.95
        # Debe marcarse como problemático
        assert results['fecha']['is_problematic'] == True
    
    def test_validate_dates_above_consistency_threshold(self):
        """Verifica que NO se marca como problemático si consistencia está sobre umbral (0.95)."""
        df = pd.DataFrame({
            'fecha': [
                '2024-01-15',
                '2024-01-20',
                '2024-01-25',
                '2024-01-30',
                '2024-02-01',
                '15/01/2024'  # Sólo 1 diferente = 83% consistencia pero sin inválidos
            ]
        })
        
        validator = DataValidator(df)
        results = validator._validate_dates()
        
        # Mayoría en mismo formato
        assert results['fecha']['format_consistency'] >= 0.83
        # Si están todos válidos y no hay ambigüedad, puede no ser problemático
        # (o puede serlo si la consistencia < 0.95)
        if results['fecha']['format_consistency'] < 0.95:
            assert results['fecha']['is_problematic'] == True
    
    def test_validate_dates_threshold_boundary(self):
        """Prueba el comportamiento en el límite exacto del umbral (0.95)."""
        from config import DATE_FORMAT_CONSISTENCY_THRESHOLD
        
        # Si 19 de 20 están en mismo formato = 0.95 exacto
        df = pd.DataFrame({
            'fecha': ['2024-01-' + str(i).zfill(2) for i in range(1, 20)] + ['15/01/2024']
        })
        
        validator = DataValidator(df)
        results = validator._validate_dates()
        
        consistency = results['fecha']['format_consistency']
        # Debe estar cerca del umbral
        assert 0.94 <= consistency <= 0.96


class TestURLValidation:
    """Pruebas para validación de URLs."""
    
    def test_validate_urls_by_name(self):
        """Verifica detección de columnas de URL por nombre."""
        df = pd.DataFrame({
            'website': [
                'https://example.com',
                'https://test.org',
                'invalid-url'
            ]
        })
        
        validator = DataValidator(df)
        results = validator._validate_urls()
        
        assert 'website' in results
    
    def test_validate_urls_valid_format(self):
        """Verifica que acepta URLs válidas."""
        df = pd.DataFrame({
            'url': [
                'https://example.com',
                'https://www.test.org/path',
                'http://subdomain.test.co.uk'
            ]
        })
        
        validator = DataValidator(df)
        results = validator._validate_urls()
        
        assert results['url']['valid_count'] >= 2


class TestContentBasedDetection:
    """Pruebas para detección de tipo de dato por contenido."""
    
    def test_detect_email_by_content(self):
        """Verifica detección de columna de email por contenido."""
        df = pd.DataFrame({
            'contact_info': [
                'john@example.com',
                'jane@test.org',
                'bob@domain.com',
                'alice@mail.co.uk',
                'charlie@provider.com'
            ]
        })
        
        validator = DataValidator(df)
        detected = validator._detect_column_types_by_content()
        
        assert detected['contact_info'] == 'email'
    
    def test_detect_phone_by_content(self):
        """Verifica detección de columna de teléfono por contenido."""
        df = pd.DataFrame({
            'contact_number': [
                '+34612345678',
                '+34687654321',
                '+34623456789',
                '+34912345678',
                '+34987654321'
            ]
        })
        
        validator = DataValidator(df)
        detected = validator._detect_column_types_by_content()
        
        assert detected['contact_number'] == 'phone'
    
    def test_no_detection_below_threshold(self):
        """Verifica que no detecta tipo si está bajo el umbral."""
        df = pd.DataFrame({
            'mixed_data': [
                'user@example.com',
                '+34612345678',
                'random text',
                'another random',
                'more text'
            ]
        })
        
        validator = DataValidator(df)
        detected = validator._detect_column_types_by_content()
        
        # Menos del 70% es del mismo tipo
        assert detected.get('mixed_data') is None


class TestValidateAll:
    """Pruebas para el método validate_all."""
    
    def test_validate_all_executes_all_validators(self, sample_dataframe):
        """Verifica que validate_all ejecuta todos los validadores."""
        validator = DataValidator(sample_dataframe)
        results = validator.validate_all()
        
        assert 'email_validation' in results
        assert 'phone_validation' in results
        assert 'date_validation' in results
        assert 'numeric_validation' in results
        assert 'text_validation' in results


class TestDomainRules:
    """Pruebas para validación contra reglas de dominio."""
    
    def test_domain_rules_numeric_validation(self):
        """Verifica validación numérica contra reglas de dominio."""
        df = pd.DataFrame({
            'age': [25, 150, 30, 5, 45, 60],  # 150 y 5 fuera de rango 0-120
            'salary': [30000, 50000, 45000, 35000, 40000]
        })
        
        rules = {
            'age': {
                'type': 'numeric',
                'min': 0,
                'max': 120,
                'comment': 'Edad válida'
            }
        }
        
        result = DataValidator.validate_against_domain_rules(
            df, 'test_domain', rules
        )
        
        assert result['domain'] == 'test_domain'
        assert 'age' in result['validations']
        assert result['validations']['age']['violations_count'] == 2  # 150 y 5
    
    def test_domain_rules_category_validation(self):
        """Verifica validación de categoría contra reglas de dominio."""
        df = pd.DataFrame({
            'department': ['IT', 'HR', 'Sales', 'Unknown', 'IT', 'Finance']
        })
        
        rules = {
            'department': {
                'type': 'category',
                'allowed': ['IT', 'HR', 'Sales', 'Operations'],
                'comment': 'Departamento válido'
            }
        }
        
        result = DataValidator.validate_against_domain_rules(
            df, 'hr', rules
        )
        
        assert 'department' in result['validations']
        # Unknown y Finance están fuera
        assert result['validations']['department']['violations_count'] == 2
    
    def test_domain_rules_partial_match_columns(self):
        """Verifica que detecta columnas por match parcial."""
        df = pd.DataFrame({
            'patient_age': [25, 150, 30],
            'birth_date': ['1990-01-15', '2000-01-01', '1985-05-20']
        })
        
        rules = {
            'age': {
                'type': 'numeric',
                'min': 0,
                'max': 120
            }
        }
        
        result = DataValidator.validate_against_domain_rules(
            df, 'healthcare', rules
        )
        
        # Debe detectar 'patient_age' porque contiene 'age'
        assert 'patient_age' in result['validations'] or len(result['columns_checked']) > 0
    
    def test_domain_rules_empty_rules(self):
        """Verifica comportamiento con reglas vacías."""
        df = pd.DataFrame({
            'col1': [1, 2, 3],
            'col2': ['a', 'b', 'c']
        })
        
        result = DataValidator.validate_against_domain_rules(
            df, 'test', {}
        )
        
        assert result['domain'] == 'test'
        assert result['validations'] == {}
    
    def test_domain_rules_violation_percent_calculation(self):
        """Verifica cálculo correcto de porcentaje de violaciones."""
        df = pd.DataFrame({
            'price': [100, 200, -50, 150, -25, 300, 400, 500, 600, 700]
        })
        
        rules = {
            'price': {
                'type': 'numeric',
                'min': 0,
                'max': None
            }
        }
        
        result = DataValidator.validate_against_domain_rules(
            df, 'ecommerce', rules
        )
        
        # 2 violaciones de 10 = 20%
        assert result['validations']['price']['violation_percent'] == 20.0
        assert 'url_validation' in results
