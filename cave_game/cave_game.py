import sys
from random import randint
import pygame
from pygame.locals import QUIT, Rect, KEYDOWN, K_SPACE, K_RETURN

pygame.init()
pygame.key.set_repeat(5, 5)
SURFACE = pygame.display.set_mode((800, 600))
FPSCLOCK = pygame.time.Clock()

def countdown(screen, font):
    """ ゲーム開始前のカウントダウン表示 """
    for i in range(3, 0, -1):
        screen.fill((0, 255, 0))
        text = font.render(str(i), True, (0, 0, 0))
        rect = text.get_rect(center=(400, 300))
        screen.blit(text, rect)
        pygame.display.update()
        pygame.time.wait(1000)

    screen.fill((0, 255, 0))
    start_text = font.render("START!", True, (255, 0, 0))
    rect = start_text.get_rect(center=(400, 300))
    screen.blit(start_text, rect)
    pygame.display.update()
    pygame.time.wait(1000)

def main():
    """ メインルーチン """
    walls = 80
    ship_y = 250
    velocity = 0
    score = 0
    slope = randint(1, 6)
    sysfont = pygame.font.SysFont(None, 36)
    ship_image = pygame.image.load("ship.png")
    bang_image = pygame.image.load("bang.png")
    holes = []
    for xpos in range(walls):
        holes.append(Rect(xpos * 10, 100, 10, 400))
    game_over = False

    # ゲーム開始前のカウントダウン
    countdown(SURFACE, sysfont)

    while True:
        is_space_down = False

        for event in pygame.event.get():
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                if event.key == K_SPACE:
                    is_space_down = True

        # 自機を移動
        if not game_over:
            score += 10
            velocity += -3 if is_space_down else 3
            ship_y += velocity

            # 洞窟をスクロール
            edge = holes[-1].copy()
            test = edge.move(0, slope)
            if test.top <= 0 or test.bottom >= 600:
                slope = randint(1, 6) * (-1 if slope > 0 else 1)
                edge.inflate_ip(0, -20)
            edge.move_ip(10, slope)
            holes.append(edge)
            del holes[0]
            holes = [x.move(-10, 0) for x in holes]

            # 衝突 ?
            if holes[0].top > ship_y or \
                holes[0].bottom < ship_y + 80:
                game_over = True

        # 描画
        SURFACE.fill((0, 255, 0))
        for hole in holes:
            pygame.draw.rect(SURFACE, (0, 0, 0), hole)
        SURFACE.blit(ship_image, (0, ship_y))
        score_image = sysfont.render("score is {}".format(score),
                                     True, (0, 0, 225))
        SURFACE.blit(score_image, (600, 20))

        if game_over:
            SURFACE.blit(bang_image, (0, ship_y-40))
                
        pygame.display.update()
        FPSCLOCK.tick(15)

if __name__ == '__main__':
    main()