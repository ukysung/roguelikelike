import os
from flask import Flask, session, redirect, url_for, escape, request
from game import KeyCode, Game

app = Flask(__name__)


@app.route('/')
def index():
    return app.send_static_file('index.html')


key_map = {'38': KeyCode.up, '40': KeyCode.down, '39': KeyCode.right, '37': KeyCode.left}
game = Game()
g_loop = game.turn()
g_loop.send(None)


@app.route('/command', methods=['POST'])
def command():
    raw_dir = request.form.get('direction')
    key = key_map.get(raw_dir, KeyCode.invalid)
    if key is not KeyCode.invalid:
        text = g_loop.send(key)
        return text

# set the secret key.  keep this really secret:
app.secret_key = os.urandom(24)
app.run()
