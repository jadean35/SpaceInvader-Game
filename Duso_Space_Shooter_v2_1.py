"""Duso Space Shooter v2.1 — level continuation and red interface."""
import json
import math
import random
import sys
from pathlib import Path

import pygame

WIDTH, HEIGHT, FPS = 800, 600, 60
ASSETS = Path('Duso_Space_Shooter_v2_Assets')


def resource_path(name):
    base = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
    return base / name


def writable_score_path():
    # Keep saved scores outside the bundled app (also works when packaged).
    import os
    folder = Path(os.environ.get('LOCALAPPDATA') or Path.home()) / 'DusoSpaceShooter'
    folder.mkdir(parents=True, exist_ok=True)
    return folder / 'highscore.json'


pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Duso Space Shooter v2.1')
clock = pygame.time.Clock()
RED = (255, 65, 65)
font = pygame.font.SysFont('arial', 24, bold=True)
small = pygame.font.SysFont('arial', 18)
big = pygame.font.SysFont('arial', 52, bold=True)


def image(name, size, alpha=True):
    path = resource_path(name)
    try:
        img = pygame.image.load(str(path))
        img = img.convert_alpha() if alpha else img.convert()
        return pygame.transform.smoothscale(img, size)
    except (pygame.error, OSError) as exc:
        print(f'Could not load {path}: {exc}')
        placeholder = pygame.Surface(size, pygame.SRCALPHA)
        placeholder.fill((60, 120, 220, 220))
        pygame.draw.rect(placeholder, 'white', placeholder.get_rect(), 2)
        return placeholder


ships = [image(f'player_{c}.png', (64, 64)) for c in ('blue', 'red', 'gold')]
enemies = [image(f'enemy_{c}.png', (48, 48)) for c in ('green', 'purple', 'red')]
boss_img = image('boss.png', (160, 120))
lasers = [image(f'laser_{c}.png', (12, 28)) for c in ('blue', 'orange', 'green')]
backgrounds = [image(f'galaxy_{c}.png', (WIDTH, HEIGHT), False) for c in ('blue', 'purple', 'red')]
menu_bg = image('menu_background.png', (WIDTH, HEIGHT), False)
over_bg = image('game_over_background.png', (WIDTH, HEIGHT), False)
power_imgs = {k: image(f'{k}.png', (32, 32)) for k in ('health', 'shield', 'extra_life', 'weapon_upgrade', 'speed_boost')}
pygame.display.set_icon(ships[0])

laser_sfx = explosion_sfx = None
try:
    if not pygame.mixer.get_init():
        pygame.mixer.init()
    pygame.mixer.music.load(str(resource_path('ovey T ft shota duso.mp3')))
    pygame.mixer.music.set_volume(0.35)
    pygame.mixer.music.play(-1)
except (pygame.error, OSError) as exc:
    print('Music unavailable:', exc)
for filename, name, volume in [('lazer.wav', 'laser', .4), ('HeliExplode.wav', 'explosion', .45)]:
    try:
        snd = pygame.mixer.Sound(str(resource_path(filename)))
        snd.set_volume(volume)
        if name == 'laser':
            laser_sfx = snd
        else:
            explosion_sfx = snd
    except (pygame.error, OSError) as exc:
        print('Sound unavailable:', exc)

try:
    high_score = int(json.loads(writable_score_path().read_text()).get('high_score', 0))
except (OSError, ValueError, TypeError):
    high_score = 0


def save_high_score():
    try:
        writable_score_path().write_text(json.dumps({'high_score': high_score}))
    except OSError as exc:
        print('Could not save score:', exc)


def draw_center(message, y, font_obj=font, color=RED):
    surface = font_obj.render(message, True, color)
    rect = surface.get_rect(center=(WIDTH // 2, y))
    shadow = font_obj.render(message, True, (0, 0, 0))
    for ox, oy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
        screen.blit(shadow, rect.move(ox, oy))
    screen.blit(surface, rect)


selected_ship = 0
state = 'menu'  # menu, playing, paused, game_over
running = True


def new_game():
    global player, score, health, lives, level, kills, bullets, enemy_list, pickups
    global boss, last_shot, last_spawn, weapon, shield_until, speed_until, state, boss_level_spawned
    player = pygame.Rect(WIDTH // 2 - 32, HEIGHT - 105, 64, 64)
    score, health, lives, level, kills = 0, 100, 3, 1, 0
    bullets, enemy_list, pickups = [], [], []
    boss = None
    boss_level_spawned = 0
    last_shot = last_spawn = pygame.time.get_ticks()
    weapon = 1
    shield_until = speed_until = 0
    state = 'playing'


def continue_game():
    """Resume at the reached level, keeping score and upgrades."""
    global player, health, lives, bullets, enemy_list, pickups, boss
    global shield_until, last_spawn, last_shot, state
    now = pygame.time.get_ticks()
    player = pygame.Rect(WIDTH // 2 - 32, HEIGHT - 105, 64, 64)
    health, lives = 100, 3
    bullets, enemy_list, pickups = [], [], []
    boss = None
    # Permit a boss to spawn again if continuing during a boss level.
    global boss_level_spawned
    boss_level_spawned = 0
    shield_until = now + 2500
    last_spawn = last_shot = now
    state = 'playing'


def fire(now):
    global last_shot
    if now - last_shot < (125 if weapon > 1 else 210):
        return
    offsets = (-17, 17) if weapon > 1 else (0,)
    for offset in offsets:
        bullets.append(pygame.Rect(player.centerx + offset - 6, player.top - 26, 12, 28))
    last_shot = now
    if laser_sfx:
        laser_sfx.play()


def damage_player(now):
    global health, lives, state, high_score, shield_until
    if now < shield_until:
        return
    health -= 34
    shield_until = now + 1100
    if health <= 0:
        lives -= 1
        if lives <= 0:
            state = 'game_over'
            if score > high_score:
                high_score = score
                save_high_score()
        else:
            health = 100
            shield_until = now + 1700


def add_pickup(x, y):
    if random.random() < .17:
        kind = random.choice(list(power_imgs))
        pickups.append({'rect': pygame.Rect(x, y, 32, 32), 'kind': kind})


new_game()
state = 'menu'
while running:
    dt = min(clock.tick(FPS) / 1000, .05)
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
            elif state == 'menu':
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    selected_ship = (selected_ship - 1) % len(ships)
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    selected_ship = (selected_ship + 1) % len(ships)
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    new_game()
            elif state == 'playing' and event.key in (pygame.K_p,):
                state = 'paused'
            elif state == 'paused' and event.key in (pygame.K_p, pygame.K_RETURN):
                state = 'playing'
            elif state == 'game_over' and event.key == pygame.K_c:
                continue_game()
            elif state == 'game_over' and event.key == pygame.K_r:
                new_game()
            elif state == 'game_over' and event.key == pygame.K_m:
                state = 'menu'

    if state == 'playing':
        previous_level = level
        keys = pygame.key.get_pressed()
        dx = int(keys[pygame.K_RIGHT] or keys[pygame.K_d]) - int(keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = int(keys[pygame.K_DOWN] or keys[pygame.K_s]) - int(keys[pygame.K_UP] or keys[pygame.K_w])
        if dx or dy:
            factor = 1 / math.sqrt(dx * dx + dy * dy)
            speed = 430 if now < speed_until else 315
            player.x += round(dx * factor * speed * dt)
            player.y += round(dy * factor * speed * dt)
            player.clamp_ip(screen.get_rect())
        if keys[pygame.K_SPACE]:
            fire(now)

        # Every 10 defeated enemies advances a level; a boss appears on levels 5, 10, ...
        level = 1 + kills // 10
        if level > previous_level:
            # Reward reaching a new level with a small health refill.
            health = min(100, health + 20)
        if now - last_spawn >= max(240, 950 - (level - 1) * 55):
            last_spawn = now
            img_index = random.randrange(3)
            rect = pygame.Rect(random.randrange(0, WIDTH - 48), -48, 48, 48)
            enemy_list.append({'rect': rect, 'type': img_index, 'hp': 1})
        if level % 5 == 0 and boss is None and boss_level_spawned != level:
            boss = {'rect': pygame.Rect(WIDTH // 2 - 80, -120, 160, 120), 'hp': 15 + level * 2, 'direction': 1}
            boss_level_spawned = level

        for enemy in enemy_list[:]:
            enemy['rect'].y += round((145 + level * 18) * dt)
            if enemy['rect'].top > HEIGHT:
                enemy_list.remove(enemy)
                damage_player(now)
            elif enemy['rect'].colliderect(player):
                enemy_list.remove(enemy)
                damage_player(now)
        if boss:
            r = boss['rect']
            if r.top < 32:
                r.y += round(140 * dt)
            else:
                r.x += round(boss['direction'] * (120 + level * 6) * dt)
                if r.left <= 0 or r.right >= WIDTH:
                    boss['direction'] *= -1
            if r.colliderect(player):
                damage_player(now)

        for bullet in bullets[:]:
            bullet.y -= round(610 * dt)
            if bullet.bottom < 0:
                bullets.remove(bullet)
                continue
            hit = False
            if boss and boss['rect'].colliderect(bullet):
                boss['hp'] -= 1
                hit = True
                if boss['hp'] <= 0:
                    score += 250
                    kills += 1
                    add_pickup(boss['rect'].centerx, boss['rect'].centery)
                    boss = None
                    if explosion_sfx:
                        explosion_sfx.play()
            if not hit:
                for enemy in enemy_list[:]:
                    if enemy['rect'].colliderect(bullet):
                        enemy_list.remove(enemy)
                        score += 10
                        kills += 1
                        add_pickup(enemy['rect'].centerx, enemy['rect'].centery)
                        if explosion_sfx:
                            explosion_sfx.play()
                        hit = True
                        break
            if hit and bullet in bullets:
                bullets.remove(bullet)

        for item in pickups[:]:
            r = item['rect']
            r.y += round(95 * dt)
            if r.top > HEIGHT:
                pickups.remove(item)
            elif r.colliderect(player):
                kind = item['kind']
                if kind == 'health':
                    health = min(100, health + 40)
                elif kind == 'extra_life':
                    lives = min(9, lives + 1)
                elif kind == 'shield':
                    shield_until = now + 6000
                elif kind == 'speed_boost':
                    speed_until = now + 6000
                elif kind == 'weapon_upgrade':
                    weapon = 2
                pickups.remove(item)

    if state == 'menu':
        screen.blit(menu_bg, (0, 0))
        draw_center('DUSO SPACE SHOOTER 2.1', 115, big)
        screen.blit(ships[selected_ship], ships[selected_ship].get_rect(center=(WIDTH // 2, 260)))
        draw_center('LEFT / RIGHT: Choose spaceship', 355)
        draw_center('ENTER or SPACE: Start game', 398)
        draw_center('Arrows / WASD: Move     SPACE: Fire     P: Pause', 447, small)
        draw_center(f'High Score: {high_score}', 515)
    elif state in ('playing', 'paused'):
        screen.blit(backgrounds[((level - 1) // 3) % 3], (0, 0))
        if now >= shield_until or (now // 120) % 2 == 0:
            screen.blit(ships[selected_ship], player)
        for enemy in enemy_list:
            screen.blit(enemies[enemy['type']], enemy['rect'])
        if boss:
            screen.blit(boss_img, boss['rect'])
            pygame.draw.rect(screen, 'red', (boss['rect'].x, boss['rect'].bottom + 5, 160, 8))
            pygame.draw.rect(screen, 'lime', (boss['rect'].x, boss['rect'].bottom + 5, max(0, min(160, boss['hp'] * 4)), 8))
        for bullet in bullets:
            screen.blit(lasers[selected_ship], bullet)
        for item in pickups:
            screen.blit(power_imgs[item['kind']], item['rect'])
        screen.blit(font.render(f'Score: {score}   Level: {level}   Lives: {lives}', True, RED), (12, 10))
        pygame.draw.rect(screen, 'red', (12, 45, 150, 14))
        pygame.draw.rect(screen, 'lime', (12, 45, round(150 * health / 100), 14))
        pygame.draw.rect(screen, RED, (12, 45, 150, 14), 2)
        if state == 'paused':
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 175))
            screen.blit(overlay, (0, 0))
            draw_center('PAUSED', 245, big)
            draw_center('P / ENTER / ESC to resume', 320)
    elif state == 'game_over':
        screen.blit(over_bg, (0, 0))
        draw_center('GAME OVER', 180, big)
        draw_center(f'Score: {score}    High Score: {high_score}', 260)
        draw_center(f'Level Reached: {level}', 305)
        draw_center('C: Continue This Level (3 Lives)', 370)
        draw_center('R: New Game    M: Menu    ESC: Exit', 420, small)

    pygame.display.flip()

pygame.quit()
sys.exit()
