

#redirect le dice al navegador que vaya a otra pagina

#url_for ("nombre de la funcion") genera una URL de una ruta a partir del nombre
#su funcion,  en vezx de escribir la ruta a mano

# request representa la peticion HTTP que hizo el usuario. Te da acceso a todo lo que mando el navegador
#datos de formularios, parametros de url, headers, cookies, etc

#session  es un diccionario especial que Flask guarda como cookie cifrada en el navegador
#del usuario. Sirve para recordar informacion entre peticiones

#flask_login----> LoginManager es el cordinador central de flask_login. Lo configuras una vez y 
#se enccargar de todo el sistema de autenticacion: saber quien se esta logueando,
#redirigir si no lo esta, cargar el usuario desde la sesion, etc.

#UserMixin Es una clase base que le añade a tu clase User los metodos que flask_login
#necesita para funcionar. Sin ella, tendrias que implementarlos vos a mano.

#login_user (user) le dice a Flask que este usuario esta autneticado. Guarda su ID en la sesion

#logout_user () borra al usuario de la sesion

# @login_required es un decorador que protege una ruta. si el usuario no esta 
#logueado, lo redirige automaticamente al login_view que configuraste

#werkzeug (es una libreria que Flask usa internamente)---> generate_password_hash 
#Estas dos funciones manejan el hashing de las contraseñas. No se deben guardar en teto plano

#decorador @login_manager.user_loader ----> este es el puente entre la sesion y tu base de datos.
#Flask_login lo llama automaticamente en cada peticion para reconstruir el objeto User a partir del id guardado en l cookie




from flask import Flask, render_template, redirect, url_for, request, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3 

app = Flask(__name__)
app.secret_key = 'clave-secreta-muy-segura'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # redirige si no autenticado

def get_db_connection():
    conn = sqlite3.connect('usuarios.db')
    conn.row_factory = sqlite3.Row
    return conn

#Crea la tabla de usuarios si no existe y agrega un usuario admin por defecto

#NOTA: TEXT es para cadenas de texto, INTEGER es para numeros enteros, UNIQUE asegura que no se repitan los valores en esa columna, NOT NULL obliga a que ese campo tenga un valor, PRIMARY KEY es la clave primaria que identifica univocamente cada fila y AUTOINCREMENT hace que el id se incremente automaticamente cada vez que se agrega un nuevo usuario.
#UNIQUE se usa para evitar que se repitan valores en campos como nombre de usuario, email, telefono o documento, lo que ayuda a mantener la integridad de los datos y evita conflictos al registrar nuevos usuarios.
#NOT NULL se usa para asegurar que ciertos campos esenciales como nombre, apellido, telefono, email, documento y password siempre tengan un valor al crear un nuevo usuario, lo que garantiza que la información sea completa y útil para la aplicación.

def crear_tabla():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            apellido TEXT NOT NULL,
            telefono INTEGER UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            documento INTEGER UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()

    conn.execute('''
        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            telefono INTEGER UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            documento INTEGER UNIQUE NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            especialidad TEXT NOT NULL,
            doctor TEXT NOT NULL,
            estado TEXT NOT NULL
        )
    ''')
    conn.commit()


    # Crear usuario admin por defecto
    admin = conn.execute(
        'SELECT * FROM usuarios WHERE nombre = ?',
        ('admin',)
    ).fetchone()

    if not admin:
        conn.execute(
            'INSERT INTO usuarios (nombre, apellido, telefono, email, documento, password) VALUES (?, ?, ?, ?, ?, ?)',
            ('admin', 'admin', '123456789', 'admin@example.com', '123456789', generate_password_hash('admin123'))
        )
        conn.commit()

    conn.close()

class User(UserMixin):
    def __init__(self, id, username):
        self.id = id
        self.username = username


@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user_data = conn.execute(
        'SELECT * FROM usuarios WHERE id = ?',
        (user_id,)
    ).fetchone()
    conn.close()

    if user_data:
        return User(user_data['id'], user_data['nombre'])
    return None



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user_data = conn.execute(
            'SELECT * FROM usuarios WHERE email = ?',
            (username,)
        ).fetchone()
        conn.close()

        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data['id'], user_data['nombre'])
            login_user(user)
            return redirect(url_for('dashboard'))

        return 'Credenciales inválidas', 401

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        telefono = request.form['telefono']
        email = request.form['email']
        documento = request.form['documento']
        password = request.form['password']

        conn = get_db_connection()

        # Verificar si el usuario ya existe
        usuario_existente = conn.execute(
            'SELECT * FROM usuarios WHERE nombre = ?',
            (nombre,)
        ).fetchone()

        if usuario_existente:
            conn.close()
            return 'El usuario ya existe'

        # Guardar nuevo usuario
        password_hash = generate_password_hash(password)
        conn.execute(
            'INSERT INTO usuarios (nombre, apellido, telefono, email, documento, password) VALUES (?, ?, ?, ?, ?, ?)',
            (nombre, apellido, telefono, email, documento, password_hash)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('registro.html')


@app.route ('/turnos')
@login_required
def turnos():
    return 'Bienvenido a la pagina de turnos'

if __name__ == '__main__':
    crear_tabla()
    app.run(debug=True)
    

