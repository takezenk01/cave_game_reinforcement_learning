# ===============================================================================
# 洞窟ゲーム
# スペースキーで自機上昇、自動で下降
# ===============================================================================
import sys
from random import randint
import pygame
from pygame.locals import QUIT, Rect, KEYDOWN, K_SPACE, K_RETURN

# ========================
# 初期化／画面・クロック設定
# ========================
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
    walls = 80      # 洞窟（横方向の穴データの個数）
    ship_y = 250    # 自機のy座標
    velocity = 0    # 自機の縦方向速度（負で上昇、正で下降）
    score = 0       # スコア
    slope = randint(1, 6)    # 洞窟の傾き
    sysfont = pygame.font.SysFont(None, 36)         # 画面表示用の標準フォントとサイズ
    ship_image = pygame.image.load("ship.png")      # 自機画像
    bang_image = pygame.image.load("bang.png")      # 衝突時の画像
    holes = []                                      # 洞窟の通路

    # 洞窟の初期化
    for xpos in range(walls):
        holes.append(Rect(xpos * 10, 100, 10, 400)) # Rect(left, top, width, height)
    game_over = False

    # ゲーム開始前のカウントダウン
    countdown(SURFACE, sysfont)

    # =======================
    # メインゲームループ開始
    # =======================
    while True:
        is_space_down = False   # このフレームでスペースキーが押されたかどうか

        # -------------
        # 入力処理
        # -------------
        for event in pygame.event.get():
            # ウィンドウの×ボタンが押されたら終了
            if event.type == QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == KEYDOWN:
                # スペースで上昇（負の加速度を与える）
                if event.key == K_SPACE:
                    is_space_down = True

        # -------------
        # 物理判定
        # -------------
        # 自機を移動
        if not game_over:

            # フレーム経過に応じてスコアを加算（ゲームが進むほど増える）
            score += 10 

             # 自機の速度更新：スペース押下で加速度-3、何もなければ加速度+3
            velocity += -3 if is_space_down else 3

            # 速度を位置に反映
            ship_y += velocity

            # 洞窟をスクロール
            edge = holes[-1].copy()
            test = edge.move(0, slope)

            # 画面端に当たったら、傾きの向きを反転しつつ通路を狭める
            if test.top <= 0 or test.bottom >= 600:
                slope = randint(1, 6) * (-1 if slope > 0 else 1)
                edge.inflate_ip(0, -20)

            # 新しい洞窟の最終位置決定
            edge.move_ip(10, slope)

             # 洞窟リスト更新
            holes.append(edge)
            del holes[0]
            holes = [x.move(-10, 0) for x in holes]

            # 衝突 ?
            if holes[0].top > ship_y or \
                holes[0].bottom < ship_y + 80:
                game_over = True

        # -------------
        # 描画処理
        # -------------
        # 背景
        SURFACE.fill((0, 255, 0))

        # 通路（空洞）
        for hole in holes:
            pygame.draw.rect(SURFACE, (0, 0, 0), hole)

        # 自機
        SURFACE.blit(ship_image, (0, ship_y))
        score_image = sysfont.render("score is {}".format(score),
                                     True, (0, 0, 225))
        
        # スコア
        SURFACE.blit(score_image, (600, 20))

        # ゲームオーバー
        if game_over:
            SURFACE.blit(bang_image, (0, ship_y-40))

        # 画面更新
        pygame.display.update()
        FPSCLOCK.tick(15)

if __name__ == '__main__':
    main()