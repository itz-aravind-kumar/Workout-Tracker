import os
os.environ["DISPLAY"] = ":0"

from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import errorcode
from datetime import datetime
from multiprocessing import Process
from timer_window import launch_timer_window

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # For flash messages

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database=""
    )

@app.route('/toggle_status/<int:student_id>', methods=['POST'])
def toggle_status(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get current status
    cursor.execute("SELECT status FROM students WHERE id = %s", (student_id,))
    current_status = cursor.fetchone()[0]

    # Toggle
    new_status = 'inactive' if current_status == 'active' else 'active'
    cursor.execute("UPDATE students SET status = %s WHERE id = %s", (new_status, student_id))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('index'))

@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students ORDER BY first_name")
    students = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('index.html', students=students)

@app.route('/add_student', methods=['GET', 'POST'])
def add_student():
    if request.method == 'POST':
        data = {key: request.form.get(key) for key in ['first_name','middle_name','last_name','gender','call_sign','runner_type']}
        dob = request.form.get('dob')
        data['dob'] = dob if dob else None 
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO students (first_name, middle_name, last_name, gender, dob, call_sign, runner_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                data['first_name'], data['middle_name'], data['last_name'], data['gender'],
                data['dob'], data['call_sign'], data['runner_type']
            ))
            conn.commit()
            flash('Student added successfully.', 'success')
        except mysql.connector.Error as err:
            flash(f"Error: {err}", 'danger')
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('index'))
    return render_template('add_student.html')


@app.route('/delete_student/<int:student_id>', methods=['POST'])
def delete_student(student_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Just mark the student as inactive instead of deleting
        cursor.execute("UPDATE students SET status = 'inactive' WHERE id = %s", (student_id,))
        conn.commit()
        flash("Student marked as inactive successfully.", "info")
    except Exception as e:
        conn.rollback()
        flash("Error marking student inactive: " + str(e), "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('index'))


@app.route('/sessions/<int:student_id>')
def sessions(student_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()

    cursor.execute("SELECT * FROM sessions WHERE student_id = %s ORDER BY session_date DESC, session_time DESC", (student_id,))
    sessions = cursor.fetchall()

    cursor.execute("SELECT * FROM students ORDER BY first_name")
    all_students = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('sessions.html', student=student, sessions=sessions, all_students=all_students)

@app.route('/duplicate_session', methods=['POST'])
def duplicate_session():
    original_session_id = int(request.form['original_session_id'])
    selected_student_ids = request.form.getlist('student_ids')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM sessions WHERE id = %s", (original_session_id,))
    original_session = cursor.fetchone()
    if not original_session:
        flash("Original session not found.", "danger")
        return redirect(request.referrer)

    cursor.execute("SELECT * FROM workouts WHERE session_id = %s", (original_session_id,))
    original_workouts = cursor.fetchall()

    for student_id in selected_student_ids:
        student_id = int(student_id)
        cursor.execute("""
            SELECT * FROM sessions
            WHERE session_date = %s AND session_time = %s AND student_id = %s
        """, (original_session['session_date'], original_session['session_time'], student_id))
        existing = cursor.fetchone()
        if existing:
            continue

        cursor.execute("""
            INSERT INTO sessions (student_id, session_date, session_time)
            VALUES (%s, %s, %s)
        """, (student_id, original_session['session_date'], original_session['session_time']))
        conn.commit()
        new_session_id = cursor.lastrowid

        for workout in original_workouts:
            cursor.execute("""
                INSERT INTO workouts (session_id, sequence_number, workout_type, duration, repetitions, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                new_session_id,
                workout['sequence_number'],
                workout['workout_type'],
                workout['duration'],
                workout['repetitions'],
                workout['notes']
            ))
        conn.commit()

    cursor.close()
    conn.close()
    flash("Session duplicated successfully!", "success")
    return redirect(request.referrer)

@app.route('/add_session/<int:student_id>', methods=['GET','POST'])
def add_session(student_id):
    if request.method == 'POST':
        session_date = request.form['session_date']
        session_time = request.form['session_time']

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO sessions (student_id, session_date, session_time)
                VALUES (%s, %s, %s)
            """, (student_id, session_date, session_time))
            conn.commit()
            flash('Session added.', 'success')
        except mysql.connector.IntegrityError as e:
            if e.errno == errorcode.ER_DUP_ENTRY:
                flash("Session already exists for this date and time.", "warning")
            else:
                flash(f"Error: {e}", "danger")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for('sessions', student_id=student_id))

    return render_template('add_session.html', student_id=student_id)

@app.route('/workouts/<int:session_id>')
def workouts(session_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
    session = cursor.fetchone()

    cursor.execute("SELECT * FROM students WHERE id = %s", (session['student_id'],))
    student = cursor.fetchone()

    cursor.execute("SELECT * FROM workouts WHERE session_id = %s ORDER BY sequence_number", (session_id,))
    workouts = cursor.fetchall()

    existing_sequences = {w['sequence_number'] for w in workouts}
    sequences = []
    for seq in range(1, 16):
        if seq in existing_sequences:
            workout = next(w for w in workouts if w['sequence_number'] == seq)
            sequences.append({'sequence': seq, 'filled': True, 'workout': workout})
        else:
            sequences.append({'sequence': seq, 'filled': False})

    cursor.close()
    conn.close()
    return render_template('workouts.html', session=session, student=student, sequences=sequences)

@app.route('/delete_session', methods=['POST'])
def delete_session():
    session_id = request.form['session_id']
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Delete workouts first (because of foreign key constraint)
        cursor.execute("DELETE FROM workouts WHERE session_id = %s", (session_id,))
        # Delete the session itself
        cursor.execute("DELETE FROM sessions WHERE id = %s", (session_id,))
        conn.commit()
        flash('Session deleted successfully.', 'success')
    except Exception as e:
        conn.rollback()
        flash('Error deleting session.', 'danger')
    finally:
        cursor.close()
        conn.close()
    return redirect(request.referrer or url_for('index'))




@app.route('/add_workout/<int:session_id>/<int:sequence_number>', methods=['GET', 'POST'])
def add_workout(session_id, sequence_number):
    if request.method == 'POST':
        workout_type = request.form['workout_type']
        critical_velocity = 'critical_velocity' in request.form
        distance = request.form.get('distance') or None
        repetitions = int(request.form.get('repetitions') or 1)
        notes = request.form.get('notes')

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            if critical_velocity:
                # Read individual rep durations
                durations = []
                for i in range(repetitions):
                    d = request.form.get(f'duration_{i+1}')
                    if not d:
                        raise ValueError(f"Duration missing for rep {i+1}")
                    if len(d.split(':')) == 2:
                        d = '00:' + d
                    duration_obj = datetime.strptime(d, '%H:%M:%S').time()
                    durations.append(duration_obj)

                # Use first duration just for `workouts` table display
                display_duration = durations[0]

                cursor.execute("""
                    INSERT INTO workouts (session_id, sequence_number, workout_type, duration, repetitions, notes, distance, critical_velocity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (session_id, sequence_number, workout_type, display_duration, repetitions, notes, distance, True))
                workout_id = cursor.lastrowid

                # Insert into rep_durations table
                for i, dur in enumerate(durations):
                    cursor.execute("""
                        INSERT INTO rep_durations (workout_id, rep_number, duration)
                        VALUES (%s, %s, %s)
                    """, (workout_id, i+1, dur))

            else:
                # Parse single duration
                d = request.form['duration']
                if len(d.split(':')) == 2:
                    d = '00:' + d
                duration_obj = datetime.strptime(d, '%H:%M:%S').time()

                cursor.execute("""
                    INSERT INTO workouts (session_id, sequence_number, workout_type, duration, repetitions, notes, distance, critical_velocity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (session_id, sequence_number, workout_type, duration_obj, repetitions, notes, distance, False))

            conn.commit()
            flash(f"Workout #{sequence_number} added.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error: {str(e)}", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('workouts', session_id=session_id))

    return render_template('add_workout.html', session_id=session_id, sequence_number=sequence_number)


@app.route('/workout_detail/<int:workout_id>')
def workout_detail(workout_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT * FROM workouts WHERE id = %s", (workout_id,))
    workout = cursor.fetchone()

    if not workout:
        flash("Workout not found.", "danger")
        return redirect(url_for('index'))

    session_id = workout['session_id']
    cursor.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
    session = cursor.fetchone()

    student_id = session['student_id']
    cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()

    rep_durations = []
    if workout['critical_velocity']:
        cursor.execute("SELECT duration FROM rep_durations WHERE workout_id = %s ORDER BY rep_number", (workout_id,))
        rep_durations = [row['duration'] for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return render_template('workout_detail.html', workout=workout, session=session, student=student, rep_durations=rep_durations)




# --- UPDATED `edit_workout` route using mysql.connector (not SQLAlchemy) ---

@app.route('/edit_workout/<int:workout_id>', methods=['GET', 'POST'])
def edit_workout(workout_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get workout details
    cursor.execute("SELECT * FROM workouts WHERE id = %s", (workout_id,))
    workout = cursor.fetchone()
    if not workout:
        flash("Workout not found.", "danger")
        return redirect(url_for('index'))

    session_id = workout['session_id']
    cursor.execute("SELECT * FROM sessions WHERE id = %s", (session_id,))
    session = cursor.fetchone()
    cursor.execute("SELECT * FROM students WHERE id = %s", (session['student_id'],))
    student = cursor.fetchone()

    cursor.execute("SELECT duration FROM rep_durations WHERE workout_id = %s ORDER BY rep_number", (workout_id,))
    rep_durations = [str(row['duration']) for row in cursor.fetchall()]

    if request.method == 'POST':
        workout_type = request.form['workout_type']
        distance = request.form.get('distance') or None
        repetitions = int(request.form.get('repetitions', 1))
        notes = request.form.get('notes')
        critical_velocity = 'critical_velocity' in request.form

        try:
            cursor.execute("""
                UPDATE workouts SET
                    workout_type = %s,
                    distance = %s,
                    repetitions = %s,
                    notes = %s,
                    critical_velocity = %s
                WHERE id = %s
            """, (workout_type, distance, repetitions, notes, critical_velocity, workout_id))

            # Clear old rep_durations
            cursor.execute("DELETE FROM rep_durations WHERE workout_id = %s", (workout_id,))

            if critical_velocity:
                for i in range(1, repetitions + 1):
                    d = request.form.get(f'duration_{i}')
                    if len(d.split(':')) == 2:
                        d = '00:' + d
                    t = datetime.strptime(d, '%H:%M:%S').time()
                    cursor.execute("""
                        INSERT INTO rep_durations (workout_id, rep_number, duration)
                        VALUES (%s, %s, %s)
                    """, (workout_id, i, t))
                display_duration = request.form.get('duration_1')
                if len(display_duration.split(':')) == 2:
                    display_duration = '00:' + display_duration
                duration_obj = datetime.strptime(display_duration, '%H:%M:%S').time()
                cursor.execute("UPDATE workouts SET duration = %s WHERE id = %s", (duration_obj, workout_id))
            else:
                d = request.form.get('duration')
                if len(d.split(':')) == 2:
                    d = '00:' + d
                t = datetime.strptime(d, '%H:%M:%S').time()
                cursor.execute("UPDATE workouts SET duration = %s WHERE id = %s", (t, workout_id))

            conn.commit()
            flash("Workout updated successfully.", "success")
            return redirect(url_for('workout_detail', workout_id=workout_id))
        except Exception as e:
            conn.rollback()
            flash("Error updating workout: " + str(e), "danger")
    
    cursor.close()
    conn.close()
    return render_template('edit_workout.html', workout=workout, session=session, student=student, rep_durations=rep_durations)


@app.route('/delete_workout/<int:workout_id>', methods=['POST'])
def delete_workout(workout_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get the session ID for redirection
    cursor.execute("SELECT session_id FROM workouts WHERE id = %s", (workout_id,))
    result = cursor.fetchone()
    if not result:
        flash("Workout not found.", "danger")
        return redirect(url_for('index'))
    session_id = result[0]

    try:
        # Delete rep_durations if present
        cursor.execute("DELETE FROM rep_durations WHERE workout_id = %s", (workout_id,))
        # Then delete the workout itself
        cursor.execute("DELETE FROM workouts WHERE id = %s", (workout_id,))
        conn.commit()
        flash("Workout deleted successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash("Error deleting workout: " + str(e), "danger")
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('workouts', session_id=session_id))


@app.route('/select_session', methods=['GET', 'POST'])
def select_session():
    if request.method == 'POST':
        session_date = request.form['session_date']
        session_type = request.form['session_time']
        return redirect(url_for('start_timers', date=session_date, session_type=session_type))
    return render_template('select_session.html')


@app.route('/start_timers')
def start_timers():
    session_date = request.args.get('date')
    session_type = request.args.get('session_type')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT s.*, st.first_name, st.last_name, st.status, w.id as workout_id, w.sequence_number, w.workout_type,
               w.duration, w.repetitions, w.distance, w.notes, w.critical_velocity
        FROM sessions s
        JOIN students st ON s.student_id = st.id
        JOIN workouts w ON s.id = w.session_id
        WHERE s.session_date = %s AND s.session_time = %s AND st.status = 'active'
        ORDER BY s.student_id, w.sequence_number
    """, (session_date, session_type))
    all_data = cursor.fetchall()

    # Attach rep_durations for CV workouts
    workout_ids = [w['workout_id'] for w in all_data if w['critical_velocity']]
    if workout_ids:
        format_strings = ','.join(['%s'] * len(workout_ids))
        cursor.execute(f"""
            SELECT workout_id, duration FROM rep_durations
            WHERE workout_id IN ({format_strings})
        """, workout_ids)
        rep_durations_map = {}
        for row in cursor.fetchall():
            rep_durations_map.setdefault(row['workout_id'], []).append(row['duration'])

        for w in all_data:
            if w['critical_velocity']:
                w['rep_durations'] = rep_durations_map.get(w['workout_id'], [])

    cursor.close()
    conn.close()

    if all_data:
        from multiprocessing import Process
        from timer_window import launch_timer_window
        p = Process(target=launch_timer_window, args=(all_data,))
        p.start()
        flash("Timer window launched.", "success")
    else:
        flash("No workouts found for selected session.", "danger")
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)
