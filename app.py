from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os

# ─────────────────────────────────────────────
#  INICIALIZACIÓN DE LA APP
# ─────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "clave-secreta-turnomed"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"   # Si no está logueado, redirige a /login


# ─────────────────────────────────────────────
#  BASE DE DATOS
# ─────────────────────────────────────────────
DB_PATH = "database/turnomed.db"

def get_conn():
    """Devuelve una conexión con row_factory para leer columnas por nombre."""
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def inicializar_base_de_datos():
    conn = get_conn()
    cursor = conn.cursor()

    # Tabla de usuarios (admin, médicos, pacientes)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id_usuario  INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre      TEXT    NOT NULL,
            apellido    TEXT    NOT NULL,
            dni         TEXT,
            telefono    TEXT,
            email       TEXT    UNIQUE NOT NULL,
            password    TEXT    NOT NULL,
            rol         TEXT    NOT NULL DEFAULT 'paciente'
        )
    """)

    # Tabla de horarios disponibles que carga el admin
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS horarios (
            id_horario  INTEGER PRIMARY KEY AUTOINCREMENT,
            medico      TEXT    NOT NULL,
            especialidad TEXT   NOT NULL,
            fecha       TEXT    NOT NULL,
            hora        TEXT    NOT NULL,
            ocupado     INTEGER NOT NULL DEFAULT 0   -- 0 = libre, 1 = ocupado
        )
    """)

    # Tabla de turnos asignados
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS turnos (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            id_paciente INTEGER NOT NULL,
            id_horario  INTEGER NOT NULL,
            paciente    TEXT    NOT NULL,
            medico      TEXT    NOT NULL,
            especialidad TEXT   NOT NULL,
            fecha       TEXT    NOT NULL,
            hora        TEXT    NOT NULL,
            FOREIGN KEY (id_paciente) REFERENCES usuarios(id_usuario),
            FOREIGN KEY (id_horario)  REFERENCES horarios(id_horario)
        )
    """)

    conn.commit()
    conn.close()


inicializar_base_de_datos()


# ─────────────────────────────────────────────
#  MODELO DE USUARIO
# ─────────────────────────────────────────────
class User(UserMixin):
    def __init__(self, usuario):
        self.id      = str(usuario["id_usuario"])
        self.nombre  = usuario["nombre"]
        self.apellido = usuario["apellido"]
        self.email   = usuario["email"]
        self.rol     = usuario["rol"]


@login_manager.user_loader
def load_user(user_id):
    """Flask-Login llama esto en cada petición para reconstruir el usuario."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE id_usuario = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return User(row)
    return None

inicializar_base_de_datos()

def crear_admin_por_defecto():
    from werkzeug.security import generate_password_hash
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE email = 'admin@turnomed.com'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO usuarios (nombre, apellido, email, password, rol) VALUES (?,?,?,?,?)",
            ("Admin", "Sistema", "admin@turnomed.com", generate_password_hash("admin123"), "admin")
        )
        conn.commit()
        print("Admin creado automáticamente.")
    conn.close()

crear_admin_por_defecto()
# ─────────────────────────────────────────────
#  FUNCIONES AUXILIARES DE BASE DE DATOS
# ─────────────────────────────────────────────
def buscar_usuario_por_email(email):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return row


def registrar_paciente(nombre, apellido, dni, telefono, email, password):
    hashed = generate_password_hash(password)
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO usuarios (nombre, apellido, dni, telefono, email, password, rol) VALUES (?,?,?,?,?,?,'paciente')",
        (nombre, apellido, dni, telefono, email, hashed)
    )
    conn.commit()
    conn.close()


def obtener_pacientes():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM usuarios WHERE rol = 'paciente'")
    rows = cursor.fetchall()
    conn.close()
    return rows


def cargar_horario(medico, especialidad, fecha, hora):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO horarios (medico, especialidad, fecha, hora) VALUES (?,?,?,?)",
        (medico, especialidad, fecha, hora)
    )
    conn.commit()
    conn.close()


def obtener_horarios_disponibles():
    """Devuelve solo los horarios que todavía no están ocupados."""
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM horarios WHERE ocupado = 0 ORDER BY fecha, hora")
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_turnos():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM turnos ORDER BY fecha, hora")
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_turnos_por_paciente(id_paciente):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM turnos WHERE id_paciente = ? ORDER BY fecha, hora",
        (id_paciente,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


def obtener_turnos_por_medico(nombre_medico):
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT paciente, especialidad, fecha, hora FROM turnos WHERE medico = ? ORDER BY fecha, hora",
        (nombre_medico,)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows


# ─────────────────────────────────────────────
#  RUTAS DE AUTENTICACIÓN
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form["email"]
        password = request.form["password"]

        usuario = buscar_usuario_por_email(email)

        if usuario and check_password_hash(usuario["password"], password):
            user = User(usuario)
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
        nombre   = request.form["nombre"]
        apellido = request.form["apellido"]
        dni      = request.form["dni"]
        telefono = request.form["telefono"]
        email    = request.form["email"]
        password = request.form["password"]

        try:
            registrar_paciente(nombre, apellido, dni, telefono, email, password)
            flash("Registro exitoso. Ya podés iniciar sesión.")
            return redirect(url_for("login"))
        except Exception:
            flash("No se pudo registrar. El correo ya puede estar registrado.")
            return redirect(url_for("registro"))

    return render_template("registro.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


# ─────────────────────────────────────────────
#  PANEL ADMIN
# ─────────────────────────────────────────────
@app.route("/admin")
@login_required
def admin():
    if current_user.rol != "admin":
        return redirect(url_for("login"))

    pacientes = obtener_pacientes()
    horarios  = obtener_horarios_disponibles()
    turnos    = obtener_turnos()

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

    medico      = request.form["medico"]
    especialidad = request.form["especialidad"]
    fecha       = request.form["fecha"]
    hora        = request.form["hora"]

    cargar_horario(medico, especialidad, fecha, hora)
    flash("Horario cargado correctamente.")
    return redirect(url_for("admin"))


@app.route("/asignar_turno", methods=["POST"])
@login_required
def asignar_turno_route():
    if current_user.rol != "admin":
        return redirect(url_for("login"))

    id_paciente  = request.form["id_paciente"]
    id_horario   = request.form["id_horario"]

    # Verificamos que el horario exista y esté libre
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM horarios WHERE id_horario = ? AND ocupado = 0", (id_horario,))
    horario = cursor.fetchone()

    if not horario:
        conn.close()
        flash("El horario ya está ocupado o no existe.")
        return redirect(url_for("admin"))

    # Buscamos el nombre del paciente
    cursor.execute("SELECT nombre, apellido FROM usuarios WHERE id_usuario = ?", (id_paciente,))
    paciente_row = cursor.fetchone()

    if not paciente_row:
        conn.close()
        flash("Paciente no encontrado.")
        return redirect(url_for("admin"))

    nombre_paciente = f"{paciente_row['nombre']} {paciente_row['apellido']}"

    # Insertamos el turno
    cursor.execute(
        """INSERT INTO turnos (id_paciente, id_horario, paciente, medico, especialidad, fecha, hora)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (id_paciente, id_horario, nombre_paciente,
         horario["medico"], horario["especialidad"], horario["fecha"], horario["hora"])
    )

    # Marcamos el horario como ocupado
    cursor.execute("UPDATE horarios SET ocupado = 1 WHERE id_horario = ?", (id_horario,))

    conn.commit()
    conn.close()

    flash(f"Turno asignado a {nombre_paciente} con {horario['medico']}.")
    return redirect(url_for("admin"))


@app.route("/cancelar_turno/<int:id_turno>", methods=["POST"])
@login_required
def cancelar_turno(id_turno):
    if current_user.rol != "admin":
        return redirect(url_for("login"))

    conn = get_conn()
    cursor = conn.cursor()

    # Obtenemos el id_horario antes de borrar para liberarlo
    cursor.execute("SELECT id_horario FROM turnos WHERE id = ?", (id_turno,))
    turno = cursor.fetchone()

    if turno:
        # Liberamos el horario
        cursor.execute("UPDATE horarios SET ocupado = 0 WHERE id_horario = ?", (turno["id_horario"],))
        # Borramos el turno
        cursor.execute("DELETE FROM turnos WHERE id = ?", (id_turno,))
        conn.commit()
        flash("Turno cancelado y horario liberado.")
    else:
        flash("Turno no encontrado.")

    conn.close()
    return redirect(url_for("admin"))


# ─────────────────────────────────────────────
#  PANEL PACIENTE
# ─────────────────────────────────────────────
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


# ─────────────────────────────────────────────
#  PANEL MÉDICO
# ─────────────────────────────────────────────
@app.route("/medico")
# @login_required
def medico():
    nombre_medico = "Dr. Jonathan Triñanes"
    turnos = obtener_turnos_por_medico(nombre_medico)

    return render_template(
        "medico.html",
        turnos=turnos,
        medico=nombre_medico
    )

# ─────────────────────────────────────────────
#  ARRANQUE
# ─────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
