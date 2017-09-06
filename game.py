import math
import pickle
import enum
import base64
from random import Random

screen_width = 80
screen_height = 50


class Tile:
    def __init__(self, blocked=None):
        self.blocked = blocked
        self.light = 0


class Rect:
    def __init__(self, x, y, w, h):
        self.x1 = x
        self.y1 = y
        self.x2 = x + w
        self.y2 = y + h


class GameObject:
    def __init__(self, game, x, y, char, color, dungeon):
        self.game = game
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
        self.game.draw_char(self.x, self.y, self.char, self.color)

    def clear(self):
        self.game.draw_char(self.x, self.y, ' ', self.color)


class Player(GameObject):
    def __init__(self, game, x, y, icon_char, player_data, dungeon):
        self.max_hp = player_data['max_hp']
        self.hp = self.max_hp
        self.defence = player_data['defence']
        self.power = player_data['power']
        self.sight = player_data['sight']
        self.name = player_data['name']
        self.end = False
        self.turn_count = 0
        super().__init__(game, x, y, icon_char, tuple(player_data['color']), dungeon)
        self.refresh_status_bar()

    def attack(self, target):
        damage = max(self.power - target.defence, 0)
        self.game.text_area('{} attacks {} for {} hit points.'.format(self.name, target.name, damage))
        target.take_damage(damage)

    def take_damage(self, damage):
        self.hp = max(self.hp - damage, 0)

        self.refresh_status_bar()

        if 0 >= self.hp:
            self.end = True
            self.color = (85, 85, 85)
            self.game.text_area('{} died!'.format(self.name))
            self.game.text_area('press any key to continue...', fg_color=(85, 85, 255))

    def use_item(self, item):
        self.hp = min(self.max_hp, self.hp + item.heal_amount)
        self.power += item.power_amount
        self.defence += item.defence_amount
        self.sight += item.sight_amount
        self.game.text_area('{} is starting to feel better!({})'.format(self.name, item.name))

    def clear_dungeon(self):
        self.end = True
        self.game.text_area('Game clear(Exit from the dungeon)')
        self.game.text_area('press any key to continue...', fg_color=(85, 85, 255))

    def move(self, dx, dy):
        if self.is_end():
            return False

        x = self.x + dx
        y = self.y + dy

        self.turn_count += 1

        for game_object in self.dungeon.get_objects():
            if game_object.x == x and game_object.y == y:
                if type(game_object) is Monster:
                    self.attack(game_object)
                    break
                elif type(game_object) is Item:
                    game_object.pick_up(self)
                    break
                elif type(game_object) is Goal:
                    game_object.touch(self)
                    break
        else:
            super().move(dx, dy)

        self.refresh_status_bar()

    def refresh_status_bar(self):
        self.game.status_bar(
            '{} - hp[{}] power[{}] defence[{}] sight[{}] turn[{}]'.format(
                self.name,
                self.hp,
                self.power,
                self.defence,
                self.sight,
                self.turn_count
            )
        )

    def is_end(self):
        return self.end


class Monster(GameObject):
    def __init__(self, game, x, y, icon_char, monster_data, dungeon):
        self.max_hp = monster_data['max_hp']
        self.hp = self.max_hp
        self.defence = monster_data['defence']
        self.power = monster_data['power']
        self.name = monster_data['name']
        super().__init__(game, x, y, icon_char, tuple(monster_data['color']), dungeon)

    def attack(self, target: Player):
        if target.is_end():
            return

        damage = max(self.power - target.defence, 0)
        self.game.text_area('{} attacks {} for {} hit points.'.format(self.name, target.name, damage))
        target.take_damage(damage)

    def take_damage(self, damage):
        self.hp -= damage

        if 0 >= self.hp:
            self.dungeon.remove_object(self)
            self.game.text_area('{} is dead!'.format(self.name))

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
    def __init__(self, game, x, y, icon_char, item_data, dungeon):
        self.heal_amount = item_data.get('hp', 0)
        self.defence_amount = item_data.get('defence', 0)
        self.power_amount = item_data.get('power', 0)
        self.sight_amount = item_data.get('sight', 0)
        self.name = item_data['name']
        super().__init__(game, x, y, icon_char, tuple(item_data['color']), dungeon)

    def pick_up(self, game_object: Player):
        game_object.use_item(self)
        self.dungeon.remove_object(self)


class Goal(GameObject):
    def __init__(self, game, x, y, dungeon):
        super().__init__(game, x, y, 'G', (255, 255, 255), dungeon)

    def touch(self, target):
        self.game.save()
        target.clear_dungeon()
        self.dungeon.remove_object(self)


class KeyCode(enum.Enum):
    invalid = -1

    up = 0
    right = 1
    down = 2
    left = 3
    esc = 4


class Dungeon:
    def __init__(self, game, game_data, object_list):
        self.object_list = object_list
        self.map_width = game_data['dungeon']['width']
        self.map_height = game_data['dungeon']['height']
        self.max_features = game_data['dungeon']['features']
        self.dungeon_map = [[Tile() for _ in range(self.map_width)] for _ in range(self.map_height)]
        self.flag = 0
        self.game = game

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
        if self.map_width > x and self.map_height > y:
            return self.dungeon_map[y][x].blocked in (True, None)
        return True

    def can_make_tile(self, x, y):
        return self.dungeon_map[y][x].blocked is None

    def set_block(self, x, y, is_block):
        self.dungeon_map[y][x].blocked = is_block

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
                if self.is_light(x, y):
                    if self.is_block(x, y):
                        self.game.draw_char(x, y, '#', (85, 85, 85))
                    elif self.is_block(x, y) is None:
                        self.game.draw_char(x, y, '#', (85, 85, 85))
                    else:
                        self.game.draw_char(x, y, '.', (170, 170, 170))
                else:
                    self.game.draw_char(x, y, ' ', (0, 0, 0))

    # Multipliers for transforming coordinates to other octants:
    mult = [
        [1, 0, 0, -1, -1, 0, 0, 1],
        [0, 1, -1, 0, 0, -1, 1, 0],
        [0, 1, 1, 0, 0, -1, -1, 0],
        [1, 0, 0, 1, -1, 0, 0, -1]
    ]

    def is_light(self, x, y):
        return self.dungeon_map[y][x].light == self.flag

    def set_light(self, x, y):
        if self.map_width > x and self.map_height > y:
            self.dungeon_map[y][x].light = self.flag

    def _cast_light(self, cx, cy, row, start, end, radius, xx, xy, yx, yy, id):
        if start < end:
            return

        radius_squared = radius * radius
        for j in range(row, radius + 1):
            dx, dy = -j - 1, -j
            blocked = False

            while dx <= 0:
                dx += 1

                X, Y = cx + dx * xx + dy * xy, cy + dx * yx + dy * yy

                l_slope, r_slope = (dx - 0.5) / (dy + 0.5), (dx + 0.5) / (dy - 0.5)
                if start < r_slope:
                    continue
                elif end > l_slope:
                    break
                else:
                    if dx * dx + dy * dy < radius_squared:
                        self.set_light(X, Y)

                    if blocked:
                        if self.is_block(X, Y):
                            new_start = r_slope
                            continue
                        else:
                            blocked = False
                            start = new_start
                    else:
                        if self.is_block(X, Y) and j < radius:
                            blocked = True
                            self._cast_light(cx, cy, j + 1, start, l_slope,
                                             radius, xx, xy, yx, yy, id + 1)
                            new_start = r_slope

            if blocked:
                break

    def do_fov(self, x, y, radius):
        self.flag += 1
        for oct in range(8):
            self._cast_light(x, y, 1, 1.0, 0.0, radius,
                             self.mult[0][oct], self.mult[1][oct],
                             self.mult[2][oct], self.mult[3][oct], 0)

    def make_tunnel(self, center_x, center_y, length, direction, random):
        length = random.randint(2, length)

        if direction == KeyCode.up:
            if center_x < 0 or center_x > self.map_width - 1:
                return False

            for y in range(center_y, center_y - length, -1):
                if y < 0 or y > self.map_height - 1:
                    return False

                if not self.can_make_tile(center_x, y):
                    return False

            for y in range(center_y, center_y - length, -1):
                self.set_block(center_x, y, False)

        elif direction == KeyCode.right:
            if center_y < 0 or center_y > self.map_height - 1:
                return False

            for y in range(center_x, center_x + length):
                if 0 > y or y > self.map_height - 1:
                    return False

                if not self.can_make_tile(y, center_y):
                    return False

            for y in range(center_x, center_x + length):
                self.set_block(y, center_y, False)

        elif direction == KeyCode.down:
            if center_x < 0 or center_x > self.map_width - 1:
                return False

            for y in range(center_y, center_y + length):
                if y < 0 or y > self.map_height - 1:
                    return False

                if not self.can_make_tile(center_x, y):
                    return False

            for y in range(center_y, center_y + length):
                self.set_block(center_x, y, False)

        elif direction == KeyCode.left:
            if center_y < 0 or center_y > self.map_height - 1:
                return False

            for y in range(center_x, center_x - length, -1):
                if y < 0 or y > self.map_height - 1:
                    return False

                if not self.can_make_tile(y, center_y):
                    return False

            for y in range(center_x, center_x - length, -1):
                self.set_block(y, center_y, False)

        return True

    def make_room(self, center_x, center_y, width, height, direction, random):
        room_width = random.randint(4, width)
        room_height = random.randint(4, height)

        if direction == KeyCode.invalid:
            return False

        if direction == KeyCode.up:
            for y in range(center_y, center_y - room_height, -1):
                if y < 0 or y > self.map_height - 1:
                    return False

                for x in range(center_x - room_width // 2, (center_x + (room_width + 1) // 2)):
                    if x < 0 or x > self.map_width - 1:
                        return False

                    if not self.can_make_tile(x, y):
                        return False

            for y in range(center_y, center_y - room_height, -1):
                for x in range(center_x - room_width // 2, (center_x + (room_width + 1) // 2)):
                    if x == center_x - room_width // 2:
                        self.set_block(x, y, True)
                    elif x == center_x + (room_width - 1) // 2:
                        self.set_block(x, y, True)
                    elif y == center_y:
                        self.set_block(x, y, True)
                    elif y == center_y - room_height + 1:
                        self.set_block(x, y, True)
                    else:
                        self.set_block(x, y, False)

        elif direction == KeyCode.right:
            for y in range(center_y - room_height // 2, center_y + (room_height + 1) // 2):
                if y < 0 or y > self.map_height - 1:
                    return False

                for x in range(center_x, center_x + room_width):
                    if x < 0 or x > self.map_width - 1:
                        return False

                    if not self.can_make_tile(x, y):
                        return False

            for y in range(center_y - room_height // 2, center_y + (room_height + 1) // 2):
                for x in range(center_x, center_x + room_width):
                    if x == center_x:
                        self.set_block(x, y, True)
                    elif x == center_x + (room_width - 1):
                        self.set_block(x, y, True)
                    elif y == center_y - room_height // 2:
                        self.set_block(x, y, True)
                    elif y == center_y + (room_height - 1) // 2:
                        self.set_block(x, y, True)
                    else:
                        self.set_block(x, y, False)

        elif direction == KeyCode.down:
            for y in range(center_y, center_y + room_height):
                if y < 0 or y > self.map_height - 1:
                    return False

                for x in range(center_x - room_width // 2, center_x + (room_width + 1) // 2):
                    if x < 0 or x > self.map_width - 1:
                        return False

                    if not self.can_make_tile(x, y):
                        return False

            for y in range(center_y, center_y + room_height):
                for x in range(center_x - room_width // 2, center_x + (room_width + 1) // 2):
                    if x == center_x - room_width // 2:
                        self.set_block(x, y, True)
                    elif x == center_x + (room_width - 1) // 2:
                        self.set_block(x, y, True)
                    elif y == center_y:
                        self.set_block(x, y, True)
                    elif y == center_y + (room_height - 1):
                        self.set_block(x, y, True)
                    else:
                        self.set_block(x, y, False)

        elif direction == KeyCode.left:
            for y in range(center_y - room_height // 2, center_y + (room_height + 1) // 2):
                if y < 0 or y > self.map_height - 1:
                    return False

                for x in range(center_x, center_x - room_width, -1):
                    if x < 0 or x > self.map_width - 1:
                        return False

                    if not self.can_make_tile(x, y):
                        return False

            for y in range(center_y - room_height // 2, center_y + (room_height + 1) // 2):
                for x in range(center_x, center_x - room_width - 1, -1):
                    if x == center_x:
                        self.set_block(x, y, True)
                    elif x == center_x - room_width:
                        self.set_block(x, y, True)
                    elif y == center_y - room_height // 2:
                        self.set_block(x, y, True)
                    elif y == center_y + (room_height - 1) // 2:
                        self.set_block(x, y, True)
                    else:
                        self.set_block(x, y, False)

        return True

    def generate_map(self, random):
        room_chance = 70
        current_features = 1

        self.make_room(self.map_width // 2, self.map_height // 2, 5, 5, KeyCode(random.randint(0, 3)), random)

        for _ in range(1000):
            if current_features >= self.max_features:
                break

            new_x = 0
            x_mod = 0
            new_y = 0
            y_mod = 0

            for _ in range(1000):
                new_x = random.randint(1, self.map_width - 2)
                new_y = random.randint(1, self.map_height - 2)
                direction = KeyCode.invalid

                if self.is_block(new_x, new_y):
                    if self.is_block(new_x, new_y + 1) is False:
                        x_mod = 0
                        y_mod = -1
                        direction = KeyCode.up
                    elif self.is_block(new_x - 1, new_y) is False:
                        x_mod = 1
                        y_mod = 0
                        direction = KeyCode.right
                    elif self.is_block(new_x, new_y - 1) is False:
                        x_mod = 0
                        y_mod = 1
                        direction = KeyCode.down
                    elif self.is_block(new_x + 1, new_y) is False:
                        x_mod = -1
                        y_mod = 0
                        direction = KeyCode.left

                    if direction is not KeyCode.invalid:
                        break

            if direction is not KeyCode.invalid:
                feature = random.randint(0, 100)

                if feature <= room_chance:
                    if self.make_room(new_x + x_mod, new_y + y_mod, 20, 20, direction, random):
                        self.set_block(new_x, new_y, False)
                        self.set_block(new_x + x_mod, new_y + y_mod, False)
                elif feature > room_chance:
                    if self.make_tunnel(new_x + x_mod, new_y + y_mod, 10, direction, random):
                        self.set_block(new_x, new_y, False)

                current_features += 1


class TextArea:
    def __init__(self, game, x, y, num_line=4):
        self.game = game
        self.text_list = list()
        self.num_line = num_line
        self.x = x
        self.y = y

    def __call__(self, text, *, fg_color=(255, 255, 255)):
        self.append_text(text, fg_color)

    def append_text(self, text, fg_color):
        self.text_list.append((text, fg_color))

        if len(self.text_list) > self.num_line:
            self.text_list.pop(0)

    def draw(self):
        for dy in range(self.num_line + 1):
            for x in range(screen_width):
                self.game.draw_char(x, self.y + dy, ' ', (0, 0, 0))

        for dy, (text, fg_color) in enumerate(self.text_list):
            for dx, letter in enumerate(text):
                self.game.draw_char(self.x + dx, self.y + dy, letter, fg_color)

    def clear(self):
        self.text_list = list()


class Game:
    def __init__(self, game_data, save_handler=None, random_seed=None):
        self.game_data = game_data

        self._buffer = [[(' ', (0, 0, 0)) for _ in range(screen_width)] for _ in range(screen_height)]

        # UI 생성
        self.text_area = TextArea(self, 0, 42)
        self.status_bar = TextArea(self, 0, 40, 1)
        self.save_handler = save_handler
        self.random_seed = random_seed
        self._player, self._object_list, self._dungeon = self.initialize(self.game_data)

    def draw_char(self, x, y, char, color):
        self._buffer[y][x] = (char, color)

    def turn(self):
        # game loop
        while True:
            self._dungeon.do_fov(self._player.x, self._player.y, self._player.sight)
            key_event = yield self.render()

            if self._player.is_end():
                self._player, self._object_list, self._dungeon = self.initialize(self.game_data)
                self.text_area.clear()

            exit_game = self.handle_keys(self._player, key_event)
            if exit_game:
                break

            for monster in self._dungeon.get_monsters():
                monster.take_turn()

    def render(self,):
        self._dungeon.draw()

        for obj in self._object_list:
            if type(obj) is Player or self._dungeon.is_light(obj.x, obj.y):
                obj.draw()

        self.status_bar.draw()
        self.text_area.draw()

        raw_text = str()
        for line in self._buffer:
            for letter, color in line:
                if color != (0, 0, 0):
                    color_str = ''.join(format(e, '02X') for e in color)
                    raw_text += '[[;#{};]{}]'.format(color_str, letter)
                else:
                    raw_text += letter
            raw_text += '\n'

        for obj in self._object_list:
            obj.clear()

        return raw_text

    def handle_keys(self, player, key_event):
        if key_event is KeyCode.esc:
            return True

        if key_event is KeyCode.up:
            player.move(0, -1)

        if key_event is KeyCode.down:
            player.move(0, 1)

        if key_event is KeyCode.left:
            player.move(-1, 0)

        if key_event is KeyCode.right:
            player.move(1, 0)

    def initialize(self, game_data):
        random = Random(self.random_seed)

        # 던전 생성 및 맵 자동 생성
        _object_list = list()
        _dungeon = Dungeon(self, game_data, _object_list)
        _dungeon.generate_map(random)

        # 몬스터, 아이템 생성 및 배치
        for k, v in game_data['entries'].items():
            if k in game_data['monsters']:
                monster_data = game_data['monsters'][k]

                num_monsters = v
                while num_monsters > 0:
                    x = random.randint(0, _dungeon.map_width - 1)
                    y = random.randint(0, _dungeon.map_height - 1)
                    if not _dungeon.is_block(x, y):
                        monster = Monster(self, x, y, k, monster_data, _dungeon)
                        _object_list.append(monster)
                        num_monsters -= 1

            elif k in game_data['items']:
                item_data = game_data['items'][k]

                num_items = v
                while num_items > 0:
                    x = random.randint(0, _dungeon.map_width - 1)
                    y = random.randint(0, _dungeon.map_height - 1)
                    if not _dungeon.is_block(x, y):
                        monster = Item(self, x, y, k, item_data, _dungeon)
                        _object_list.append(monster)
                        num_items -= 1

        # 플레이어 배치
        while True:
            x = random.randint(0, _dungeon.map_width - 1)
            y = random.randint(0, _dungeon.map_height - 1)
            if not _dungeon.is_block(x, y):
                for k, v in game_data['characters'].items():
                    _player = Player(self, x, y, k, game_data['characters'][k], _dungeon)
                    _object_list.append(_player)
                break

        # 탈출구 배치
        while True:
            x = random.randint(0, _dungeon.map_width - 1)
            y = random.randint(0, _dungeon.map_height - 1)
            if not _dungeon.is_block(x, y):
                _object_list.append(Goal(self, x, y, _dungeon))
                break

        return _player, _object_list, _dungeon

    def save(self):
        if self.save_handler:
            game_data = pickle.dumps(self)
            b64_game_data = base64.b64encode(game_data)
            self.save_handler(self._player.name, self._player.turn_count, b64_game_data)

    @classmethod
    def load(cls, b64_game_data):
        game_data = base64.b64decode(b64_game_data)
        game = pickle.loads(game_data)
        return game
