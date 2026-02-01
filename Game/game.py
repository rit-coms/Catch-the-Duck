import sys
import pygame
from pygame.examples.grid import WINDOW_WIDTH, WINDOW_HEIGHT
from pygame.locals import *

"""
Function to start and run the game loop
"""
def start():
    # Setting up window
    pygame.init()
    pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    pygame.display.set_caption("Catch the Duck")

    # Game loop
    running = True

    while running:
        for event in pygame.event.get():
            # Check for KEYDOWN event
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    pygame.quit()
                    sys.exit()