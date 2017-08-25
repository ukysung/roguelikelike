import tdl
import math
import random

screen_width = 80
screen_height = 50

map_width = 80
map_height = 40

num_monsters = 10
num_items = 5


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
    def __init__(self, x, y, char, color, dungeon):
        self.max_hp = 100
        self.hp = 100
        self.defence = 0
        self.power = 8
        self.name = 'player'
        super().__init__(x, y, char, color, dungeon)
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
    def __init__(self, *arg, **kwargs):
        self.max_hp = 10
        self.hp = 10
        self.defence = 0
        self.power = 2
        self.name = 'monster'
        super().__init__(*arg, **kwargs)

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
    def __init__(self, x, y, char, color, dungeon):
        self.heal_amount = 20
        super().__init__(x, y, char, color, dungeon)

    def pick_up(self, game_object: Player):
        game_object.heal(self.heal_amount)
        self.dungeon.remove_object(self)


class Dungeon:
    def __init__(self, width, height, object_list):
        self.object_list = object_list
        self.dungeon_map = [[Tile(True) for _ in range(height)] for _ in range(width)]

    def create_room(self, room):
        for x in range(room.x1 + 1, room.x2):
            for y in range(room.y1 + 1, room.y2):
                self.dungeon_map[x][y].blocked = False

    def create_h_tunnel(self, x1, x2, y):
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self.dungeon_map[x][y].blocked = False

    def create_v_tunnel(self, y1, y2, x):
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self.dungeon_map[x][y].blocked = False

    def is_block(self, x, y):
        return self.dungeon_map[x][y].blocked

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
        for y in range(map_height):
            for x in range(map_width):
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
tdl.set_font('terminal16x16.png', columnFirst=True, greyscale=True)
_root = tdl.init(screen_width, screen_height, title="로그라이크", fullscreen=False)
_con = tdl.Console(screen_width, screen_height)

_text_area = TextArea(0, 42)
_hp_bar = TextArea(0, 40, 1)

_object_list = list()
_dungeon = Dungeon(map_width, map_height, _object_list)
_dungeon.create_room(Rect(10, 10, 20, 20))
_dungeon.create_room(Rect(50, 10, 20, 20))
_dungeon.create_h_tunnel(25, 55, 15)
_dungeon.create_h_tunnel(25, 55, 25)

_player = Player(screen_width // 2, screen_height // 2, '@', (85, 85, 255), _dungeon)
_player.x = 25
_player.y = 23
_object_list.append(_player)

while num_monsters > 0:
    x = random.randint(0, map_width - 1)
    y = random.randint(0, map_height - 1)
    if not _dungeon.is_block(x, y):
        monster = Monster(x, y, 'B', (255, 85, 85), _dungeon)
        _object_list.append(monster)
        num_monsters -= 1

while num_items > 0:
    x = random.randint(0, map_width - 1)
    y = random.randint(0, map_height - 1)
    if not _dungeon.is_block(x, y):
        item = Item(x, y, 'i', (85, 255, 85), _dungeon)
        _object_list.append(item)
        num_items -= 1

# game loop
while not tdl.event.is_window_closed():

    render(_dungeon, _object_list, _text_area, _hp_bar)

    exit_game = handle_keys(_player)
    if exit_game:
        break

    for monster in _dungeon.get_monsters():
        monster.take_turn()
