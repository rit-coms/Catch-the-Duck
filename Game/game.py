import math
import pygame
from pygame import Vector2

#screen
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 960, 540
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Catch The Duck!")
clock = pygame.time.Clock()
font_gameover = pygame.font.SysFont(None, 72)
font_timer = pygame.font.SysFont(None, 36)

gameover = False
start_time = pygame.time.get_ticks()
elapsed_time = 0.0

OBSTACLES = [
    pygame.Rect(100, 100, 50, 200),
    pygame.Rect(600, 150, 150, 50),
    pygame.Rect(350, 450, 100, 50)
]

LINE_COLOR = (255, 0, 0)    # Red
OBSTACLE_COLOR = (0, 0, 255) # Blue

# 8 ray directions as unit vectors
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

def cast_8_rays(origin, obstacles, screen_w, screen_h, ray_length):
    results = {}

    for i in range(8):
        angle = math.radians(i * 45)
        dx = math.cos(angle)
        dy = math.sin(angle)

        # Just use a long ray, no clamping
        far_end = (origin[0] + dx * ray_length, origin[1] + dy * ray_length)

        closest_point = far_end
        closest_dist = Vector2(origin).distance_to(Vector2(far_end))

        for obstacle in obstacles:
            clipped = obstacle.clipline(origin, far_end)
            if clipped:
                hit_point = clipped[0]
                dist = Vector2(origin).distance_to(Vector2(hit_point))
                if dist < closest_dist:
                    closest_dist = dist
                    closest_point = hit_point

        results[i] = {
            "distance": closest_dist,
            "endpoint": closest_point,
            "angle": math.degrees(angle)
        }

    return results

#player
player_image = pygame.transform.scale(pygame.image.load("../Visual/player.png"), (31, 51))
player_pos = [150, 350]
player_Xmove = 0

#player jumping variables
player_Yvel = 0
gravity = 0.6
jump_strength = 12
ground_y = 350
player_on_ground = True

def player_(x, y):
    player_rect = pygame.Rect(x, y, 31, 51)
    screen.blit(player_image, player_rect)

#ai
ai_image = pygame.transform.scale(pygame.image.load("../Visual/AI.png"), (51, 51))
ai_pos = [350, 350]
ai_Xmove = 0

#ai jumping variables
ai_Yvel = 0
ai_gravity = 0.6
ai_jump_strength = 12
ai_ground_y = 350
ai_on_ground = True

def ai(x, y):
    ai_rect = pygame.Rect(x, y, 51, 51)
    screen.blit(ai_image, ai_rect)

#wrap around screen edges when fully off screen
def wrap_around(x, y, w, h, screen_w, screen_h):
    if x > screen_w:
        x = -w
    elif x < -w:
        x = screen_w
    if y > screen_h:
        y = -h
    elif y < -h:
        y = screen_h
    return x, y

#starting game loop
running = True
while running:
    clock.tick(60)  # 60 fps

    screen.fill((0, 0, 0))  # black bg
    keys = pygame.key.get_pressed()

    # Event scanner
    for event in pygame.event.get():
        match event.type:
            case pygame.QUIT:
                running = False
            case pygame.KEYDOWN:
                match event.key:
                    case pygame.K_LEFT:
                        player_Xmove = -1
                    case pygame.K_RIGHT:
                        player_Xmove = 1
                    case pygame.K_UP:
                        if player_on_ground:
                            player_Yvel = -jump_strength
                            player_on_ground = False
                    case pygame.K_a:
                        ai_Xmove = -1
                    case pygame.K_d:
                        ai_Xmove = 1
                    case pygame.K_w:
                        if ai_on_ground:
                            ai_Yvel = -ai_jump_strength
                            ai_on_ground = False
            case pygame.KEYUP:
                match event.key:
                    case pygame.K_LEFT:
                        if keys[pygame.K_RIGHT]:
                            player_Xmove = 1
                        else:
                            player_Xmove = 0
                    case pygame.K_RIGHT:
                        if keys[pygame.K_LEFT]:
                            player_Xmove = -1
                        else:
                            player_Xmove = 0
                    case pygame.K_a:
                        if keys[pygame.K_d]:
                            ai_Xmove = 1
                        else:
                            ai_Xmove = 0
                    case pygame.K_d:
                        if keys[pygame.K_a]:
                            ai_Xmove = -1
                        else:
                            ai_Xmove = 0

    # Cast all 8 rays from the AI
    ai_center = [ai_pos[0] + ai_image.get_width() // 2, ai_pos[1] + ai_image.get_height() // 2]
    ray_data = cast_8_rays(ai_center, OBSTACLES, SCREEN_WIDTH, SCREEN_HEIGHT, RAY_LENGTH)
    distances = {name: data["distance"] for name, data in ray_data.items()}

    # Horizontal movement
    player_pos[0] += player_Xmove
    ai_pos[0] += ai_Xmove

    # Auto-jumping (held key)
    if player_on_ground and keys[pygame.K_UP]:
        player_Yvel = -jump_strength
        player_on_ground = False
    if ai_on_ground and keys[pygame.K_w]:
        ai_Yvel = -ai_jump_strength
        ai_on_ground = False

    # Player vertical physics
    player_Yvel += gravity
    player_pos[1] += player_Yvel
    if player_pos[1] >= ground_y:
        player_pos[1] = ground_y
        player_Yvel = 0
        player_on_ground = True

    # AI vertical physics
    ai_Yvel += ai_gravity
    ai_pos[1] += ai_Yvel
    if ai_pos[1] >= ai_ground_y:
        ai_pos[1] = ai_ground_y
        ai_Yvel = 0
        ai_on_ground = True

    # Wrap around screen edges
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

    # Collision between player and AI
    if player_image.get_rect(x=player_pos[0], y=player_pos[1]).colliderect(
            ai_image.get_rect(x=ai_pos[0], y=ai_pos[1])):
        if not gameover:
            gameover = True
            elapsed_time = (pygame.time.get_ticks() - start_time) / 1000.0

    # Render
    if not gameover:
        # Draw obstacles
        for obstacle in OBSTACLES:
            pygame.draw.rect(screen, OBSTACLE_COLOR, obstacle)

        # Draw all 8 rays
        for name, data in ray_data.items():
            pygame.draw.line(screen, LINE_COLOR, ai_center, data["endpoint"], 2)

        # Draw player and AI
        player_(player_pos[0], player_pos[1])
        ai(ai_pos[0], ai_pos[1])
    else:
        # Game over screen
        text = font_gameover.render("GAME OVER", True, (255, 0, 0))
        screen.blit(text, (
            screen.get_width() // 2 - text.get_width() // 2,
            screen.get_height() // 2 - text.get_height() // 2
        ))
        timer_msg = f"Time: {elapsed_time:.2f}s"
        timer_text = font_timer.render(timer_msg, True, (255, 255, 255))
        screen.blit(timer_text, (
            screen.get_width() // 2 - timer_text.get_width() // 2,
            screen.get_height() // 2 + 40
        ))

    pygame.display.update()