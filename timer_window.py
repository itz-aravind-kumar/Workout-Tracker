import tkinter as tk
import time as time_module
import math

def launch_timer_window(workouts):
    def format_time(seconds):
        return time_module.strftime("%M:%S", time_module.gmtime(seconds))

    def format_session_time(seconds):
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def update_all_timers():
        nonlocal session_start_time, session_active

        if session_active:
            current_time = time_module.time()
            session_elapsed = int(current_time - session_start_time)
            session_timer_label.config(text=format_session_time(session_elapsed))

        all_completed = True

        for i in range(len(timer_labels)):
            if workout_index[i] >= len(sequences[i]):
                workout_labels[i].config(text="✅ DONE")
                reps_labels[i].config(text="")
                timer_labels[i].config(text="")
                continue
            else:
                all_completed = False

            if reps_left[i] > 0:
                time_left[i] -= 1
                if time_left[i] < 0:
                    time_left[i] = 0
                timer_labels[i].config(text=format_time(time_left[i]))

                if time_left[i] == 0:
                    reps_left[i] -= 1
                    completed = sequences[i][workout_index[i]]['repetitions'] - reps_left[i]
                    total = sequences[i][workout_index[i]]['repetitions']
                    reps_labels[i].config(text=f"Reps: {completed+1}/{total}" if reps_left[i] > 0 else f"Reps: {total}/{total}")

                    if reps_left[i] > 0:
                        time_left[i] = sequences[i][workout_index[i]]['duration'].seconds
            else:
                workout_index[i] += 1
                if workout_index[i] < len(sequences[i]):
                    current = sequences[i][workout_index[i]]
                    reps_left[i] = current['repetitions']
                    time_left[i] = current['duration'].seconds
                    workout_labels[i].config(text=current['workout_type'])
                    reps_labels[i].config(text=f"Reps: 1/{reps_left[i]}")
                    timer_labels[i].config(text=format_time(time_left[i]))
                else:
                    workout_labels[i].config(text="✅ DONE")
                    reps_labels[i].config(text="")
                    timer_labels[i].config(text="")

        if all_completed and session_active:
            session_active = False
            session_timer_label.config(fg="#059669")

        root.after(1000, update_all_timers)

    grouped = {}
    for w in workouts:
        first = w.get('first_name', '').strip()
        name = f"{first}".capitalize()
        if name not in grouped:
            grouped[name] = []
        grouped[name].append(w)

    root = tk.Tk()
    root.title("Workout Timers")
    root.configure(bg="black")
    root.attributes("-fullscreen", True)
    root.bind('<Escape>', lambda e: root.destroy())

    session_start_time = time_module.time()
    session_active = True

    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    total_students = len(grouped)

    if total_students <= 4:
        cols, rows = 2, 2
    elif total_students <= 6:
        cols, rows = 3, 2
    elif total_students == 7:
        cols, rows = 4, 2
    elif total_students == 8:
        cols, rows = 4, 2
    elif total_students <= 9:
        cols, rows = 3, 3
    elif total_students <= 12:
        cols, rows = 4, 3
    elif total_students <= 16:
        cols, rows = 4, 4
    elif total_students <= 20:
        cols, rows = 5, 4
    else:
        cols = 6
        rows = math.ceil(total_students / 6)

    header_frame = tk.Frame(root, bg="black", height=100)
    header_frame.pack(fill="x")
    header_frame.pack_propagate(False)

    title_label = tk.Label(
        header_frame, text="WORKOUT TIMERS", font=("Arial", 38, "bold"), fg="red", bg="black"
    )
    title_label.pack(side="left", padx=20, pady=10)

    session_timer_label = tk.Label(
        header_frame, text="00:00:00", font=("Arial", 80, "bold"), bg="black", fg="red", relief="solid"
    )
    session_timer_label.pack(side="right", padx=20, pady=4)

    session_label = tk.Label(
        header_frame, text="SESSION TIME: ", font=("Arial", 40, "bold"), bg="black", fg="red"
    )
    session_label.pack(side="right", padx=(20, 5), pady=10)

    main_frame = tk.Frame(root, bg="black")
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    available_width = screen_width
    available_height = screen_height

    if total_students == 7:
        box_width = (available_width // 4) - 15
        box_height = (available_height // 2) - 15
    else:
        box_width = (available_width // cols) - 15
        box_height = (available_height // rows) - 15

    box_width = max(box_width, 250)
    box_height = max(box_height, 180)

    timer_labels = []
    reps_labels = []
    workout_labels = []
    time_left = []
    reps_left = []
    sequences = []
    workout_index = []

    for i in range(cols):
        main_frame.grid_columnconfigure(i, weight=1)
    for i in range(rows):
        main_frame.grid_rowconfigure(i, weight=1)

    row = 0
    col = 0

    for idx, (name, workout_list) in enumerate(grouped.items()):
        if total_students == 7 and idx == 4:
            row += 1
            col = 0
        elif col >= cols:
            row += 1
            col = 0

        box = tk.Frame(
            main_frame, bg="#ffffff", padx=3, pady=5,
            bd=1, relief="solid", width=box_width, height=box_height
        )
        box.grid(row=row, column=col, padx=2, pady=0.5, sticky="nsew")
        box.grid_propagate(False)

        header_frame = tk.Frame(box, bg="#1e3a8a", height=85)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        name_font_size = max(37, min(42, box_width // 10))
        name_label = tk.Label(header_frame, text=name.upper(), font=("Arial", name_font_size, "bold"), bg="#1e3a8a", fg="white")
        name_label.pack(expand=True)

        content_frame = tk.Frame(box, bg="#ffffff")
        content_frame.pack(fill="both", expand=True)

        workout_text = workout_list[0]['workout_type']
        distance = workout_list[0].get('distance')
        if distance:
            workout_text += f"  ({distance}m)"

        workout_label_font_size = max(30, min(40, box_width // 16))
        workout_label = tk.Label(content_frame, text=workout_text, font=("Arial", workout_label_font_size, "bold"), bg="#ffffff", fg="#1f2937")
        workout_label.pack(pady=0)

        reps_font_size = max(35, min(40, box_width // 16))
        reps_label = tk.Label(content_frame, text=f"Reps: 1/{workout_list[0]['repetitions']}", font=("Arial", reps_font_size, "bold"), bg="#ffffff", fg="#059669")
        reps_label.pack(pady=0)

        timer_font_size = max(75, min(53, box_width // 5))
        timer_label = tk.Label(content_frame, text=format_time(workout_list[0]['duration'].seconds), font=("Arial", timer_font_size, "bold"), bg="#ffffff", fg="#dc2626")
        timer_label.pack(pady=1)

        notes = workout_list[0].get('notes')
        if notes:
            tk.Label(content_frame, text=f"Note: {notes}", font=("Arial", 20, "italic"), bg="#ffffff", fg="#19191b", wraplength=box_width-40, justify="center").pack(pady=0)

        workout_labels.append(workout_label)
        reps_labels.append(reps_label)
        timer_labels.append(timer_label)
        time_left.append(workout_list[0]['duration'].seconds)
        reps_left.append(workout_list[0]['repetitions'])
        sequences.append(workout_list)
        workout_index.append(0)

        col += 1

    control_frame = tk.Frame(root, bg="black", height=30)
    control_frame.pack(fill="x", side="bottom")
    control_label = tk.Label(control_frame, text="Press ESC to exit fullscreen", font=("Arial", 10), bg="black", fg="gray")
    control_label.pack(pady=5)

    update_all_timers()
    root.mainloop()



