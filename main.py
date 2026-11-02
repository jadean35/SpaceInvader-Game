import pygame
import random
from pygame import mixer

# Initialize pygame
mixer.init()
pygame.init()

mixer.music.load('ovey T ft shota duso.mp3')
mixer.music.play(-1)

# Set up game window
WINDOW_WIDTH = 800
WINDOW_HEIGHT =  600
window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pygame.display.set_caption("Duso Space Shooter")

# Set up clock for controlling game speed
clock = pygame.time.Clock()

# Load player image
player_image = pygame.image.load('spaceship.png').convert_alpha()
background = pygame.image.load('Blue Moon Galaxy.png').convert_alpha()
alien = pygame.image.load('alien.png')
bullet = pygame.image.load('bullet.png').convert_alpha()

pygame.display.set_icon(alien)

# Load enemy image
enemy_image = pygame.image.load('enemy.png').convert_alpha()

# Set up player variables
player_x = WINDOW_WIDTH // 2
player_y = WINDOW_HEIGHT - 100
player_speed = 5

# Set up enemy variables
enemy_list = []
enemy_speed = 3
enemy_spawn_time = 60

# Set up bullet variables
bullet_list = []
bullet_speed = 10

# Set up score variable
score = 0


# Define collision function
def check_collision(rect1, rect2):
    if rect1.colliderect(rect2):
        return True
    else:
        return False
    #mixer.music.load('laser.mp3')
   # mixer.music.play()


# Main game loop
while True:
    # Handle events
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            quit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                # Fire bullet
                bullet_list.append(pygame.Rect(player_x + 23, player_y - 15, 4, 15))

    # Move player
    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT] and player_x > 0:
        player_x -= player_speed
    if keys[pygame.K_RIGHT] and player_x < WINDOW_WIDTH - player_image.get_width():
        player_x += player_speed


    # Spawn enemies
    if random.randint(0, enemy_spawn_time) == 0:
        enemy_list.append(
            pygame.Rect(random.randint(0, WINDOW_WIDTH - enemy_image.get_width()), 0, enemy_image.get_width(),
                        enemy_image.get_height()))

    # Move enemies
    for enemy in enemy_list:
        enemy.move_ip(0, enemy_speed)
        if enemy.top > WINDOW_HEIGHT:
            enemy_list.remove(enemy)

    # Move bullets
    for bullet in bullet_list:
        bullet.move_ip(0, -bullet_speed)
        if bullet.bottom < 0:
            bullet_list.remove(bullet)
            bullet_sound = mixer.Sound('lazer.wav ')
            bullet_sound.play()

    # Check for collisions
    for enemy in enemy_list:
        for bullet in bullet_list:
            if check_collision(enemy, bullet):
                enemy_list.remove(enemy)
                bullet_list.remove(bullet)
                score += 10
                explosion_sound = mixer.Sound('HeliExplode.wav')
                explosion_sound.play()



    for enemy in enemy_list:
        if check_collision(enemy, pygame.Rect(player_x, player_y, player_image.get_width(), player_image.get_height())):
            pygame.quit()
            quit()

    # Draw everything
    window.blit(background, (0, 0))
    window.blit(player_image, (player_x, player_y))
    for enemy in enemy_list:
        window.blit(enemy_image, enemy)
    for bullet in bullet_list:
        pygame.draw.rect(window, (255, 255, 255), bullet)
    font = pygame.font.SysFont(None, 30)
    score_text = font.render("Score: " + str(score), True, (255, 255, 255))
    window.blit(score_text, (10, 10))
    pygame.display.update()


    # Control game speed
    clock.tick(60)
