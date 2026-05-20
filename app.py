
from flask import Flask, render_template, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3

app = Flask(__name__)

# Lista para guardar los turnos mientras el servidor esté prendido
turnos_asignados = []
# Lista de horarios que aparecen en el formulario
horarios_disponibles = ["08:00", "09:00", "10:00", "11:00", "12:00"]

@app.route('/')
def home():
    # Le pasamos la lista de turnos a la agenda
    return render_template('agenda.html', turnos=turnos_asignados)

@app.route('/asignar-turno', methods=['GET', 'POST'])
def asignar():
    if request.method == 'POST':
        # Guardamos lo que el usuario escribió en el formulario
        nuevo_turno = {
            'paciente': request.form['paciente'],
            'especialidad': request.form['especialidad'],
            'hora': request.form['horario'],
            'estado': 'Ocupado'
        }
        turnos_asignados.append(nuevo_turno)
        
        # Sacamos el horario de la lista para que no se repita
        if request.form['horario'] in horarios_disponibles:
            horarios_disponibles.remove(request.form['horario'])
            
        return redirect(url_for('home')) # Volvemos a la tabla

    return render_template('formulario.html', horarios=horarios_disponibles)

if __name__ == '__main__':
    app.run(debug=True)



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



app = Flask(__name__)
app.secret_key = "clave-secreta-turnomed"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

inicializar_base_de_datos()



class User(UserMixin):
    def __init__(self, usuario):
        self.id = str(usuario["id_usuario"])
        self.nombre = usuario["nombre"]
        self.apellido = usuario["apellido"]
        self.email = usuario["email"]
        self.rol = usuario["rol"]



@login_manager.user_loader
def load_user(user_id):

    def login():
        if request.method == "POST":
            email = request.form["email"]
        password = request.form["password"]

        usuario = buscar_usuario_por_email(email)


        login_user(user)

        if user.rol == "admin":
                return redirect(url_for("admin"))
        elif user.rol == "paciente":
                return redirect(url_for("paciente"))
        elif user.rol == "medico":
                return redirect(url_for("medico"))

        flash("Correo o contraseña incorrectos.")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form["nombre"]
        apellido = request.form["apellido"]
        dni = request.form["dni"]
        telefono = request.form["telefono"]
        email = request.form["email"]
        password = request.form["password"]

        try:
            registrar_paciente(nombre, apellido, dni, telefono, email, password)
            flash("Registro exitoso. Ya podés iniciar sesión.")
            return redirect(url_for("login"))
        except Exception:
            flash("No se pudo registrar. El correo ya puede estar registrado.")
            return redirect(url_for("registro"))

    return render_template("registro.html")


@app.route("/admin")
@login_required
def admin():
    if current_user.rol != "admin":
        return redirect(url_for("login"))

    pacientes = obtener_pacientes()
    horarios = obtener_horarios_disponibles()
    turnos = obtener_turnos()

    return render_template(
        "admin.html",
        pacientes=pacientes,
        horarios=horarios,
        turnos=turnos,
        usuario=current_user
    )


@app.route("/cargar_horario", methods=["POST"])
@login_required
def cargar_horario_route():
    if current_user.rol != "admin":
        return redirect(url_for("login"))

    medico = request.form["medico"]
    especialidad = request.form["especialidad"]
    fecha = request.form["fecha"]
    hora = request.form["hora"]

    cargar_horario(medico, especialidad, fecha, hora)
    flash("Horario cargado correctamente.")
    return redirect(url_for("admin"))
def asignar_turno(id_usuario, id_horario):
    import sqlite3
    # Nos conectamos a la base de datos de TurnoMed
    conn = sqlite3.connect('database/turnomed.db')
    cursor = conn.cursor()
    
    try:
        # Insertamos el turno usando los datos que vienen del formulario
        cursor.execute(
            "INSERT INTO turnos (paciente, hora, medico, especialidad) VALUES (?, ?, ?, ?)",
            (id_usuario, id_horario, "Jonathan Triñanes", "Cardiología")
        )
        conn.commit() # Guardamos los cambios en el archivo .db
        return True   # Le avisamos a la ruta que salió todo bien
    except sqlite3.Error as e:
        print(f"Error en la base de datos: {e}")
        return False  # Si algo falló, avisamos
    finally:
        conn.close()  # Cerramos la conexión siempreS

@app.route("/asignar_turno", methods=["POST"])
@login_required
def asignar_turno_route():
    if current_user.rol != "admin":
        return redirect(url_for("login"))

    # Capturamos lo que la admin escribe en la web
    id_usuario = request.form["id_usuario"]  # Nombre del paciente
    id_horario = request.form["id_horario"]  # Hora seleccionada

    # Conectamos directo a tu base de datos para guardar el turno
    import sqlite3
    conn = sqlite3.connect('database/turnomed.db')
    cursor = conn.cursor()
    
    try:
        # Metemos el turno asignándoselo a Jonathan Triñanes automáticamente
        cursor.execute(
            "INSERT INTO turnos (paciente, hora, medico, especialidad) VALUES (?, ?, ?, ?)",
            (id_usuario, id_horario, "Jonathan Triñanes", "Obstetricia")
        )
        conn.commit()  # Guardamos los cambios en el archivo .db
        flash("Turno asignado correctamente.")
    except sqlite3.Error as e:
        print(f"Error en la base de datos: {e}")
        flash("Hubo un error al guardar el turno.")
    finally:
        conn.close()   # Cerramos la conexión para que no se trabe

    return redirect(url_for("admin"))
@app.route("/cancelar_turno/<int:id_turno>")
@login_required
def cancelar_turno_route(id_turno):
    if current_user.rol not in ["admin", "paciente"]:
        return redirect(url_for("login"))

    cancelar_turno(id_turno)

    if current_user.rol == "admin":
        return redirect(url_for("admin"))

    return redirect(url_for("paciente"))


@app.route("/paciente")
@login_required
def paciente():
    if current_user.rol != "paciente":
        return redirect(url_for("login"))

    turnos = obtener_turnos_por_paciente(current_user.id)

    return render_template(
        "paciente.html",
        usuario=current_user,
        turnos=turnos
    )
def obtener_turnos_por_medico(nombre):
    # Nos conectamos a la base de datos que tenés en la carpeta database
    conn = sqlite3.connect('database/turnomed.db')
    conn.row_factory = sqlite3.Row  # Esto ayuda a que Flask lea las columnas por su nombre
    cursor = conn.cursor()
    
    # Buscamos en la tabla de turnos aquellos que coincidan con el médico
    cursor.execute("SELECT paciente, especialidad, hora FROM turnos WHERE medico = ?", (nombre,))
    turnos_reales = cursor.fetchall()
    
    conn.close()
    return turnos_reales

def obtener_medico_actual():
    # De manera temporal para probar tu vista, devolvemos al Dr. Jonathan Triñanes
    return "Jonathan Triñanes"

@app.route("/medico")
# @login_required  <-- Poné el signo # acá adelante para desactivar el bloqueo temporalmente
def medico():
    # Dejamos solo estas líneas para que cargue directo:
    nombre_medico = obtener_medico_actual()
    turnos = obtener_turnos_por_medico(nombre_medico)
    
    return render_template(
        "medico.html",
        turnos=turnos,
        medico=nombre_medico
    ) 


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))
  
if __name__ == "__main__":
    app.run(debug=True)
            
