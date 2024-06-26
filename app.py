from datetime import datetime
import xmltodict
import requests
from flask import Flask, json, jsonify, redirect, request, render_template, url_for, session
from flask_session import Session
import sqlite3 as sq
import bcrypt
import random
from flask_assets import Environment, Bundle

counter = 0

app = Flask(__name__)
assets = Environment(app)

js = Bundle('js/chart.min.js', output='gen/packed.js')
assets.register('js_all', js)

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
            cur.execute('INSERT INTO users (username, password, createdate) VALUES (?, ?, ?)', (usern, hashed_password, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
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
            Page {
                airingSchedules(notYetAired: true) {
                    media {
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
        }
        '''

        response = requests.post(url, json={'query': query})
        data = response.json()

        currently_airing_anime = []
        for schedule in data['data']['Page']['airingSchedules']:
            anime = schedule['media']
            title = anime['title']['english'] or anime['title']['romaji']
            description = anime['description']
            image_url = anime['coverImage']['large']
            airing_day = "Unknown"
            episode = "Unknown"
            if anime.get("nextAiringEpisode"):
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

@app.get('/content/characters/<int:id>')
def get_char_by_id(id):
        
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
                characters {
                    edges {
                        role
                        node {
                            id
                            name {
                                full
                                native
                            }
                            image {
                                large
                                medium
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
        return render_template('char_details.html', data=data, username=session.get('username', None))

@app.get('/content/<int:id>')
def get_item_by_id(id, is_anime="None"):
    if is_anime == "None":
        is_anime = request.args.get('is_anime', 'false') == 'true'
    
    variables = {
        'id': id,  # Passa il nome dell'anime come stringa
    }
    if is_anime:
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
                                image {
                                    large
                                    medium
                                }
                            }
                        }
                    }
                }
            }
        '''
    else:
        query = '''
            query ($id: Int) {
                Media (id: $id, type: MANGA) {
                    id
                    title {
                        romaji
                        english
                        native
                    }
                    type
                    format
                    status
                    chapters
                    volumes
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
                    characters {
                        edges {
                            role
                            node {
                                id
                                name {
                                    full
                                    native
                                }
                                image {
                                    large
                                    medium
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
        if is_anime:
            return render_template('search.html', username=session.get('username', None), anime_message='Anime non trovato')
        else:
            return render_template('search.html', username=session.get('username', None), manga_message='Manga non trovato')
    else:
        if is_anime:
            return render_template('anime_item_details.html', data=data, username=session.get('username', None))
        else:
            return render_template('manga_item_details.html', data=data, username=session.get('username', None))

@app.get('/content/search/<string:name>')
def get_item_by_name(name, is_anime=True):

    variables = {
        'title': name,  # Passa il nome dell'anime come stringa
    }

    if is_anime:
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
        '''
    else:
        query = '''
            query ($title: String) {
                Media (search: $title, type: MANGA) {
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

    return get_item_by_id(data['data']['Media']['id'], is_anime)

@app.get('/content/search/')
def search():
    
    return render_template('search.html', username=session.get('username', None))

@app.route('/anime', methods=['POST'])
def get_anime_name():
        if request.method == 'POST':
            name = request.form['title']
            return get_item_by_name(name, True) # True per indicare che è un anime

@app.route('/manga', methods=['POST'])
def get_manga_name():
        if request.method == 'POST':
            name = request.form['title']
            return get_item_by_name(name, False) # False per indicare che è un manga

@app.route('/topchar')
def topchar():
    limit = request.args.get('limit', default=10, type=int)
    url = "https://graphql.anilist.co"

    # Query GraphQL per ottenere i personaggi più popolari
    query = """
    query ($page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            characters(sort: FAVOURITES_DESC) {
                id
                name {
                    full
                }
                image {
                    large
                }
                favourites
                description
            }
        }
    }
    """

    # Parametri della query
    variables = {
        "page": 1,
        "perPage": limit
    }

    # Effettua la richiesta POST all'API di AniList
    response = requests.post(url, json={'query': query, 'variables': variables})

    data = response.json()

    for character in data['data']['Page']['characters']:
        description = character['description']
        # Sostituisci "__" con una nuova riga per separare le informazioni
        description = description.replace(":__", ": ")
        description = description.replace(":**", ": ")

        description_lines = description.split('__')
        character['description_lines'] = description_lines

    return render_template('topchar.html', data=data, username=session.get('username', None))

@app.route('/topanime')
def topanime():
    limit = request.args.get('limit', default=10, type=int)
    url = "https://graphql.anilist.co"

    # Query GraphQL per ottenere i personaggi più popolari
    query = """
        query ($page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            media(sort: SCORE_DESC, type: ANIME) {
            id
            title {
                romaji
                english
                native
            }
            coverImage {
                large
            }
            startDate {
                year
                month
                day
            }
            description
            genres
            averageScore
            popularity
            type
            format
            status
            episodes
            studios {
                nodes {
                name
                }
            }
            }
        }
        }
    """

    # Parametri della query
    variables = {
        "page": 1,
        "perPage": limit
    }

    # Effettua la richiesta POST all'API di AniList
    response = requests.post(url, json={'query': query, 'variables': variables})

    data = response.json()

    return render_template('topanime.html', data=data, username=session.get('username', None))

@app.route('/topmanga')
def topmanga():
    limit = request.args.get('limit', default=10, type=int)
    url = "https://graphql.anilist.co"

    # Query GraphQL per ottenere i personaggi più popolari
    query = """
        query ($page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            media(sort: SCORE_DESC, type: MANGA) {
            id
            title {
                romaji
                english
                native
            }
            coverImage {
                large
            }
            startDate {
                year
                month
                day
            }
            description
            genres
            averageScore
            popularity
            type
            format
            status
            chapters
            volumes
            }
        }
        }
    """

    # Parametri della query
    variables = {
        "page": 1,
        "perPage": limit
    }

    # Effettua la richiesta POST all'API di AniList
    response = requests.post(url, json={'query': query, 'variables': variables})

    data = response.json()

    return render_template('topmanga.html', data=data, username=session.get('username', None))

@app.route('/toggle_favourite', methods=['POST'])
def toggle_favourite():
    data = request.json
    anime_id = data.get('animeId')
    user_id = data.get('userId')

    try:
        conn = sq.connect('anime.sqlite3')
        cursor = conn.cursor()

        # Verifica se l'anime è già nei preferiti dell'utente
        cursor.execute("SELECT 1 FROM user_anime WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
        row = cursor.fetchone()

        if row:
            # Rimuovi l'anime dai preferiti dell'utente
            cursor.execute("DELETE FROM user_anime WHERE user_id = ? AND anime_id = ?", (user_id, anime_id))
            conn.commit()

            conn.close()
            return jsonify({'success': True, 'message': 'Anime rimosso dai preferiti'})
        else:
            # Aggiungi l'anime ai preferiti dell'utente
            cursor.execute("INSERT INTO user_anime (user_id, anime_id) VALUES (?, ?)", (user_id, anime_id))
            conn.commit()

            conn.close()
            return jsonify({'success': True, 'message': 'Anime aggiunto ai preferiti'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/toggle_favourite_m', methods=['POST'])
def toggle_favourite_m():
    data = request.json
    manga_id = data.get('mangaId')
    user_id = data.get('userId')

    try:
        conn = sq.connect('anime.sqlite3')
        cursor = conn.cursor()

        # Verifica se il manga è già nei preferiti dell'utente
        cursor.execute("SELECT 1 FROM user_manga WHERE user_id = ? AND manga_id = ?", (user_id, manga_id))
        row = cursor.fetchone()

        if row:
            # Rimuovi il manga dai preferiti dell'utente
            cursor.execute("DELETE FROM user_manga WHERE user_id = ? AND manga_id = ?", (user_id, manga_id))
            conn.commit()

            conn.close()
            return jsonify({'success': True, 'message': 'Manga rimosso dai preferiti'})
        else:
            # Aggiungi il manga ai preferiti dell'utente
            cursor.execute("INSERT INTO user_manga (user_id, manga_id) VALUES (?, ?)", (user_id, manga_id))
            conn.commit()

            conn.close()
            return jsonify({'success': True, 'message': 'Manga aggiunto ai preferiti'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/account')
def account():
    if 'logged_in' in session:
        conn = sq.connect('anime.sqlite3')
        cur = conn.cursor()
        cur.execute('SELECT createdate FROM users WHERE username = ?', (session['username'],))
        data_string = cur.fetchone()[0]
        cur.execute('SELECT streak FROM users WHERE username = ?', (session['username'],))
        streak = cur.fetchone()[0]
        cur.execute('SELECT anime_id FROM user_anime WHERE user_id = ?', (session['username'],))
        anime = cur.fetchall()
        cur.execute('SELECT manga_id FROM user_manga WHERE user_id = ?', (session['username'],))
        manga = cur.fetchall()
        cur.execute('SELECT username FROM users ORDER BY streak DESC')
        users = cur.fetchall()
        conn.close()

        # controlla se username di sessione è presente nella lista degli utenti
        if (session['username'],) in users:
            # se presente, controlla in che posizione è. Se primo, top=1, se secondo, top=2, ecc.
            top = users.index((session['username'],)) + 1
        else:
            top = None

        # controlla se la tupla anime ha elementi vuoti
        if anime:
            anime = [anime[i][0] for i in range(len(anime))]
        else:
            anime = []

        # controlla se la tupla manga ha elementi vuoti
        if manga:
            manga = [manga[i][0] for i in range(len(manga))]
        else:
            manga = []

        url = "https://graphql.anilist.co"
        anime_data = []
        manga_data = []

        # fetch di ogni anime/manga dall'api di anilist
        for id in manga:
            query = """
                query ($id: Int) {
                    Media (id: $id) {
                        id
                        title {
                            romaji
                            english
                            native
                        }
                        coverImage {
                            large
                        }
                    }
                }
                """

            variables = {
                "id": id
            }

            response = requests.post(url, json={"query": query, "variables": variables})
            manga_data.append(response.json())

        for id in anime:
            query = """
                query ($id: Int) {
                    Media (id: $id) {
                        id
                        title {
                            romaji
                            english
                            native
                        }
                        coverImage {
                            large
                        }
                    }
                }
                """

            variables = {
                "id": id
            }

            response = requests.post(url, json={"query": query, "variables": variables})

            anime_data.append(response.json())

        data = datetime.strptime(data_string, "%Y-%m-%d %H:%M:%S")

        # Formatta la data nel formato desiderato
        data = data.strftime("%d-%m-%Y")
        return render_template('account.html', username=session.get('username', None), createdate=data, anime=anime_data, manga=manga_data, streak=streak, top=top)
    else:
        return redirect('/login')

@app.route('/quote')
def quote():
    # controlla se nella tabella user_quotes del database è presente la data odierna, se sì non effettua la richiesta all'api e restituisce quei dati, altrimenti genera una nuova richiesta
    conn = sq.connect('anime.sqlite3')
    cur = conn.cursor()

    today = datetime.today().date()

    cur.execute('SELECT * FROM quotes WHERE date = ?', (today,))
    row = cur.fetchone()
    conn.close()

    if row:
        result = row
    else:
        result = None

    if result is not None:
        result_json = {
            'id': result[0],
            'anime': result[2],
            'character': result[3],
            'quote': result[4],
            'date': result[5]
        }
        return render_template('quote.html', username=session.get('username', None), data=result_json)
    else:
        url = "https://animechan.xyz/api/random"
        response = requests.get(url)
        data = response.json()
        result = {
            'anime': data['anime'],
            'character': data['character'],
            'quote': '"' + data['quote'] + '"',
            'date': datetime.today().date()
        }
        conn = sq.connect('anime.sqlite3')
        cur = conn.cursor()
        cur.execute('INSERT INTO quotes (date, anime, character, quote) VALUES (?, ?, ?, ?)', (datetime.now().strftime('%Y-%m-%d'), data['anime'], data['character'], data['quote']))
        conn.commit()
        conn.close()

        conn = sq.connect('anime.sqlite3')
        cur = conn.cursor()
        cur.execute('SELECT quote_id FROM quotes WHERE date = ?', (today,))
        row = cur.fetchone()
        conn.close()
        
        result['id'] = row[0]
        return render_template('quote.html', username=session.get('username', None), data=result) 

@app.route('/toggle_favourite_q', methods=['POST'])
def toggle_favourite_q():
    data = request.json
    quote_id = data.get('quoteId')
    user_id = data.get('userId')

    try:
        conn = sq.connect('anime.sqlite3')
        cursor = conn.cursor()

        cursor.execute("SELECT 1 FROM user_quotes WHERE user_id = ? AND quote_id = ?", (user_id, quote_id))
        row = cursor.fetchone()

        if row:
            cursor.execute("DELETE FROM user_quotes WHERE user_id = ? AND quote_id = ?", (user_id, quote_id))
            conn.commit()
            conn.close()
            return jsonify({'success': True, 'message': 'Quote rimossa dai preferiti'})
        else:
            cursor.execute("INSERT INTO user_quotes (user_id, quote_id) VALUES (?, ?)", (user_id, quote_id))
            conn.commit()

            conn.close()
            return jsonify({'success': True, 'message': 'Quote aggiunta ai preferiti'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/favquotes')
def favquotes():
    conn = sq.connect('anime.sqlite3')
    cur = conn.cursor()
    cur.execute('''
                SELECT * FROM quotes 
                    JOIN user_quotes ON quotes.quote_id = user_quotes.quote_id
                WHERE 
                    user_quotes.user_id = ?
                ''', (session.get('username'),))
    data = cur.fetchall()
    conn.close()

    data = [list(row) for row in data]
    
    formatted_data = [{'id': row[0], 'anime': row[2], 'character': row[3], 'quote': row[4], 'date': row[5]} for row in data]

    return render_template('favquotes.html', data=formatted_data, username=session.get('username', None))

@app.route('/newgame')
def newgame():

    return render_template('newgame.html', username=session.get('username', None))

def generateQuestions(mode):
    # 1: indovina copertina dall'anime
    # 2: indovina l'anime dalla copertina
    # 3: indovina l'anime dal personaggio
    # 4: indovina il personaggio dall'anime
    # tutti hanno 4 opzioni, solo una è corretta. Tutto è preso dall'api di AniList in modo randomico, prediligendo i più popolari
    query = ""
    if mode == 1 or mode == 2:
        query = """
        query ($page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            media(sort: SCORE_DESC, type: ANIME) {
                id
                title {
                    romaji
                    english
                    native
                }
                coverImage {
                    large
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
                                image {
                                    large
                                    medium
                                }
                            }
                        }
                    }
                }
            }
        }
        """
    else:
        query = """
        query ($page: Int, $perPage: Int) {
        Page(page: $page, perPage: $perPage) {
            media(sort: SCORE_DESC, type: ANIME) {
                id
                title {
                    romaji
                    english
                    native
                }
                coverImage {
                    large
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
                                image {
                                    large
                                    medium
                                }
                            }
                        }
                    }
                }
            }
        }
        """
    # Parametri della query
    variables = {
        "page": 1,
        "perPage": 150
    }

    url = 'https://graphql.anilist.co'
    # Effettua la richiesta POST all'API di AniList
    response = requests.post(url, json={'query': query, 'variables': variables})
    data = response.json()

    random_anime = random.sample(data['data']['Page']['media'], 4)
    solution = random_anime[0]
    random.shuffle(random_anime)
    return solution, random_anime

@app.route('/game/<int:mode>')
def game(mode):
    answer = request.args.get('answer')
    solution = request.args.get('solution')
    counter = request.args.get('counter', 0, type=int)

    if answer is None or solution is None:
        counter = 0

    # Se si è risposto correttamente, aumenta il contatore
    if is_correct_answer(answer, solution):
        counter += 1
    else:
        # Se si è risposto erroneamente, resetta il contatore
        counter = 0

    selected_mode = mode
    solution, data = generateQuestions(selected_mode)

    # 1: indovina copertina dall'anime
    # 2: indovina l'anime dalla copertina
    # 3: indovina l'anime dal personaggio
    # 4: indovina il personaggio dall'anime
    # tutti hanno 4 opzioni, solo una è corretta. Tutto è preso dall'api di AniList in modo randomico, prediligendo i più popolari
    if mode == 1:
        # soluzione contiene il titolo dell'anime e l'id
        solution = solution['title']['romaji'], solution['id']
        options = {
            'option': [(anime['coverImage']['large']) for anime in data],
            'id': [(anime['id']) for anime in data]
        }
    elif mode == 2:
        # soluzione contiene copertina dell'anime e l'id
        solution = solution['coverImage']['large'], solution['id']
        # data = [(anime['coverImage']['large'], anime['title']['romaji'], anime['id']) for anime in data]
        options = {
            'option': [(anime['title']['romaji']) for anime in data],
            'id': [(anime['id']) for anime in data]
        }
    elif mode == 3:
        # soluzione contiene un personaggio casuale e l'id
        solution = solution['characters']['edges'][0]['node']['name']['full'], solution['id']
        options = {
            'option': [(anime['title']['romaji']) for anime in data],
            'id': [(anime['id']) for anime in data]
        }
    elif mode == 4:
        # soluzione contiene il titolo dell'anime e l'id
        solution = solution['title']['romaji'], solution['id']
        # options contiene un personaggio causale e l'id
        options = {
            'option': [(anime['characters']['edges'][0]['node']['name']['full']) for anime in data],
            'id': [(anime['id']) for anime in data]
        }

    # connetti il database e prendi dalla colonna record il record dell'utente
    conn = sq.connect('anime.sqlite3')
    cur = conn.cursor()
    cur.execute('SELECT streak FROM users WHERE username = ?', (session.get('username'),))
    record = cur.fetchone()[0]
    conn.close()
    if counter > record:
        # connetti il database e aggiorna il record dell'utente
        conn = sq.connect('anime.sqlite3')
        cur = conn.cursor()
        cur.execute('UPDATE users SET streak = ? WHERE username = ?', (counter, session.get('username')))
        conn.commit()
        conn.close()
        record = counter

    return render_template('game.html', username=session.get('username', None), mode=selected_mode, data=options, solution=solution, counter=counter, record=record)

def is_correct_answer(answer, solution):
    # Confronta la risposta data con la soluzione
    print(answer, solution)
    return answer == solution

@app.route('/stats')
def stats():
    conn = sq.connect('anime.sqlite3')
    cur = conn.cursor()
    cur.execute('SELECT * FROM users ORDER BY streak DESC')
    data = cur.fetchall()
    data = [{'username': row[1], 'streak': row[4]} for row in data]
    conn.close()

    return render_template('stats.html', username=session.get('username', None), top=data)

@app.route('/get_stats')
def get_stats():
    conn = sq.connect('anime.sqlite3')
    cur = conn.cursor()
    # SELECT che torna il numero di utenti per ogni giorno in ordine crescente, ignorando le ore
    cur.execute('SELECT DATE(createdate) as createdate, COUNT(*) FROM users GROUP BY DATE(createdate)')
    data2 = cur.fetchall()
    data2 = [{'createdate': row[0], 'count': row[1]} for row in data2]
    conn.close()
    # per ogni elemento count in data2, somma count a quello precedente. Se è il primo elemento non aggiungere nulla
    for i in range(1, len(data2)):
        data2[i]['count'] += data2[i-1]['count']

    return jsonify(data2)

if __name__ == '__main__':
    app.run(debug=True)
