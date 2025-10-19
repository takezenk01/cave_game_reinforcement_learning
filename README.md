# cave_game_reinforcement_learning
# 洞窟ゲーム自動プレイ

# 概要
既存のゲームを、強化学習（PPO）エージェントが疑似キーボード入力で自動プレイするツールです。
他のプラットフォームで開発されたゲームを、強化学習で学習させたエージェントで自動プレイさせたいと思い開発しました。

学習は描画レスシミュレーション環境で高速化し、実動作は本物のゲームに対して**KEYDOWN(K_SPACE)**を疑似入力して操作します。

## Why this matters for Morikatron
- **無改造で自動化**：既存ゲームへ侵襲せず AI を適用 → **開発/QA 向け AI ツール**に直結。  
- **高速学習→本番適用**：ShadowSim で素早く学習し、本番は元ゲームにキー注入で運用。  
- **QA拡張性**：スコア・生存時間・ステージ進行の自動収集、失敗パターンの再現/回帰テストまで拡張可能。

## Quick Start
```bash
pip install "stable-baselines3[extra]==2.3.0" gymnasium pygame
# 学習（描画なし）
python rl_keyboard_wrapper.py --train --timesteps 300000
# 自動プレイ（元ゲームは cave_orig.py の main() を無改造で起動）
python rl_keyboard_wrapper.py --play --game_module cave_orig --model ppo_cave_key.zip --seconds 90
