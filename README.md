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

## 🌐 オンラインで遊ぶ
Webブラウザ上でインストール不要で今すぐプレイできます：
- **[GitHub Pages 版](https://maichi333.github.io/agri-tetris/)**
- **[Cloudflare Workers 版](https://my-cloudflare-site.maichi333.workers.dev/tetris/)**

## 📖 操作方法

| キー | 動作 |
|---|---|
| `←` / `→` | 左右移動（長押しで高速移動） |
| `↑` / `X` | 右回転（時計回り / SRS） |
| `Z` | 左回転（反時計回り / SRS） |
| `↓` | ソフトドロップ（通常より高速落下） |
| `Space` | ハードドロップ（即時着地＆ロック） |
| `C` / `Shift` | ホールド（キープ） |
| `Tab` | DAS / ARR 操作感切替（NORMAL / FAST / PRO） |
| `Enter` | ゾーン発動（ゲージ満タン時） |
| `M` | BGM・効果音ミュート切替 |
| `P` | ポーズ |
| `R` | リスタート / タイトルへ戻る |

詳しいゲームルール（四季の農業テーマ、特殊アイテム、SRSウォールキック、ゾーンシステム等）は [HANDOFF.md](HANDOFF.md) および `tetris_manual.html` をご覧ください。
