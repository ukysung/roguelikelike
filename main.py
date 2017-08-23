import tdl

screen_width = 80
screen_height = 50

map_width = 80
map_height = 45

color_dark_wall = (0, 0, 255)
color_dark_ground = (255, 255, 255)


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
        if not self.dungeon.is_block(self.x + dx, self.y + dy):
            self.x += dx
            self.y += dy

    def draw(self):
        _con.draw_char(self.x, self.y, self.char, self.color, bg=None)

    def clear(self):
        _con.draw_char(self.x, self.y, ' ', self.color, bg=None)


class Dungeon:
    def __init__(self, width, height):
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


def render(area, object_list):
    for y in range(map_height):
        for x in range(map_width):
            if area.is_block(x, y):
                _con.draw_char(x, y, None, fg=None, bg=color_dark_wall)
            else:
                _con.draw_char(x, y, None, fg=None, bg=color_dark_ground)

    for obj in object_list:
        obj.draw()

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
tdl.set_font('arial10x10.png', greyscale=True, altLayout=True)
_root = tdl.init(screen_width, screen_height, title="로그라이크", fullscreen=False)
_con = tdl.Console(screen_width, screen_height)

_dungeon = Dungeon(map_width, map_height)
_dungeon.create_room(Rect(20, 15, 10, 15))
_dungeon.create_room(Rect(50, 15, 10, 15))
_dungeon.create_h_tunnel(25, 55, 23)

_player = GameObject(screen_width // 2, screen_height // 2, '@', (0, 0, 0), _dungeon)
_object_list = [_player]
_player.x = 25
_player.y = 23

# game loop
while not tdl.event.is_window_closed():
    render(_dungeon, _object_list)

    exit_game = handle_keys(_player)
    if exit_game:
        break
