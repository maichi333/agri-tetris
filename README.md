# 🌾 大収穫！ 農業テトリス (agri-tetris)

農業とテトリスを融合させたオリジナルゲームです。  
**ローカルデスクトップ版（Python/Pygame）** と **Webブラウザ版（Pyodide/WebAssembly）** の両方に対応しています。

## 🎮 プレイ方法

### 1. ローカルデスクトップで遊ぶ（推奨）
Python 3.10+ がインストールされている環境で実行できます。

```bash
# 依存パッケージのインストール
pip install pygame-ce numpy Pillow

# ゲーム起動
python tetris.py
# または Windows の場合 tetris.bat をダブルクリック
```

### 2. Webブラウザで遊ぶ
ローカルHTTPサーバーを起動してアクセスしてください（Pyodideによるブラウザ内Python実行）。

```bash
python -m http.server 8000
```
ブラウザで `http://localhost:8000/index.html` を開きます。

## 📖 操作方法・ゲーム仕様

詳しいゲームルール（SRSウォールキック、DAS/ARR切替、ゾーンシステム等）は [HANDOFF.md](HANDOFF.md) および `tetris_manual.html` をご覧ください。
