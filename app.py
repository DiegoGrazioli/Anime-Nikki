#import requests
from flask import Flask, redirect, request, render_template, url_for, session
from flask_session import Session
import sqlite3 as sq
import bcrypt

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

def hash_password(password):
    # Genera un salt casuale
    salt = bcrypt.gensalt()
    # Hasha la password con il salt
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password

def check_login(usern, passw):
    conn = sq.connect('anime.sqlite3')
    cur = conn.cursor()
    cur.execute('SELECT * FROM users WHERE username = ?', (usern,))
    user = cur.fetchone()
    conn.close()


    if user:
        # Ottieni l'indice della colonna 'password'
        password_index = cur.description.index(('password', None, None, None, None, None, None))
        hashed_password = user[password_index]
        
        # Controlla se la password fornita corrisponde alla password hashata nel database
        if bcrypt.checkpw(passw.encode('utf-8'), hashed_password):
            return user
        else:
            return None
    else:
        return None

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usern = request.form['username']
        passw = request.form['password']

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
        
        hashed_password = hash_password(passw)

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
            cur.execute('INSERT INTO users (username, password) VALUES (?, ?)', (usern, hashed_password))
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