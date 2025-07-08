from flask import Flask

app = Flask(__name__)

# Configuraciones
app.config['SECRET_KEY'] = 'tu-clave-secreta-aqui'
app.config['TEMPLATES_AUTO_RELOAD'] = True

from app import routes
