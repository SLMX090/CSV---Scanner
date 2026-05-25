"""
Pruebas para el módulo utils/patterns.py
"""

import pytest
from utils.patterns import ValidationPatterns, get_column_type_hints


class TestEmailValidationPattern:
    """Pruebas para validación de email con expresiones regulares."""
    
    def test_valid_emails(self):
        """Verifica que acepta emails válidos."""
        valid_emails = [
            'user@example.com',
            'john.doe@domain.co.uk',
            'test+tag@test.org',
            'a@b.co'
        ]
        
        for email in valid_emails:
            assert ValidationPatterns.is_valid_email(email)
    
    def test_invalid_emails(self):
        """Verifica que rechaza emails inválidos."""
        invalid_emails = [
            'not-an-email',
            '@example.com',
            'user@',
            'user @example.com',
            'user..name@example.com'
        ]
        
        for email in invalid_emails:
            assert not ValidationPatterns.is_valid_email(email)
    
    def test_email_case_insensitive(self):
        """Verifica que la validación de email ignora mayúsculas."""
        assert ValidationPatterns.is_valid_email('User@Example.COM')
        assert ValidationPatterns.is_valid_email('USER@EXAMPLE.COM')


class TestPhoneValidationPattern:
    """Pruebas para validación de teléfono."""
    
    def test_valid_phones(self):
        """Verifica que acepta teléfonos válidos."""
        valid_phones = [
            '+34612345678',
            '34612345678',
            '+1-555-123-4567',
            '(555) 123-4567',
            '555.123.4567'
        ]
        
        for phone in valid_phones:
            assert ValidationPatterns.is_valid_phone(phone)
    
    def test_invalid_phones(self):
        """Verifica que rechaza teléfonos inválidos."""
        invalid_phones = [
            'not-a-phone',
            '123',  # Muy corto
            'abc-def-ghij'
        ]
        
        for phone in invalid_phones:
            assert not ValidationPatterns.is_valid_phone(phone)


class TestURLValidationPattern:
    """Pruebas para validación de URL."""
    
    def test_valid_urls(self):
        """Verifica que acepta URLs válidas."""
        valid_urls = [
            'https://example.com',
            'https://www.example.com',
            'http://example.co.uk/path',
            'https://sub.example.com/path?query=value'
        ]
        
        for url in valid_urls:
            assert ValidationPatterns.is_valid_url(url)
    
    def test_invalid_urls(self):
        """Verifica que rechaza URLs inválidas."""
        invalid_urls = [
            'not-a-url',
            'www.example.com',  # Sin protocolo
            'http://',
            'ftp://example.com'  # Protocolo no permitido
        ]
        
        for url in invalid_urls:
            assert not ValidationPatterns.is_valid_url(url)


class TestDateFormatValidation:
    """Pruebas para validación de formato de fecha."""
    
    def test_valid_date_formats(self):
        """Verifica que detecta formatos de fecha válidos."""
        valid_dates = [
            '2024-01-15',
            '15/01/2024',
            '01/15/2024',
            '15-01-2024',
            '2024/01/15'
        ]
        
        for date in valid_dates:
            assert ValidationPatterns.is_valid_date_format(date)
    
    def test_invalid_date_formats(self):
        """Verifica que rechaza formatos de fecha inválidos."""
        invalid_dates = [
            'not-a-date',
            '2024-13-01',  # Mes inválido
            '2024-01-32',  # Día inválido
            '01-2024-15'
        ]
        
        for date in invalid_dates:
            assert not ValidationPatterns.is_valid_date_format(date)


class TestNumericValidation:
    """Pruebas para validación de números."""
    
    def test_is_integer(self):
        """Verifica validación de enteros."""
        assert ValidationPatterns.is_integer('123')
        assert ValidationPatterns.is_integer('-456')
        assert not ValidationPatterns.is_integer('12.34')
        assert not ValidationPatterns.is_integer('abc')
    
    def test_is_float(self):
        """Verifica validación de flotantes."""
        assert ValidationPatterns.is_float('123.45')
        assert ValidationPatterns.is_float('123')
        assert ValidationPatterns.is_float('-456.78')
        assert not ValidationPatterns.is_float('abc')


class TestSpecialCharacterDetection:
    """Pruebas para detección de caracteres especiales."""
    
    def test_has_special_chars(self):
        """Verifica detección de caracteres especiales."""
        assert ValidationPatterns.has_special_chars('test@123')
        assert ValidationPatterns.has_special_chars('hello#world')
        assert not ValidationPatterns.has_special_chars('test123')
        assert not ValidationPatterns.has_special_chars('hello_world')
    
    def test_has_leading_trailing_spaces(self):
        """Verifica detección de espacios al inicio/final."""
        assert ValidationPatterns.has_leading_trailing_spaces(' test')
        assert ValidationPatterns.has_leading_trailing_spaces('test ')
        assert ValidationPatterns.has_leading_trailing_spaces(' test ')
        assert not ValidationPatterns.has_leading_trailing_spaces('test')


class TestDataTypeInference:
    """Pruebas para inferencia de tipo de dato."""
    
    def test_infer_data_type_integer(self):
        """Verifica inferencia de tipo entero."""
        assert ValidationPatterns.infer_data_type('123') == 'Entero'
        assert ValidationPatterns.infer_data_type('-456') == 'Entero'
    
    def test_infer_data_type_float(self):
        """Verifica inferencia de tipo flotante."""
        assert ValidationPatterns.infer_data_type('123.45') == 'Flotante'
        assert ValidationPatterns.infer_data_type('-456.78') == 'Flotante'
    
    def test_infer_data_type_email(self):
        """Verifica inferencia de tipo email."""
        assert ValidationPatterns.infer_data_type('user@example.com') == 'Email'
    
    def test_infer_data_type_phone(self):
        """Verifica inferencia de tipo teléfono."""
        assert ValidationPatterns.infer_data_type('+34612345678') == 'Teléfono'
    
    def test_infer_data_type_text(self):
        """Verifica inferencia de tipo texto."""
        assert ValidationPatterns.infer_data_type('random text') == 'Texto'
    
    def test_infer_data_type_null(self):
        """Verifica inferencia de tipo nulo."""
        assert ValidationPatterns.infer_data_type(None) == 'Nulo'
        assert ValidationPatterns.infer_data_type('') == 'Nulo'


class TestColumnTypeHints:
    """Pruebas para sugerencias de tipo basadas en nombre de columna."""
    
    def test_hint_datetime(self):
        """Verifica hint para columnas de fecha."""
        assert get_column_type_hints('fecha') == 'Fecha/Hora'
        assert get_column_type_hints('date_created') == 'Fecha/Hora'
        assert get_column_type_hints('timestamp') == 'Fecha/Hora'
    
    def test_hint_email(self):
        """Verifica hint para columnas de email."""
        assert get_column_type_hints('email') == 'Email'
        assert get_column_type_hints('correo_contacto') == 'Email'
        assert get_column_type_hints('mail') == 'Email'
    
    def test_hint_phone(self):
        """Verifica hint para columnas de teléfono."""
        assert get_column_type_hints('telefono') == 'Teléfono'
        assert get_column_type_hints('phone_number') == 'Teléfono'
        assert get_column_type_hints('celular') == 'Teléfono'
    
    def test_hint_url(self):
        """Verifica hint para columnas de URL."""
        assert get_column_type_hints('url') == 'URL'
        assert get_column_type_hints('website') == 'URL'
        assert get_column_type_hints('web_link') == 'URL'
    
    def test_hint_id(self):
        """Verifica hint para columnas de identificador."""
        assert get_column_type_hints('id') == 'Identificador'
        assert get_column_type_hints('codigo') == 'Identificador'
        assert get_column_type_hints('identificador') == 'Identificador'
    
    def test_hint_none(self):
        """Verifica que retorna None para columnas sin hint."""
        assert get_column_type_hints('random_column') is None
        assert get_column_type_hints('data') is None
