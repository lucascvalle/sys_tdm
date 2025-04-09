import re
from django.core.exceptions import ValidationError

def validate_legacy_code(value):
    pattern = r'^[A-Z]{2}\d{4}-\d{6}\.\d{2}-[A-Z]{4}_V\d+$'
    if not re.match(pattern, value):
        raise ValidationError("Formato de código legado inválido. Use: XXYYYY-DDMMAA.ZZ-ELNS_VX")