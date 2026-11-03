"""Duso Space Shooter v2.2 — standalone Pygame upgrade.
Place beside your PNG, MP3, and WAV files and run with Python 3.11 + pygame.
"""
import json
import math
import os
import random
import sys
from pathlib import Path

import pygame

WIDTH, HEIGHT, FPS = 800, 600, 60
RED = (255, 65, 75)
WHITE = (255, 255, 255)
GOLD = (255, 213, 72)
DARK = (15, 10, 28)
PLAYER_SIZE = (64, 64)
ENEMY_SIZE = (48, 48)
BOSS_SIZE = (160, 120)
INVULNERABLE_MS = 2000
START_LIVES = 3
KILLS_PER_LEVEL = 10


def resource_path(name):
    base = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    return base / name


def score_path():
    root = Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'DusoSpaceShooter'
    root.mkdir(parents=True, exist_ok=True)
    return root / 'highscore.json'


def read_highscore():
    try:
        return max(0, int(json.loads(score_path().read_text()).get('highscore', 0)))
    except (OSError, ValueError, TypeError, AttributeError):
        return 0


def write_highscore(value):
    try:
        score_path().write_text(json.dumps({'highscore': int(value)}))
    except OSError as exc:
        print('Could not save high score:', exc)


pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Duso Space Shooter v2.2')
clock = pygame.time.Clock()
font = pygame.font.SysFont('arial', 23, bold=True)
small = pygame.font.SysFont('arial', 17, bold=True)
big = pygame.font.SysFont('arial', 48, bold=True)


def image(name, size, alpha=True):
    path = resource_path(name)
    try:
        loaded = pygame.image.load(str(path))
        loaded = loaded.convert_alpha() if alpha else loaded.convert()
        return pygame.transform.smoothscale(loaded, size)
    except (pygame.error, OSError) as exc:
        print('Image unavailable:', path, exc)
        fallback = pygame.Surface(size, pygame.SRCALPHA)
        fallback.fill((70, 100, 160, 255))
        pygame.draw.rect(fallback, RED, fallback.get_rect(), 2)
        return fallback


players = [image(n, PLAYER_SIZE) for n in ('player_blue.png', 'player_red.png', 'player_gold.png')]
enemy_sprites = [image(n, ENEMY_SIZE) for n in ('enemy_green.png', 'enemy_purple.png', 'enemy_red.png')]
boss_sprite = image('boss.png', BOSS_SIZE)
lasers = [image(n, (12, 28)) for n in ('laser_blue.png', 'laser_green.png', 'laser_orange.png')]
backgrounds = [image(n, (WIDTH, HEIGHT), False) for n in ('galaxy_blue.png', 'galaxy_purple.png', 'galaxy_red.png')]
menu_bg = image('menu_background.png', (WIDTH, HEIGHT), False)
over_bg = image('game_over_background.png', (WIDTH, HEIGHT), False)
pickup_sprites = {name: image(name + '.png', (32, 32)) for name in ('health', 'shield', 'extra_life', 'weapon_upgrade', 'speed_boost')}
try:
    pygame.display.set_icon(players[0])
except pygame.error:
    pass

sounds = {}
try:
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    for key, filename in [('laser', 'lazer.wav'), ('explosion', 'HeliExplode.wav')]:
        try:
            sounds[key] = pygame.mixer.Sound(str(resource_path(filename)))
            sounds[key].set_volume(0.35 if key == 'laser' else 0.55)
        except (OSError, pygame.error) as exc:
            print('Sound unavailable:', filename, exc)
    for song in ('ovey T ft shota duso.mp3', 'Ovey T Shota Duso.mp3'):
        if resource_path(song).is_file():
            pygame.mixer.music.load(str(resource_path(song)))
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)
            break
except (OSError, pygame.error) as exc:
    print('Audio unavailable:', exc)


def play(key):
    if key in sounds:
        sounds[key].play()


def label(text, center, face=font, color=RED):
    # Black shadow improves readability on bright galaxy images.
    shadow = face.render(str(text), True, DARK)
    ink = face.render(str(text), True, color)
    rect = ink.get_rect(center=center)
    screen.blit(shadow, rect.move(2, 2))
    screen.blit(ink, rect)


ship_choice = 0
highscore = read_highscore()
state = 'menu'
muted = False
particles = []


def start_game():
    global state, player, score, level, kills_in_level, lives, health
    global enemies, bullets, enemy_bullets, pickups, boss, last_shot, last_spawn
    global invulnerable_until, weapon_level, speed_boost_until, shield, level_banner_until
    player = pygame.Rect(WIDTH // 2 - 32, HEIGHT - 110, *PLAYER_SIZE)
    score, level, kills_in_level = 0, 1, 0
    lives, health, shield = START_LIVES, 100, False
    enemies, bullets, enemy_bullets, pickups = [], [], [], []
    boss = None
    last_shot = last_spawn = pygame.time.get_ticks()
    invulnerable_until = pygame.time.get_ticks() + 1200
    weapon_level = 1
    speed_boost_until = 0
    level_banner_until = pygame.time.get_ticks() + 1400
    particles.clear()
    state = 'playing'


def explode(x, y, count=22):
    for _ in range(count):
        angle = random.random() * math.tau
        speed = random.uniform(1.5, 5)
        particles.append([float(x), float(y), math.cos(angle) * speed,
                          math.sin(angle) * speed, random.randint(14, 28)])
    play('explosion')


def lose_life():
    global lives, health, invulnerable_until, state, shield, highscore
    now = pygame.time.get_ticks()
    if now < invulnerable_until:
        return
    if shield:
        shield = False
        invulnerable_until = now + 1000
        explode(player.centerx, player.centery, 10)
        return
    lives -= 1
    explode(player.centerx, player.centery)
    # Remove nearby enemies and hostile bullets to create a safe respawn area.
    enemies[:] = [e for e in enemies if abs(e['rect'].centerx - WIDTH // 2) > 125 or e['rect'].y < HEIGHT - 230]
    enemy_bullets.clear()
    player.centerx = WIDTH // 2
    player.bottom = HEIGHT - 35
    health = 100
    invulnerable_until = now + INVULNERABLE_MS
    if lives <= 0:
        state = 'game_over'
        if score > highscore:
            highscore = score
            write_highscore(highscore)


def add_score(points):
    global score, highscore
    score += points
    if score > highscore:
        highscore = score
        write_highscore(highscore)


def spawn_enemy():
    kind = random.randrange(3)
    rect = pygame.Rect(random.randrange(0, WIDTH - 48), -48, *ENEMY_SIZE)
    enemies.append({'rect': rect, 'kind': kind, 'hp': 1 + level // 7,
                    'speed': min(7.0, 2.0 + level * 0.24 + random.random())})


def spawn_boss():
    global boss
    hp = 15 + level * 4
    boss = {'rect': pygame.Rect(WIDTH // 2 - 80, -120, *BOSS_SIZE),
            'hp': hp, 'max_hp': hp, 'direction': 1, 'last_fire': pygame.time.get_ticks()}


def level_up():
    global level, kills_in_level, health, level_banner_until
    level += 1
    kills_in_level = 0
    health = min(100, health + 25)
    level_banner_until = pygame.time.get_ticks() + 1800
    if level % 5 == 0:
        enemies.clear()
        spawn_boss()


def enemy_defeated(rect, boss_kill=False):
    global kills_in_level
    explode(rect.centerx, rect.centery, 10 if not boss_kill else 40)
    add_score(150 if boss_kill else 10)
    if random.random() < (0.85 if boss_kill else 0.09):
        kind = random.choice(list(pickup_sprites))
        pickups.append({'rect': pygame.Rect(rect.centerx - 16, rect.centery - 16, 32, 32), 'kind': kind})
    kills_in_level += 1 if not boss_kill else KILLS_PER_LEVEL
    if kills_in_level >= KILLS_PER_LEVEL:
        level_up()


def shoot(now):
    global last_shot
    cooldown = 125 if weapon_level >= 3 else 205
    if now - last_shot < cooldown:
        return
    last_shot = now
    count = 1 if weapon_level == 1 else (2 if weapon_level == 2 else 3)
    for offset in ({1: [0], 2: [-15, 15], 3: [-22, 0, 22]}[count]):
        rect = pygame.Rect(player.centerx + offset - 6, player.top - 20, 12, 28)
        bullets.append({'rect': rect, 'damage': 2 if weapon_level >= 4 else 1})
    play('laser')


def apply_pickup(kind):
    global health, lives, shield, weapon_level, speed_boost_until
    if kind == 'health':
        health = min(100, health + 40)
    elif kind == 'extra_life':
        lives = min(9, lives + 1)
    elif kind == 'shield':
        shield = True
    elif kind == 'weapon_upgrade':
        weapon_level = min(4, weapon_level + 1)
    elif kind == 'speed_boost':
        speed_boost_until = pygame.time.get_ticks() + 8000


start_game()
state = 'menu'
running = True
while running:
    dt = clock.tick(FPS) / 1000
    now = pygame.time.get_ticks()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if state == 'playing':
                    state = 'paused'
                elif state == 'paused':
                    state = 'playing'
                else:
                    running = False
            elif event.key == pygame.K_m and state in ('game_over', 'paused'):
                state = 'menu'
            elif event.key == pygame.K_v:
                muted = not muted
                if pygame.mixer.get_init():
                    pygame.mixer.music.set_volume(0 if muted else 0.35)
                    for key, sound in sounds.items():
                        sound.set_volume(0 if muted else (0.35 if key == 'laser' else 0.55))
            elif state == 'menu':
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    ship_choice = (ship_choice - 1) % len(players)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    ship_choice = (ship_choice + 1) % len(players)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    start_game()
            elif state == 'playing' and event.key == pygame.K_p:
                state = 'paused'
            elif state == 'paused' and event.key in (pygame.K_p, pygame.K_RETURN):
                state = 'playing'
            elif state == 'game_over':
                if event.key == pygame.K_r:
                    start_game()
                elif event.key == pygame.K_c:
                    # Continue at the same level, score and weapon tier, with fresh lives.
                    lives = START_LIVES
                    health = 100
                    shield = False
                    player.center = (WIDTH // 2, HEIGHT - 75)
                    enemies.clear()
                    enemy_bullets.clear()
                    bullets.clear()
                    invulnerable_until = now + INVULNERABLE_MS
                    state = 'playing'

    if state == 'playing':
        keys = pygame.key.get_pressed()
        dx = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = int(keys[pygame.K_DOWN] or keys[pygame.K_s]) - int(keys[pygame.K_UP] or keys[pygame.K_w])
        magnitude = math.hypot(dx, dy) or 1
        speed = 8 if now < speed_boost_until else 5
        player.x += round(dx / magnitude * speed)
        player.y += round(dy / magnitude * speed)
        player.clamp_ip(screen.get_rect())
        if keys[pygame.K_SPACE]:
            shoot(now)

        if boss is None:
            interval = max(260, 950 - level * 48)
            if now - last_spawn >= interval:
                last_spawn = now
                spawn_enemy()

        for e in enemies[:]:
            e['rect'].y += round(e['speed'])
            if e['rect'].top > HEIGHT:
                enemies.remove(e)
            elif e['rect'].colliderect(player):
                enemies.remove(e)
                lose_life()
                if state != 'playing':
                    break

        if state == 'playing' and boss:
            r = boss['rect']
            if r.y < 35:
                r.y += 2
            else:
                r.x += boss['direction'] * min(5, 2 + level // 4)
                if r.left <= 0 or r.right >= WIDTH:
                    boss['direction'] *= -1
                    r.clamp_ip(screen.get_rect())
            if now - boss['last_fire'] >= max(450, 1200 - level * 25):
                boss['last_fire'] = now
                for off in (-35, 0, 35):
                    enemy_bullets.append(pygame.Rect(r.centerx + off - 5, r.bottom, 10, 24))
            if r.colliderect(player):
                lose_life()

        for hostile in enemy_bullets[:]:
            hostile.y += 6 + level // 5
            if hostile.top > HEIGHT:
                enemy_bullets.remove(hostile)
            elif hostile.colliderect(player):
                enemy_bullets.remove(hostile)
                lose_life()

        for bullet in bullets[:]:
            bullet['rect'].y -= 11
            rect = bullet['rect']
            if rect.bottom < 0:
                bullets.remove(bullet)
                continue
            hit = False
            if boss and rect.colliderect(boss['rect']):
                boss['hp'] -= bullet['damage']
                hit = True
                if boss['hp'] <= 0:
                    dead_rect = boss['rect'].copy()
                    boss = None
                    enemy_defeated(dead_rect, boss_kill=True)
            if not hit:
                for e in enemies[:]:
                    if rect.colliderect(e['rect']):
                        e['hp'] -= bullet['damage']
                        hit = True
                        if e['hp'] <= 0:
                            enemies.remove(e)
                            enemy_defeated(e['rect'])
                        break
            if hit and bullet in bullets:
                bullets.remove(bullet)

        for pickup in pickups[:]:
            pickup['rect'].y += 3
            if pickup['rect'].top > HEIGHT:
                pickups.remove(pickup)
            elif pickup['rect'].colliderect(player):
                apply_pickup(pickup['kind'])
                pickups.remove(pickup)

    # Update particle animation even when showing game over.
    for particle in particles[:]:
        particle[0] += particle[2]
        particle[1] += particle[3]
        particle[4] -= 1
        if particle[4] <= 0:
            particles.remove(particle)

    if state == 'menu':
        screen.blit(menu_bg, (0, 0))
        label('DUSO SPACE SHOOTER 2.2', (WIDTH // 2, 125), big)
        screen.blit(players[ship_choice], (WIDTH // 2 - 32, 215))
        label('LEFT / RIGHT: Select spaceship', (WIDTH // 2, 325))
        label('ENTER or SPACE: Start game', (WIDTH // 2, 370))
        label('Arrows / WASD: Move   SPACE: Shoot   P: Pause', (WIDTH // 2, 425), small)
        label('V: Mute / Unmute   ESC: Exit', (WIDTH // 2, 455), small)
        label(f'High Score: {highscore}', (WIDTH // 2, 525))
    elif state == 'game_over':
        screen.blit(over_bg, (0, 0))
        label('GAME OVER', (WIDTH // 2, 180), big)
        label(f'Score: {score}    High Score: {highscore}', (WIDTH // 2, 275))
        label(f'Level Reached: {level}', (WIDTH // 2, 325))
        label('C: Continue   R: Restart   M: Main Menu', (WIDTH // 2, 420))
        label('ESC: Exit', (WIDTH // 2, 465), small)
    else:
        bg_index = ((level - 1) // 3) % len(backgrounds)
        screen.blit(backgrounds[bg_index], (0, 0))
        for e in enemies:
            screen.blit(enemy_sprites[e['kind']], e['rect'])
        if boss:
            screen.blit(boss_sprite, boss['rect'])
            bar = pygame.Rect(boss['rect'].x, boss['rect'].y - 15, BOSS_SIZE[0], 9)
            pygame.draw.rect(screen, DARK, bar)
            pygame.draw.rect(screen, RED, (bar.x, bar.y, int(bar.w * max(0, boss['hp']) / boss['max_hp']), bar.h))
        for b in bullets:
            screen.blit(lasers[min(2, weapon_level - 1)], b['rect'])
        for b in enemy_bullets:
            pygame.draw.rect(screen, GOLD, b, border_radius=3)
        for pickup in pickups:
            screen.blit(pickup_sprites[pickup['kind']], pickup['rect'])
        if now >= invulnerable_until or (now // 130) % 2 == 0:
            screen.blit(players[ship_choice], player)
            if shield:
                pygame.draw.circle(screen, (90, 190, 255), player.center, 39, 3)
        for px, py, _, _, life in particles:
            pygame.draw.circle(screen, GOLD if life % 2 else RED, (int(px), int(py)), max(1, life // 8))
        label(f'Score: {score}   High: {highscore}', (155, 22), small)
        label(f'Level: {level}   Lives: {lives}', (WIDTH - 120, 22), small)
        pygame.draw.rect(screen, DARK, (15, 48, 170, 15))
        pygame.draw.rect(screen, RED, (15, 48, int(170 * health / 100), 15))
        label(f'HP {health}  Weapon {weapon_level}', (113, 78), small)
        if now < level_banner_until:
            label(f'LEVEL {level}' + (' — BOSS!' if level % 5 == 0 else ''), (WIDTH // 2, 140), big)
        if state == 'paused':
            shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            shade.fill((0, 0, 0, 170))
            screen.blit(shade, (0, 0))
            label('PAUSED', (WIDTH // 2, 250), big)
            label('P or ENTER: Resume   M: Main Menu', (WIDTH // 2, 330))

    pygame.display.flip()

pygame.quit()
sys.exit()
