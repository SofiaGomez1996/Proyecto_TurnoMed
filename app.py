from flask import Flask, render_template, request, redirect, url_for

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