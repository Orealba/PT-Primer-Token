"""
This module takes care of starting the API Server, Loading the DB and Adding the endpoints
"""
import os
from flask import Flask, request, jsonify, url_for, send_from_directory
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from api.utils import APIException, generate_sitemap
from api.models import db, User
from api.routes import api
from api.admin import setup_admin
from api.commands import setup_commands
import datetime
from  flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity


#from models import Person

ENV = os.getenv("FLASK_ENV")
static_file_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), '../public/')
app = Flask(__name__)
app.url_map.strict_slashes = False

# database condiguration
db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace("postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
MIGRATE = Migrate(app, db, compare_type = True)
db.init_app(app)

# Allow CORS requests to this API
CORS(app)

# add the admin
setup_admin(app)

# add the admin
setup_commands(app)



jwt=JWTManager(app)

# Add all endpoints form the API with a "api" prefix
app.register_blueprint(api, url_prefix='/api')

# Handle/serialize errors like a JSON object
@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

# generate sitemap with all your endpoints
@app.route('/')
def sitemap():
    if ENV == "development":
        return generate_sitemap(app)
    return send_from_directory(static_file_dir, 'index.html')


@app.route('/login', methods=['POST'])
def iniciar_sesion():
    request_body = request.get_json()
    print(request_body)
    user= User.query.filter_by(email=request_body['email']).first()
    if user:
        if user.password == request_body['password']:
            tiempo= datetime.timedelta(minutes=1)
            acceso = create_access_token(identity=user.email, expires_delta=tiempo)
            return jsonify({
                "mensaje": "inicio de sesión correcto",
                "duracion": tiempo.total_seconds(),
                "token": acceso
            }),200
        else:
            return "error,revisa la contraseña",404
    else:        
        return "user no existe",400

@app.route('/singup', methods=['POST'])
def singup():
    request_body = request.get_json()#recogemos la información en la variable request_body
    
    if not (request_body['email'] and request_body['password'] and request_body['repeat_password']):#comprobamos que todos los valores esten introducidos
        return "falta alguna información", 400
    if not (request_body['password']== request_body['repeat_password']):#comprobamos que la contraseña y la repetición de la contraseña coinciden
        return 'las contraseñas no coinciden',500


    user =User(email=request_body['email'],password=request_body['password'], is_active=True)#creamos la variable user donde relacionamos los datos del formulario con la tabla User
    if user: #si lo anterior ha ido bien
        db.session.add(user)#guardamos los cambios
        db.session.commit()#confirmamos los cambios realizados
        token=create_access_token(identity= user.id, expires_delta=datetime.timedelta(minutes=1)) #creamos el toke nada más hacer el registro
        return jsonify({'token': token}), 201 #enviamos el token para que inicie sesión al registrarse
    return "user no existe"



# any other endpoint will try to serve it like a static file
@app.route('/<path:path>', methods=['GET'])
def serve_any_other_file(path):
    if not os.path.isfile(os.path.join(static_file_dir, path)):
        path = 'index.html'
    response = send_from_directory(static_file_dir, path)
    response.cache_control.max_age = 0 # avoid cache memory
    return response


# this only runs if `$ python src/main.py` is executed
if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3001))
    app.run(host='0.0.0.0', port=PORT, debug=True)
