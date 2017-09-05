import json
import os
from uuid import uuid4
from flask import Flask, session, redirect, url_for, escape, request
from game import KeyCode, Game


app = Flask(__name__)

# 게임 데이터 로드
with open('game_data.json', 'r', encoding='utf-8') as f:
    game_data = json.load(f)

game_session = dict()


@app.route('/')
def index():
    if 'uuid' not in session:
        game = Game(game_data)
        game.g_loop = game.turn()
        game.g_loop.send(None)

        uuid = uuid4()
        game_session[uuid] = game
        session['uuid'] = uuid

    return app.send_static_file('index.html')


key_map = {'38': KeyCode.up, '40': KeyCode.down, '39': KeyCode.right, '37': KeyCode.left}


@app.route('/command', methods=['POST'])
def command():
    raw_dir = request.form.get('direction')
    key = key_map.get(raw_dir, KeyCode.invalid)
    if key is not KeyCode.invalid:
        if 'uuid' not in session:
            return ''

        uuid = session['uuid']
        game = game_session[uuid]
        text = game.g_loop.send(key)
        return text

app.secret_key = os.urandom(24)
app.run(host='0.0.0.0', port=80)
