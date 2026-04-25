import math
import sys
from pathlib import Path

import pygame
import torch

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
font_small = pygame.font.SysFont(None, 28)
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
CHARACTERS_SCALAR=1.15

# Controller
pygame.joystick.init()

if pygame.joystick.get_count() > 0:
    controller = pygame.joystick.Joystick(0)
    print(f"Connected: {controller.get_name()}")

LINE_COLOR = (255, 0, 0)
map_mask = pygame.mask.from_surface(map)
rect_mask_cache = {}
prev_dist = 0.0

# initialize agent
agent = DuckAgent()

ACTION_NAMES = ["idle", "left", "right", "jump", "jump+left", "jump+right"]


def map_solid_at(x, y):
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
    rect_mask = get_rect_mask(character.width, character.height)
    return map_mask.overlap(rect_mask, (character.x, character.y)) is not None


def character_on_map(character):
    y = character.bottom
    if y < 0 or y >= SCREEN_HEIGHT:
        return False
    left = max(0, character.left)
    right = min(SCREEN_WIDTH, character.right)
    for x in range(left, right):
        if map_solid_at(x, y):
            return True
    return False


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

player_Yvel = 0
gravity = 0.6
jump_strength = 12
player_on_ground = True

def player_(x, y):
    sprite = player_image if player_facing_left else player_image_flipped
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

ai_Yvel = 0
ai_gravity = 0.6
ai_jump_strength = 12
ai_on_ground = True
num_training_loops = 0
last_mean_reward = 0.0
current_action = 0
current_probs = [1/6] * 6

def ai(x, y):
    sprite = ai_image_flipped if ai_facing_left else ai_image
    screen.blit(sprite, (x, y))


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
    x_move = 0
    should_jump = False
    facing = ai_facing_left

    if action == 0:
        x_move = 0
    elif action == 1:
        x_move = -1
        facing = True
    elif action == 2:
        x_move = 1
        facing = False
    elif action == 3:
        should_jump = True
    elif action == 4:
        x_move = -1
        should_jump = True
        facing = True
    elif action == 5:
        x_move = 1
        should_jump = True
        facing = False

    return x_move, should_jump, facing


def reset_duck():
    global ai_pos, ai_Yvel, ai_Xmove, ai_on_ground, ai_facing_left, prev_dist
    ai_pos[:] = list(AI_SPAWN)
    ai_Yvel = 0
    ai_Xmove = 0
    ai_on_ground = True
    ai_facing_left = False
    prev_dist = 0.0


def reset_player():
    global player_pos, player_Yvel, player_Xmove, player_on_ground, player_facing_left
    player_pos[:] = list(PLAYER_SPAWN)
    player_Yvel = 0
    player_Xmove = 0
    player_on_ground = True
    player_facing_left = True


# ghost round state
player_recording = []
last_recording = []
is_ghost_round = False
ghost_round_count = 0
MAX_GHOST_ROUNDS = 15
ghost_frame = 0

# waiting for player to start next round after training
waiting_for_start = False

running = True
caught_this_frame = False

while running:

    screen.blit(background_image, (0, 0))
    screen.blit(map, (0, 0))
    keys = pygame.key.get_pressed()

    # --- ghost round: override player position from recording ---
    if is_ghost_round:
        if ghost_frame < len(last_recording):
            player_pos[0], player_pos[1] = last_recording[ghost_frame]
            ghost_frame += 1
        else:
            result = agent.train()
            if result is not None:
                last_mean_reward = result
            num_training_loops += 1
            ghost_round_count += 1

            if ghost_round_count >= MAX_GHOST_ROUNDS:
                is_ghost_round = False
                waiting_for_start = True
                reset_player()
                reset_duck()
                player_recording = []
            else:
                reset_duck()
                ghost_frame = 0
    else:
        clock.tick(60)

    # event scanner
    for event in pygame.event.get():
        match event.type:
            case pygame.QUIT:
                running = False
            case pygame.KEYDOWN:
                # space starts next round after training
                if waiting_for_start and event.key == pygame.K_SPACE:
                    waiting_for_start = False
                    gameover = False
                    start_time = pygame.time.get_ticks()

                elif not is_ghost_round and not waiting_for_start:
                    match event.key:
                        case pygame.K_LEFT:
                            player_Xmove = -1.5
                            player_facing_left = True
                        case pygame.K_RIGHT:
                            player_Xmove = 1.5
                            player_facing_left = False
                        case pygame.K_UP:
                            if player_on_ground:
                                player_Yvel = -jump_strength
                                player_on_ground = False
                        case pygame.K_r:
                            if gameover:
                                gameover = False
                                reset_player()
                                reset_duck()
                                player_recording = []
                                start_time = pygame.time.get_ticks()

            case pygame.KEYUP:
                if not is_ghost_round and not waiting_for_start:
                    match event.key:
                        case pygame.K_LEFT:
                            if keys[pygame.K_RIGHT]:
                                player_Xmove = 1.5
                                player_facing_left = False
                            else:
                                player_Xmove = 0
                        case pygame.K_RIGHT:
                            if keys[pygame.K_LEFT]:
                                player_Xmove = -1.5
                                player_facing_left = True
                            else:
                                player_Xmove = 0
                        case pygame.K_a:
                            if keys[pygame.K_d]:
                                ai_Xmove = 1.5
                                ai_facing_left = False
                            else:
                                ai_Xmove = 0
                        case pygame.K_d:
                            if keys[pygame.K_a]:
                                ai_Xmove = -1.5
                                ai_facing_left = True
                            else:
                                ai_Xmove = 0

            case pygame.JOYBUTTONDOWN:
                if not is_ghost_round and not waiting_for_start and event.button == 0:
                    if player_on_ground:
                        player_Yvel = -jump_strength
                        player_on_ground = False
                if waiting_for_start and event.button == 2:
                    waiting_for_start = False
                    gameover = False
                    start_time = pygame.time.get_ticks()

            case pygame.JOYAXISMOTION:
                if not is_ghost_round and not waiting_for_start and event.axis == 3:
                    if event.value < -0.5:
                        player_Xmove = -1.5
                        player_facing_left = True
                    elif event.value > 0.5:
                        player_Xmove = 1.5
                        player_facing_left = False
                    else:
                        player_Xmove = 0

    # --- waiting for start screen ---
    if waiting_for_start:
        screen.fill((0, 0, 0))
        done_text = font_gameover.render("Training Complete!", True, (255, 255, 0))
        stats_text = font_timer.render(
            f"Training Loops: {num_training_loops} | Avg Reward: {last_mean_reward:.3f}",
            True, (255, 255, 255)
        )
        start_text = font_timer.render("Press B to start the next round", True, (0, 255, 0))
        screen.blit(done_text, (
            SCREEN_WIDTH // 2 - done_text.get_width() // 2,
            SCREEN_HEIGHT // 2 - 80
        ))
        screen.blit(stats_text, (
            SCREEN_WIDTH // 2 - stats_text.get_width() // 2,
            SCREEN_HEIGHT // 2
        ))
        screen.blit(start_text, (
            SCREEN_WIDTH // 2 - start_text.get_width() // 2,
            SCREEN_HEIGHT // 2 + 60
        ))
        pygame.display.update()
        continue

    # --- ai logic ---
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
    current_action = action

    # grab probs for HUD display
    with torch.no_grad():
        probs, _ = agent.model(obs)
    current_probs = probs.numpy()

    if should_jump and ai_on_ground:
        ai_Yvel = -ai_jump_strength
        ai_on_ground = False

    if not is_ghost_round:
        player_pos[0] += player_Xmove
    ai_pos[0] += ai_Xmove

    if not is_ghost_round:
        if player_on_ground and keys[pygame.K_UP]:
            player_Yvel = -jump_strength
            player_on_ground = False

    # player vertical physics
    if not is_ghost_round:
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

    # ai vertical physics
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

    # wrap around
    if not is_ghost_round:
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

    # handle real round gameover
    if caught_this_frame and not gameover and not is_ghost_round:
        gameover = True
        elapsed_time = (pygame.time.get_ticks() - start_time) / 1000.0
        result = agent.train()
        if result is not None:
            last_mean_reward = result
        num_training_loops += 1
        last_recording = [pos[:] for pos in player_recording]
        player_recording = []
        if len(last_recording) > 0:
            is_ghost_round = True
            ghost_round_count = 0
            ghost_frame = 0
            gameover = False
            reset_duck()

    # handle ghost round catch
    if caught_this_frame and is_ghost_round:
        result = agent.train()
        if result is not None:
            last_mean_reward = result
        num_training_loops += 1
        ghost_round_count += 1

        if ghost_round_count >= MAX_GHOST_ROUNDS:
            is_ghost_round = False
            waiting_for_start = True
            reset_player()
            reset_duck()
            player_recording = []
        else:
            reset_duck()
            ghost_frame = 0

    # reward
    reward = agent.compute_reward(
        ai_pos=ai_pos,
        player_pos=player_pos,
        ai_on_ground=ai_on_ground,
        caught=caught_this_frame,
        prev_dist=prev_dist,
        screen_w=SCREEN_WIDTH,
        screen_h=SCREEN_HEIGHT,
        action=action
    )
    prev_dist = agent.wrap_aware_dist(ai_pos, player_pos, SCREEN_WIDTH, SCREEN_HEIGHT)

    if not is_ghost_round and not gameover:
        player_recording.append(player_pos[:])

    agent.store_reward(reward, done=caught_this_frame)

    # --- render ---
    if is_ghost_round:
        screen.fill((0, 0, 0))
        training_text = font_gameover.render("Training...", True, (255, 255, 0))
        round_text = font_timer.render(
            f"Ghost Round {ghost_round_count + 1}/{MAX_GHOST_ROUNDS} | "
            f"Training Loops: {num_training_loops} | Avg Reward: {last_mean_reward:.3f}",
            True, (255, 255, 255)
        )
        screen.blit(training_text, (
            SCREEN_WIDTH // 2 - training_text.get_width() // 2,
            SCREEN_HEIGHT // 2 - training_text.get_height() // 2
        ))
        screen.blit(round_text, (
            SCREEN_WIDTH // 2 - round_text.get_width() // 2,
            SCREEN_HEIGHT // 2 + 40
        ))

    elif not gameover:
        for name, data in ray_data.items():
            pygame.draw.line(screen, LINE_COLOR, ai_center, data["endpoint"], 2)

        player_(player_pos[0], player_pos[1])
        ai(ai_pos[0], ai_pos[1])

        # top stats
        episode_text = font_timer.render(
            f"Training Loops: {num_training_loops} | Avg Reward: {last_mean_reward:.3f}",
            True, (255, 255, 255)
        )
        screen.blit(episode_text, (10, 10))

    else:
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