from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3
import os
import threading

try:
    import webview
except ImportError:
    webview = None
#configuración de la app
app = Flask(__name__)
app.secret_key = "clave-secreta-turnomed"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

DB_PATH = "database/turnomed.db"
UPLOAD_FOLDER = "static/imagenes/medicos"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
#base da datos

def get_conn():
    
    os.makedirs("database", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def archivo_permitido(nombre_archivo):
    return (
        "." in nombre_archivo and
        nombre_archivo.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )
def inicializar_base_de_datos():
    conn = get_conn()
    cursor = conn.cursor()
#usuarios, medicos, horarios y turnos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            dni TEXT,
            telefono TEXT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL DEFAULT 'paciente'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicos (
            id_medico INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            especialidad TEXT NOT NULL,
            email TEXT,
            telefono TEXT,
            foto TEXT,
            activo INTEGER DEFAULT 1
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS horarios (
            id_horario INTEGER PRIMARY KEY AUTOINCREMENT,
            id_medico INTEGER NOT NULL,
            especialidad TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            ocupado INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (id_medico) REFERENCES medicos(id_medico)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS turnos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_paciente INTEGER NOT NULL,
            id_horario INTEGER NOT NULL,
            id_medico INTEGER NOT NULL,
            paciente TEXT NOT NULL,
            especialidad TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            estado TEXT NOT NULL DEFAULT 'Confirmado',
            llamado INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (id_paciente) REFERENCES usuarios(id_usuario),
            FOREIGN KEY (id_horario) REFERENCES horarios(id_horario),
            FOREIGN KEY (id_medico) REFERENCES medicos(id_medico)
        )
    """)

    conn.commit()
    conn.close()

#datos iniciales para pruebas
def crear_datos_iniciales():
    conn = get_conn()
    cursor = conn.cursor()

    usuarios = [
        ("Admin", "Sistema", "00000000", "1122334455", "admin@turnomed.com", generate_password_hash("admin123"), "admin"),
        ("Juan", "Pérez", "11111111", "1133445566", "paciente@turnomed.com", generate_password_hash("paciente123"), "paciente"),
        ("Carlos", "Gómez", "22222222", "1144556677", "medico@turnomed.com", generate_password_hash("medico123"), "medico"),
    ]

    for usuario in usuarios:
        existe = cursor.execute(
            "SELECT * FROM usuarios WHERE email = ?",
            (usuario[4],)
        ).fetchone()

        if not existe:
            cursor.execute("""
                INSERT INTO usuarios
                (nombre, apellido, dni, telefono, email, password, rol)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, usuario)

    medicos = [
        ("Carlos", "Gómez", "Clínica Médica", "medico@turnomed.com", "1144556677", "medico_default.png"),
        ("Laura", "Ruiz", "Pediatría", "laura.ruiz@turnomed.com", "1166778899", "medico_default.png"),
    ]

    for medico in medicos:
        existe = cursor.execute("""
            SELECT * FROM medicos
            WHERE nombre = ? AND apellido = ? AND especialidad = ?
        """, (medico[0], medico[1], medico[2])).fetchone()

        if not existe:
            cursor.execute("""
                INSERT INTO medicos
                (nombre, apellido, especialidad, email, telefono, foto, activo)
                VALUES (?, ?, ?, ?, ?, ?, 1)
            """, medico)

    conn.commit()
    conn.close()


inicializar_base_de_datos()
crear_datos_iniciales()

#user model para flask-login
class User(UserMixin):
    def __init__(self, usuario):
        self.id = str(usuario["id_usuario"])
        self.nombre = usuario["nombre"]
        self.apellido = usuario["apellido"]
        self.email = usuario["email"]
        self.rol = usuario["rol"]


@login_manager.user_loader
def load_user(user_id):
    conn = get_conn()
    usuario = conn.execute(
        "SELECT * FROM usuarios WHERE id_usuario = ?",
        (user_id,)
    ).fetchone()
    conn.close()

    if usuario:
        return User(usuario)

    return None

#funciones para manejar usuarios, médicos, horarios y turnos
def buscar_usuario_por_email(email):
    conn = get_conn()
    usuario = conn.execute(
        "SELECT * FROM usuarios WHERE email = ?",
        (email,)
    ).fetchone()
    conn.close()
    return usuario


def registrar_paciente(nombre, apellido, dni, telefono, email, password):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO usuarios
        (nombre, apellido, dni, telefono, email, password, rol)
        VALUES (?, ?, ?, ?, ?, ?, 'paciente')
    """, (
        nombre,
        apellido,
        dni,
        telefono,
        email.strip().lower(),
        generate_password_hash(password)
    ))

    conn.commit()
    conn.close()


def obtener_pacientes(busqueda=None):
    conn = get_conn()

    if busqueda:
        termino = f"%{busqueda.strip()}%"

        pacientes = conn.execute("""
            SELECT *
            FROM usuarios
            WHERE rol = 'paciente'
            AND (
                nombre LIKE ?
                OR apellido LIKE ?
                OR dni LIKE ?
                OR email LIKE ?
                OR telefono LIKE ?
            )
            ORDER BY apellido, nombre
        """, (
            termino,
            termino,
            termino,
            termino,
            termino
        )).fetchall()
    else:
        pacientes = conn.execute("""
            SELECT *
            FROM usuarios
            WHERE rol = 'paciente'
            ORDER BY apellido, nombre
        """).fetchall()

    conn.close()
    return pacientes


def obtener_medicos():
    conn = get_conn()
    medicos = conn.execute("""
        SELECT * FROM medicos
        WHERE activo = 1
        ORDER BY especialidad, apellido, nombre
    """).fetchall()
    conn.close()
    return medicos


def obtener_especialidades():
    conn = get_conn()
    especialidades = conn.execute("""
        SELECT DISTINCT especialidad
        FROM medicos
        WHERE activo = 1
        ORDER BY especialidad
    """).fetchall()
    conn.close()
    return especialidades


def obtener_horarios_disponibles():
    conn = get_conn()
    horarios = conn.execute("""
        SELECT horarios.*, medicos.nombre, medicos.apellido
        FROM horarios
        INNER JOIN medicos ON horarios.id_medico = medicos.id_medico
        WHERE horarios.ocupado = 0
        ORDER BY horarios.fecha, horarios.hora
    """).fetchall()
    conn.close()
    return horarios
def obtener_horarios_filtrados(especialidad=None, id_medico=None):
    conn = get_conn()

    query = """
        SELECT
            horarios.*,
            medicos.nombre AS medico_nombre,
            medicos.apellido AS medico_apellido
        FROM horarios
        INNER JOIN medicos
        ON horarios.id_medico = medicos.id_medico
        WHERE horarios.ocupado = 0
    """

    params = []

    if especialidad:
        query += " AND horarios.especialidad = ?"
        params.append(especialidad)

    if id_medico:
        query += " AND horarios.id_medico = ?"
        params.append(id_medico)

    query += " ORDER BY horarios.fecha, horarios.hora"

    horarios = conn.execute(query, params).fetchall()
    conn.close()

    return horarios


def obtener_turnos():
    conn = get_conn()
    turnos = conn.execute("""
        SELECT
            turnos.*,
            usuarios.nombre AS paciente_nombre,
            usuarios.apellido AS paciente_apellido,
            medicos.nombre AS medico_nombre,
            medicos.apellido AS medico_apellido
        FROM turnos
        INNER JOIN usuarios ON turnos.id_paciente = usuarios.id_usuario
        INNER JOIN medicos ON turnos.id_medico = medicos.id_medico
        ORDER BY turnos.fecha, turnos.hora
    """).fetchall()
    conn.close()
    return turnos


def obtener_turnos_por_paciente(id_paciente):
    conn = get_conn()
    turnos = conn.execute("""
        SELECT
            turnos.*,
            medicos.nombre AS medico_nombre,
            medicos.apellido AS medico_apellido
        FROM turnos
        INNER JOIN medicos ON turnos.id_medico = medicos.id_medico
        WHERE turnos.id_paciente = ?
        ORDER BY turnos.fecha, turnos.hora
    """, (id_paciente,)).fetchall()
    conn.close()
    return turnos


def obtener_turnos_por_medico(id_medico):
    conn = get_conn()
    turnos = conn.execute("""
        SELECT
            turnos.*,
            usuarios.nombre AS paciente_nombre,
            usuarios.apellido AS paciente_apellido,
            usuarios.telefono,
            medicos.nombre AS medico_nombre,
            medicos.apellido AS medico_apellido
        FROM turnos
        INNER JOIN usuarios ON turnos.id_paciente = usuarios.id_usuario
        INNER JOIN medicos ON turnos.id_medico = medicos.id_medico
        WHERE turnos.id_medico = ?
        ORDER BY turnos.fecha, turnos.hora
    """, (id_medico,)).fetchall()
    conn.close()
    return turnos


def obtener_medico_por_email(email):
    conn = get_conn()
    medico = conn.execute("""
        SELECT * FROM medicos
        WHERE email = ?
    """, (email.strip().lower(),)).fetchone()
    conn.close()
    return medico
def obtener_usuario_por_id(id_usuario):
    conn = get_conn()

    usuario = conn.execute("""
        SELECT *
        FROM usuarios
        WHERE id_usuario = ?
    """, (id_usuario,)).fetchone()

    conn.close()
    return usuario


def actualizar_usuario(
    id_usuario,
    nombre,
    apellido,
    dni,
    telefono,
    email
):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE usuarios
        SET
            nombre = ?,
            apellido = ?,
            dni = ?,
            telefono = ?,
            email = ?
        WHERE id_usuario = ?
    """, (
        nombre,
        apellido,
        dni,
        telefono,
        email,
        id_usuario
    ))

    conn.commit()
    conn.close()


def cambiar_password_usuario(
    id_usuario,
    nueva_password
):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE usuarios
        SET password = ?
        WHERE id_usuario = ?
    """, (
        generate_password_hash(nueva_password),
        id_usuario
    ))

    conn.commit()
    conn.close()
#rutas de autenticación, administración, paciente y médico
@app.route("/")
def index():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        email = request.form["email"].strip().lower()
        password = request.form["password"]

        usuario = buscar_usuario_por_email(email)

        if not usuario:
            flash("No existe un usuario registrado con ese correo.")
            return redirect(url_for("login"))

        if not check_password_hash(usuario["password"], password):
            flash("La contraseña ingresada es incorrecta.")
            return redirect(url_for("login"))

        user = User(usuario)
        login_user(user)

        if user.rol == "admin":
            flash(f"Bienvenido/a {user.nombre}.")
            return redirect(url_for("admin"))

        if user.rol == "paciente":
            flash(f"Bienvenido/a {user.nombre}.")
            return redirect(url_for("paciente"))

        if user.rol == "medico":
            flash(f"Bienvenido/a Dr/a {user.apellido}.")
            return redirect(url_for("medico"))

        flash("El usuario no tiene un rol válido asignado.")
        logout_user()
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        try:
            registrar_paciente(
                request.form["nombre"],
                request.form["apellido"],
                request.form["dni"],
                request.form["telefono"],
                request.form["email"],
                request.form["password"]
            )
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

#panel admin
@app.route("/admin")
@login_required
def admin():

    if current_user.rol != "admin":
        flash("No tenés permiso para ingresar al panel de administración.")
        return redirect(url_for("login"))

    filtro_especialidad = request.args.get("especialidad", "")
    filtro_medico = request.args.get("id_medico", "")
    busqueda_paciente = request.args.get("buscar_paciente", "")

    horarios = obtener_horarios_filtrados(
        filtro_especialidad if filtro_especialidad else None,
        filtro_medico if filtro_medico else None
    )

    return render_template(
        "admin.html",
        usuario=current_user,
        pacientes=obtener_pacientes(busqueda_paciente),
        busqueda_paciente=busqueda_paciente,
        medicos=obtener_medicos(),
        especialidades=obtener_especialidades(),
        horarios=horarios,
        turnos=obtener_turnos(),
        filtro_especialidad=filtro_especialidad,
        filtro_medico=filtro_medico
    )


@app.route("/admin/agregar_medico", methods=["POST"])
@login_required
def agregar_medico():

    if current_user.rol != "admin":
        flash("No tenés permiso para realizar esta acción.")
        return redirect(url_for("login"))

    nombre = request.form["nombre"]
    apellido = request.form["apellido"]
    especialidad = request.form["especialidad"]
    email = request.form["email"].strip().lower()
    telefono = request.form["telefono"]
    password_inicial = request.form["password"]

    foto_archivo = request.files.get("foto")
    nombre_foto = "medico_default.png"

    if foto_archivo and foto_archivo.filename != "":

        if not archivo_permitido(foto_archivo.filename):
            flash("Formato de imagen no permitido. Usá PNG, JPG, JPEG o WEBP.")
            return redirect(url_for("admin"))

        nombre_seguro = secure_filename(foto_archivo.filename)
        nombre_foto = f"{email.replace('@', '_').replace('.', '_')}_{nombre_seguro}"
        ruta_foto = os.path.join(app.config["UPLOAD_FOLDER"], nombre_foto)

        foto_archivo.save(ruta_foto)

    conn = get_conn()
    cursor = conn.cursor()

    try:
        usuario_existente = cursor.execute("""
            SELECT *
            FROM usuarios
            WHERE email = ?
        """, (email,)).fetchone()

        if usuario_existente:
            conn.close()
            flash("Ya existe un usuario registrado con ese correo.")
            return redirect(url_for("admin"))

        cursor.execute("""
            INSERT INTO usuarios
            (
                nombre,
                apellido,
                dni,
                telefono,
                email,
                password,
                rol
            )
            VALUES (?, ?, ?, ?, ?, ?, 'medico')
        """, (
            nombre,
            apellido,
            "",
            telefono,
            email,
            generate_password_hash(password_inicial)
        ))

        cursor.execute("""
            INSERT INTO medicos
            (
                nombre,
                apellido,
                especialidad,
                email,
                telefono,
                foto,
                activo
            )
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (
            nombre,
            apellido,
            especialidad,
            email,
            telefono,
            nombre_foto
        ))

        conn.commit()
        flash("Médico agregado correctamente. Ya puede iniciar sesión con su email y contraseña inicial.")

    except Exception:
        flash("No se pudo agregar el médico. Revisá los datos cargados.")

    conn.close()
    return redirect(url_for("admin"))


@app.route("/cargar_horario", methods=["POST"])
@login_required
def cargar_horario_route():
    if current_user.rol != "admin":
        flash("No tenés permiso para cargar horarios.")
        return redirect(url_for("login"))

    id_medico = request.form["id_medico"]
    fecha = request.form["fecha"]
    hora = request.form["hora"]

    conn = get_conn()
    cursor = conn.cursor()

    medico = cursor.execute("""
        SELECT * FROM medicos
        WHERE id_medico = ?
    """, (id_medico,)).fetchone()

    if not medico:
        conn.close()
        flash("Médico no encontrado.")
        return redirect(url_for("admin"))

    existe = cursor.execute("""
        SELECT * FROM horarios
        WHERE id_medico = ? AND fecha = ? AND hora = ?
    """, (id_medico, fecha, hora)).fetchone()

    if existe:
        conn.close()
        flash("Ese horario ya está cargado para el médico seleccionado.")
        return redirect(url_for("admin"))

    cursor.execute("""
        INSERT INTO horarios
        (id_medico, especialidad, fecha, hora, ocupado)
        VALUES (?, ?, ?, ?, 0)
    """, (id_medico, medico["especialidad"], fecha, hora))

    conn.commit()
    conn.close()

    flash("Horario cargado correctamente.")
    return redirect(url_for("admin"))


@app.route("/asignar_turno", methods=["POST"])
@login_required
def asignar_turno_route():
    if current_user.rol != "admin":
        flash("No tenés permiso para asignar turnos.")
        return redirect(url_for("login"))

    id_paciente = request.form["id_paciente"]
    id_horario = request.form["id_horario"]

    conn = get_conn()
    cursor = conn.cursor()

    horario = cursor.execute("""
        SELECT horarios.*, medicos.nombre, medicos.apellido
        FROM horarios
        INNER JOIN medicos ON horarios.id_medico = medicos.id_medico
        WHERE horarios.id_horario = ? AND horarios.ocupado = 0
    """, (id_horario,)).fetchone()

    if not horario:
        conn.close()
        flash("El horario ya está ocupado o no existe.")
        return redirect(url_for("admin"))

    paciente = cursor.execute("""
        SELECT * FROM usuarios
        WHERE id_usuario = ?
    """, (id_paciente,)).fetchone()

    if not paciente:
        conn.close()
        flash("Paciente no encontrado.")
        return redirect(url_for("admin"))

    nombre_paciente = f"{paciente['nombre']} {paciente['apellido']}"

    cursor.execute("""
        INSERT INTO turnos
        (id_paciente, id_horario, id_medico, paciente, especialidad, fecha, hora, estado, llamado)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Confirmado', 0)
    """, (
        id_paciente,
        id_horario,
        horario["id_medico"],
        nombre_paciente,
        horario["especialidad"],
        horario["fecha"],
        horario["hora"]
    ))

    cursor.execute("""
        UPDATE horarios
        SET ocupado = 1
        WHERE id_horario = ?
    """, (id_horario,))

    conn.commit()
    conn.close()

    flash("Turno asignado correctamente.")
    return redirect(url_for("admin"))


@app.route("/cancelar_turno/<int:id_turno>", methods=["POST"])
@login_required
def cancelar_turno(id_turno):
    if current_user.rol != "admin":
        flash("No tenés permiso para cancelar turnos desde administración.")
        return redirect(url_for("login"))

    conn = get_conn()
    cursor = conn.cursor()

    turno = cursor.execute("""
        SELECT * FROM turnos
        WHERE id = ?
    """, (id_turno,)).fetchone()

    if turno:
        cursor.execute("""
            UPDATE horarios
            SET ocupado = 0
            WHERE id_horario = ?
        """, (turno["id_horario"],))

        cursor.execute("""
            UPDATE turnos
            SET estado = 'Cancelado'
            WHERE id = ?
        """, (id_turno,))

        conn.commit()
        flash("Turno cancelado correctamente. El horario volvió a estar disponible.")
    else:
        flash("Turno no encontrado.")

    conn.close()
    return redirect(url_for("admin"))
#panel paciente

@app.route("/paciente")
@login_required
def paciente():
    if current_user.rol != "paciente":
        flash("No tenés permiso para ingresar a la vista paciente.")
        return redirect(url_for("login"))

    return render_template(
        "paciente.html",
        usuario=current_user,
        turnos=obtener_turnos_por_paciente(current_user.id)
    )


@app.route("/paciente/cancelar_turno/<int:id_turno>", methods=["POST"])
@login_required
def paciente_cancelar_turno(id_turno):
    if current_user.rol != "paciente":
        flash("No tenés permiso para cancelar este turno.")
        return redirect(url_for("login"))

    conn = get_conn()
    cursor = conn.cursor()

    turno = cursor.execute("""
        SELECT * FROM turnos
        WHERE id = ? AND id_paciente = ?
    """, (id_turno, current_user.id)).fetchone()

    if turno:
        cursor.execute("""
            UPDATE horarios
            SET ocupado = 0
            WHERE id_horario = ?
        """, (turno["id_horario"],))

        cursor.execute("""
            UPDATE turnos
            SET estado = 'Cancelado'
            WHERE id = ?
        """, (id_turno,))

        conn.commit()
        flash("Turno cancelado con éxito. Si desea solicitar otro turno debe comunicarse con la administradora.")
    else:
        flash("No se pudo cancelar el turno seleccionado.")

    conn.close()
    return redirect(url_for("paciente"))


@app.route("/paciente/modificar_turno/<int:id_turno>", methods=["GET", "POST"])
@login_required
def paciente_modificar_turno(id_turno):
    if current_user.rol != "paciente":
        flash("No tenés permiso para modificar este turno.")
        return redirect(url_for("login"))

    conn = get_conn()
    cursor = conn.cursor()

    turno = cursor.execute("""
        SELECT * FROM turnos
        WHERE id = ? AND id_paciente = ?
    """, (id_turno, current_user.id)).fetchone()

    if not turno:
        conn.close()
        flash("Turno no encontrado.")
        return redirect(url_for("paciente"))

    if request.method == "POST":
        nuevo_id_horario = request.form.get("id_horario")

        if not nuevo_id_horario:
            flash("Seleccioná un nuevo horario para modificar el turno.")
            conn.close()
            return redirect(url_for("paciente_modificar_turno", id_turno=id_turno))

        nuevo = cursor.execute("SELECT * FROM horarios WHERE id_horario = ?", (nuevo_id_horario,)).fetchone()

        if not nuevo or nuevo["ocupado"] == 1:
            conn.close()
            flash("El horario seleccionado no está disponible.")
            return redirect(url_for("paciente_modificar_turno", id_turno=id_turno))

        # liberar horario anterior
        cursor.execute("UPDATE horarios SET ocupado = 0 WHERE id_horario = ?", (turno["id_horario"],))

        # asignar nuevo horario
        cursor.execute("UPDATE horarios SET ocupado = 1 WHERE id_horario = ?", (nuevo_id_horario,))

        # actualizar turno
        cursor.execute("""
            UPDATE turnos
            SET id_horario = ?, id_medico = ?, fecha = ?, hora = ?, especialidad = ?
            WHERE id = ?
        """, (
            nuevo_id_horario,
            nuevo["id_medico"],
            nuevo["fecha"],
            nuevo["hora"],
            nuevo["especialidad"],
            id_turno
        ))

        conn.commit()
        conn.close()

        flash("Turno modificado correctamente.")
        return redirect(url_for("paciente"))

    # GET: mostrar formulario con horarios disponibles de la misma especialidad
    horarios_disponibles = obtener_horarios_filtrados(especialidad=turno["especialidad"], id_medico=None)
    conn.close()

    return render_template(
        "modificar_turno.html",
        usuario=current_user,
        turno=turno,
        horarios=horarios_disponibles,
        back_url=url_for("paciente")
    )


@app.route("/admin/modificar_turno/<int:id_turno>", methods=["GET", "POST"])
@login_required
def admin_modificar_turno(id_turno):
    if current_user.rol != "admin":
        flash("No tenés permiso para ingresar al panel de administración.")
        return redirect(url_for("login"))

    conn = get_conn()
    cursor = conn.cursor()

    turno = cursor.execute("SELECT * FROM turnos WHERE id = ?", (id_turno,)).fetchone()

    if not turno:
        conn.close()
        flash("Turno no encontrado.")
        return redirect(url_for("admin"))

    if request.method == "POST":
        nuevo_id_horario = request.form.get("id_horario")

        if not nuevo_id_horario:
            flash("Seleccioná un nuevo horario para modificar el turno.")
            conn.close()
            return redirect(url_for("admin_modificar_turno", id_turno=id_turno))

        nuevo = cursor.execute("SELECT * FROM horarios WHERE id_horario = ?", (nuevo_id_horario,)).fetchone()

        if not nuevo or nuevo["ocupado"] == 1:
            conn.close()
            flash("El horario seleccionado no está disponible.")
            return redirect(url_for("admin_modificar_turno", id_turno=id_turno))

        # liberar horario anterior
        cursor.execute("UPDATE horarios SET ocupado = 0 WHERE id_horario = ?", (turno["id_horario"],))

        # asignar nuevo horario
        cursor.execute("UPDATE horarios SET ocupado = 1 WHERE id_horario = ?", (nuevo_id_horario,))

        # actualizar turno
        cursor.execute("""
            UPDATE turnos
            SET id_horario = ?, id_medico = ?, fecha = ?, hora = ?, especialidad = ?
            WHERE id = ?
        """, (
            nuevo_id_horario,
            nuevo["id_medico"],
            nuevo["fecha"],
            nuevo["hora"],
            nuevo["especialidad"],
            id_turno
        ))

        conn.commit()
        conn.close()

        flash("Turno modificado correctamente.")
        return redirect(url_for("admin"))

    horarios_disponibles = obtener_horarios_filtrados(especialidad=turno["especialidad"], id_medico=None)
    conn.close()

    return render_template(
        "modificar_turno.html",
        usuario=current_user,
        turno=turno,
        horarios=horarios_disponibles,
        back_url=url_for("admin")
    )


@app.route("/medico")
@login_required
def medico():
    if current_user.rol != "medico":
        flash("No tenés permiso para ingresar a la vista médica.")
        return redirect(url_for("login"))

    medico_db = obtener_medico_por_email(current_user.email)

    if not medico_db:
        flash("No hay médico asociado a este usuario.")
        return redirect(url_for("login"))

    return render_template(
        "medico.html",
        usuario=current_user,
        medico=medico_db,
        turnos=obtener_turnos_por_medico(medico_db["id_medico"])
    )


@app.route("/medico/llamado/<int:id_turno>", methods=["POST"])
@login_required
def medico_llamado(id_turno):
    if current_user.rol != "medico":
        flash("No tenés permiso para modificar la agenda médica.")
        return redirect(url_for("login"))

    conn = get_conn()
    cursor = conn.cursor()

    turno = cursor.execute("""
        SELECT llamado
        FROM turnos
        WHERE id = ?
    """, (id_turno,)).fetchone()

    if turno:
        nuevo_estado = 0 if turno["llamado"] == 1 else 1

        cursor.execute("""
            UPDATE turnos
            SET llamado = ?
            WHERE id = ?
        """, (nuevo_estado, id_turno))

        conn.commit()
        flash("Estado del paciente actualizado.")
    else:
        flash("Turno no encontrado.")

    conn.close()
    return redirect(url_for("medico"))


@app.route("/medico/perfil", methods=["GET", "POST"])
@login_required
def perfil_medico():

    if current_user.rol != "medico":
        flash("No tenés permiso.")
        return redirect(url_for("login"))

    usuario = obtener_usuario_por_id(current_user.id)
    medico = obtener_medico_por_email(current_user.email)

    if request.method == "POST":

        email_nuevo = request.form["email"].strip().lower()

        actualizar_usuario(
            current_user.id,
            request.form["nombre"],
            request.form["apellido"],
            "",
            request.form["telefono"],
            email_nuevo
        )

        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE medicos
            SET
                nombre = ?,
                apellido = ?,
                telefono = ?,
                email = ?
            WHERE id_medico = ?
        """, (
            request.form["nombre"],
            request.form["apellido"],
            request.form["telefono"],
            email_nuevo,
            medico["id_medico"]
        ))

        conn.commit()
        conn.close()

        password_actual = request.form["password_actual"]
        nueva_password = request.form["nueva_password"]
        confirmar_password = request.form["confirmar_password"]

        if nueva_password:

            if not check_password_hash(
                usuario["password"],
                password_actual
            ):
                flash("La contraseña actual es incorrecta.")
                return redirect(url_for("perfil_medico"))

            if nueva_password != confirmar_password:
                flash("Las contraseñas nuevas no coinciden.")
                return redirect(url_for("perfil_medico"))

            cambiar_password_usuario(
                current_user.id,
                nueva_password
            )

        flash("Perfil actualizado correctamente.")
        return redirect(url_for("perfil_medico"))

    return render_template(
        "perfil_medico.html",
        usuario=usuario,
        medico=medico
    )


@app.route("/paciente/perfil", methods=["GET", "POST"])
@login_required
def perfil_paciente():

    if current_user.rol != "paciente":
        flash("No tenés permiso.")
        return redirect(url_for("login"))

    usuario = obtener_usuario_por_id(
        int(current_user.id)
    )

    if request.method == "POST":

        actualizar_usuario(
            int(current_user.id),
            request.form["nombre"],
            request.form["apellido"],
            request.form["dni"],
            request.form["telefono"],
            request.form["email"].strip().lower()
        )

        password_actual = request.form["password_actual"]
        nueva_password = request.form["nueva_password"]
        confirmar_password = request.form["confirmar_password"]

        if nueva_password:

            if not check_password_hash(
                usuario["password"],
                password_actual
            ):
                flash("La contraseña actual es incorrecta.")
                return redirect(url_for("perfil_paciente"))

            if nueva_password != confirmar_password:
                flash("Las contraseñas nuevas no coinciden.")
                return redirect(url_for("perfil_paciente"))

            cambiar_password_usuario(
                int(current_user.id),
                nueva_password
            )

        flash("Perfil actualizado correctamente.")
        return redirect(url_for("perfil_paciente"))

    return render_template(
        "perfil_paciente.html",
        usuario=usuario
    )

if __name__ == "__main__":
    app.run(debug=True)