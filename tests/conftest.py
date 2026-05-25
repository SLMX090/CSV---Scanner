"""
Fixtures compartidas para las pruebas.
"""

import pytest
import pandas as pd
import io
import os
import tempfile


@pytest.fixture
def sample_valid_csv():
    """Retorna un CSV válido como string."""
    return """nombre,correo,telefono,fecha_nacimiento
Juan,juan@example.com,+34612345678,1990-01-15
María,maria@example.com,+34687654321,1985-06-20
Pedro,pedro@example.com,+34623456789,1992-03-10"""


@pytest.fixture
def sample_csv_with_bad_lines():
    """Retorna un CSV con líneas mal formadas."""
    return """nombre,correo,telefono
Juan,juan@example.com,+34612345678
María,maria@example.com
Pedro,pedro@example.com,+34623456789,EXTRA_COLUMN"""


@pytest.fixture
def sample_csv_with_delimiter_confusion():
    """Retorna un CSV donde hay posible confusión de delimitador."""
    return """nombre;correo;telefono
Juan;juan@example.com;+34612345678
María;maria@example.com;+34687654321
Pedro;pedro@example.com;+34623456789"""


@pytest.fixture
def sample_csv_mixed_dates():
    """Retorna un CSV con fechas en formatos mixtos."""
    return """nombre,fecha_registro
Juan,2024-01-15
María,15/01/2024
Pedro,01-15-2024
Ana,15.01.2024"""


@pytest.fixture
def sample_csv_with_duplicates():
    """Retorna un CSV con nombres de columna duplicados después de limpieza."""
    return """nombre,nombre,NOMBRE,nombre-data
Juan,Pérez,123,ABC
María,García,456,DEF"""


@pytest.fixture
def sample_csv_with_bad_column_names():
    """Retorna un CSV con nombres de columna problemáticos."""
    return """A-B,A@B,123column,_validColumn,Unnamed: 0
valor1,valor2,valor3,valor4,valor5
valor6,valor7,valor8,valor9,valor10"""


@pytest.fixture
def sample_csv_with_emails():
    """Retorna un CSV con datos de email para validación de contenido."""
    return """email_address,contact_info
user1@example.com,john.doe@mail.com
invalid-email,jane.smith@domain.co.uk
user2@test.org,not-an-email
user3@company.com,mary@business.com"""


@pytest.fixture
def sample_csv_with_phones():
    """Retorna un CSV con datos de teléfono para validación de contenido."""
    return """phone_number,contact_number
+34612345678,+34 (6) 12-34-56-78
invalid-phone,+34687654321
34623456789,+34-98-765-4321
+34912345678,34912345678"""


@pytest.fixture
def sample_csv_file(sample_valid_csv):
    """Retorna un archivo CSV temporal."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
        f.write(sample_valid_csv)
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_dataframe():
    """Retorna un DataFrame de pandas para pruebas."""
    return pd.DataFrame({
        'nombre': ['Juan', 'María', 'Pedro'],
        'correo': ['juan@example.com', 'maria@example.com', 'pedro@example.com'],
        'telefono': ['+34612345678', '+34687654321', '+34623456789'],
        'edad': [30, 25, 35],
        'fecha': ['2024-01-15', '2024-02-20', '2024-03-10']
    })
