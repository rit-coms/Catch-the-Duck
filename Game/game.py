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
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
screen = pygame.display.set_mode((SCREEN_WIDTH,SCREEN_HEIGHT))
clock = pygame.time.Clock()

gameover=False

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

def player_(x, y):
    screen.blit(player_image, (x, y))

#ai
ai_image = pygame.transform.scale(pygame.image.load("../Visual/AI.png"), (51, 51))
ai_pos = [350, 350]
ai_center = [ai_pos[0] + (512/2)/32, ai_pos[1] + (512/2)/32]

def ai(x, y):
    screen.blit(ai_image, (x, y))

#starting game loop

running = True
while running:
    clock.tick(60) #60 fps

    screen.fill((0, 0, 0))  #black bg setup

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
            case pygame.KEYUP:
                match event.key:
                    case pygame.K_LEFT | pygame.K_RIGHT:
                        player_Xmove = 0
                        # make jump physics here

        # Get mouse position for line direction
        mouse_pos = pygame.mouse.get_pos()

        # Calculate a distant end point for the theoretical line (raycasting)
        # This point should be far enough to cover the whole screen or more
        # A simple way for a line of sight is to use a large vector towards the mouse
        direction_vector = (mouse_pos[0] - ai_center[0], mouse_pos[1] - ai_center[1])
        # Normalize and multiply by a large distance (e.g., screen dimensions)
        distance = max(SCREEN_WIDTH, SCREEN_HEIGHT)
        if direction_vector[0] != 0 or direction_vector[1] != 0:
            length = (direction_vector[0] ** 2 + direction_vector[1] ** 2) ** 0.5
            normalized_direction = (direction_vector[0] / length, direction_vector[1] / length)
            far_end_pos = (ai_center[0] + normalized_direction[0] * distance,
                           ai_center[1] + normalized_direction[1] * distance)
        else:
            far_end_pos = mouse_pos

        # Default end point is the far point
        actual_end_pos = far_end_pos

        # Check for collisions with obstacles
        for obstacle in OBSTACLES:
            # clipline returns a tuple of ((start_x, start_y), (end_x, end_y)) if it collides
            # or an empty tuple if not
            clipped_line = obstacle.clipline(ai_center, far_end_pos)
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
        pygame.draw.line(screen, LINE_COLOR, ai_center, actual_end_pos, 2)


    player_pos[0] += player_Xmove
    if player_image.get_rect(x=player_pos[0], y=player_pos[1]).colliderect(ai_image.get_rect(x=ai_pos[0], y=ai_pos[1])):
            gameover = True


    if gameover!=True:
        player_(player_pos[0], player_pos[1])
        ai(ai_pos[0], ai_pos[1])

    pygame.display.update()
