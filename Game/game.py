import math
import sys
from pathlib import Path

import pygame
from pygame import Vector2
import time

'''
This part here makes it so it opens properly in any directory
'''
PROJECT_ROOT = Path(__file__).resolve().parent.parent
VISUAL_DIR = PROJECT_ROOT / "Visual"

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Model.duck_agent import DuckAgent

"""
todo's
make players into rectangles
put a redo button in there
make the game replayable
"""

#screen
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 960, 720
screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
pygame.display.set_caption("Catch The Duck!")
clock = pygame.time.Clock()
font_gameover = pygame.font.SysFont(None, 72)
font_timer = pygame.font.SysFont(None, 36)
background_image = pygame.transform.scale(
    pygame.image.load(VISUAL_DIR / "CatchTheDuckBackground.PNG").convert(),
    (SCREEN_WIDTH, SCREEN_HEIGHT),
)
map = pygame.transform.scale(
    pygame.image.load(VISUAL_DIR / "map.png").convert_alpha(),
    (SCREEN_WIDTH, SCREEN_HEIGHT),
)

gameover = False
start_time = pygame.time.get_ticks()
elapsed_time = 0.0
CHARACTERS_SCALAR=1.15 #scaling size of player and AI

# Controller
pygame.joystick.init()

if pygame.joystick.get_count() > 0:
    controller = pygame.joystick.Joystick(0)
    print(f"Connected: {controller.get_name()}")

OBSTACLES = [
    pygame.Rect(100, 100, 50, 200),
    pygame.Rect(600, 150, 150, 50),
    pygame.Rect(350, 450, 100, 50)
]

LINE_COLOR = (255, 0, 0) # Red
map_mask = pygame.mask.from_surface(map)
rect_mask_cache = {}

# initialize agent
agent = DuckAgent()


def map_solid_at(x, y):
    """
    true when map pixel is solid according to map mask.
    """
    xi, yi = int(x), int(y)
    if 0 <= xi < SCREEN_WIDTH and 0 <= yi < SCREEN_HEIGHT:
        return bool(map_mask.get_at((xi, yi)))
    return False


def get_rect_mask(width, height):
    key = (width, height)
    if key not in rect_mask_cache:
        rect_mask_cache[key] = pygame.mask.Mask(key, fill=True)
    return rect_mask_cache[key]


def character_inside_map(character):
    """
    true when any part of the character rect overlaps the map.
    """
    rect_mask = get_rect_mask(character.width, character.height)
    return map_mask.overlap(rect_mask, (character.x, character.y)) is not None


def character_on_map(character):
    """
    checks one row under the character for map support.
    """
    y = character.bottom
    if y < 0 or y >= SCREEN_HEIGHT:
        return False

    left = max(0, character.left)
    right = min(SCREEN_WIDTH, character.right)
    for x in range(left, right):
        if map_solid_at(x, y):
            return True
    return False


RAY_DIRECTIONS = {
    "right":      ( 1,  0),
    "left":       (-1,  0),
    "down":       ( 0,  1),
    "up":         ( 0, -1),
    "up_right":   ( 1, -1),
    "up_left":    (-1, -1),
    "down_right": ( 1,  1),
    "down_left":  (-1,  1),
}

RAY_LENGTH = max(SCREEN_WIDTH, SCREEN_HEIGHT)


def cast_8_rays(origin, screen_w, screen_h, ray_length):
    results = {}
    for i in range(8):
        angle = math.radians(i * 45)
        dx = math.cos(angle)
        dy = math.sin(angle)
        far_end = (origin[0] + dx * ray_length, origin[1] + dy * ray_length)
        closest_point = far_end
        closest_dist = ray_length

        for step in range(1, ray_length + 1):
            sample_x = origin[0] + dx * step
            sample_y = origin[1] + dy * step

            if not (0 <= sample_x < screen_w and 0 <= sample_y < screen_h):
                closest_point = (sample_x, sample_y)
                closest_dist = step
                break

            if map_solid_at(sample_x, sample_y):
                closest_point = (sample_x, sample_y)
                closest_dist = step
                break
        results[i] = {
            "distance": closest_dist,
            "endpoint": closest_point,
            "angle": math.degrees(angle)
        }
    return results


# player
player_image = pygame.transform.scale(
    pygame.image.load(VISUAL_DIR / "Ritchie.png"),
    (34 * CHARACTERS_SCALAR, 51 * CHARACTERS_SCALAR),
)
player_image_flipped = pygame.transform.flip(player_image, True, False)
PLAYER_SPAWN = (SCREEN_WIDTH/5, 540)
player_pos = [PLAYER_SPAWN[0], PLAYER_SPAWN[1]]
player_Xmove = 0
player_facing_left = True

#player jumping variables
player_Yvel = 0
gravity = 0.6
jump_strength = 12
player_on_ground = True

def player_(x, y):
    sprite = player_image if player_facing_left else player_image_flipped
    player_rect = pygame.Rect(x, y, 31, 51)
    screen.blit(sprite, (x, y))

#ai
ai_image = pygame.transform.scale(
    pygame.image.load(VISUAL_DIR / "gustavo.png"),
    (37 * CHARACTERS_SCALAR, 51 * CHARACTERS_SCALAR),
)
ai_image_flipped = pygame.transform.flip(ai_image, True, False)
AI_SPAWN = (SCREEN_WIDTH-(SCREEN_WIDTH/5), 540)
ai_pos = [AI_SPAWN[0], AI_SPAWN[1]]
ai_Xmove = 0
ai_facing_left = False

#ai jumping variables
ai_Yvel = 0
ai_gravity = 0.6
ai_jump_strength = 12
ai_on_ground = True

def ai(x, y):
    sprite = ai_image_flipped if ai_facing_left else ai_image
    ai_rect = pygame.Rect(x, y, 51, 51)
    screen.blit(sprite, (x, y))

"""
wrap around screen edges when fully off screen
"""
def wrap_around(x_pos, y_pos, width, height, screen_width, screen_height):
    if x_pos > screen_width:
        x_pos = -width
    elif x_pos < -width:
        x_pos = screen_width
    if y_pos > screen_height:
        y_pos = -height
    elif y_pos < -height:
        y_pos = screen_height
    return x_pos, y_pos


def apply_action(action):
    """
    Translates action index into duck movement.
    Returns (x_move, should_jump, facing_left)
    0: idle
    1: left
    2: right
    3: jump
    4: jump + left
    5: jump + right
    """
    x_move = 0
    should_jump = False
    facing = ai_facing_left  # default: keep current facing

    if action == 0:   # idle
        x_move = 0
    elif action == 1: # left
        x_move = -1
        facing = True
    elif action == 2: # right
        x_move = 1
        facing = False
    elif action == 3: # jump
        should_jump = True
    elif action == 4: # jump + left
        x_move = -1
        should_jump = True
        facing = True
    elif action == 5: # jump + right
        x_move = 1
        should_jump = True
        facing = False

    return x_move, should_jump, facing


# starting game loop
running = True
caught_this_frame = False
round_trained = False

while running:
    clock.tick(60) #60 fps

    screen.blit(background_image, (0, 0))
    screen.blit(map,(0,0))
    keys = pygame.key.get_pressed() #key state checker

    #event scanner
    for event in pygame.event.get():
        match event.type:
            case pygame.QUIT:
                running = False
            case pygame.KEYDOWN:
                match event.key:
                    case pygame.K_LEFT:
                        player_Xmove = -1
                        player_facing_left = True
                    case pygame.K_RIGHT:
                        player_Xmove = 1
                        player_facing_left = False
                    case pygame.K_UP:
                        if player_on_ground:
                            player_Yvel = -jump_strength
                            player_on_ground = False
                    case pygame.K_r:
                        if gameover:
                            gameover = False
                            player_pos[:] = list(PLAYER_SPAWN)
                            ai_pos[:] = list(AI_SPAWN)
                            player_Yvel = ai_Yvel = 0
                            player_Xmove = ai_Xmove = 0
                            player_on_ground = ai_on_ground = True
                            start_time = pygame.time.get_ticks()

            case pygame.KEYUP:
                match event.key:
                    case pygame.K_LEFT:
                        if keys[pygame.K_RIGHT]:
                            player_Xmove = 1
                            player_facing_left = False
                        else:
                            player_Xmove = 0
                        #stop horizontal movement when key released
                    case pygame.K_RIGHT:
                        if keys[pygame.K_LEFT]:
                            player_Xmove = -1
                            player_facing_left = True
                        else:
                            player_Xmove = 0
                        #stop horizontal movement when key released
                    case pygame.K_a:
                        if keys[pygame.K_d]:
                            ai_Xmove = 1
                            ai_facing_left = False
                        else:
                            ai_Xmove = 0
                        #stop horizontal movement when key released
                    case pygame.K_d:
                        if keys[pygame.K_a]:
                            ai_Xmove = -1
                            ai_facing_left = True
                        else:
                            ai_Xmove = 0
                        #stop horizontal movement when key released

            case pygame.JOYBUTTONDOWN:
                if event.button == 0:
                    if player_on_ground:
                        player_Yvel = -jump_strength
                        player_on_ground = False

            case pygame.JOYAXISMOTION:
                if event.axis == 3:
                    if event.value < -0.5:
                        player_Xmove = -1
                        player_facing_left = True
                    elif event.value > 0.5:
                        player_Xmove = 1
                        player_facing_left = False
                    else:
                        player_Xmove = 0


    # ai logic
    ai_center = [ai_pos[0] + ai_image.get_width() // 2,
                 ai_pos[1] + ai_image.get_height() // 2]
    ray_data = cast_8_rays(ai_center, SCREEN_WIDTH, SCREEN_HEIGHT, RAY_LENGTH)

    obs = agent.build_observation(
        ai_pos=ai_pos,
        ai_vel_x=ai_Xmove,
        ai_vel_y=ai_Yvel,
        ai_on_ground=ai_on_ground,
        player_pos=player_pos,
        ray_data=ray_data,
        screen_w=SCREEN_WIDTH,
        screen_h=SCREEN_HEIGHT
    )

    action = agent.select_action(obs)
    ai_Xmove, should_jump, ai_facing_left = apply_action(action)

    if should_jump and ai_on_ground:
        ai_Yvel = -ai_jump_strength
        ai_on_ground = False

    # horizontal movement
    player_pos[0] += player_Xmove
    ai_pos[0] += ai_Xmove

    # auto-jumping for player
    if player_on_ground and keys[pygame.K_UP]:
        player_Yvel = -jump_strength
        player_on_ground = False
    if ai_on_ground and keys[pygame.K_w]:
        ai_Yvel = -ai_jump_strength
        ai_on_ground = False

    #player vertical physics (gravity + landing on map mask)
    player_Yvel += gravity
    player_pos[1] += player_Yvel
    player_rect = player_image.get_rect(x=int(player_pos[0]), y=int(player_pos[1]))
    if player_Yvel >= 0:
        if character_inside_map(player_rect):
            while character_inside_map(player_rect):
                player_pos[1] -= 1
                player_rect.y = int(player_pos[1])
            player_Yvel = 0
            player_on_ground = True
        else:
            player_on_ground = character_on_map(player_rect)
    else:
        if character_inside_map(player_rect):
            while character_inside_map(player_rect):
                player_pos[1] += 1
                player_rect.y = int(player_pos[1])
            player_Yvel = 0
        player_on_ground = False

    #ai vertical physics (gravity + landing on map mask)
    ai_Yvel += ai_gravity
    ai_pos[1] += ai_Yvel
    ai_rect = ai_image.get_rect(x=int(ai_pos[0]), y=int(ai_pos[1]))
    if ai_Yvel >= 0:
        if character_inside_map(ai_rect):
            while character_inside_map(ai_rect):
                ai_pos[1] -= 1
                ai_rect.y = int(ai_pos[1])
            ai_Yvel = 0
            ai_on_ground = True
        else:
            ai_on_ground = character_on_map(ai_rect)
    else:
        if character_inside_map(ai_rect):
            while character_inside_map(ai_rect):
                ai_pos[1] += 1
                ai_rect.y = int(ai_pos[1])
            ai_Yvel = 0
        ai_on_ground = False

    #wrap around screen edges
    player_pos[0], player_pos[1] = wrap_around(
        player_pos[0], player_pos[1],
        player_image.get_width(), player_image.get_height(),
        screen.get_width(), screen.get_height()
    )
    ai_pos[0], ai_pos[1] = wrap_around(
        ai_pos[0], ai_pos[1],
        ai_image.get_width(), ai_image.get_height(),
        screen.get_width(), screen.get_height()
    )

    # collision
    caught_this_frame = player_image.get_rect(
        x=player_pos[0], y=player_pos[1]
    ).colliderect(
        ai_image.get_rect(x=ai_pos[0], y=ai_pos[1])
    )

    if caught_this_frame and not gameover:
        gameover = True
        elapsed_time = (pygame.time.get_ticks() - start_time) / 1000.0

    # calculate reward and store experience
    reward = agent.compute_reward(
        ai_pos=ai_pos,
        player_pos=player_pos,
        ai_on_ground=ai_on_ground,
        caught=caught_this_frame
    )
    agent.store_reward(reward, done=caught_this_frame)
    if len(agent.rewards) >= 256:
        agent.train()

    # render
    if not gameover:
        for name, data in ray_data.items():
            pygame.draw.line(screen, LINE_COLOR, ai_center, data["endpoint"], 2)

        player_(player_pos[0], player_pos[1])
        ai(ai_pos[0], ai_pos[1])

    else:
        #game over screen (needs a game over png and replay button)
        text = font_gameover.render("GAME OVER", True, (255, 0, 0))
        screen.blit(text, (
            screen.get_width() // 2 - text.get_width() // 2,
            screen.get_height() // 2 - text.get_height() // 2
        ))
        timer_msg = f"Time: {elapsed_time:.2f}s | Press R to replay"
        timer_text = font_timer.render(timer_msg, True, (255, 255, 255))
        screen.blit(timer_text, (
            screen.get_width() // 2 - timer_text.get_width() // 2,
            screen.get_height() // 2 + 40
        ))

    pygame.display.update()
