
import pygame
import random
import math
import json
import sys
from pathlib import Path

# -------------------------------
# DUSO SPACE SHOOTER v1.1
# -------------------------------

pygame.init()

WIDTH, HEIGHT = 800, 600
FPS = 60

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Duso Space Shooter v1.1")
clock = pygame.time.Clock()

RED = (255, 55, 65)
WHITE = (255, 255, 255)
YELLOW = (255, 220, 60)
GREEN = (70, 255, 110)
BLUE = (60, 170, 255)
BLACK = (8, 10, 25)

font = pygame.font.SysFont("arial", 24, bold=True)
small_font = pygame.font.SysFont("arial", 18, bold=True)
big_font = pygame.font.SysFont("arial", 48, bold=True)

BASE = Path(
    getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
)

SCORE_FILE = Path.home() / ".duso_space_shooter_score.json"


def load_image(filename, size, color=BLUE):
    try:
        img = pygame.image.load(str(BASE / filename)).convert_alpha()
        return pygame.transform.smoothscale(img, size)
    except (pygame.error, OSError):
        img = pygame.Surface(size, pygame.SRCALPHA)
        img.fill(color)
        pygame.draw.rect(img, WHITE, img.get_rect(), 2)
        return img


def load_sound(filename):
    try:
        return pygame.mixer.Sound(str(BASE / filename))
    except (pygame.error, OSError):
        return None


def play_sound(sound):
    if sound and not muted:
        sound.set_volume(music_volume)
        sound.play()


def draw_text(message, x, y, color=RED, size="normal"):
    selected = {
        "small": small_font,
        "normal": font,
        "big": big_font
    }[size]

    shadow = selected.render(message, True, BLACK)
    image = selected.render(message, True, color)

    screen.blit(shadow, (x + 2, y + 2))
    screen.blit(image, (x, y))


def read_high_score():
    try:
        return int(json.loads(
            SCORE_FILE.read_text()
        ).get("score", 0))
    except (OSError, ValueError, TypeError):
        return 0


def save_high_score(value):
    try:
        SCORE_FILE.write_text(json.dumps({"score": value}))
    except OSError:
        pass


# -------------------------------
# GAME IMAGES
# -------------------------------

player_images = [
    load_image("player_blue.png", (60, 60)),
    load_image("player_red.png", (60, 60), RED),
    load_image("player_gold.png", (60, 60), YELLOW)
]

enemy_images = [
    load_image("enemy_green.png", (45, 45), GREEN),
    load_image("enemy_purple.png", (45, 45), RED),
    load_image("enemy_red.png", (45, 45), RED)
]

boss_image = load_image("boss.png", (150, 110), RED)

backgrounds = [
    load_image("galaxy_blue.png", (WIDTH, HEIGHT)),
    load_image("galaxy_purple.png", (WIDTH, HEIGHT)),
    load_image("galaxy_red.png", (WIDTH, HEIGHT))
]

laser_image = load_image("laser_blue.png", (10, 28), BLUE)

# -------------------------------
# MUSIC AND SOUND
# -------------------------------

music_volume = 0.35
muted = False

laser_sound = load_sound("lazer.wav")
explosion_sound = load_sound("HeliExplode.wav")

try:
    pygame.mixer.music.load(
        str(BASE / "ovey T ft shota duso.mp3")
    )
    pygame.mixer.music.set_volume(music_volume)
    pygame.mixer.music.play(-1)
except (pygame.error, OSError):
    print("Background music unavailable.")


def update_volume():
    pygame.mixer.music.set_volume(
        0 if muted else music_volume
    )


def change_volume(amount):
    global music_volume

    music_volume = max(
        0.0, min(1.0, round(music_volume + amount, 2))
    )
    update_volume()


# -------------------------------
# GAME STATE
# -------------------------------

high_score = read_high_score()

selected_ship = 0
game_state = "menu"

player = pygame.Rect(370, 500, 60, 60)

score = 0
level = 1
lives = 3
health = 100
shield = 0
weapon_level = 1

enemies = []
bullets = []
enemy_bullets = []
particles = []
powerups = []

boss = None
boss_health = 0
boss_max_health = 0

kills_this_level = 0
spawn_timer = 0
last_shot = 0
invincible_until = 0


def reset_game():
    global score, level, lives, health, shield
    global weapon_level, boss, boss_health
    global kills_this_level, spawn_timer
    global invincible_until, game_state

    score = 0
    level = 1
    lives = 3
    health = 100
    shield = 0
    weapon_level = 1

    boss = None
    boss_health = 0

    kills_this_level = 0
    spawn_timer = 0
    invincible_until = pygame.time.get_ticks() + 1500

    enemies.clear()
    bullets.clear()
    enemy_bullets.clear()
    particles.clear()
    powerups.clear()

    player.centerx = WIDTH // 2
    player.bottom = HEIGHT - 20

    game_state = "playing"


def explosion(x, y, color=RED):
    for _ in range(20):
        particles.append({
            "x": float(x),
            "y": float(y),
            "vx": random.uniform(-5, 5),
            "vy": random.uniform(-5, 5),
            "life": random.randint(15, 35),
            "color": color
        })

    play_sound(explosion_sound)


def spawn_enemy():
    image_index = random.randrange(len(enemy_images))

    enemies.append({
        "rect": pygame.Rect(
            random.randint(0, WIDTH - 45),
            -50,
            45,
            45
        ),
        "image": image_index,
        "speed": min(7, 2 + level * 0.25)
    })


def shoot():
    global last_shot

    now = pygame.time.get_ticks()
    cooldown = max(110, 320 - weapon_level * 45)

    if now - last_shot < cooldown:
        return

    last_shot = now

    if weapon_level == 1:
        offsets = [0]
    elif weapon_level == 2:
        offsets = [-15, 15]
    else:
        offsets = [-22, 0, 22]

    for offset in offsets:
        bullets.append(
            pygame.Rect(
                player.centerx + offset - 5,
                player.top - 25,
                10,
                28
            )
        )

    play_sound(laser_sound)


def player_hit():
    global lives, health, shield
    global invincible_until, game_state

    now = pygame.time.get_ticks()

    if now < invincible_until:
        return

    if shield > 0:
        shield -= 1
        invincible_until = now + 900
        return

    explosion(player.centerx, player.centery, BLUE)

    lives -= 1
    health = 100

    player.centerx = WIDTH // 2
    player.bottom = HEIGHT - 20

    invincible_until = now + 2000

    if lives <= 0:
        game_state = "gameover"


def defeat_enemy(enemy):
    global score, kills_this_level, high_score

    explosion(enemy["rect"].centerx, enemy["rect"].centery)

    score += 10
    kills_this_level += 1

    if score > high_score:
        high_score = score
        save_high_score(high_score)

    if random.random() < 0.12:
        powerups.append({
            "rect": pygame.Rect(
                enemy["rect"].centerx - 12,
                enemy["rect"].centery,
                24,
                24
            ),
            "type": random.choice([
                "health", "shield", "life", "weapon"
            ])
        })


def next_level():
    global level, kills_this_level, health
    global boss, boss_health, boss_max_health

    level += 1
    kills_this_level = 0
    health = min(100, health + 20)

    enemies.clear()
    enemy_bullets.clear()

    if level % 5 == 0:
        boss = pygame.Rect(WIDTH // 2 - 75, 35, 150, 110)
        boss_max_health = 20 + level * 5
        boss_health = boss_max_health
    else:
        boss = None


def update_game():
    global spawn_timer, boss, boss_health
    global score, high_score, kills_this_level
    global health, lives, shield, weapon_level
    global game_state

    keys = pygame.key.get_pressed()

    speed = 5

    if keys[pygame.K_LEFT] or keys[pygame.K_a]:
        player.x -= speed
    if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
        player.x += speed
    if keys[pygame.K_UP] or keys[pygame.K_w]:
        player.y -= speed
    if keys[pygame.K_DOWN] or keys[pygame.K_s]:
        player.y += speed

    player.clamp_ip(screen.get_rect())

    if keys[pygame.K_SPACE]:
        shoot()

    # Enemy spawning
    if boss is None:
        spawn_timer += 1

        if spawn_timer >= max(15, 60 - level * 3):
            spawn_enemy()
            spawn_timer = 0

    # Player lasers
    for bullet in bullets[:]:
        bullet.y -= 10

        if bullet.bottom < 0:
            bullets.remove(bullet)
            continue

        hit = False

        for enemy in enemies[:]:
            if bullet.colliderect(enemy["rect"]):
                enemies.remove(enemy)
                defeat_enemy(enemy)
                hit = True
                break

        if boss is not None and bullet.colliderect(boss):
            boss_health -= 1
            hit = True

            if boss_health <= 0:
                explosion(boss.centerx, boss.centery, YELLOW)
                boss = None

                score += 250
                if score > high_score:
                    high_score = score
                    save_high_score(high_score)

                next_level()

        if hit and bullet in bullets:
            bullets.remove(bullet)

    # Enemy movement and collision
    for enemy in enemies[:]:
        enemy["rect"].y += int(max(1, enemy["speed"]))

        if enemy["rect"].top > HEIGHT:
            enemies.remove(enemy)
            continue

        if enemy["rect"].colliderect(player):
            enemies.remove(enemy)
            player_hit()

    # Boss movement and collision
    if boss is not None:
        boss.x += int(math.sin(
            pygame.time.get_ticks() / 400
        ) * 3)

        boss.clamp_ip(screen.get_rect())

        if boss.colliderect(player):
            player_hit()

        if random.random() < 0.025:
            enemy_bullets.append(
                pygame.Rect(boss.centerx, boss.bottom, 12, 20)
            )

    # Enemy lasers
    for bullet in enemy_bullets[:]:
        bullet.y += 6

        if bullet.top > HEIGHT:
            enemy_bullets.remove(bullet)
        elif bullet.colliderect(player):
            enemy_bullets.remove(bullet)
            player_hit()

    # Power-ups
    for item in powerups[:]:
        item["rect"].y += 3

        if item["rect"].top > HEIGHT:
            powerups.remove(item)
            continue

        if item["rect"].colliderect(player):
            kind = item["type"]

            if kind == "health":
                health = min(100, health + 30)
            elif kind == "shield":
                shield = min(5, shield + 1)
            elif kind == "life":
                lives = min(9, lives + 1)
            elif kind == "weapon":
                weapon_level = min(3, weapon_level + 1)

            powerups.remove(item)

    # Explosion particles
    for particle in particles[:]:
        particle["x"] += particle["vx"]
        particle["y"] += particle["vy"]
        particle["life"] -= 1

        if particle["life"] <= 0:
            particles.remove(particle)

    # Advance to next level
    if boss is None and kills_this_level >= 10:
        next_level()


def draw_game():
    background_index = ((level - 1) // 5) % len(backgrounds)
    screen.blit(backgrounds[background_index], (0, 0))

    for enemy in enemies:
        screen.blit(
            enemy_images[enemy["image"]],
            enemy["rect"]
        )

    for bullet in bullets:
        screen.blit(laser_image, bullet)

    for bullet in enemy_bullets:
        pygame.draw.rect(screen, RED, bullet)

    if boss is not None:
        screen.blit(boss_image, boss)

        pygame.draw.rect(
            screen, RED, (250, 12, 300, 15), 2
        )
        pygame.draw.rect(
            screen, GREEN,
            (
                252, 14,
                int(296 * boss_health / boss_max_health),
                11
            )
        )

    for item in powerups:
        color = {
            "health": GREEN,
            "shield": BLUE,
            "life": YELLOW,
            "weapon": RED
        }[item["type"]]

        pygame.draw.ellipse(screen, color, item["rect"])

    for particle in particles:
        pygame.draw.circle(
            screen,
            particle["color"],
            (int(particle["x"]), int(particle["y"])),
            3
        )

    # Flash during respawn protection
    now = pygame.time.get_ticks()

    if now >= invincible_until or (now // 120) % 2 == 0:
        screen.blit(player_images[selected_ship], player)

    draw_text(f"SCORE: {score}", 12, 10)
    draw_text(f"LEVEL: {level}", 12, 40)
    draw_text(f"LIVES: {lives}", 12, 70)
    draw_text(f"SHIELD: {shield}", 12, 100)

    draw_text(f"HP: {health}%", WIDTH - 145, 10)
    draw_text(
        f"VOL: {int(music_volume * 100)}%",
        WIDTH - 145, 40
    )
    draw_text(f"WEAPON: {weapon_level}", WIDTH - 170, 70)

    if muted:
        draw_text("MUTED", WIDTH - 145, 100)


def draw_menu():
    screen.blit(backgrounds[0], (0, 0))

    draw_text(
        "DUSO SPACE SHOOTER",
        125, 90, RED, "big"
    )
    draw_text("VERSION 1.1", 325, 155, YELLOW)

    screen.blit(
        player_images[selected_ship],
        (WIDTH // 2 - 30, 225)
    )

    draw_text("LEFT / RIGHT: SELECT SHIP", 240, 320)
    draw_text("ENTER: START GAME", 280, 360)
    draw_text("SPACE: FIRE", 315, 400)
    draw_text("+ / - : MUSIC VOLUME", 270, 440)
    draw_text(
        f"MUSIC VOLUME: {int(music_volume * 100)}%",
        260, 480
    )


def draw_game_over():
    screen.blit(backgrounds[2], (0, 0))

    draw_text("GAME OVER", 255, 150, RED, "big")
    draw_text(f"SCORE: {score}", 315, 245)
    draw_text(f"HIGH SCORE: {high_score}", 265, 285)
    draw_text("C: CONTINUE WITH 3 LIVES", 220, 350)
    draw_text("R: RESTART", 310, 390)
    draw_text("M: MAIN MENU", 290, 430)


def continue_game():
    global lives, health, game_state, invincible_until

    lives = 3
    health = 100

    player.centerx = WIDTH // 2
    player.bottom = HEIGHT - 20

    enemies.clear()
    enemy_bullets.clear()

    invincible_until = pygame.time.get_ticks() + 2000
    game_state = "playing"


# -------------------------------
# MAIN GAME LOOP
# -------------------------------

running = True

while running:
    clock.tick(FPS)

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_ESCAPE:
                if game_state == "playing":
                    game_state = "paused"
                elif game_state == "paused":
                    game_state = "playing"
                else:
                    running = False

            # Volume controls
            if event.key in (
                pygame.K_EQUALS,
                pygame.K_PLUS,
                pygame.K_KP_PLUS
            ):
                change_volume(0.05)

            if event.key in (
                pygame.K_MINUS,
                pygame.K_KP_MINUS
            ):
                change_volume(-0.05)

            if event.key == pygame.K_v:
                muted = not muted
                update_volume()

            if game_state == "menu":

                if event.key == pygame.K_LEFT:
                    selected_ship = (
                        selected_ship - 1
                    ) % len(player_images)

                if event.key == pygame.K_RIGHT:
                    selected_ship = (
                        selected_ship + 1
                    ) % len(player_images)

                if event.key == pygame.K_RETURN:
                    reset_game()

            elif game_state == "playing":

                if event.key == pygame.K_p:
                    game_state = "paused"

            elif game_state == "paused":

                if event.key in (
                    pygame.K_p,
                    pygame.K_RETURN
                ):
                    game_state = "playing"

            elif game_state == "gameover":

                if event.key == pygame.K_c:
                    continue_game()

                elif event.key == pygame.K_r:
                    reset_game()

                elif event.key == pygame.K_m:
                    game_state = "menu"

    if game_state == "playing":
        update_game()
        draw_game()

    elif game_state == "menu":
        draw_menu()

    elif game_state == "paused":
        draw_game()
        draw_text("PAUSED", 300, 260, RED, "big")
        draw_text("P: RESUME", 320, 330)

    elif game_state == "gameover":
        draw_game_over()

    pygame.display.flip()

pygame.quit()
sys.exit()
