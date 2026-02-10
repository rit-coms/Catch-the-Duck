import pygame, time

"""
todo's
Getting center of player and ai
drawing 8 raycasting lines
getting distance
stop flicker
stop line passthrough entrance of object
"""


#screen
pygame.init()
SCREEN_WIDTH, SCREEN_HEIGHT = 960, 540
screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
pygame.display.set_caption("Catch The Duck!")
clock = pygame.time.Clock()
font_gameover = pygame.font.SysFont(None, 72)
font_timer = pygame.font.SysFont(None, 36)

gameover=False
start_time = pygame.time.get_ticks()
elapsed_time = 0.0

OBSTACLES = [
    pygame.Rect(100, 100, 50, 200),
    pygame.Rect(600, 150, 150, 50),
    pygame.Rect(350, 450, 100, 50)
]

LINE_COLOR = (255, 0, 0) # Red
OBSTACLE_COLOR = (0, 0, 255) # Blue

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
    screen.blit(player_image, (x, y))

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
    screen.blit(ai_image, (x, y))

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
    clock.tick(60) #60 fps

    screen.fill((0, 0, 0))  #black bg setup
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
                        #stop horizontal movement when key released
                    case pygame.K_RIGHT:
                        if keys[pygame.K_LEFT]:
                            player_Xmove = -1
                        else:
                            player_Xmove = 0
                        #stop horizontal movement when key released
                    case pygame.K_a:
                        if keys[pygame.K_d]:
                            ai_Xmove = 1
                        else:
                            ai_Xmove = 0
                        #stop horizontal movement when key released
                    case pygame.K_d:
                        if keys[pygame.K_a]:
                            ai_Xmove = -1
                        else:
                            ai_Xmove = 0
                        #stop horizontal movement when key released

        # Get mouse position for line direction
        mouse_pos = pygame.mouse.get_pos()

        # Calculate a distant end point for the theoretical line (raycasting)
        # This point should be far enough to cover the whole screen or more
        # A simple way for a line of sight is to use a large vector towards the mouse
        direction_vector = (mouse_pos[0] - ai_pos[0], mouse_pos[1] - ai_pos[1])
        # Normalize and multiply by a large distance (e.g., screen dimensions)
        distance = max(SCREEN_WIDTH, SCREEN_HEIGHT)
        if direction_vector[0] != 0 or direction_vector[1] != 0:
            length = (direction_vector[0] ** 2 + direction_vector[1] ** 2) ** 0.5
            normalized_direction = (direction_vector[0] / length, direction_vector[1] / length)
            far_end_pos = (ai_pos[0] + normalized_direction[0] * distance,
                           ai_pos[1] + normalized_direction[1] * distance)
        else:
            far_end_pos = mouse_pos

        # Default end point is the far point
        actual_end_pos = far_end_pos

        # Check for collisions with obstacles
        for obstacle in OBSTACLES:
            # clipline returns a tuple of ((start_x, start_y), (end_x, end_y)) if it collides
            # or an empty tuple if not
            clipped_line = obstacle.clipline(ai_pos, far_end_pos)
            if clipped_line:
                # The second point of the clipped line is the intersection point
                intersection_point = clipped_line[1]
                # We want the *closest* intersection point if there are multiple obstacles.
                # This logic finds the first one, for multiple you'd need to compare distances.
                # A more robust raycasting system would be needed for complex maps.

                # For simplicity, we just stop at the first one in the loop
                actual_end_pos = intersection_point
                break  # Stop checking other obstacles once a collision is found



        # Draw obstacles
        for obstacle in OBSTACLES:
            pygame.draw.rect(screen, OBSTACLE_COLOR, obstacle)

        # Draw the line that stops at the collision point
        pygame.draw.line(screen, LINE_COLOR, ai_pos, actual_end_pos, 2)


    player_pos[0] += player_Xmove
    if player_image.get_rect(x=player_pos[0], y=player_pos[1]).colliderect(ai_image.get_rect(x=ai_pos[0], y=ai_pos[1])):
            gameover = True
    #horizontal movement
    player_X += player_Xmove
    ai_X += ai_Xmove

    #auto-jumping
    if player_on_ground and keys[pygame.K_UP]:
        player_Yvel = -jump_strength
        player_on_ground = False
    if ai_on_ground and keys[pygame.K_w]:
        ai_Yvel = -ai_jump_strength
        ai_on_ground = False

    #player vertical physics (gravity + landing)
    player_Yvel += gravity
    player_Y += player_Yvel
    if player_Y >= ground_y:
        #snap to ground and reset jump state
        player_Y = ground_y
        player_Yvel = 0
        player_on_ground = True

    #ai vertical physics (gravity + landing)
    ai_Yvel += ai_gravity
    ai_Y += ai_Yvel
    if ai_Y >= ai_ground_y:
        #snap to ground and reset jump state
        ai_Y = ai_ground_y
        ai_Yvel = 0
        ai_on_ground = True

    #wrap around screen edges
    player_X, player_Y = wrap_around(
        player_X, player_Y,
        player_image.get_width(), player_image.get_height(),
        screen.get_width(), screen.get_height()
    )
    ai_X, ai_Y = wrap_around(
        ai_X, ai_Y,
        ai_image.get_width(), ai_image.get_height(),
        screen.get_width(), screen.get_height()
    )

    #collision between player and ai
    if player_image.get_rect(x=player_X, y=player_Y).colliderect(ai_image.get_rect(x=ai_X, y=ai_Y)):
            if gameover != True:
                gameover = True
                elapsed_time = (pygame.time.get_ticks() - start_time) / 1000.0

    #render
    if gameover!=True:
        #draw player and ai
        player_(player_pos[0], player_pos[1])
        ai(ai_pos[0], ai_pos[1])
    else:
        #game over screen (needs a game over png and replay button)
        text = font_gameover.render("GAME OVER", True, (255, 0, 0))
        screen.blit(text, (screen.get_width()//2 - text.get_width()//2, screen.get_height()//2 - text.get_height()//2))
        timer_msg = f"Time: {elapsed_time:.2f}s"
        timer_text = font_timer.render(timer_msg, True, (255, 255, 255))
        screen.blit(timer_text, (screen.get_width()//2 - timer_text.get_width()//2, screen.get_height()//2 + 40))


    pygame.display.update()
