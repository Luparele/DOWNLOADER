from web_app.main import app
from a2wsgi import ASGIMiddleware

# This file bridges FastAPI (ASGI) to PythonAnywhere's Gunicorn (WSGI)
# Point the PythonAnywhere Web tab WSGI config file to `application`
application = ASGIMiddleware(app)
