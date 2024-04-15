from datetime import datetime
import json
import xmltodict
import requests
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

@app.route('/calendar', methods=['GET', 'POST'])
def calendar():
    if 'logged_in' in session:
        app.config["SESSION_PERMANENT"] = False
        app.config["SESSION_TYPE"] = "filesystem"
        Session(app)

        # Funzione per ottenere gli anime in corso dall'API di AniList
        url = "https://graphql.anilist.co"

        query = '''
        query {
            Page(page: 1, perPage: 100) {
                media(status: RELEASING, type: ANIME) {
                    id
                    title {
                        romaji
                        english
                    }
                    description
                    coverImage {
                        large
                    }
                    nextAiringEpisode {
                        airingAt
                        episode
                    }
                }
            }
        }
        '''

        response = requests.post(url, json={'query': query})
        data = response.json()

        currently_airing_anime = []
        for anime in data['data']['Page']['media']:
            title = anime['title']['romaji']
            description = anime['description']
            image_url = anime['coverImage']['large']
            airing_day = "Unknown"
            episode = "Unknown"
            if anime["nextAiringEpisode"]:
                episode = anime["nextAiringEpisode"]["episode"]
                airing_at = anime["nextAiringEpisode"]["airingAt"]
                # Convertiamo il timestamp dell'episodio successivo in un giorno della settimana
                airing_day = datetime.fromtimestamp(airing_at).strftime('%A')
            currently_airing_anime.append({'title': title, 'description': description, 'image_url': image_url, 'airing_day': airing_day, 'episode': episode})

        return render_template('calendar.html', username=session['username'], data=currently_airing_anime)
    else:
        return redirect('/login')

@app.route('/home')
def home():
    if 'logged_in' in session:
        url = "https://www.animenewsnetwork.com/encyclopedia/reports.xml?id=148&nlist=140&nskip=0"
        response = requests.get(url)
        xml_data = response.text

        # Converto l'XML in un dizionario Python
        data_dict = xmltodict.parse(xml_data)

        for item in data_dict['report']['item']:
            # Aggiungo un campo 'image_url' a ciascun dizionario
            item['anime']['@href'] = item['anime']['@href'][27:]
            item['date_added'] = item['date_added'][0:10]
            # item['anime']['@href'] = 'https://www.animenewsnetwork.com/encyclopedia/api.xml?title' + item['anime']['@href']
            # single_response = requests.get(item['anime']['@href'])
            # single_xml_data = single_response.text
            # single_data_dict = xmltodict.parse(single_xml_data)
            # if 'anime' in single_data_dict['ann']:
            #     item['additional_data'] = single_data_dict['ann']['anime']

        url = "https://www.animenewsnetwork.com/encyclopedia/reports.xml?id=149&nlist=140&nskip=0"
        response = requests.get(url)
        xml_data = response.text

        # Converto l'XML in un dizionario Python
        data_dict2 = xmltodict.parse(xml_data)

        for item in data_dict2['report']['item']:
            # Aggiungo un campo 'image_url' a ciascun dizionario
            item['manga']['@href'] = item['manga']['@href'][27:]
            item['date_added'] = item['date_added'][0:10]
        
        # https://www.animenewsnetwork.com/encyclopedia/reports.xml?id=149&nlist=140&nskip=0

        return render_template('home.html', username=session['username'], data=data_dict, data2=data_dict2)
    else:
        return redirect('/login')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    return redirect('/login')


@app.get('/content/<int:id>')
def get_item_by_id(id):
    
    variables = {
        'id': id,  # Passa il nome dell'anime come stringa
    }

    query = '''
        query ($id: Int) {
            Media (id: $id, type: ANIME) {
                id
                title {
                    romaji
                    english
                    native
                }
                type
                format
                status
                episodes
                duration
                averageScore
                popularity
                description
                coverImage {
                    large
                    medium
                }
                bannerImage
                startDate {
                    year
                    month
                    day
                }
                endDate {
                    year
                    month
                    day
                }
                genres
                synonyms
                season
                source
                studios {
                    nodes {
                        id
                        name
                    }
                }
                trailer {
                    id
                    site
                    thumbnail
                }
                staff {
                    edges {
                        role
                        node {
                            id
                            name {
                                full
                                native
                            }
                        }
                    }
                }
                characters {
                    edges {
                        role
                        node {
                            id
                            name {
                                full
                                native
                            }
                        }
                    }
                }
            }
        }
    '''

    url = 'https://graphql.anilist.co'
    response = requests.post(url, json={'query': query, 'variables': variables})
    data = response.json()
    if data is None or data.get('data', None) is None or data['data'].get('Media', None) is None:  
        return render_template('search.html', username=session.get('username', None), message='Anime non trovato')
    else:
        return render_template('item_details.html', data=data, username=session.get('username', None))

@app.get('/content/search/<string:name>')
def get_item_by_name(name):

    variables = {
        'title': name,  # Passa il nome dell'anime come stringa
    }

    query = '''
        query ($title: String) {
            Media (search: $title, type: ANIME) {
                id
                title {
                    romaji
                    english
                    native
                }
            }
        }
    ''';

    url = 'https://graphql.anilist.co'
    response = requests.post(url, json={'query': query, 'variables': variables})
    data = response.json()

    return get_item_by_id(data['data']['Media']['id'])

@app.get('/content/search/')
def search():
    
    return render_template('search.html', username=session.get('username', None))

@app.route('/get_name', methods=['POST'])
def get_name():
        if request.method == 'POST':
            name = request.form['title']
            return get_item_by_name(name)

if __name__ == '__main__':
    app.run(debug=True)
