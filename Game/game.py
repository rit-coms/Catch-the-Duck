import pygame, time

#screen
pygame.init()
screen = pygame.display.set_mode((800,600))
clock = pygame.time.Clock()

gameover=False 

#player
player_image = pygame.transform.scale(pygame.image.load("Game/img/player.png"), (31, 51))
player_X, player_Y = 150, 350
player_Xmove = 0

def player_(x, y):
    screen.blit(player_image, (x, y))

#ai
ai_image = pygame.transform.scale(pygame.image.load("Game/img/AI.png"), (51, 51))
ai_X, ai_Y = 350, 350

def ai(x, y):
    screen.blit(ai_image, (x, y))

#main
running = True
while running == True:
    clock.tick(60) #60 fps

    screen.fill((0, 0, 0))  #black bg setup

    #event scanner
    for i in pygame.event.get():
        match i.type:
            case pygame.QUIT:
                running = False
            case pygame.KEYDOWN:
                match i.key:
                    case pygame.K_LEFT:
                        player_Xmove = -1
                    case pygame.K_RIGHT:
                        player_Xmove = 1
            case pygame.KEYUP:
                match i.key:
                    case pygame.K_LEFT | pygame.K_RIGHT:
                        player_Xmove = 0
                        # make jump physics here


    player_X += player_Xmove
    if player_image.get_rect(x=player_X, y=player_Y).colliderect(ai_image.get_rect(x=ai_X, y=ai_Y)):
            gameover = True


    if gameover!=True:
        player_(player_X, player_Y)
        ai(ai_X, ai_Y)

    pygame.display.update()
