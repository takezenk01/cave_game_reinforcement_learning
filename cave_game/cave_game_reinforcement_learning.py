# ===============================================================================
# 目的:
#   既存のゲームに対して、強化学習エージェントが
#   疑似キーボード入力（KEYDOWN）で自動プレイするツールを実装。
#
# 企図:
#   - 「ゲーム開発やQA事業で使用できるAIツール制作」に直結する実装を想定。
#   - 学習（高速）と本番運用（ゲーム操作）を分離した環境を構築。
#
# 使い方:
#   github上にあるREADME.mdをご参照ください。
#   https://github.com/takezenk01/cave_game_reinforcement_learning.git/README.md
# ===============================================================================

import importlib
import os
from dataclasses import dataclass
from typing import Optional
import argparse

import numpy as np
import random
import importlib
import threading
import pygame
from pygame.locals import KEYDOWN, K_SPACE, QUIT

import gymnasium as gym
from gymnasium import spaces
from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv, VecMonitor
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import EvalCallback, StopTrainingOnNoModelImprovement

# =======================================================================
#    環境に ship.png / bang.png が無くても止まらないよう、単色Surfaceで代替。
# =======================================================================
_real_img_load = pygame.image.load
def _safe_image_load(path):
    try:
        return _real_img_load(path)
    except Exception:
        # 代替の単色Surface
        if "ship" in path:
            surf = pygame.Surface((40, 80))
            surf.fill((0, 0, 255))
            return surf.convert()
        elif "bang" in path:
            surf = pygame.Surface((80, 120))
            surf.fill((255, 0, 0))
            return surf.convert()
        else:
            surf = pygame.Surface((10, 10))
            surf.fill((200, 200, 200))
            return surf.convert()
pygame.image.load = _safe_image_load

# =================================================================
# 1) Simulation: 元ゲームの物理/乱数挙動を外部で再現する軽量シミュレータ
#    ・描画なし&低次元観測でPPOを高速に学習
# =================================================================
@dataclass
class Cfg:
    W = 800            # 画面の幅
    H = 600            # 画面の高さ
    WALLS = 80         # 洞窟（横方向の穴データの個数）
    COL_W = 10         # 通路の幅
    SHIP_H = 80        # 自機の高さ
    G_DOWN = 3         # 重力速度
    G_UP = -3          # 自機上昇速度
    SLOPE_MIN = 1      # 通路の上下移動量の最小値
    SLOPE_MAX = 6      # 通路の上下移動量の最大値
    HOLE_TOP0 = 100    # 通路の上端初期位置
    HOLE_H0 = 400      # 通路の高さ初期位置
    SHRINK = 20        # 通路を小さくする量
    FPS = 15           # フレームレート

class Simulation:
    """
    ゲームを再現するクラス。
    - reset(): 内部状態を初期化するクラス
    - obs():  現在のゲーム状態を低次元ベクトルで返す。
    - step(press_space): 1フレーム進める
    """
    def __init__(self, seed: int = 123, cfg: Cfg = Cfg()):
        self.cfg = cfg
        # 元コードはrandintを使うため、random.Random(seed) で同系列化
        self.rng_py = random.Random(seed)  # 元コードと同じ系列で randint を発生
        self.reset()

    def reset(self):
        self.ship_y = 250
        self.velocity = 0
        self.score = 0
        self.slope = self.rng_py.randint(self.cfg.SLOPE_MIN, self.cfg.SLOPE_MAX)
        # 穴配列（xpos*10, 100, 10, 400）
        self.holes = [[x * self.cfg.COL_W, self.cfg.HOLE_TOP0, self.cfg.COL_W, self.cfg.HOLE_H0]
                      for x in range(self.cfg.WALLS)]
        self.steps = 0
        self.game_over = False
        return self.obs()

    def obs(self):
        hole0 = self.holes[0]
        top = hole0[1]
        bottom = top + hole0[3]
        ship_y_norm = np.clip(self.ship_y / (self.cfg.H - 1), 0, 1)
        vel_norm = np.clip(self.velocity / 30.0, -1, 1)
        top_norm = np.clip(top / (self.cfg.H - 1), 0, 1)
        bottom_norm = np.clip(bottom / (self.cfg.H - 1), 0, 1)
        slope_norm = np.clip(self.slope / float(self.cfg.SLOPE_MAX), -1, 1)
        return np.array([ship_y_norm, vel_norm, top_norm, bottom_norm, slope_norm], dtype=np.float32)

    def step(self, press_space: bool):
        if self.game_over:
            return self.obs(), 0.0, True

        self.steps += 1
        self.score += 10

        # 入力（押す/押さない）→ 速度 → 位置
        self.velocity += self.cfg.G_UP if press_space else self.cfg.G_DOWN
        self.ship_y += self.velocity

        # 縦穴スクロールと反転処理（反転時は穴を狭める）
        last = self.holes[-1].copy()
        test_top = last[1] + self.slope
        test_bottom = test_top + last[3]
        if test_top <= 0 or test_bottom >= self.cfg.H:
            s = self.rng_py.randint(self.cfg.SLOPE_MIN, self.cfg.SLOPE_MAX)
            self.slope = s * (-1 if self.slope > 0 else 1)
            last[3] = max(10, last[3] - self.cfg.SHRINK) 
        last[0] += self.cfg.COL_W
        last[1] += self.slope
        self.holes.append(last)
        self.holes.pop(0)
        for h in self.holes:
            h[0] -= self.cfg.COL_W

        # 衝突判定
        hole0 = self.holes[0]
        hole_top = hole0[1]
        hole_bottom = hole0[1] + hole0[3]
        crash = (hole_top > self.ship_y) or (hole_bottom < self.ship_y + self.cfg.SHIP_H)

        # 画面外もクラッシュ扱いとする
        if self.ship_y < 0 or (self.ship_y + self.cfg.SHIP_H) > self.cfg.H:
            crash = True
        if crash:
            self.game_over = True

        # 報酬：生存 + 中央維持のshaping + クラッシュペナルティ
        center = (hole_top + hole_bottom) / 2.0
        ship_c = self.ship_y + self.cfg.SHIP_H / 2.0
        dist = abs(center - ship_c) / (self.cfg.H / 2.0)
        reward = 0.1 + (1.0 - dist) * 0.002
        if crash:
            reward += -1.0
        return self.obs(), float(reward), self.game_over

# =====================================================
# 2) 学習: SimulationをGymnasium環境にラップしてPPOで学習
# =====================================================
def train(model_path="ppo_cave_key.zip", timesteps=300_000, vec_envs=8, seed=123):
    class CaveEnv(gym.Env):
        """
        Simulationを最小限でGym API化。
        観測と行動は低次元&離散で軽量化。

        Parameters
        ----------
        model_path
            学習済みモデルの保存先パス
        timesteps : int
            総ステップ数
        vec_envs : int
            並列環境数（大きいほどサンプル収集が早いがメモリを消費）
        seed : int
            乱数シード
        ------------
        """

        metadata = {}
        def __init__(self):
            super().__init__()
            self.sim = Simulation(seed=seed)
            self.action_space = spaces.Discrete(2)
            low = np.array([0.0, -1.0, 0.0, 0.0, -1.0], dtype=np.float32)
            high = np.array([1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float32)
            self.observation_space = spaces.Box(low, high, dtype=np.float32)
            self.max_steps = 4000
            self.steps = 0

        def reset(self, seed: Optional[int] = None, options=None):
            self.sim = Simulation(seed=seed if seed is not None else 123)
            self.steps = 0
            return self.sim.reset(), {}
        
        def step(self, a: int):
            self.steps += 1
            obs, rew, done = self.sim.step(bool(a == 1))
            truncated = self.steps >= self.max_steps
            return obs, rew, done, truncated, {"score": self.sim.score}

    def make_env():
        return CaveEnv()

    # 並列化で学習を高速化
    env = make_vec_env(make_env, n_envs=vec_envs, vec_env_cls=DummyVecEnv)
    env = VecMonitor(env)
    eval_env = make_vec_env(make_env, n_envs=1, vec_env_cls=DummyVecEnv)
    eval_env = VecMonitor(eval_env)

    # モデル定義（PPO）
    policy_kwargs = dict(net_arch=[128, 128])
    model = PPO("MlpPolicy", env, verbose=1, policy_kwargs=policy_kwargs,
                n_steps=512, batch_size=1024, gamma=0.995, gae_lambda=0.95,
                learning_rate=3e-4, n_epochs=10, clip_range=0.2, seed=seed)

    # 早期終了
    stop_cb = StopTrainingOnNoModelImprovement(max_no_improvement_evals=10, min_evals=5, verbose=1)
    eval_cb = EvalCallback(eval_env, best_model_save_path="./cave_key_best",
                           log_path="./cave_key_logs", eval_freq=10_000,
                           deterministic=True, render=False, callback_after_eval=stop_cb)

    model.learn(total_timesteps=timesteps, callback=eval_cb)
    model.save(model_path)
    env.close(); eval_env.close()
    print(f"[OK] saved -> {model_path}")

# ======================================================================
# 3) 推論コントローラ: 観測から行動（押す/押さない）を決め、フレーム同期を維持
# ======================================================================
class RLController:
    def __init__(self, model_path="ppo_cave_key.zip", seed=123):
        from stable_baselines3 import PPO
        self.model = PPO.load(model_path)   # 学習済みPPOをロード
        self.sim = Simulation(seed=seed)    # シミュレーション
        self.last_action = 0                # 直近の行動（0もしくは1）

    def decide(self):
        # 現在観測から、このフレームで押すべきかを決定
        obs = self.sim.obs()
        a, _ = self.model.predict(obs, deterministic=True)
        self.last_action = int(a)
        return self.last_action

    def end_frame(self):
        # フレーム終了後にシミュレーションを1アクション進め、次フレームを最新化
        self.sim.step(self.last_action == 1)

# =============================================================================
# 4) ゲームを起動し、疑似KEYDOWNで自動プレイ
#    - pygame.event.get を一時フック: 行動=1 のフレームに KEYDOWN(K_SPACE) を追加
#    - pygame.display.update を一時フック: 描画後にSimulationを1アクション進め同期
#    - 規定時間経過で QUIT をポスト
# =============================================================================
def play_with_keyboard_emulation(game_module="cave_game", seed=123, seconds=60, model_path="ppo_cave_key.zip"):

    # 乱数シードを同期
    random.seed(seed)

    # 元ゲームをimport
    gm = importlib.import_module(game_module)

    # RLコントローラ準備
    controller = RLController(model_path=model_path, seed=seed)

    # --- カウントダウン中フラグ ---
    game_active = False
    orig_countdown = getattr(gm, "countdown", None)
    if callable(orig_countdown):
        def countdown_wrapper(*args, **kwargs):
            nonlocal game_active
            try:
                return orig_countdown(*args, **kwargs)
            finally:
                # カウントダウン終了後に初めてRLを動かす
                game_active = True
        setattr(gm, "countdown", countdown_wrapper)
    else:
        # countdownが無い場合は即アクティブ
        game_active = True

    # 元APIを保存
    game_get = pygame.event.get
    game_update = pygame.display.update

    # コントローラーの決定ごとに KEYDOWN(K_SPACE) を追加
    def injected_get():
        # カウントダウン中はキーを押さないしない
        if not game_active:
            return list(game_get())
        act = controller.decide()
        events = list(game_get())
        if act == 1:
            events.append(pygame.event.Event(KEYDOWN, key=K_SPACE))
        return events

    # 画面更新後にシミュレーションを1アクション進め、次フレームを同期
    def injected_update(*args, **kwargs):
        ret = game_update(*args, **kwargs)
        # カウントダウン中はShadowSimを進めない（同期維持）
        if game_active:
            controller.end_frame()
        return ret

    # パッチ適用
    pygame.event.get = injected_get
    pygame.display.update = injected_update

    # seconds経過でQUITをポストして安全終了
    stopper = threading.Timer(seconds, lambda: pygame.event.post(pygame.event.Event(QUIT)))
    stopper.daemon = True
    stopper.start()

    try:
        gm.main()  # ゲームをそのまま起動
    finally:
        # パッチを必ず戻す
        pygame.event.get = game_get
        pygame.display.update = game_update
        try:
            stopper.cancel()
        except Exception:
            pass

# =================================
# 5) CLI エントリ: 学習 or 自動プレイ
# =================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true", help="PPO学習を実行")
    parser.add_argument("--timesteps", type=int, default=300000, help="学習ステップ数")
    parser.add_argument("--vec_envs", type=int, default=8, help="並列環境数（CPU）")
    parser.add_argument("--seed", type=int, default=123, help="乱数シード（元ゲームと同期）")
    parser.add_argument("--model", type=str, default="ppo_cave_key.zip", help="学習済みモデルの保存/読込パス")
    parser.add_argument("--play", action="store_true", help="ゲームを疑似キーボードで自動プレイ")
    parser.add_argument("--game_module", type=str, default="cave_game", help="元ゲームのモジュール名")
    parser.add_argument("--seconds", type=int, default=60, help="自動プレイ時間（秒）")
    args = parser.parse_args()

    # 学習モード
    if args.train:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # 学習は描画不要
        train(model_path=args.model, timesteps=args.timesteps, vec_envs=args.vec_envs, seed=args.seed)

    # 自動プレイモード
    if args.play:
        play_with_keyboard_emulation(game_module=args.game_module, seed=args.seed, seconds=args.seconds, model_path=args.model)
