#import requests
from flask import Flask, redirect, request, render_template, url_for, session
from flask_session import Session
import sqlite3 as sq

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

def get_db():
    conn = sq.connect('anime.sqlite3')
    conn.row_factory = sq.Row
    return conn

@app.route('/')
def index():
    return redirect('/login')

def check_login(usern, passw):
    conn = sq.connect('anime.sqlite3')
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE username = ? AND password = ?', (usern, passw))
    result = cur.fetchone()
    conn.close()
    return result

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usern = request.form['username']
        passw = request.form['password']

        passw = str(hash(passw))

        result = check_login(usern, passw)
        if result:
            session['logged_in'] = True
            session['username'] = usern
            return redirect('/home')
        else:
            return render_template('login.html', message='Password o username errati. Riprova.')
    return render_template('login.html')

@app.route('/go_login')
def go_login():
    return redirect('/login')

@app.route('/go_register')
def go_register():
    return redirect('/register')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        usern = request.form['username']
        passw = request.form['password']
        
        passw = str(hash(passw))

        # Controlla se l'utente esiste già nel database
        conn = sq.connect('anime.sqlite3')
        cur = conn.cursor()
        cur.execute('SELECT * FROM users WHERE username = ?', (usern,))
        existing_user = cur.fetchone()
        
        if existing_user:
            conn.close()
            return render_template('register.html', message='Username già in uso. Scegli un altro username.')
        else:
            # Inserisci il nuovo utente nel database
            cur.execute('INSERT INTO users (username, password) VALUES (?, ?)', (usern, passw))
            conn.commit()
            conn.close()
            
            # Effettua il login automatico per il nuovo utente
            session['logged_in'] = True
            session['username'] = usern
            
            return redirect('/home')
    
    return render_template('register.html')

@app.route('/home')
def home():
    if 'logged_in' in session:
        return render_template('home.html', username=session['username'])
    else:
        return redirect('/login')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)