# fuel_depot_digital_twin/api/auth.py
import os
from functools import wraps
from flask import request, abort

# In a real production environment, use a more secure way to store and manage API keys,
# such as a secure vault service (e.g., HashiCorp Vault, AWS Secrets Manager).
API_KEY = os.getenv("API_KEY", "your_api_key_here")

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get('x-api-key') and request.headers.get('x-api-key') == API_KEY:
            return f(*args, **kwargs)
        else:
            abort(401)
    return decorated_function