import tdl
import math
import random
import json
import enum

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
        self.sight = player_data['sight']
        self.name = player_data['name']
        self.end = False
        super().__init__(x, y, icon_char, tuple(player_data['color']), dungeon)
        self.refresh_status_bar()

    def attack(self, target):
        damage = max(self.power - target.defence, 0)
        _text_area('{} attacks {} for {} hit points.'.format(self.name, target.name, damage))
        target.take_damage(damage)

    def take_damage(self, damage):
        self.hp = max(self.hp - damage, 0)

        self.refresh_status_bar()

        if 0 >= self.hp:
            self.end = True
            self.color = (85, 85, 85)
            _text_area('{} died!'.format(self.name))
            _text_area('press any key to continue...', fg_color=(85, 85, 255))

    def use_item(self, item):
        self.hp = min(self.max_hp, self.hp + item.heal_amount)
        self.power += item.power_amount
        self.defence += item.defence_amount
        self.sight += item.sight_amount
        _text_area('{} is starting to feel better!({})'.format(self.name, item.name))
        self.refresh_status_bar()

    def clear_dungeon(self):
        self.end = True
        _text_area('Game clear(Exit from the dungeon)')
        _text_area('press any key to continue...', fg_color=(85, 85, 255))

    def move(self, dx, dy):
        if self.is_end():
            return

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
                elif type(game_object) is Goal:
                    game_object.touch(self)
                    break
        else:
            super().move(dx, dy)

    def refresh_status_bar(self):
        _status_bar(
            '{} - hp[{}] power[{}] defence[{}] sight[{}]'.format(
                self.name,
                self.hp,
                self.power,
                self.defence,
                self.sight
            )
        )

    def is_end(self):
        return self.end


class Monster(GameObject):
    def __init__(self, x, y, icon_char, monster_data, dungeon):
        self.max_hp = monster_data['max_hp']
        self.hp = self.max_hp
        self.defence = monster_data['defence']
        self.power = monster_data['power']
        self.name = monster_data['name']
        super().__init__(x, y, icon_char, tuple(monster_data['color']), dungeon)

    def attack(self, target: Player):
        if target.is_end():
            return

        damage = max(self.power - target.defence, 0)
        _text_area('{} attacks {} for {} hit points.'.format(self.name, target.name, damage))
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
        self.heal_amount = item_data.get('hp', 0)
        self.defence_amount = item_data.get('defence', 0)
        self.power_amount = item_data.get('power', 0)
        self.sight_amount = item_data.get('sight', 0)
        self.name = item_data['name']
        super().__init__(x, y, icon_char, tuple(item_data['color']), dungeon)

    def pick_up(self, game_object: Player):
        game_object.use_item(self)
        self.dungeon.remove_object(self)


class Goal(GameObject):
    def __init__(self, x, y, dungeon):
        super().__init__(x, y, 'G', (255, 255, 255), dungeon)

    def touch(self, target):
        target.clear_dungeon()
        self.dungeon.remove_object(self)


class Direction(enum.Enum):
    invalid = -1

    up = 0
    right = 1
    down = 2
    left = 3


class Dungeon:
    def __init__(self, game_data, object_list):
        self.object_list = object_list
        self.map_width = game_data['dungeon']['width']
        self.map_height = game_data['dungeon']['height']
        self.max_features = game_data['dungeon']['features']
        self.dungeon_map = [[Tile() for _ in range(self.map_width)] for _ in range(self.map_height)]
        self.flag = 0

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
        return self.dungeon_map[y][x].blocked in (True, None)

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
                        _con.draw_char(x, y, '#', fg=(85, 85, 85), bg=None)
                    elif self.is_block(x, y) is None:
                        _con.draw_char(x, y, '#', fg=(85, 85, 85), bg=None)
                    else:
                        _con.draw_char(x, y, '.', fg=(170, 170, 170), bg=None)
                else:
                    _con.draw_char(x, y, ' ', fg=None, bg=None)

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

    def make_tunnel(self, center_x, center_y, length, direction):
        length = random.randint(2, length)

        if direction == Direction.up:
            if center_x < 0 or center_x > self.map_width - 1:
                return False

            for y in range(center_y, center_y - length, -1):
                if y < 0 or y > self.map_height - 1:
                    return False

                if not self.can_make_tile(center_x, y):
                    return False

            for y in range(center_y, center_y - length, -1):
                self.set_block(center_x, y, False)

        elif direction == Direction.right:
            if center_y < 0 or center_y > self.map_height - 1:
                return False

            for y in range(center_x, center_x + length):
                if 0 > y or y > self.map_height - 1:
                    return False

                if not self.can_make_tile(y, center_y):
                    return False

            for y in range(center_x, center_x + length):
                self.set_block(y, center_y, False)

        elif direction == Direction.down:
            if center_x < 0 or center_x > self.map_width - 1:
                return False

            for y in range(center_y, center_y + length):
                if y < 0 or y > self.map_height - 1:
                    return False

                if not self.can_make_tile(center_x, y):
                    return False

            for y in range(center_y, center_y + length):
                self.set_block(center_x, y, False)

        elif direction == Direction.left:
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

    def make_room(self, center_x, center_y, width, height, direction):
        room_width = random.randint(4, width)
        room_height = random.randint(4, height)

        if direction == Direction.invalid:
            return False

        if direction == Direction.up:
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
                        
        elif direction == Direction.right:
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
                        
        elif direction == Direction.down:
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
                        
        elif direction == Direction.left:
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

    def generate_map(self):
        room_chance = 70
        current_features = 1

        self.make_room(self.map_width // 2, self.map_height // 2, 5, 5, Direction(random.randint(0, 3)))

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
                direction = Direction.invalid

                if self.is_block(new_x, new_y):
                    if self.is_block(new_x, new_y + 1) is False:
                        x_mod = 0
                        y_mod = -1
                        direction = Direction.up
                    elif self.is_block(new_x - 1, new_y) is False:
                        x_mod = 1
                        y_mod = 0
                        direction = Direction.right
                    elif self.is_block(new_x, new_y - 1) is False:
                        x_mod = 0
                        y_mod = 1
                        direction = Direction.down
                    elif self.is_block(new_x + 1, new_y) is False:
                        x_mod = -1
                        y_mod = 0
                        direction = Direction.left

                    if direction is not Direction.invalid:
                        break

            if direction is not Direction.invalid:
                feature = random.randint(0, 100)

                if feature <= room_chance:
                    if self.make_room(new_x + x_mod, new_y + y_mod, 20, 20, direction):
                        self.set_block(new_x, new_y, False)
                        self.set_block(new_x + x_mod, new_y + y_mod, False)
                elif feature > room_chance:
                    if self.make_tunnel(new_x + x_mod, new_y + y_mod, 10, direction):
                        self.set_block(new_x, new_y, False)

                current_features += 1


class TextArea:
    def __init__(self, x, y, num_line=4, bg_color=None):
        self.text_list = list()
        self.num_line = num_line
        self.x = x
        self.y = y
        self.bg_color = bg_color

    def __call__(self, text, *, fg_color=None):
        self.append_text(text, fg_color)

    def append_text(self, text, fg_color):
        self.text_list.append((text, fg_color))

        if len(self.text_list) > self.num_line:
            self.text_list.pop(0)

    def draw(self):
        for i in range(self.num_line + 1):
            _con.draw_str(self.x, self.y + i, ' ' * 80)

        for i, (text, fg_color) in enumerate(self.text_list):
            _con.draw_str(self.x, self.y + i, text, fg=fg_color, bg=self.bg_color)

    def clear(self):
        self.text_list = list()


def render(dungeon, object_list, text_area, hp_bar):
    dungeon.draw()

    for obj in object_list:
        if type(obj) is Player or dungeon.is_light(obj.x, obj.y):
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


def initialize(game_data):
    # 던전 생성 및 맵 자동 생성
    _object_list = list()
    _dungeon = Dungeon(game_data, _object_list)
    _dungeon.generate_map()

    # 몬스터, 아이템 생성 및 배치
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

    # 플레이어 배치
    while True:
        x = random.randint(0, _dungeon.map_width - 1)
        y = random.randint(0, _dungeon.map_height - 1)
        if not _dungeon.is_block(x, y):
            for k, v in game_data['characters'].items():
                _player = Player(x, y, k, game_data['characters'][k], _dungeon)
                _object_list.append(_player)
            break

    # 탈출구 배치
    while True:
        x = random.randint(0, _dungeon.map_width - 1)
        y = random.randint(0, _dungeon.map_height - 1)
        if not _dungeon.is_block(x, y):
            _object_list.append(Goal(x, y, _dungeon))
            break

    return _player, _object_list, _dungeon

if __name__ == "__main__":
    # 게임 데이터 로드
    with open('game_data.json', 'r') as f:
        game_data = json.load(f)

    # tdl 라이브러리 초기화 : 폰트, 콘솔
    tdl.set_font('terminal16x16.png', columnFirst=True, greyscale=True)
    _root = tdl.init(screen_width, screen_height, title="로그라이크", fullscreen=False)
    _con = tdl.Console(screen_width, screen_height)

    # UI 생성
    _text_area = TextArea(0, 42)
    _status_bar = TextArea(0, 40, 1, (160, 160, 160))
    _player, _object_list, _dungeon = initialize(game_data)

    # game loop
    while not tdl.event.is_window_closed():
        _dungeon.do_fov(_player.x, _player.y, _player.sight)
        render(_dungeon, _object_list, _text_area, _status_bar)

        if _player.is_end():
            _player, _object_list, _dungeon = initialize(game_data)
            _text_area.clear()

        exit_game = handle_keys(_player)
        if exit_game:
            break

        for monster in _dungeon.get_monsters():
            monster.take_turn()
