from flask import Flask, render_template, request, redirect, session, flash, send_file
import sqlite3
import os
from werkzeug.utils import secure_filename
import plotly.express as px
import pandas as pd
import csv

app = Flask(__name__)
app.secret_key = 'your_secret_key'  
app.config['UPLOAD_FOLDER'] = 'static/profile_pics'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'}

# Database initialization
def init_db():
    conn = sqlite3.connect('health_app.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    name TEXT,
                    age INTEGER,
                    health_goals TEXT,
                    profile_picture TEXT
                  )''')
    c.execute('''CREATE TABLE IF NOT EXISTS health_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    symptoms TEXT,
                    mood TEXT,
                    sleep_hours INTEGER,
                    water_intake INTEGER,
                    notes TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                  )''')
    conn.commit()
    conn.close()

init_db()

# Helper function to get database connection
def get_db_connection():
    conn = sqlite3.connect('health_app.db')
    conn.row_factory = sqlite3.Row
    return conn

# Routes

@app.route('/')
def home():
    return redirect('/login')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password)).fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            return redirect('/logs')
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
        conn.commit()
        conn.close()
        flash('Registration successful! Please log in.', 'success')
        return redirect('/login')

    return render_template('register.html')

@app.route('/logs', methods=['GET', 'POST'])
def logs():
    if not session.get('user_id'):
        return redirect('/login')

    user_id = session.get('user_id')
    conn = get_db_connection()

    if request.method == 'POST':
        date = request.form['date']
        symptoms = request.form['symptoms']
        mood = request.form['mood']
        sleep_hours = request.form['sleep_hours']
        water_intake = request.form['water_intake']
        notes = request.form['notes']
        conn.execute("INSERT INTO health_logs (user_id, date, symptoms, mood, sleep_hours, water_intake, notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                     (user_id, date, symptoms, mood, sleep_hours, water_intake, notes))
        conn.commit()

    logs = conn.execute("SELECT * FROM health_logs WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return render_template('logs.html', logs=logs)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if not session.get('user_id'):
        return redirect('/login')
    
    user_id = session.get('user_id')
    conn = get_db_connection()

    if request.method == 'POST':
        name = request.form['name']
        age = request.form['age']
        health_goals = request.form['health_goals']

        if 'profile_picture' in request.files:
            file = request.files['profile_picture']
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                profile_picture = filepath
            else:
                profile_picture = None
        else:
            profile_picture = None

        conn.execute("UPDATE users SET name = ?, age = ?, health_goals = ?, profile_picture = ? WHERE id = ?",
                     (name, age, health_goals, profile_picture, user_id))
        conn.commit()
        conn.close()
        flash("Profile updated successfully!", 'success')

    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/charts', methods=['GET'])
def charts():
    if not session.get('user_id'):
        return redirect('/login')
    
    user_id = session.get('user_id')
    conn = get_db_connection()
    logs = conn.execute("SELECT * FROM health_logs WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()

    data = {
        'Date': [log['date'] for log in logs],
        'Mood': [log['mood'] for log in logs],
        'Sleep Hours': [log['sleep_hours'] for log in logs],
        'Water Intake': [log['water_intake'] for log in logs],
    }
    
    df = pd.DataFrame(data)
    
    mood_chart = px.line(df, x='Date', y='Mood', title='Mood Over Time')
    sleep_chart = px.line(df, x='Date', y='Sleep Hours', title='Sleep Hours Over Time')
    water_chart = px.line(df, x='Date', y='Water Intake', title='Water Intake Over Time')

    return render_template('charts.html', mood_chart=mood_chart.to_html(), sleep_chart=sleep_chart.to_html(), water_chart=water_chart.to_html())

@app.route('/export/csv')
def export_csv():
    if not session.get('user_id'):
        return redirect('/login')
    
    user_id = session.get('user_id')
    conn = get_db_connection()
    logs = conn.execute("SELECT * FROM health_logs WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()

    csv_file = 'health_logs.csv'
    with open(csv_file, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['Date', 'Symptoms', 'Mood', 'Sleep Hours', 'Water Intake', 'Notes'])
        for log in logs:
            writer.writerow([log['date'], log['symptoms'], log['mood'], log['sleep_hours'], log['water_intake'], log['notes']])

    return send_file(csv_file, as_attachment=True)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

if __name__ == '__main__':
    app.run(debug=True)
