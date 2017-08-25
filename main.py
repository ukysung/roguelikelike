import tdl
import math
import random
import json

screen_width = 80
screen_height = 50


class Tile:
    def __init__(self, blocked):
        self.blocked = blocked


class Rect:
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h


class GameObject:
    def __init__(self, x, y, char, color, dungeon):
        self.x = x
        self.y = y
        self.char = char
        self.color = color
        self.dungeon = dungeon

    def move(self, dx, dy):
        if self.dungeon.can_move(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy

    def draw(self):
        _con.draw_char(self.x, self.y, self.char, self.color, bg=None)

    def clear(self):
        _con.draw_char(self.x, self.y, ' ', self.color, bg=None)


class Player(GameObject):
    def __init__(self, x, y, icon_char, player_data, dungeon):
        self.max_hp = player_data['max_hp']
        self.hp = self.max_hp
        self.defence = player_data['defence']
        self.power = player_data['power']
        self.name = player_data['name']
        super().__init__(x, y, icon_char, tuple(player_data['color']), dungeon)
        self.refresh_hp_bar()

    def attack(self, target):
        damage = max(self.power - target.defence, 0)
        _text_area('{} attacks {} for {} hit points.'.format(self.name, target.name, damage))
        target.take_damage(damage)

    def take_damage(self, damage):
        self.hp -= damage

        self.refresh_hp_bar()

        if 0 >= self.hp:
            _text_area('{} died!'.format(self.name))

    def heal(self, amout):
        self.hp = min(self.max_hp, self.hp + amout)
        _text_area('{} is starting to feel better!'.format(self.name))
        self.refresh_hp_bar()

    def move(self, dx, dy):
        x = self.x + dx
        y = self.y + dy

        for game_object in self.dungeon.get_objects():
            if game_object.x == x and game_object.y == y:
                if type(game_object) is Monster:
                    self.attack(game_object)
                    break
                elif type(game_object) is Item:
                    game_object.pick_up(self)
                    break
        else:
            super().move(dx, dy)

    def refresh_hp_bar(self):
        _hp_bar('{} - hp[{}]'.format(self.name, self.hp))


class Monster(GameObject):
    def __init__(self, x, y, icon_char, monster_data, dungeon):
        self.max_hp = monster_data['max_hp']
        self.hp = self.max_hp
        self.defence = monster_data['defence']
        self.power = monster_data['power']
        self.name = monster_data['name']
        super().__init__(x, y, icon_char, tuple(monster_data['color']), dungeon)

    def attack(self, target: Player):
        damage = max(self.power - target.defence, 0)
        target.take_damage(damage)

    def take_damage(self, damage):
        self.hp -= damage

        if 0 >= self.hp:
            self.dungeon.remove_object(self)
            _text_area('{} is dead!'.format(self.name))

    def _distance_to(self, game_object):
        dx = game_object.x - self.x
        dy = game_object.y - self.y
        return math.sqrt(dx ** 2 + dy ** 2)

    def _move_towards(self, game_object):
        dx = game_object.x - self.x
        dy = game_object.y - self.y
        distance = self._distance_to(game_object)

        dx = int(round(dx / distance))
        dy = int(round(dy / distance))
        self.move(dx, dy)

    def take_turn(self):
        player = self.dungeon.get_player()
        if self._distance_to(player) >= 2:
            self._move_towards(player)
        else:
            self.attack(player)


class Item(GameObject):
    def __init__(self, x, y, icon_char, item_data, dungeon):
        self.heal_amount = item_data['hp']
        self.name = item_data['name']
        super().__init__(x, y, icon_char, tuple(item_data['color']), dungeon)

    def pick_up(self, game_object: Player):
        game_object.heal(self.heal_amount)
        self.dungeon.remove_object(self)


class Dungeon:
    def __init__(self, game_data, object_list):
        self.object_list = object_list
        map_data = list()
        height = 0
        for line in game_data['map']:
            height += 1
            row_data = list()
            width = 0
            for char in line:
                width += 1
                if char == '#':
                    row_data.append(Tile(True))
                elif char == '.':
                    row_data.append(Tile(False))
            self.map_width = width
            map_data.append(row_data)
        self.map_height = height
        self.dungeon_map = map_data

    def create_room(self, room):
        for x in range(room.x1 + 1, room.x2):
            for y in range(room.y1 + 1, room.y2):
                self.dungeon_map[y][x].blocked = False

    def create_h_tunnel(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.dungeon_map[y][x].blocked = False

    def create_v_tunnel(self, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.dungeon_map[y][x].blocked = False

    def is_block(self, x, y):
        return self.dungeon_map[y][x].blocked

    def can_move(self, x, y):
        return not self.is_block(x, y) and not any([i.x == x and i.y == y for i in self.object_list])

    def get_monsters(self):
        return [i for i in self.object_list if isinstance(i, Monster)]

    def get_items(self):
        return [i for i in self.object_list if isinstance(i, Item)]

    def get_objects(self):
        return self.object_list

    def get_player(self):
        return [i for i in self.object_list if isinstance(i, Player)].pop()

    def remove_object(self, game_object):
        self.object_list.remove(game_object)

    def draw(self):
        for y, row in enumerate(self.dungeon_map):
            for x in range(len(row)):
                if self.is_block(x, y):
                    _con.draw_char(x, y, '#', fg=(85, 85, 85), bg=None)
                else:
                    _con.draw_char(x, y, '.', fg=(170, 170, 170), bg=None)


class TextArea:
    def __init__(self, x, y, num_line=4):
        self.text_list = list()
        self.num_line = num_line
        self.x = x
        self.y = y

    def __call__(self, text):
        self.append_text(text)

    def append_text(self, text):
        self.text_list.append(text)

        if len(self.text_list) > self.num_line:
            self.text_list.pop(0)

    def draw(self):
        for i in range(self.num_line + 1):
            _con.draw_str(self.x, self.y + i, ' ' * 80)

        for i, text in enumerate(self.text_list):
            _con.draw_str(self.x, self.y + i, text)


def render(dungeon, object_list, text_area, hp_bar):
    dungeon.draw()

    for obj in object_list:
        obj.draw()

    hp_bar.draw()
    text_area.draw()

    _root.blit(_con, 0, 0, screen_width, screen_height, 0, 0)

    tdl.flush()

    for obj in object_list:
        obj.clear()


def handle_keys(game_object):
    user_input = tdl.event.key_wait()

    if user_input.key == 'ESCAPE':
        return True

    if user_input.key == 'ENTER' and user_input.alt:
        tdl.set_fullscreen(not tdl.get_fullscreen())

    if user_input.key == 'UP':
        game_object.move(0, -1)

    if user_input.key == 'DOWN':
        game_object.move(0, 1)

    if user_input.key == 'LEFT':
        game_object.move(-1, 0)

    if user_input.key == 'RIGHT':
        game_object.move(1, 0)


# initialize
with open('game_data.json', 'r') as f:
    game_data = json.load(f)

tdl.set_font('terminal16x16.png', columnFirst=True, greyscale=True)
_root = tdl.init(screen_width, screen_height, title="로그라이크", fullscreen=False)
_con = tdl.Console(screen_width, screen_height)

_text_area = TextArea(0, 42)
_hp_bar = TextArea(0, 40, 1)

_object_list = list()
_dungeon = Dungeon(game_data, _object_list)

for k, v in game_data['entries'].items():
    if k in game_data['monsters']:
        monster_data = game_data['monsters'][k]

        num_monsters = v
        while num_monsters > 0:
            x = random.randint(0, _dungeon.map_width - 1)
            y = random.randint(0, _dungeon.map_height - 1)
            if not _dungeon.is_block(x, y):
                monster = Monster(x, y, k, monster_data, _dungeon)
                _object_list.append(monster)
                num_monsters -= 1

    elif k in game_data['items']:
        item_data = game_data['items'][k]

        num_items = v
        while num_items > 0:
            x = random.randint(0, _dungeon.map_width - 1)
            y = random.randint(0, _dungeon.map_height - 1)
            if not _dungeon.is_block(x, y):
                monster = Item(x, y, k, item_data, _dungeon)
                _object_list.append(monster)
                num_items -= 1

while True:
    x = random.randint(0, _dungeon.map_width - 1)
    y = random.randint(0, _dungeon.map_height - 1)
    if not _dungeon.is_block(x, y):
        for k, v in game_data['characters'].items():
            _player = Player(x, y, k, game_data['characters'][k], _dungeon)
            _object_list.append(_player)
        break

# game loop
while not tdl.event.is_window_closed():

    render(_dungeon, _object_list, _text_area, _hp_bar)

    exit_game = handle_keys(_player)
    if exit_game:
        break

    for monster in _dungeon.get_monsters():
        monster.take_turn()
