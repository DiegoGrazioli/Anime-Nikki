#import requests
from flask import Flask, redirect, request, render_template, url_for
import sqlite3

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':


        # Then get the data from the form
        username = request.form['username']
        password = request.form['password']

        # Get the username/password associated with this tag
        return render_template('home.html')

    else:
        return render_template('login.html')

@app.route('/home')
def home():
    return render_template('home.html')

if __name__ == '__main__':
    app.run(debug=True)