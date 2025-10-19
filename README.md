# 洞窟ゲーム自動プレイ

既存のゲームを強化学習エージェントが、疑似キーボード操作で自動プレイを行うシステムです。  
ゲームAI研究・QA自動化・開発支援に活用できるような、AIを目指して、作成しました。

---

## プロジェクト概要

- **目的**　
  既存のプラットフォームのゲームを自動プレイできる強いAIを作りたいという目的で、
  既存のゲームに手を加えず、AIが「人間の代わりにプレイ」できる環境を構築しました。
  今後、こういった技術を応用し、ゲームが上手いプレイヤーのプレイを学習することで、さらに強いAIを作成し、
  ゲーム大会等の練習相手になりうるのではと考えています。

  **特徴**
  | 機能 | 説明 |
  |------|------|
  | 既存ゲーム対応可能 | 元ゲーム(`cave_game.py`)を一切変更せず、外部から操作可能 |
  | 高速学習 | 物理挙動を再現する`Simulation`で描画レス学習（PPO） |
  | 疑似キーボード | `pygame.event.get()`をフックして自動で`KEYDOWN(K_SPACE)`を認識 |
  | 同期制御 | `pygame.display.update()`後に内部シミュレータを1フレーム進め、動作同期 |
  | 拡張性 | 動画保存・TensorBoard・CNN観測などに容易に発展可能 |

  ---

## 動作確認環境

| 環境 | バージョン / 備考 |
|------|--------------------|
| OS | Windows 10 / 11|
| Python | 3.10以上 |
| GPU | CUDA 12.1 (任意。CPUでも動作可) |
| Pygame | 2.5.2 以上 |
| Stable-Baselines3 | 2.3.0 |

---

## インストール手順

### 1. クローン or ダウンロード
```bash
git clone https://github.com/takezenk01/cave_game_reinforcement_learning.git
cd cave_game_reinforcement_learning/cave_game
```

### 2. 依存パッケージのインストール
```bash
pip install -r requirements.txt
```

## 起動方法
### 1. 学習フェーズ（PPO強化学習）
```bash
python cave_game_reinforcement_learning.py --train --timesteps 300000
```
学習結果は ppo_cave_key.zip に保存されます。

### 2. 実プレイ（元ゲームをAIが操作）
```bash
python cave_game_reinforcement_learning.py --play --game_module cave_game --seconds 300
```

### 学習アルゴリズム概要（PPO）
Policy Gradient (Actor-Critic) による方策最適化。
状態空間：[ship_y, velocity, hole_top, hole_bottom, slope]
行動空間：2（押す / 押さない）
報酬設計：
生存: +0.1
穴の中心に近いほど: +(1 - dist) × 0.002
衝突時: -1.0
これにより、「中心を維持しながら生存時間を伸ばす」行動を自律的に学習します。
