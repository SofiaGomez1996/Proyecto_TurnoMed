# 🏥 TurnoMed

Sistema web de gestión de turnos médicos para consultorios pequeños.

---

## 📌 Descripción

TurnoMed es una aplicación desarrollada en Python que permite gestionar turnos médicos de forma simple.

El sistema está pensado para un consultorio pequeño donde:

- La administradora (recepcionista) otorga los turnos  
- El paciente solo consulta o solicita  
- El médico solo visualiza su agenda  

---

## 🧠 Tecnologías

- Python 3  
- Flask  
- SQLite  
- HTML / CSS / Bootstrap  

---

## ⚙️ Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-repo/turnomed.git
cd turnomed
2. Crear entorno virtual
python -m venv venv
3. Activar entorno

Windows:

venv\Scripts\activate

Mac/Linux:

source venv/bin/activate
4. Instalar dependencias
pip install flask
▶️ Ejecutar el proyecto
python app.py

Abrir en navegador:

http://localhost:5000
📁 Estructura del proyecto
turnomed/
│
├── app.py
├── database/
│   └── turnomed.db
├── templates/
│   ├── login.html
│   ├── admin.html
│   ├── paciente.html
│   └── medico.html
├── static/
│   └── estilos.css
└── README.md
👥 Roles del sistema
👩‍💼 Administradora
Carga horarios
Asigna turnos
Gestiona agenda
🧑‍⚕️ Médico
Consulta agenda
👤 Paciente
Consulta turnos
Solicita turno
🧪 Pruebas

Probar:

Login correcto e incorrecto
Asignación de turnos
Cancelación
Visualización por rol
📌 Flujo del sistema
Admin carga horarios
Admin asigna turnos
Paciente consulta
Médico visualiza agenda
🚀 Buenas prácticas del equipo
Hacer commits claros
No subir archivos innecesarios
Probar antes de subir
Trabajar por ramas
🌱 Futuras mejoras
Notificaciones
Reportes
Multi consultorio
Pagos