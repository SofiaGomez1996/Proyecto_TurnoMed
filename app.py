

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

def crear_tabla():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()

    # Crear usuario admin por defecto
    admin = conn.execute(
        'SELECT * FROM usuarios WHERE username = ?',
        ('admin',)
    ).fetchone()

    if not admin:
        conn.execute(
            'INSERT INTO usuarios (username, password) VALUES (?, ?)',
            ('admin', generate_password_hash('admin123'))
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
        return User(user_data['id'], user_data['username'])
    return None



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user_data = conn.execute(
            'SELECT * FROM usuarios WHERE username = ?',
            (username,)
        ).fetchone()
        conn.close()

        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data['id'], user_data['username'])
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
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()

        # Verificar si el usuario ya existe
        usuario_existente = conn.execute(
            'SELECT * FROM usuarios WHERE username = ?',
            (username,)
        ).fetchone()

        if usuario_existente:
            conn.close()
            return 'El usuario ya existe'

        # Guardar nuevo usuario
        password_hash = generate_password_hash(password)
        conn.execute(
            'INSERT INTO usuarios (username, password) VALUES (?, ?)',
            (username, password_hash)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('registro.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return 'Bienvenido al dashboard'

if __name__ == '__main__':
    crear_tabla()
    app.run(debug=True)
    
