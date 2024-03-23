#import requests
from flask import Flask, redirect, request, render_template
import sqlite3

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('login.html')

if __name__ == '__main__':
    app.run(debug=True)