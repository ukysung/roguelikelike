import json
import os
import datetime
import threading
from flask import Flask, session, request, send_from_directory, jsonify
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
    try:
        session['random_seed'] = int(seed)
        if 'user_name' in session:
            user_name = session['user_name']
            game_session.pop(user_name)
            session.pop('user_name')
            session.pop('map_data')
    except ValueError:
        session['random_seed'] = None

    return app.send_static_file('index.html')


key_map = {'38': KeyCode.up, '40': KeyCode.down, '39': KeyCode.right, '37': KeyCode.left}


def save_callback(player_name, player_turn_count, game_data):
    with mysql.get_db().cursor() as cursor:
        sql = 'INSERT INTO `users` (`user_name`, `score`, `map_data`) VALUES (%s, %s, %s)' \
              'ON DUPLICATE KEY UPDATE score = IF(score > %s, %s, score), map_data = IF(score > %s, %s, map_data), last_login = now()'
        cursor.execute(
            sql, (
                player_name, player_turn_count, game_data, player_turn_count, player_turn_count, player_turn_count, game_data
            )
        )

    mysql.get_db().commit()


class ThreadSafeIter:
    def __init__(self, it):
        self.it = it
        self.lock = threading.Lock()

    def __iter__(self):
        return self

    def next(self, *args, **kwargs):
        with self.lock:
            return self.it.next(*args, **kwargs)

    def send(self, *args, **kwargs):
        with self.lock:
            return self.it.send(*args, **kwargs)


def init_user(user_name):
    random_seed = session.get('random_seed', None)
    game = Game(server_data, user_name, save_callback, random_seed)
    game_context = ThreadSafeIter(game.turn())
    map_data = game_context.send(None)
    game_session[user_name] = game_context
    session['user_name'] = user_name
    session['map_data'] = map_data
    return map_data


@app.route('/login', methods=['POST'])
def login():
    user_name = request.form.get('user_name')

    if 'user_name' not in session:
        return init_user(user_name)
    else:
        if session['user_name'] == user_name:
            return session['map_data']
        else:
            session_user_name = session['user_name']
            game_session.pop(session_user_name)
            session.pop('user_name')
            session.pop('map_data')
            return init_user(user_name)


@app.route('/command', methods=['POST'])
def command():
    raw_dir = request.form.get('direction')
    key = key_map.get(raw_dir, KeyCode.invalid)
    if key is not KeyCode.invalid:
        if 'user_name' not in session:
            return ''

        user_name = session['user_name']
        game_context = game_session[user_name]
        map_data = game_context.send(key)
        session['map_data'] = map_data
        return map_data
    else:
        return ''


class MySQLCache:
    def __init__(self, mysql, refresh_tick=5):
        self.refresh_tick = refresh_tick
        self.mysql = mysql
        self.last_access_time = datetime.datetime.min
        self.result = None

    def get(self):
        def dots(string, length):
            return (string[:length] + '..') if len(string) > length else string

        now = datetime.datetime.now()

        if (now - self.last_access_time).seconds > self.refresh_tick:
            with self.mysql.get_db().cursor() as cursor:
                sql = 'SELECT user_name, score FROM users ORDER BY score, last_login DESC LIMIT 10'
                cursor.execute(sql)
                self.result = [[dots(i[0], 8), i[1]] for i in cursor.fetchall()]

            self.last_access_time = now

        return self.result


@app.route('/high_rank', methods=['POST'])
def high_rank():
    rank = db_cache.get()
    return jsonify(rank=rank)

app.config['MYSQL_DATABASE_USER'] = server_data['mysql']['user']
app.config['MYSQL_DATABASE_PASSWORD'] = server_data['mysql']['password']
app.config['MYSQL_DATABASE_DB'] = server_data['mysql']['database']
app.config['MYSQL_DATABASE_HOST'] = server_data['mysql']['host']
app.config['MYSQL_DATABASE_PORT'] = server_data['mysql']['port']
mysql = MySQL(app)
db_cache = MySQLCache(mysql)

app.secret_key = os.urandom(24)
app.run(host='0.0.0.0', port=80, threaded=True)
