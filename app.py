#import requests
from flask import Flask, redirect, request, render_template, url_for
import sqlite3 as sq

app = Flask(__name__)

def get_db():
    conn = sq.connect('anime.sqlite3')
    conn.row_factory = sq.Row
    return conn

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/access', methods=['POST'])
def login():
    # Get the data from the form
    usern = request.form.get('username')
    passw = request.form.get('password')

    # Connect to the database
    conn = get_db()
    cur = conn.cursor()

    # Execute the query to check if the username and password match
    cur.execute('SELECT * FROM users WHERE username = ? AND password = ?', (usern, passw))
    result = cur.fetchone()

    # Close the database connection
    conn.close()

    # Check if the result is not None, indicating a successful login
    if result is not None:
        return redirect('/home')
    else:
        return render_template('login.html', message='Password o username errati. Riprova.')

@app.route('/new_user')
def go_register():
    return render_template('register.html', message='')

@app.route('/login')
def go_login():
    return render_template('login.html', message='')

@app.route('/register', methods=['POST'])
def register():
    # Get the data from the form
    usern = request.form.get('username')
    passw = request.form.get('password')

    # Connect to the database
    conn = get_db()
    cur = conn.cursor()

    # Execute the query to check if the username and password match
    cur.execute('INSERT INTO users (username, password) VALUES (?, ?)', (usern, passw))

    # Close the database connection
    conn.close()

    # Check if the result is not None, indicating a successful login
    return redirect('/home')

@app.route('/home')
def home():
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True)