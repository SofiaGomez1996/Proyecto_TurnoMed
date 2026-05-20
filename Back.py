import sqlite3
import os
from werkzeug.security import generate_password_hash

# Ruta absoluta para evitar errores de Windows
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Carpeta database
DATABASE_FOLDER = os.path.join(BASE_DIR, "database")

# Archivo .db
DB_PATH = os.path.join(DATABASE_FOLDER, "turnomed.db")


def conectar_db():

    # Crear carpeta database si no existe
    if not os.path.exists(DATABASE_FOLDER):
        os.makedirs(DATABASE_FOLDER)

    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    return conexion


def crear_tablas():

    conexion = conectar_db()
    cursor = conexion.cursor()

    # TABLA USUARIOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            apellido TEXT NOT NULL,
            dni TEXT UNIQUE,
            telefono TEXT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            rol TEXT NOT NULL
        )
    """)

    # TABLA HORARIOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS horarios (
            id_horario INTEGER PRIMARY KEY AUTOINCREMENT,
            medico TEXT NOT NULL,
            especialidad TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            disponible INTEGER DEFAULT 1
        )
    """)

    # TABLA TURNOS
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS turnos (
            id_turno INTEGER PRIMARY KEY AUTOINCREMENT,
            id_usuario INTEGER NOT NULL,
            medico TEXT NOT NULL,
            especialidad TEXT NOT NULL,
            fecha TEXT NOT NULL,
            hora TEXT NOT NULL,
            estado TEXT DEFAULT 'Confirmado',

            FOREIGN KEY(id_usuario)
            REFERENCES usuarios(id_usuario)
        )
    """)

    conexion.commit()
    conexion.close()


def crear_usuarios_iniciales():

    conexion = conectar_db()
    cursor = conexion.cursor()

    usuarios = [

        (
            "Admin",
            "TurnoMed",
            "00000000",
            "1122334455",
            "admin@turnomed.com",
            generate_password_hash("admin123"),
            "admin"
        ),

        (
            "Juan",
            "Pérez",
            "11111111",
            "1133445566",
            "paciente@turnomed.com",
            generate_password_hash("paciente123"),
            "paciente"
        ),

        (
            "Carlos",
            "Gómez",
            "22222222",
            "1144556677",
            "medico@turnomed.com",
            generate_password_hash("medico123"),
            "medico"
        )
    ]

    for usuario in usuarios:

        cursor.execute("""
            SELECT * FROM usuarios
            WHERE email = ?
        """, (usuario[4],))

        existe = cursor.fetchone()

        if not existe:
            cursor.execute("""
                INSERT INTO usuarios (
                    nombre,
                    apellido,
                    dni,
                    telefono,
                    email,
                    password,
                    rol
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, usuario)

    conexion.commit()
    conexion.close()


def crear_horarios_iniciales():

    conexion = conectar_db()
    cursor = conexion.cursor()

    horarios = [

        (
            "Dr. Gómez",
            "Clínica Médica",
            "2026-05-20",
            "09:00"
        ),

        (
            "Dr. Gómez",
            "Clínica Médica",
            "2026-05-20",
            "10:00"
        ),

        (
            "Dra. Ruiz",
            "Pediatría",
            "2026-05-21",
            "11:00"
        )
    ]

    for horario in horarios:

        cursor.execute("""
            SELECT * FROM horarios
            WHERE medico = ?
            AND fecha = ?
            AND hora = ?
        """, (
            horario[0],
            horario[2],
            horario[3]
        ))

        existe = cursor.fetchone()

        if not existe:
            cursor.execute("""
                INSERT INTO horarios (
                    medico,
                    especialidad,
                    fecha,
                    hora,
                    disponible
                )
                VALUES (?, ?, ?, ?, 1)
            """, horario)

    conexion.commit()
    conexion.close()


def inicializar_base_de_datos():

    crear_tablas()
    crear_usuarios_iniciales()
    crear_horarios_iniciales()


def buscar_usuario_por_email(email):

    conexion = conectar_db()

    usuario = conexion.execute("""
        SELECT *
        FROM usuarios
        WHERE email = ?
    """, (email,)).fetchone()

    conexion.close()

    return usuario


def buscar_usuario_por_id(id_usuario):

    conexion = conectar_db()

    usuario = conexion.execute("""
        SELECT *
        FROM usuarios
        WHERE id_usuario = ?
    """, (id_usuario,)).fetchone()

    conexion.close()

    return usuario


def registrar_paciente(
    nombre,
    apellido,
    dni,
    telefono,
    email,
    password
):

    conexion = conectar_db()
    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO usuarios (
            nombre,
            apellido,
            dni,
            telefono,
            email,
            password,
            rol
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        nombre,
        apellido,
        dni,
        telefono,
        email,
        generate_password_hash(password),
        "paciente"
    ))

    conexion.commit()
    conexion.close()


def obtener_pacientes():

    conexion = conectar_db()

    pacientes = conexion.execute("""
        SELECT *
        FROM usuarios
        WHERE rol = 'paciente'
        ORDER BY apellido, nombre
    """).fetchall()

    conexion.close()

    return pacientes


def cargar_horario(
    medico,
    especialidad,
    fecha,
    hora
):

    conexion = conectar_db()
    cursor = conexion.cursor()

    cursor.execute("""
        INSERT INTO horarios (
            medico,
            especialidad,
            fecha,
            hora,
            disponible
        )
        VALUES (?, ?, ?, ?, 1)
    """, (
        medico,
        especialidad,
        fecha,
        hora
    ))

    conexion.commit()
    conexion.close()


def obtener_horarios_disponibles():

    conexion = conectar_db()

    horarios = conexion.execute("""
        SELECT *
        FROM horarios
        WHERE disponible = 1
        ORDER BY fecha, hora
    """).fetchall()

    conexion.close()

    return horarios


def asignar_turno(
    id_usuario,
    id_horario
):

    conexion = conectar_db()
    cursor = conexion.cursor()

    horario = cursor.execute("""
        SELECT *
        FROM horarios
        WHERE id_horario = ?
        AND disponible = 1
    """, (id_horario,)).fetchone()

    if horario is None:
        conexion.close()
        return False

    cursor.execute("""
        INSERT INTO turnos (
            id_usuario,
            medico,
            especialidad,
            fecha,
            hora,
            estado
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        id_usuario,
        horario["medico"],
        horario["especialidad"],
        horario["fecha"],
        horario["hora"],
        "Confirmado"
    ))

    cursor.execute("""
        UPDATE horarios
        SET disponible = 0
        WHERE id_horario = ?
    """, (id_horario,))

    conexion.commit()
    conexion.close()

    return True


def obtener_turnos():

    conexion = conectar_db()

    turnos = conexion.execute("""
        SELECT
            turnos.*,
            usuarios.nombre,
            usuarios.apellido
        FROM turnos
        INNER JOIN usuarios
        ON turnos.id_usuario =
        usuarios.id_usuario
        ORDER BY fecha, hora
    """).fetchall()

    conexion.close()

    return turnos


def obtener_turnos_por_paciente(id_usuario):

    conexion = conectar_db()

    turnos = conexion.execute("""
        SELECT *
        FROM turnos
        WHERE id_usuario = ?
        ORDER BY fecha, hora
    """, (id_usuario,)).fetchall()

    conexion.close()

    return turnos


def obtener_turnos_por_medico(medico):

    conexion = conectar_db()

    turnos = conexion.execute("""
        SELECT
            turnos.*,
            usuarios.nombre,
            usuarios.apellido
        FROM turnos
        INNER JOIN usuarios
        ON turnos.id_usuario =
        usuarios.id_usuario
        WHERE medico = ?
        ORDER BY fecha, hora
    """, (medico,)).fetchall()

    conexion.close()

    return turnos


def cancelar_turno(id_turno):

    conexion = conectar_db()
    cursor = conexion.cursor()

    cursor.execute("""
        UPDATE turnos
        SET estado = 'Cancelado'
        WHERE id_turno = ?
    """, (id_turno,))

    conexion.commit()
    conexion.close()


def obtener_medico_actual():
    return "Dr. Gómez"