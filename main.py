
import pygame
import random
import sys
from pathlib import Path

# ==========================================
# DUSO SPACE SHOOTER
# ==========================================

# Find game files in PyCharm and packaged EXE
def resource_path(filename):
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent

    return str(base_path / filename)


# Initialize pygame
pygame.init()

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600

window = pygame.display.set_mode(
    (WINDOW_WIDTH, WINDOW_HEIGHT)
)
pygame.display.set_caption("Duso Space Shooter")

clock = pygame.time.Clock()

# ==========================================
# LOAD IMAGES
# ==========================================

def load_image(filename):
    return pygame.image.load(
        resource_path(filename)
    ).convert_alpha()


player_image = load_image("spaceship.png")
enemy_image = load_image("enemy.png")
alien_image = load_image("alien.png")
bullet_image = load_image("bullet.png")

background = pygame.image.load(
    resource_path("Blue Moon Galaxy.png")
).convert()

background = pygame.transform.scale(
    background, (WINDOW_WIDTH, WINDOW_HEIGHT)
)

pygame.display.set_icon(alien_image)

# ==========================================
# LOAD MUSIC AND SOUND EFFECTS
# ==========================================

music_ready = False
laser_sound = None
explosion_sound = None

try:
    if not pygame.mixer.get_init():
        pygame.mixer.init()

    music_ready = True

    pygame.mixer.music.load(
        resource_path("ovey T ft shota duso.mp3")
    )
    pygame.mixer.music.set_volume(0.4)
    pygame.mixer.music.play(-1)

except (pygame.error, OSError) as error:
    print("Music error:", error)

if music_ready:
    try:
        laser_sound = pygame.mixer.Sound(
            resource_path("lazer.wav")
        )
        laser_sound.set_volume(0.5)

        explosion_sound = pygame.mixer.Sound(
            resource_path("HeliExplode.wav")
        )
        explosion_sound.set_volume(0.6)

    except (pygame.error, OSError) as error:
        print("Sound effect error:", error)

# ==========================================
# PLAYER SETTINGS
# ==========================================

player_x = WINDOW_WIDTH // 2 - player_image.get_width() // 2
player_y = WINDOW_HEIGHT - 100
player_speed = 5

# ==========================================
# ENEMY SETTINGS
# ==========================================

enemy_list = []
enemy_speed = 3
enemy_spawn_time = 60
spawn_counter = 0

# ==========================================
# BULLET SETTINGS
# ==========================================

bullet_list = []
bullet_speed = 10
bullet_cooldown = 200
last_shot = 0

# ==========================================
# SCORE AND FONTS
# ==========================================

score = 0
font = pygame.font.SysFont(None, 32)
large_font = pygame.font.SysFont(None, 65)

game_over = False
running = True

# ==========================================
# FUNCTIONS
# ==========================================

def fire_bullet():
    global last_shot

    current_time = pygame.time.get_ticks()

    if current_time - last_shot >= bullet_cooldown:
        bullet_x = (
            player_x + player_image.get_width() // 2
            - bullet_image.get_width() // 2
        )

        bullet_y = player_y - bullet_image.get_height()

        bullet = pygame.Rect(
            bullet_x,
            bullet_y,
            bullet_image.get_width(),
            bullet_image.get_height()
        )

        bullet_list.append(bullet)
        last_shot = current_time

        if laser_sound:
            laser_sound.play()


def reset_game():
    global player_x, score, game_over
    global spawn_counter, last_shot

    player_x = (
        WINDOW_WIDTH // 2 - player_image.get_width() // 2
    )

    score = 0
    game_over = False
    spawn_counter = 0
    last_shot = 0

    enemy_list.clear()
    bullet_list.clear()


# ==========================================
# MAIN GAME LOOP
# ==========================================

while running:

    clock.tick(60)

    # Handle events
    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:
                running = False

            if event.key == pygame.K_SPACE and not game_over:
                fire_bullet()

            if event.key == pygame.K_r and game_over:
                reset_game()

    if not running:
        break

    keys = pygame.key.get_pressed()

    if not game_over:

        # Move player
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            player_x -= player_speed

        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            player_x += player_speed

        player_x = max(
            0,
            min(
                player_x,
                WINDOW_WIDTH - player_image.get_width()
            )
        )

        # Hold Space to shoot
        if keys[pygame.K_SPACE]:
            fire_bullet()

        # Spawn enemies
        spawn_counter += 1

        if spawn_counter >= enemy_spawn_time:
            spawn_counter = 0

            enemy_x = random.randint(
                0,
                WINDOW_WIDTH - enemy_image.get_width()
            )

            enemy = pygame.Rect(
                enemy_x,
                -enemy_image.get_height(),
                enemy_image.get_width(),
                enemy_image.get_height()
            )

            enemy_list.append(enemy)

        # Move enemies
        for enemy in enemy_list[:]:
            enemy.y += enemy_speed

            if enemy.top > WINDOW_HEIGHT:
                enemy_list.remove(enemy)

        # Move bullets
        for bullet in bullet_list[:]:
            bullet.y -= bullet_speed

            if bullet.bottom < 0:
                bullet_list.remove(bullet)

        # Check bullet/enemy collisions
        for enemy in enemy_list[:]:

            for bullet in bullet_list[:]:

                if enemy.colliderect(bullet):

                    if enemy in enemy_list:
                        enemy_list.remove(enemy)

                    if bullet in bullet_list:
                        bullet_list.remove(bullet)

                    score += 10

                    if explosion_sound:
                        explosion_sound.play()

                    break

        # Check player/enemy collisions
        player_rect = pygame.Rect(
            player_x,
            player_y,
            player_image.get_width(),
            player_image.get_height()
        )

        for enemy in enemy_list:

            if player_rect.colliderect(enemy):
                game_over = True
                break

    # ======================================
    # DRAW GAME
    # ======================================

    # Draw background FIRST
    window.blit(background, (0, 0))

    # Draw player
    window.blit(
        player_image,
        (player_x, player_y)
    )

    # Draw enemies
    for enemy in enemy_list:
        window.blit(enemy_image, enemy)

    # Draw bullets
    for bullet in bullet_list:
        window.blit(bullet_image, bullet)

    # Draw score
    score_text = font.render(
        f"Score: {score}",
        True,
        (255, 255, 255)
    )

    window.blit(score_text, (15, 15))

    # Game Over screen
    if game_over:

        overlay = pygame.Surface(
            (WINDOW_WIDTH, WINDOW_HEIGHT),
            pygame.SRCALPHA
        )

        overlay.fill((0, 0, 0, 170))
        window.blit(overlay, (0, 0))

        game_over_text = large_font.render(
            "GAME OVER",
            True,
            (255, 60, 60)
        )

        final_score_text = font.render(
            f"Final Score: {score}",
            True,
            (255, 255, 255)
        )

        restart_text = font.render(
            "Press R to Restart",
            True,
            (255, 255, 255)
        )

        window.blit(
            game_over_text,
            game_over_text.get_rect(
                center=(WINDOW_WIDTH // 2, 230)
            )
        )

        window.blit(
            final_score_text,
            final_score_text.get_rect(
                center=(WINDOW_WIDTH // 2, 310)
            )
        )

        window.blit(
            restart_text,
            restart_text.get_rect(
                center=(WINDOW_WIDTH // 2, 360)
            )
        )

    pygame.display.flip()

# Clean exit
pygame.quit()
sys.exit()
