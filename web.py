import json
import os
from uuid import uuid4
from flask import Flask, session, request, send_from_directory
from flask.ext.mysql import MySQL
from game import KeyCode, Game


app = Flask(__name__)

# 게임 데이터 로드
with open('game_data.json', 'r', encoding='utf-8') as f:
    server_data = json.load(f)

game_session = dict()


@app.route('/static/<path>')
def send_static_file(path):
    return send_from_directory('static', path)


@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.png')


@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/seed/<seed>')
def take_random_seed(seed):
    session['random_seed'] = int(seed)
    if 'uuid' in session:
        uuid = session['uuid']
        del game_session[uuid]
        del session['uuid']
        del session['map_data']

    return app.send_static_file('index.html')


key_map = {'38': KeyCode.up, '40': KeyCode.down, '39': KeyCode.right, '37': KeyCode.left}


def save_callback(player_name, player_turn_count, game_data):
    # with mysql.get_db().cursor() as cursor:
    #     sql = 'INSERT INTO `users` (`user_name`, `score`, `map_data`) VALUES (%s, %s, %s)' \
    #           'ON DUPLICATE KEY UPDATE score = IF(score > %s, %s, score), map_data = IF(score > %s, %s, map_data), last_login = now()'
    #     cursor.execute(
    #         sql, (
    #             player_name, player_turn_count, game_data, player_turn_count, player_turn_count, game_data, game_data
    #         )
    #     )
    #
    # mysql.get_db().commit()
    pass


@app.route('/login', methods=['POST'])
def login():
    if 'uuid' not in session:
        random_seed = session.get('random_seed', None)
        game = Game(server_data, save_callback, random_seed)
        game_context = game.turn()
        map_data = game_context.send(None)
        uuid = uuid4()
        game_session[uuid] = game_context
        session['uuid'] = uuid
        session['map_data'] = map_data
        return map_data
    else:
        return session['map_data']


@app.route('/command', methods=['POST'])
def command():
    raw_dir = request.form.get('direction')
    key = key_map.get(raw_dir, KeyCode.invalid)
    if key is not KeyCode.invalid:
        if 'uuid' not in session:
            return ''

        uuid = session['uuid']
        game_context = game_session[uuid]
        map_data = game_context.send(key)
        session['map_data'] = map_data
        return map_data
    else:
        return ''


app.config['MYSQL_DATABASE_USER'] = server_data['mysql']['user']
app.config['MYSQL_DATABASE_PASSWORD'] = server_data['mysql']['password']
app.config['MYSQL_DATABASE_DB'] = server_data['mysql']['database']
app.config['MYSQL_DATABASE_HOST'] = server_data['mysql']['host']
app.config['MYSQL_DATABASE_PORT'] = server_data['mysql']['port']
mysql = MySQL(app)

app.secret_key = os.urandom(24)
app.run(host='0.0.0.0', port=80)
