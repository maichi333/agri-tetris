# =============================================================================
#  tetris.py  ―  Pygame テトリス モダンUI版
#
#  操作:
#    ← →        : 左右移動
#    ↑           : 回転
#    ↓           : ソフトドロップ
#    Space       : ハードドロップ
#    C / Shift   : ホールド
#    P           : ポーズ
#    R           : リスタート
# =============================================================================

import pygame
import sys
import random
import copy
import os
import subprocess
import threading
import tempfile
import math
import asyncio

# ── ブラウザ環境（Pyodide）検出 ──
try:
    import platform as _plt
    _IN_BROWSER = _plt.system() == 'Emscripten'
except Exception:
    _IN_BROWSER = False

# ゲームディレクトリの解決（ブラウザでは __file__ が未定義の場合がある）
try:
    _GAME_DIR = os.path.dirname(os.path.abspath(__file__))
except (NameError, Exception):
    _GAME_DIR = '/home/pyodide'

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

# =============================================================================
#  ★ レイアウト定数
# =============================================================================

CELL     = 32           # 1 マスのサイズ (px)
COLS     = 10
ROWS     = 20

BOARD_X  = 170          # ボード左端 X
BOARD_Y  = 15           # ボード上端 Y
BOARD_W  = COLS * CELL  # 320
BOARD_H  = ROWS * CELL  # 640

SCREEN_W = 700
SCREEN_H = BOARD_H + BOARD_Y * 2   # 670

FPS          = 60
FALL_NORMAL  = 48
FALL_SOFT    = 4
FALL_LEVEL   = 4        # レベルアップごとに速くなるフレーム数

# ★ エフェクト設定（ここで調整できます）
FLASH_DURATION     = 10   # ライン消去フラッシュの長さ（フレーム）
PARTICLE_PER_CELL  = 5    # セルごとに生成するパーティクル数
SHAKE_TETRIS       = 12   # テトリス時の揺れフレーム数
SHAKE_HARDDROP     = 5    # ハードドロップ時の揺れフレーム数

# ロックディレイ設定
LOCK_DELAY         = 30   # 着地後のロック猶予フレーム数（0.5 秒 @ 60fps）
LOCK_RESET_MAX     = 15   # 1 ピースあたりのタイマーリセット上限（無限スピン防止）

# ゾーンシステム設定
ZONE_GAUGE_MAX = 100.0      # ゾーンゲージ満タン値
ZONE_DURATION  = 840        # ゾーン持続フレーム数（14 秒 @ 60fps）
ZONE_CELL      = '__ZONE__' # ゾーン行セルのセンチネル値（str で None / 色 tuple と区別）

# ガーベージシステム設定
GARBAGE_COLOR    = (90, 100, 112)  # ガーベージ行のグレーメタリック色
GARBAGE_WARN_DUR = 180             # 警告表示フレーム数（3 秒 @ 60fps）

# DAS / ARR 設定プリセット
#   DAS_DELAY : 長押し後、最初の連続移動が始まるまでのフレーム数
#   ARR_SPEED : 連続移動の間隔フレーム数（1=毎フレーム、2=1フレームおき…）
#   Tab キーでゲーム中・タイトル画面から切り替え可能
DAS_PRESETS = {
    'NORMAL': (10, 2),   # デフォルト。ゆったりした感触
    'FAST':   ( 6, 1),   # 素早いが安全。慣れたプレイヤー向け
    'PRO':    ( 3, 1),   # DAS が短くほぼ即応。上級者向け
}
DAS_PRESET_ORDER = ['NORMAL', 'FAST', 'PRO']   # Tab で循環する順序

# =============================================================================
#  SRS ウォールキックテーブル（Super Rotation System 公式）
#  キー = (from_rot, to_rot)  値 = [(dx, dy), ...] dy は下方向が正（画面座標系）
# =============================================================================

SRS_KICKS_JLSTZ = {
    # 時計回り (CW)
    (0, 1): [( 0, 0), (-1, 0), (-1,-1), ( 0, 2), (-1, 2)],
    (1, 2): [( 0, 0), ( 1, 0), ( 1, 1), ( 0,-2), ( 1,-2)],
    (2, 3): [( 0, 0), ( 1, 0), ( 1,-1), ( 0, 2), ( 1, 2)],
    (3, 0): [( 0, 0), (-1, 0), (-1, 1), ( 0,-2), (-1,-2)],
    # 反時計回り (CCW)
    (0, 3): [( 0, 0), ( 1, 0), ( 1, 1), ( 0,-2), ( 1,-2)],
    (3, 2): [( 0, 0), (-1, 0), (-1,-1), ( 0, 2), (-1, 2)],
    (2, 1): [( 0, 0), (-1, 0), (-1, 1), ( 0,-2), (-1,-2)],
    (1, 0): [( 0, 0), ( 1, 0), ( 1,-1), ( 0, 2), ( 1, 2)],
}

SRS_KICKS_I = {
    # 時計回り (CW)
    (0, 1): [( 0, 0), (-2, 0), ( 1, 0), (-2,-1), ( 1, 2)],
    (1, 2): [( 0, 0), (-1, 0), ( 2, 0), (-1, 2), ( 2,-1)],
    (2, 3): [( 0, 0), ( 2, 0), (-1, 0), ( 2, 1), (-1,-2)],
    (3, 0): [( 0, 0), ( 1, 0), (-2, 0), ( 1,-2), (-2, 1)],
    # 反時計回り (CCW)
    (0, 3): [( 0, 0), (-1, 0), ( 2, 0), (-1, 2), ( 2,-1)],
    (3, 2): [( 0, 0), (-2, 0), ( 1, 0), (-2,-1), ( 1, 2)],
    (2, 1): [( 0, 0), ( 1, 0), (-2, 0), ( 1,-2), (-2, 1)],
    (1, 0): [( 0, 0), ( 2, 0), (-1, 0), ( 2, 1), (-1,-2)],
}

# ハイスコア保存先
HISCORE_FILE = os.path.join(_GAME_DIR, "tetris_hiscore.txt")

# =============================================================================
#  色定義（固定色）
# =============================================================================

C_GOLD  = (255, 195,  45)   # ゴールド（スコア・レベル）
C_WHITE = (255, 255, 255)

# =============================================================================
#  ビジュアルテーマ定義  ── レベル5ごとに自動切替
#  インデックス: 0=Lv1-5深海  1=Lv6-10森林  2=Lv11-15火山  3=Lv16+宇宙
# =============================================================================

THEMES = [
    {   # ── Lv 1-5: 春の畑（播種・芽吹き）─────────────────────
        'name':    '春の畑',
        'bg_top':  ( 16,  26,  14),   # 柔らかな若葉と黒土のグラデーション
        'bg_bot':  ( 28,  44,  22),
        'board':   ( 12,  18,  10),
        'border':  ( 72, 138,  54),   # 新緑グリーン
        'grid':    ( 20,  34,  16),
        'panel':   ( 18,  30,  15),
        'c_text':  (220, 245, 205),
        'c_dim':   (120, 160, 105),
        'particle_type': 'leaf',
        'particle_count': 24,
    },
    {   # ── Lv 6-10: 夏の水田（青葉・清流）────────────────────
        'name':    '夏の水田',
        'bg_top':  (  8,  26,  38),   # 清流ブルーと青々とした稲穂
        'bg_bot':  ( 12,  50,  62),
        'board':   (  6,  18,  26),
        'border':  ( 45, 150, 180),   # 澄んだ水色
        'grid':    ( 14,  36,  48),
        'panel':   ( 12,  32,  44),
        'c_text':  (195, 240, 255),
        'c_dim':   ( 85, 155, 180),
        'particle_type': 'bubble',
        'particle_count': 26,
    },
    {   # ── Lv 11-15: 秋の果樹園（完熟・実り）─────────────────
        'name':    '秋の果樹園',
        'bg_top':  ( 42,  20,   6),   # 実りの夕暮れオレンジ・アンバー
        'bg_bot':  ( 72,  36,  10),
        'board':   ( 24,  10,   4),
        'border':  (210, 115,  28),   # 完熟ゴールド・オレンジ
        'grid':    ( 52,  26,   8),
        'panel':   ( 48,  22,   6),
        'c_text':  (255, 228, 190),
        'c_dim':   (185, 115,  65),
        'particle_type': 'ember',
        'particle_count': 30,
    },
    {   # ── Lv 16+: 大収穫祭（夜市・直売所）───────────────────
        'name':    '大収穫祭',
        'bg_top':  ( 24,   8,  36),   # 祝祭の夜空と提灯の煌めき
        'bg_bot':  ( 44,  14,  64),
        'board':   ( 16,   5,  24),
        'border':  (225, 185,  45),   # 黄金の稲穂ゴールド
        'grid':    ( 38,  16,  52),
        'panel':   ( 34,  12,  48),
        'c_text':  (255, 240, 205),
        'c_dim':   (175, 125, 195),
        'particle_type': 'star',
        'particle_count': 45,
    },
]

def _theme_for_level(level):
    return THEMES[min((level - 1) // 5, len(THEMES) - 1)]

# テトリミノの色（宮崎農業テーマ）
# I=白ねぎ(白緑)  O=マンゴー(完熟黄)  T=なす(深紫)
# S=きゅうり(濃緑) Z=トマト(鮮赤)  J=ブルーベリー(濃青) L=にんじん(橙)
PIECE_COLORS = {
    'I': (200, 235, 200),   # 白ねぎ: 白みがかった緑
    'O': (255, 200,   0),   # マンゴー: 完熟の黄（太陽のたまご）
    'T': (120,  30, 160),   # なす: 深い紫
    'S': ( 30, 160,  40),   # きゅうり: 宮崎特産の濃い緑
    'Z': (220,  40,  40),   # トマト: 鮮やかな赤
    'J': ( 30,  60, 180),   # ブルーベリー: 濃い青
    'L': (230, 110,  20),   # にんじん: オレンジ
}

# ピースと野菜の対応（ツールチップ・デバッグ用）
PIECE_NAMES = {
    'I': '白ねぎ', 'O': 'マンゴー', 'T': 'なす',
    'S': 'きゅうり', 'Z': 'トマト', 'J': 'ブルーベリー', 'L': 'にんじん',
}

# TETRIS ロゴ各文字の色
LOGO_COLORS = [
    (230,  60,  60),
    (230, 140,  40),
    (225, 220,  40),
    ( 55, 205,  55),
    ( 55, 135, 230),
    (160,  55, 230),
]

# =============================================================================
#  テトリミノ形状定義（4×4 マトリクス）
# =============================================================================

TETROMINOES = {
    'I': [[0,0,0,0],[1,1,1,1],[0,0,0,0],[0,0,0,0]],
    'O': [[0,1,1,0],[0,1,1,0],[0,0,0,0],[0,0,0,0]],
    'T': [[0,1,0,0],[1,1,1,0],[0,0,0,0],[0,0,0,0]],
    'S': [[0,1,1,0],[1,1,0,0],[0,0,0,0],[0,0,0,0]],
    'Z': [[1,1,0,0],[0,1,1,0],[0,0,0,0],[0,0,0,0]],
    'J': [[1,0,0,0],[1,1,1,0],[0,0,0,0],[0,0,0,0]],
    'L': [[0,0,1,0],[1,1,1,0],[0,0,0,0],[0,0,0,0]],
}

# =============================================================================
#  サウンドユーティリティ
# =============================================================================

SAMPLE_RATE = 44100

def build_tetris_fanfare():
    """numpy で C5→E5→G5→C6 の上昇ファンファーレを合成"""
    if not HAS_NUMPY:
        return None
    notes = [523.25, 659.25, 783.99, 1046.50]
    durs  = [0.12,   0.12,   0.12,   0.35  ]
    parts = []
    for freq, d in zip(notes, durs):
        n = int(SAMPLE_RATE * d)
        t = np.linspace(0, d, n, False)
        w = (np.sin(2*np.pi*freq*t)
             + 0.3*np.sin(2*np.pi*freq*2*t)
             + 0.1*np.sin(2*np.pi*freq*3*t))
        fade = int(n * 0.2)
        w[-fade:] *= np.linspace(1, 0, fade)
        parts.append(w)
    combined = np.concatenate(parts)
    combined = combined / np.max(np.abs(combined))
    combined = (combined * 0.6 * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.column_stack([combined, combined]))

def _make_tone(freq, dur, vol=0.25, harmonics=None, fade_ratio=0.30):
    """正弦波トーンを合成して pygame.Sound を返す。harmonics=[(倍率, 音量), ...]"""
    if not HAS_NUMPY:
        return None
    n = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, n, False)
    w = np.sin(2 * np.pi * freq * t)
    if harmonics:
        for hf, hv in harmonics:
            w += hv * np.sin(2 * np.pi * freq * hf * t)
    fade = max(1, int(n * fade_ratio))
    w[-fade:] *= np.linspace(1, 0, fade)
    peak = np.max(np.abs(w)) + 1e-9
    w = (w / peak * vol * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.column_stack([w, w]))

def _make_noise_burst(dur, vol=0.20):
    """指数減衰するホワイトノイズ（ロック音・衝撃音）"""
    if not HAS_NUMPY:
        return None
    n   = int(SAMPLE_RATE * dur)
    rng = np.random.default_rng(42)
    w   = rng.uniform(-1, 1, n)
    # 簡易ローパスフィルタ
    k = 12
    w = np.convolve(w, np.ones(k) / k, mode='same')
    env = np.exp(-np.linspace(0, 10, n))
    w   = w * env
    peak = np.max(np.abs(w)) + 1e-9
    w = (w / peak * vol * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.column_stack([w, w]))

def _make_clear_sound(count, pitch_mul=1.0):
    """ライン消去音：count に応じて連続ディン♪を合成。pitch_mul でピッチシフト"""
    if not HAS_NUMPY:
        return None
    base_freqs = [880, 1047, 1319]
    freqs = [f * pitch_mul for f in base_freqs[:count]]
    note_dur = 0.10
    parts = []
    for f in freqs:
        n = int(SAMPLE_RATE * note_dur)
        t = np.linspace(0, note_dur, n, False)
        w = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2 * t)
        fade = int(n * 0.25)
        w[-fade:] *= np.linspace(1, 0, fade)
        parts.append(w)
    combined = np.concatenate(parts)
    peak = np.max(np.abs(combined)) + 1e-9
    combined = (combined / peak * 0.35 * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.column_stack([combined, combined]))

def _make_heartbeat():
    """デンジャー時の心拍音（65Hz + 45Hz、鋭い指数減衰、~0.18秒）"""
    if not HAS_NUMPY:
        return None
    dur = 0.18
    n   = int(SAMPLE_RATE * dur)
    t   = np.linspace(0, dur, n, False)
    # 2つの低周波正弦波を重ねて心拍っぽさを演出
    w = (np.sin(2 * np.pi * 65 * t)
         + 0.6 * np.sin(2 * np.pi * 45 * t))
    # 鋭い指数減衰エンベロープ
    env = np.exp(-np.linspace(0, 18, n))
    w   = w * env
    peak = np.max(np.abs(w)) + 1e-9
    w = (w / peak * 0.45 * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.column_stack([w, w]))

def _make_item_sound():
    """アイテム発動音：「ピコーン！」高い電子音 (1800Hz→2600Hz 上昇 + 倍音)"""
    if not HAS_NUMPY:
        return None
    dur = 0.22
    n   = int(SAMPLE_RATE * dur)
    t   = np.linspace(0, dur, n, False)
    # 周波数が時間とともに上昇するチャープ
    freq = 1800 + 800 * (t / dur)
    w    = (np.sin(2 * np.pi * np.cumsum(freq) / SAMPLE_RATE)
            + 0.4 * np.sin(2 * np.pi * np.cumsum(freq * 2) / SAMPLE_RATE)
            + 0.15 * np.sin(2 * np.pi * np.cumsum(freq * 3) / SAMPLE_RATE))
    # 短いアタック＋素早いフェードアウト
    atk  = int(n * 0.05)
    fade = int(n * 0.45)
    w[:atk]  *= np.linspace(0, 1, atk)
    w[-fade:] *= np.linspace(1, 0, fade)
    peak = np.max(np.abs(w)) + 1e-9
    w = (w / peak * 0.38 * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.column_stack([w, w]))

def _make_zone_sound():
    """ゾーン突入音：「キィィィィン！」高音がゆっくり減衰しながら微振動する"""
    if not HAS_NUMPY:
        return None
    dur = 1.4
    n   = int(SAMPLE_RATE * dur)
    t   = np.linspace(0, dur, n, False)
    # 基音 3000Hz + 第2倍音でキンとした質感
    w   = (np.sin(2 * np.pi * 3000 * t)
           + 0.5  * np.sin(2 * np.pi * 6000 * t)
           + 0.15 * np.sin(2 * np.pi * 9000 * t))
    # 微振動（AM変調）でキィィィィン感
    shimmer = 1.0 + 0.18 * np.sin(2 * np.pi * 12 * t)
    w = w * shimmer
    # 鋭いアタック + 長めの指数減衰
    atk = int(n * 0.01)
    w[:atk] *= np.linspace(0, 1, atk)
    env = np.exp(-np.linspace(0, 6, n))
    w   = w * env
    peak = np.max(np.abs(w)) + 1e-9
    w = (w / peak * 0.40 * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.column_stack([w, w]))

def _make_garbage_sound():
    """ガーベージ警告音：「ガガガッ」低周波地響き（重厚なスタッター付きノイズ）"""
    if not HAS_NUMPY:
        return None
    dur = 0.55
    n   = int(SAMPLE_RATE * dur)
    rng = np.random.default_rng(77)
    noise = rng.uniform(-1, 1, n)
    # 強力なローパスで低周波化
    k = 40
    noise = np.convolve(noise, np.ones(k) / k, mode='same')
    # ガガガ スタッター（20Hz のオン/オフ）
    t = np.linspace(0, dur, n, False)
    stutter = 0.35 + 0.65 * (np.sin(2 * np.pi * 18 * t) > 0).astype(float)
    noise = noise * stutter
    # 指数減衰
    env   = np.exp(-np.linspace(0, 7, n))
    noise = noise * env
    # 低域サイン波を重ねて重厚感を追加（55Hz）
    bass  = np.sin(2 * np.pi * 55 * t) * np.exp(-np.linspace(0, 10, n))
    noise = noise + 0.6 * bass
    peak  = np.max(np.abs(noise)) + 1e-9
    noise = (noise / peak * 0.55 * 32767).astype(np.int16)
    return pygame.sndarray.make_sound(np.column_stack([noise, noise]))

def start_bgm_thread(youtube_url):
    """バックグラウンドで YouTube 音声をダウンロード＆ループ再生"""
    import glob

    def _try_play(path):
        try:
            print(f"[BGM] 再生試行: {path} ({os.path.getsize(path)//1024} KB)")
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(0.4)
            pygame.mixer.music.play(-1)
            print("[BGM] 再生開始！")
            return True
        except Exception as e:
            print(f"[BGM] 再生失敗: {e}")
            return False

    def _find_ffmpeg():
        try:
            import imageio_ffmpeg
            p = imageio_ffmpeg.get_ffmpeg_exe()
            print(f"[BGM] ffmpeg: {p}")
            return p
        except ImportError:
            pass
        import shutil
        p = shutil.which("ffmpeg")
        if p:
            return p
        print("[BGM] ffmpeg 未検出。pip install imageio-ffmpeg を推奨します。")
        return None

    def _webm_to_wav(src, ffmpeg):
        dst = src.rsplit(".", 1)[0] + ".wav"
        r = subprocess.run([ffmpeg, "-y", "-i", src,
                            "-ar", "44100", "-ac", "2", dst],
                           capture_output=True, timeout=120)
        return dst if r.returncode == 0 and os.path.exists(dst) else None

    def _worker():
        try:
            try:
                import yt_dlp
                print(f"[BGM] yt_dlp: {yt_dlp.version.__version__}")
            except ImportError:
                print("[BGM] yt_dlp 未検出。pip install yt-dlp を実行してください。")
                return

            ffmpeg  = _find_ffmpeg()
            tmpdir  = tempfile.mkdtemp(prefix="tetris_bgm_")
            tmpl    = os.path.join(tmpdir, "bgm.%(ext)s")
            print(f"[BGM] ダウンロード先: {tmpdir}")

            # 試行1: mp3 変換（ffmpeg あり）
            if ffmpeg:
                print("[BGM] 試行1: mp3 変換ダウンロード中...")
                r = subprocess.run(
                    [sys.executable, "-m", "yt_dlp", "--no-playlist",
                     "-x", "--audio-format", "mp3", "--audio-quality", "5",
                     "--ffmpeg-location", os.path.dirname(ffmpeg),
                     "-o", tmpl, youtube_url],
                    capture_output=True, text=True, timeout=180)
                files = glob.glob(os.path.join(tmpdir, "bgm.*"))
                print(f"[BGM] 試行1 生成: {files}")
                for f in files:
                    if _try_play(f):
                        return

            # 試行2: 変換なし → webm なら wav に変換
            for f in glob.glob(os.path.join(tmpdir, "bgm.*")):
                try: os.remove(f)
                except OSError: pass
            print("[BGM] 試行2: 変換なしダウンロード中...")
            subprocess.run(
                [sys.executable, "-m", "yt_dlp", "--no-playlist",
                 "-f", "bestaudio[ext=mp3]/bestaudio",
                 "-o", tmpl, youtube_url],
                capture_output=True, text=True, timeout=180)
            files = glob.glob(os.path.join(tmpdir, "bgm.*"))
            print(f"[BGM] 試行2 生成: {files}")
            for f in sorted(files, key=os.path.getsize, reverse=True):
                if f.endswith((".webm", ".opus", ".ogg")) and ffmpeg:
                    print(f"[BGM] {os.path.basename(f)} → wav 変換中...")
                    wav = _webm_to_wav(f, ffmpeg)
                    if wav and _try_play(wav):
                        return
                elif _try_play(f):
                    return
            print("[BGM] すべての試行が失敗しました。")
        except Exception as e:
            import traceback
            print(f"[BGM] エラー: {e}")
            traceback.print_exc()

    threading.Thread(target=_worker, daemon=True).start()

# =============================================================================
#  ブロック描画（光沢3D風）
# =============================================================================

# アイテム記号描画用フォントキャッシュ
_item_font_cache: dict = {}

_browser_ft_obj = None  # ブラウザ用 freetype Font オブジェクト（共有）
_BROWSER_FONT_PATH = '/home/pyodide/NotoSansJP-Regular.ttf'
_browser_sdl_ttf_ok = None  # SDL_ttf でフォントが使えるか（None=未確認）

def _get_browser_font(size):
    """ブラウザ環境: /home/pyodide/ のフォントを SDL_ttf → freetype → デフォルト の順で試す"""
    global _browser_ft_obj, _browser_sdl_ttf_ok
    # SDL_ttf を最初に試す（pygame.font.Font）
    if _browser_sdl_ttf_ok is None:
        try:
            import os as _os2
            if _os2.path.exists(_BROWSER_FONT_PATH) and _os2.path.getsize(_BROWSER_FONT_PATH) > 1000:
                _tf = pygame.font.Font(_BROWSER_FONT_PATH, 16)
                _ts2 = _tf.render("日", True, (255, 255, 255))
                _browser_sdl_ttf_ok = _ts2.get_width() > 1
            else:
                _browser_sdl_ttf_ok = False
        except Exception:
            _browser_sdl_ttf_ok = False
    if _browser_sdl_ttf_ok:
        try:
            return pygame.font.Font(_BROWSER_FONT_PATH, size)
        except Exception:
            pass
    # freetype フォールバック
    if _browser_ft_obj is None:
        try:
            import pygame.freetype as _pft2
            _browser_ft_obj = _pft2.Font(_BROWSER_FONT_PATH)
            _browser_ft_obj.antialiased = True
        except Exception:
            _browser_ft_obj = False
    if _browser_ft_obj and _browser_ft_obj is not False:
        class _FTFontG:
            def __init__(self, ft, sz):
                self._ft, self._size = ft, sz
            def render(self, text, antialias, color):
                if not text: return pygame.Surface((1, self._size), pygame.SRCALPHA)
                try:
                    s, _ = self._ft.render(text, fgcolor=color, size=self._size)
                    return s
                except: return pygame.Surface((self._size, self._size), pygame.SRCALPHA)
            def get_height(self): return self._size
            def get_linesize(self): return int(self._size * 1.3)
        return _FTFontG(_browser_ft_obj, size)
    # 最終フォールバック
    return pygame.font.Font(None, size)

def _get_item_font(size):
    if size not in _item_font_cache:
        if _IN_BROWSER:
            _item_font_cache[size] = _get_browser_font(max(8, size - 10))
        else:
            _item_font_cache[size] = pygame.font.SysFont("Arial", max(8, size - 10), bold=True)
    return _item_font_cache[size]

def _rainbow_color(offset=0.0):
    """時間に連動してレインボーサイクルする色を返す（offset で位相をずらす）"""
    t = pygame.time.get_ticks() / 350.0 + offset
    return (
        int(127 + 128 * math.sin(t)),
        int(127 + 128 * math.sin(t + 2.094)),   # +2π/3
        int(127 + 128 * math.sin(t + 4.189)),   # +4π/3
    )

def draw_cell(surface, px, py, color, size=CELL, alpha=255, item_type=None):
    """光沢のある 3D ブロックを描く。野菜ディテール付き農業テーマ版"""
    if alpha < 255:
        # ゴースト：枠線のみ半透明
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha//3), (1, 1, size-2, size-2), border_radius=3)
        pygame.draw.rect(s, (*color, alpha),    (1, 1, size-2, size-2), width=1, border_radius=3)
        surface.blit(s, (px, py))
        return

    # ── 恵みの雨（RAINBOW）：ブロック色をレインボーサイクリングに上書き ──
    if item_type == 'RAINBOW':
        color = _rainbow_color()

    # ── 恵みの雨（RAINBOW）：多層グロー＋スパークル ──
    if item_type == 'RAINBOW':
        ticks  = pygame.time.get_ticks()
        pulse  = 0.60 + 0.40 * math.sin(ticks / 130.0)
        ext    = 12   # グロー張り出し幅
        glow   = pygame.Surface((size + ext*2, size + ext*2), pygame.SRCALPHA)
        for i in range(5):
            m  = i * 2
            gc = _rainbow_color(offset=i * 0.35)
            a  = int(90 * pulse * (5 - i) / 5)
            pygame.draw.rect(glow, (*gc, a),
                             (m, m, size + ext*2 - m*2, size + ext*2 - m*2),
                             border_radius=7)
        surface.blit(glow, (px - ext, py - ext))

        # 雨粒スパークル（十字型）
        rng = random.Random(px * 997 + py * 31 + ticks // 100)
        for _ in range(5):
            sx  = px - 6 + rng.randint(0, size + 12)
            sy  = py - 6 + rng.randint(0, size + 12)
            sc  = _rainbow_color(offset=rng.random() * 3.0)
            arm = rng.randint(2, 4)
            pygame.draw.line(surface, sc, (sx - arm, sy), (sx + arm, sy), 1)
            pygame.draw.line(surface, sc, (sx, sy - arm), (sx, sy + arm), 1)
            pygame.draw.circle(surface, (255, 255, 255), (sx, sy), 1)

    # ── 耕運機 / 完熟堆肥 / 除草：グロー ──
    elif item_type in ('DRILL', 'COMPOST', 'WEEDER'):
        glow_colors = {
            'DRILL':   (100, 220, 255),
            'COMPOST': (255, 180,  50),
            'WEEDER':  (100, 240, 130),
        }
        glow_col = glow_colors[item_type]
        glow = pygame.Surface((size + 8, size + 8), pygame.SRCALPHA)
        for i, a in enumerate([50, 35, 20]):
            m = i * 2
            pygame.draw.rect(glow, (*glow_col, a),
                             (m, m, size + 8 - m*2, size + 8 - m*2), border_radius=5)
        surface.blit(glow, (px - 4, py - 4))

    # ── ブロック本体 ──
    # 色からどの野菜か逆引き（アイテム色は除外）
    piece_kind = next((k for k, c in PIECE_COLORS.items() if c == color), None)
    # 丸い野菜（きゅうり・マンゴー・トマト・なす）は角丸を強調
    round_kinds = {'S', 'O', 'Z', 'T', 'J'}
    brad = 7 if piece_kind in round_kinds else 3
    r = pygame.Rect(px+1, py+1, size-2, size-2)
    pygame.draw.rect(surface, color, r, border_radius=brad)

    # 上・左ハイライト
    bright = tuple(min(255, c + 72) for c in color)
    pygame.draw.rect(surface, bright, (px+2, py+2, size-4, 4))
    pygame.draw.rect(surface, bright, (px+2, py+6, 4,  size-8))

    # 下・右シャドウ
    dark = tuple(max(0, c - 68) for c in color)
    pygame.draw.rect(surface, dark, (px+2,      py+size-5, size-4, 4))
    pygame.draw.rect(surface, dark, (px+size-5, py+2,      4,      size-7))

    # 鏡面ハイライト（左上コーナー）
    spec = tuple(min(255, c + 140) for c in color)
    pygame.draw.rect(surface, spec, (px+3, py+3, 6, 3))
    pygame.draw.rect(surface, spec, (px+3, py+3, 3, 6))

    if piece_kind and size >= 20:
        cx_c = px + size // 2   # セル中央X
        cy_c = py + size // 2   # セル中央Y

        # ── 白ねぎ（I）: 断面の年輪風・横縞 ──
        if piece_kind == 'I':
            # 薄い横帯2本（ネギの節）
            band = (min(255, color[0]+40), min(255, color[1]+40), min(255, color[2]+30))
            pygame.draw.rect(surface, band, (px+3, py + size//3 - 1, size-6, 3))
            pygame.draw.rect(surface, band, (px+3, py + size*2//3 - 1, size-6, 3))
            # 中心に白い髄（白ねぎの内側）
            pygame.draw.ellipse(surface, (240, 255, 240),
                                (cx_c - size//6, cy_c - size//5, size//3, size*2//5))

        # ── マンゴー（O）: 完熟グラデーション（左上オレンジ→右下ゴールド）+ 縦長光沢 ──
        elif piece_kind == 'O':
            # ①完熟ブラッシュ: 左上コーナーに赤〜オレンジの半透明グラデーション
            grad = pygame.Surface((size - 2, size - 2), pygame.SRCALPHA)
            for step in range(6):
                alpha  = 95 - step * 14
                radius = (size * (6 - step)) // 7
                pygame.draw.circle(grad, (215, 55, 0, max(0, alpha)),
                                   (size // 4, size // 5), radius)
            surface.blit(grad, (px + 1, py + 1))
            # ②縦に細長い光沢（果実の張り・太陽のたまご風ハイライト）
            pygame.draw.ellipse(surface, (255, 252, 185),
                                (px + size//4,     py + size//10,
                                 max(4, size//5),  size * 2 // 5))
            # ③右下の反射（黄色い照り返し）
            pygame.draw.ellipse(surface, (255, 220, 80),
                                (px + size * 11 // 20, py + size * 11 // 20,
                                 max(4, size // 5),    max(3, size // 6)))

        # ── なす（T）: つやつや茄子 + 緑のへた ──
        elif piece_kind == 'T':
            # 光沢ハイライト（紫の明るい楕円）
            pygame.draw.ellipse(surface, (200, 120, 255),
                                (px + size//5, py + size//6, size//3, size*2//5))
            # 緑のへた（上部中央）
            heta_col = (30, 140, 30)
            pygame.draw.rect(surface, heta_col,
                             (cx_c - size//5, py+1, size*2//5, size//5), border_radius=2)
            pygame.draw.line(surface, heta_col,
                             (cx_c - size//4, py+3), (cx_c - size//3, py-2), 2)
            pygame.draw.line(surface, heta_col,
                             (cx_c + size//4, py+3), (cx_c + size//3, py-2), 2)

        # ── きゅうり（S）: 深い緑 + 肩グラデーション + トゲ白点 + 花の残り ──
        elif piece_kind == 'S':
            # ①胴体を少し深い緑でオーバーレイ（下部の深み）
            deep = (max(0, color[0]-18), max(0, color[1]-25), max(0, color[2]-8))
            pygame.draw.rect(surface, deep,
                             (px+2, py + size//4, size-4, size*3//4 - 3), border_radius=4)
            # ②上部の肩：黄緑（収穫直後の色）
            shoulder = (85, 210, 45)
            pygame.draw.rect(surface, shoulder,
                             (px+2, py+2, size-4, size//4), border_radius=4)
            # ③縦の稜線（きゅうりの筋）
            ridge = (max(0, color[0]-10), min(255, color[1]+35), max(0, color[2]-5))
            for rx_off in (size//4, size//2, size*3//4):
                pygame.draw.line(surface, ridge,
                                 (px + rx_off, py+3), (px + rx_off, py+size-4), 1)
            # ④イボイボ（緑の円）+ 中心に白い鋭いトゲ先端
            dot_col = (min(255, color[0]+55), min(255, color[1]+50), min(255, color[2]+25))
            bump_pos = [(size//4, size//3), (size*3//4, size//4),
                        (size//3, size*2//3), (size*2//3, size*2//3)]
            for bdx, bdy in bump_pos:
                pygame.draw.circle(surface, dot_col,
                                   (px + bdx, py + bdy), max(2, size//14))
                pygame.draw.circle(surface, (235, 255, 210),
                                   (px + bdx, py + bdy), max(1, size//24))
            # ⑤乾燥した花の残り（右下の小さな黄色ドット）
            pygame.draw.circle(surface, (215, 205, 25),
                               (px + size*3//4, py + size - 6), max(2, size//17))

        # ── トマト（Z）: ヘタ（星型5葉）+ 縦筋 ──
        elif piece_kind == 'Z':
            # 縦方向のハイライト筋（トマトのくびれ）
            seg_col = (min(255, color[0]+30), max(0, color[1]-10), max(0, color[2]-10))
            pygame.draw.line(surface, seg_col, (cx_c, py+9), (cx_c, py+size-5), 1)
            # ヘタ: 星型（5枚の三角形の葉）
            stem_col  = (25, 145, 25)
            stem_dark = (15, 100, 15)
            cy_stem   = py + 7
            # 中央の軸（小さな濃い緑円）
            pygame.draw.circle(surface, stem_dark, (cx_c, cy_stem), max(2, size//14))
            # 5枚の葉（三角ポリゴン）
            for i in range(5):
                ang    = math.radians(-90 + i * 72)
                tip_x  = int(cx_c + (size // 5) * math.cos(ang))
                tip_y  = int(cy_stem + (size // 5) * math.sin(ang))
                la = ang - math.radians(28)
                ra = ang + math.radians(28)
                br = max(2, size // 12)
                lx = int(cx_c + br * math.cos(la))
                ly = int(cy_stem + br * math.sin(la))
                rx_ = int(cx_c + br * math.cos(ra))
                ry_ = int(cy_stem + br * math.sin(ra))
                pygame.draw.polygon(surface, stem_col,
                                    [(tip_x, tip_y), (lx, ly), (rx_, ry_)])

        # ── ブルーベリー（J）: 丸い艶 + 王冠 ──
        elif piece_kind == 'J':
            # 大きな白〜青グロー楕円
            pygame.draw.ellipse(surface, (140, 180, 255),
                                (px + size//4, py + size//6, size//3, size//3))
            # 特徴的な5点クラウン（上端中央）
            crown_col = (100, 140, 220)
            for i in range(5):
                ang = math.radians(-90 + i * 72)
                r_crown = size // 6
                bx_c = int(cx_c + r_crown * math.cos(ang))
                by_c = int(py + 4 + r_crown * math.sin(ang))
                pygame.draw.circle(surface, crown_col, (bx_c, by_c), max(2, size//16))

        # ── にんじん（L）: 横の節 + 緑の葉芽 ──
        elif piece_kind == 'L':
            # 横方向の暗い帯（にんじんの節）
            ring_col = (max(0, color[0]-40), max(0, color[1]-20), max(0, color[2]-5))
            for ry_off in (size//3, size*2//3):
                pygame.draw.line(surface, ring_col,
                                 (px+3, py+ry_off), (px+size-4, py+ry_off), 2)
            # 上部に小さな緑の葉
            leaf_col = (50, 160, 40)
            pygame.draw.line(surface, leaf_col, (cx_c-3, py+3), (cx_c-6, py-2), 2)
            pygame.draw.line(surface, leaf_col, (cx_c,   py+2), (cx_c,   py-3), 2)
            pygame.draw.line(surface, leaf_col, (cx_c+3, py+3), (cx_c+6, py-2), 2)

    # ── アイテムブロック：中央に記号 ──
    if item_type and size >= 16:
        sym_map = {'RAINBOW': '★', 'DRILL': '耕', 'COMPOST': '肥', 'WEEDER': '刈'}
        symbol  = sym_map.get(item_type, '★')
        font   = _get_item_font(size)
        shd_s  = font.render(symbol, True, (0, 0, 0))
        shd_r  = shd_s.get_rect(center=(px + size//2 + 1, py + size//2 + 1))
        surface.blit(shd_s, shd_r)
        sym_col = _rainbow_color(offset=1.5) if item_type == 'RAINBOW' else (255, 255, 255)
        sym_s   = font.render(symbol, True, sym_col)
        sym_r   = sym_s.get_rect(center=(px + size//2, py + size//2))
        surface.blit(sym_s, sym_r)

# =============================================================================
#  パーティクル（火花）クラス
# =============================================================================

class Particle:
    """ブロック消去時に飛び散る小さな四角形パーティクル"""
    __slots__ = ('x','y','vx','vy','color','life','max_life','size')

    def __init__(self, x, y, color):
        self.x       = float(x)
        self.y       = float(y)
        angle        = random.uniform(0, 2 * math.pi)
        speed        = random.uniform(2.0, 7.0)
        self.vx      = math.cos(angle) * speed
        self.vy      = math.sin(angle) * speed - 1.5   # 少し上向きバイアス
        self.color   = color
        self.life    = random.randint(22, 42)
        self.max_life = self.life
        self.size    = random.randint(3, 7)

    def update(self):
        """移動・減衰。生存していれば True を返す"""
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.28          # 重力
        self.vx *= 0.96          # 空気抵抗
        self.life -= 1
        return self.life > 0

    def draw(self, surface):
        alpha = int(255 * self.life / self.max_life)
        size  = max(1, int(self.size * self.life / self.max_life))
        s = pygame.Surface((size, size), pygame.SRCALPHA)
        s.fill((*self.color[:3], alpha))
        surface.blit(s, (int(self.x) - size // 2, int(self.y) - size // 2))


# =============================================================================
#  スコアポップアップ
# =============================================================================

class ScorePopup:
    """スコア加算時にボード上でふわっと浮き上がる数字（カスタムテキスト・色対応）"""
    __slots__ = ('x', 'y', 'text', 'life', 'max_life', 'color')

    def __init__(self, x, y, pts=None, text=None, color=(255, 215, 40)):
        self.x        = float(x)
        self.y        = float(y)
        self.text     = text if text is not None else f"+{pts:,}"
        self.color    = color
        self.life     = 68
        self.max_life = 68

    def update(self):
        self.y    -= 1.4      # 上方向に浮上
        self.life -= 1
        return self.life > 0

    def draw(self, surface, font):
        alpha = int(255 * self.life / self.max_life)
        surf  = font.render(self.text, True, self.color)
        surf.set_alpha(alpha)
        surface.blit(surf, surf.get_rect(center=(int(self.x), int(self.y))))

# =============================================================================
#  背景アンビエントパーティクル（テーマ固有）
# =============================================================================

class BgParticle:
    """テーマに応じた背景の演出パーティクル（泡・葉・炎・星）"""
    __slots__ = ('ptype','x','y','vx','vy','size','alpha','angle','rot_speed',
                 'twinkle','color')

    def __init__(self, ptype, initial=False):
        self.ptype = ptype
        self._reset(initial)

    def _reset(self, initial=False):
        pt = self.ptype
        self.x         = random.uniform(0, SCREEN_W)
        self.angle     = random.uniform(0, 360)
        self.rot_speed = random.uniform(-1.8, 1.8)
        self.twinkle   = random.uniform(0, math.pi * 2)

        if pt == 'bubble':
            self.y     = random.uniform(0, SCREEN_H) if initial else SCREEN_H + 10.0
            self.vy    = -random.uniform(0.35, 0.95)
            self.vx    = random.uniform(-0.12, 0.12)
            self.size  = random.randint(2, 5)
            self.alpha = random.randint(45, 120)
            self.color = (115, 195, 255)
        elif pt == 'leaf':
            self.y     = random.uniform(0, SCREEN_H) if initial else -12.0
            self.vy    = random.uniform(0.55, 1.4)
            self.vx    = random.uniform(-0.6, 0.6)
            self.size  = random.randint(5, 9)
            self.alpha = random.randint(95, 185)
            self.color = random.choice(
                [(50,160,55),(40,140,45),(70,185,60),(110,85,30),(85,165,50)])
        elif pt == 'ember':
            self.y     = random.uniform(0, SCREEN_H) if initial else SCREEN_H + 10.0
            self.vy    = -random.uniform(0.55, 2.0)
            self.vx    = random.uniform(-0.45, 0.45)
            self.size  = random.randint(1, 3)
            self.alpha = random.randint(160, 255)
            self.color = random.choice([(255,80,0),(255,145,0),(255,205,80)])
        else:  # star
            self.y     = random.uniform(0, SCREEN_H)
            self.vy    = random.uniform(0.03, 0.18)
            self.vx    = 0.0
            self.size  = random.randint(1, 2)
            self.alpha = random.randint(115, 225)
            self.color = random.choice(
                [(255,255,255),(200,200,255),(255,240,200),(180,220,255)])

    def update(self):
        self.x += self.vx
        self.y += self.vy
        if self.ptype == 'leaf':
            self.angle += self.rot_speed
        if self.ptype == 'star':
            self.twinkle += 0.038
        # 画面外でリセット
        if self.ptype in ('bubble','ember') and self.y < -15:
            self._reset()
        elif self.ptype == 'leaf' and self.y > SCREEN_H + 15:
            self._reset()
        elif self.ptype == 'star' and self.y > SCREEN_H + 5:
            self.y = -3.0
            self.x = random.uniform(0, SCREEN_W)

    def draw(self, surface):
        pt  = self.ptype
        ix  = int(self.x)
        iy  = int(self.y)
        sz  = self.size
        col = self.color
        a   = self.alpha

        if pt == 'bubble':
            s = pygame.Surface((sz*2+4, sz*2+4), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, a//3), (sz+2, sz+2), sz)
            pygame.draw.circle(s, (*col, a),    (sz+2, sz+2), sz, 1)
            surface.blit(s, (ix - sz - 2, iy - sz - 2))

        elif pt == 'leaf':
            s = pygame.Surface((sz*3+2, sz*2+2), pygame.SRCALPHA)
            pygame.draw.ellipse(s, (*col, a), (0, 0, sz*3, sz*2))
            rot = pygame.transform.rotate(s, self.angle)
            surface.blit(rot, rot.get_rect(center=(ix, iy)))

        elif pt == 'ember':
            s = pygame.Surface((sz*2+2, sz*2+2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, a), (sz+1, sz+1), sz)
            surface.blit(s, (ix - sz - 1, iy - sz - 1))

        else:  # star
            tw_a = int(a * (0.55 + 0.45 * math.sin(self.twinkle)))
            s = pygame.Surface((sz*2+2, sz*2+2), pygame.SRCALPHA)
            pygame.draw.circle(s, (*col, tw_a), (sz+1, sz+1), sz)
            if sz >= 2:   # 十字ハイライト
                pygame.draw.line(s, (*col, tw_a//2),
                                 (sz+1, 0), (sz+1, sz*2+1))
                pygame.draw.line(s, (*col, tw_a//2),
                                 (0, sz+1), (sz*2+1, sz+1))
            surface.blit(s, (ix - sz - 1, iy - sz - 1))

# =============================================================================
#  7-Bag ランダマイザー（公式テトリスのランダム方式）
# =============================================================================

class SevenBag:
    def __init__(self):
        self._queue = []

    def _fill(self):
        bag = list(TETROMINOES.keys())
        random.shuffle(bag)
        self._queue.extend(bag)

    def peek(self, n):
        while len(self._queue) < n:
            self._fill()
        return list(self._queue[:n])

    def pop(self):
        self.peek(1)
        kind = self._queue.pop(0)
        # 15% の確率でいずれかのアイテムタイプを付与
        item = random.choice(ITEM_TYPES) if random.random() < ITEM_CHANCE else None
        return Piece(kind, item_type=item)

# =============================================================================
#  テトリミノクラス
# =============================================================================

ITEM_TYPES    = ['RAINBOW', 'DRILL', 'COMPOST', 'WEEDER']
ITEM_CHANCE   = 0.18   # アイテム付与確率 18%

# アイテムブロックの色（通常色に重ねて表示）
ITEM_COLORS = {
    'RAINBOW': (255, 230,  60),   # 恵みの雨: 金色
    'DRILL':   ( 80, 220, 255),   # 耕運機: 水色
    'COMPOST': (255, 175,  40),   # 完熟堆肥: 黄金アンバー
    'WEEDER':  ( 80, 230, 110),   # 除草・草刈機: エメラルドグリーン
}

# アイテム表示名（農業テーマ）
ITEM_DISPLAY = {
    'RAINBOW': '恵みの雨',     # 虹色の雨で浄化・行消去
    'DRILL':   '耕運機',       # 土を耕してブロックを縦破壊
    'COMPOST': '完熟堆肥',     # 豊作スコアボーナス＋ゾーン蓄積
    'WEEDER':  '除草・草刈機', # 邪魔なガーベージを一掃
}

class Piece:
    def __init__(self, kind, item_type=None):
        self.kind      = kind
        self.shape     = copy.deepcopy(TETROMINOES[kind])
        self.color     = PIECE_COLORS[kind]
        self.x         = COLS // 2 - 2
        self.y         = 0
        self.rot       = 0   # 回転ステート 0=North 1=East 2=South 3=West
        self.item_type = item_type   # None / 'RAINBOW' / 'DRILL'
        # アイテム付きは色をアイテムカラーで上書き
        if item_type:
            self.color = ITEM_COLORS[item_type]

    def rotate(self):
        """時計回り（CW）回転"""
        n = len(self.shape)
        return [[self.shape[n-1-j][i] for j in range(n)] for i in range(n)]

    def rotate_ccw(self):
        """反時計回り（CCW）回転"""
        n = len(self.shape)
        return [[self.shape[j][n-1-i] for j in range(n)] for i in range(n)]

    def cells(self, shape=None, dx=0, dy=0):
        s = shape if shape is not None else self.shape
        return [(self.x+c+dx, self.y+r+dy)
                for r, row in enumerate(s)
                for c, val in enumerate(row) if val]

# =============================================================================
#  ボードクラス
# =============================================================================

class Board:
    def __init__(self):
        self.grid = [[None]*COLS for _ in range(ROWS)]

    def is_valid(self, cells):
        for x, y in cells:
            if x < 0 or x >= COLS or y >= ROWS:
                return False
            if y >= 0 and self.grid[y][x] is not None:
                return False
        return True

    def lock(self, piece):
        for x, y in piece.cells():
            if 0 <= y < ROWS and 0 <= x < COLS:
                self.grid[y][x] = piece.color

    def clear_lines(self):
        # ゾーン行（ZONE_CELL で埋まった行）は通常クリアの対象外として保持する
        new_grid = [row for row in self.grid
                    if any(c is None for c in row)              # 未完成行→保持
                    or any(c == ZONE_CELL for c in row)]        # ゾーン行→保持
        cleared  = ROWS - len(new_grid)
        for _ in range(cleared):
            new_grid.insert(0, [None]*COLS)
        self.grid = new_grid
        return cleared

    def push_garbage_lines(self, count):
        """count 行のガーベージ行を最下部に挿入し既存ブロックを上に押し上げる。
        最上行が押し出された（オーバーフロー）場合は True を返す。"""
        overflow = False
        for _ in range(count):
            # 最上行に非 None ブロックがあればオーバーフロー
            if any(c is not None and c != ZONE_CELL for c in self.grid[0]):
                overflow = True
            # 全行を 1 行上にシフト（先頭を捨てる）
            self.grid.pop(0)
            # 穴あきガーベージ行を最下行に追加（穴は 1 列ランダム）
            hole_col = random.randint(0, COLS - 1)
            new_row  = [None if c == hole_col else GARBAGE_COLOR
                        for c in range(COLS)]
            self.grid.append(new_row)
        return overflow

# =============================================================================
#  ハイスコア読み書き
# =============================================================================

def load_hiscore():
    if _IN_BROWSER:
        try:
            from js import localStorage
            val = localStorage.getItem('daishukaku_hiscore')
            return int(val) if val is not None else 0
        except Exception:
            return 0
    try:
        with open(HISCORE_FILE) as f:
            return int(f.read().strip())
    except Exception:
        return 0

def save_hiscore(score):
    if _IN_BROWSER:
        try:
            from js import localStorage
            localStorage.setItem('daishukaku_hiscore', str(score))
        except Exception:
            pass
        return
    try:
        with open(HISCORE_FILE, 'w') as f:
            f.write(str(score))
    except Exception:
        pass

# =============================================================================
#  UI描画ヘルパー
# =============================================================================

def draw_panel_box(surface, rect, title=None, font=None,
                   panel_col=(22,32,60), border_col=(55,78,120), dim_col=(100,115,155)):
    """ラベル付きパネルボックスを描く（色はテーマに応じて上書き可）"""
    pygame.draw.rect(surface, panel_col,  rect, border_radius=8)
    pygame.draw.rect(surface, border_col, rect, width=2, border_radius=8)
    if title and font:
        t = font.render(title, True, dim_col)
        surface.blit(t, (rect.x + 9, rect.y + 6))

def draw_tetris_logo(surface, cx, y, font):
    """TETRIS を虹色で描く"""
    letters = "TETRIS"
    surfs   = [font.render(ch, True, LOGO_COLORS[i]) for i, ch in enumerate(letters)]
    total_w = sum(s.get_width() for s in surfs)
    x = cx - total_w // 2
    for s in surfs:
        surface.blit(s, (x, y))
        x += s.get_width()

def draw_level_badge(surface, cx, cy, level, font_num, font_lbl,
                     border_col=(55,78,120), dim_col=(100,115,155)):
    """ダイヤモンド形のレベルバッジ"""
    sz = 44
    pts = [(cx, cy-sz), (cx+sz, cy), (cx, cy+sz), (cx-sz, cy)]
    # 塗り
    pygame.draw.polygon(surface, (38, 52, 88), pts)
    # 枠
    pygame.draw.polygon(surface, border_col, pts, 2)
    # 農家ランク ラベル
    lbl = font_lbl.render("農家ランク", True, dim_col)
    surface.blit(lbl, lbl.get_rect(center=(cx, cy - sz + 16)))
    # 数字
    num = font_num.render(str(level), True, C_GOLD)
    surface.blit(num, num.get_rect(center=(cx, cy + 10)))

def draw_mini_piece(surface, kind, cx, cy, cell_size=18):
    """NEXT / HOLD 用ミニピース（中心座標指定）"""
    shape = TETROMINOES[kind]
    color = PIECE_COLORS[kind]
    cells = [(c, r) for r, row in enumerate(shape)
             for c, v in enumerate(row) if v]
    if not cells:
        return
    min_c = min(c for c, _ in cells)
    max_c = max(c for c, _ in cells)
    min_r = min(r for _, r in cells)
    max_r = max(r for _, r in cells)
    w = (max_c - min_c + 1) * cell_size
    h = (max_r - min_r + 1) * cell_size
    ox = cx - w // 2
    oy = cy - h // 2
    for c, r in cells:
        draw_cell(surface, ox + (c - min_c)*cell_size,
                  oy + (r - min_r)*cell_size, color, cell_size)

# =============================================================================
#  メインゲームクラス
# =============================================================================

class Tetris:

    def __init__(self):
        # ── ブラウザ環境ではオーディオをスキップ、display は run() 内で初期化 ──
        if _IN_BROWSER:
            # set_mode() は Pyodide 環境では動作しないため、
            # オフスクリーン Surface + JavaScript canvas putImageData で代替
            print("[INIT] ブラウザモード: オフスクリーン Surface を使用")
            pygame.init()
            self.screen = pygame.Surface((SCREEN_W, SCREEN_H))
            print(f"[INIT] Surface 作成 OK")
        else:
            try:
                pygame.mixer.pre_init(SAMPLE_RATE, -16, 2, 512)
            except Exception as e:
                print(f"[AUDIO] pre_init 失敗: {e}")
            pygame.init()
            pygame.display.set_caption("TETRIS")
            self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock  = pygame.time.Clock()

        # ── サウンド初期化（ブラウザ環境では全スキップ） ──
        self.snd_tetris      = None
        self.snd_move        = None
        self.snd_rotate      = None
        self.snd_lock        = None
        self.snd_clear_cache = {c: [None]*9 for c in range(1, 4)}
        self.snd_heartbeat   = None
        self.snd_item        = None
        self.snd_zone        = None
        self.snd_garbage     = None
        if not _IN_BROWSER:
            try:
                pygame.mixer.init()
                self.snd_tetris  = build_tetris_fanfare()
                self.snd_move    = _make_tone(380, 0.035, vol=0.12)
                self.snd_rotate  = _make_tone(560, 0.055, vol=0.15, harmonics=[(2, 0.2)])
                self.snd_lock    = _make_noise_burst(0.08, vol=0.22)
                self.snd_clear_cache = {
                    count: [_make_clear_sound(count, 2 ** (min(i, 8) / 12))
                            for i in range(9)]
                    for count in range(1, 4)
                }
                self.snd_heartbeat = _make_heartbeat()
                self.snd_item      = _make_item_sound()
                self.snd_zone      = _make_zone_sound()
                self.snd_garbage   = _make_garbage_sound()
                # BGM
                _bgm_path = os.path.join(_GAME_DIR, "テトリス  重音テトSV.mp3")
                pygame.mixer.music.load(_bgm_path)
                pygame.mixer.music.set_volume(0.4)
                pygame.mixer.music.play(-1)
            except Exception as e:
                print(f"[AUDIO] 初期化失敗: {e}")

        # フォント
        if _IN_BROWSER:
            # /home/pyodide/ は Pyodide の既定ホームで MEMFS に確実に存在する
            _FT_PATH = '/home/pyodide/NotoSansJP-Regular.ttf'

            # ファイル存在確認
            import os as _os
            _font_exists = _os.path.exists(_FT_PATH)
            _font_size_b = _os.path.getsize(_FT_PATH) if _font_exists else 0
            print(f"[FONT] path={_FT_PATH} exists={_font_exists} size={_font_size_b}")

            _ft_obj = None  # pygame.freetype.Font オブジェクト

            if _font_exists and _font_size_b > 1000:
                # ① pygame.font.Font (SDL_ttf) で試す
                try:
                    _test_f = pygame.font.Font(_FT_PATH, 20)
                    _test_s = _test_f.render("日", True, (255, 255, 255))
                    print(f"[FONT] SDL_ttf OK: 日=({_test_s.get_width()}x{_test_s.get_height()})")
                    del _test_f, _test_s
                    _sdl_ttf_ok = True
                except Exception as _e1:
                    print(f"[FONT] SDL_ttf 失敗: {_e1}")
                    _sdl_ttf_ok = False

                # ② pygame.freetype で試す（SDL_ttf が失敗した場合）
                if not _sdl_ttf_ok:
                    try:
                        import pygame.freetype as _pft
                        _ft_obj = _pft.Font(_FT_PATH)
                        _ft_obj.antialiased = True
                        _ts, _ = _ft_obj.render("日", fgcolor=(255, 255, 255), size=20)
                        print(f"[FONT] freetype OK: 日=({_ts.get_width()}x{_ts.get_height()})")
                    except Exception as _fe:
                        print(f"[FONT] freetype 失敗: {_fe}")
                        _ft_obj = None
            else:
                _sdl_ttf_ok = False
                print("[FONT] フォントファイルが見つからないためデフォルトフォントを使用")

            class _FTFont:
                """pygame.freetype.Font を pygame.font.Font 互換 API でラップ"""
                def __init__(self, ft, size):
                    self._ft   = ft
                    self._size = size
                def render(self, text, antialias, color):
                    if not text:
                        return pygame.Surface((1, self._size), pygame.SRCALPHA)
                    try:
                        s, _ = self._ft.render(text, fgcolor=color, size=self._size)
                        return s
                    except Exception:
                        return pygame.Surface((self._size, self._size), pygame.SRCALPHA)
                def get_height(self):   return self._size
                def get_linesize(self): return int(self._size * 1.3)
                def size(self, text):
                    try:
                        _, r = self._ft.render(text, fgcolor=(0, 0, 0), size=self._size)
                        return r.width, r.height
                    except:
                        return self._size * max(1, len(text)), self._size

            def _bf(size):
                # SDL_ttf が成功していればパス直接
                if _sdl_ttf_ok:
                    try:
                        return pygame.font.Font(_FT_PATH, size)
                    except Exception:
                        pass
                # freetype ラッパー
                if _ft_obj is not None:
                    return _FTFont(_ft_obj, size)
                # 最終フォールバック: デフォルトフォント
                return pygame.font.Font(None, size)

            self.f_logo     = _bf(34)
            self.f_big      = _bf(52)
            self.f_lv       = _bf(30)
            self.f_num      = _bf(24)
            self.f_med      = _bf(19)
            self.f_sm       = _bf(14)
            self.f_jp       = _bf(26)
            self.f_jp_sm    = _bf(14)
            self.f_ja_title = _bf(76)
            self.f_go_title = _bf(46)
            self.f_go_score = _bf(54)
        else:
            self.f_logo  = pygame.font.SysFont("Arial Black", 34, bold=True)
            self.f_big   = pygame.font.SysFont("Arial", 52, bold=True)
            self.f_lv    = pygame.font.SysFont("Arial", 30, bold=True)
            self.f_num   = pygame.font.SysFont("Arial", 24, bold=True)
            self.f_med   = pygame.font.SysFont("Arial", 19, bold=True)
            self.f_sm    = pygame.font.SysFont("Arial", 14)
            _jp_names = ["meiryo", "yugothic", "ms gothic", "msgothic"]
            self.f_jp       = pygame.font.SysFont(",".join(_jp_names), 26)
            self.f_jp_sm    = pygame.font.SysFont(",".join(_jp_names), 14)
            self.f_ja_title = pygame.font.SysFont(",".join(_jp_names), 76, bold=True)
            self.f_go_title = pygame.font.SysFont(",".join(_jp_names), 46, bold=True)
            self.f_go_score = pygame.font.SysFont("Arial Black", 54, bold=True)

        # エフェクト用オフスクリーンサーフェス（シェイク適用のため）
        self.game_surf = pygame.Surface((SCREEN_W, SCREEN_H))

        self.hi_score = load_hiscore()
        # ── DAS/ARR プリセット（ゲームをまたいで保持）──
        self.das_preset = 'NORMAL'
        # ── タイトル画面 ──
        self.state     = 'TITLE'   # 'TITLE' | 'PLAYING'
        if _IN_BROWSER:
            self.f_title = _bf(76)
        else:
            self.f_title = pygame.font.SysFont("Arial Black", 76, bold=True)
        # アトラクトモード Bot 状態
        self._attr_pid       = None
        self._attr_rdelta    = 0
        self._attr_tx        = 0
        self._attr_rots_done = 0
        self._attr_timer     = 0
        self._running = True   # メインループ制御フラグ（ブラウザ終了用）
        self._new_game()

    # ---------- タイトルへ戻る ----------
    def _go_title(self):
        """ゲームオーバー・プレイ中からタイトル画面へ安全に戻る"""
        _muted = getattr(self, 'bgm_muted', False)
        self._new_game()
        self.bgm_muted = _muted
        self.state = 'TITLE'
        # タイトルへ戻るときは BGM を止める
        if not _IN_BROWSER:
            try: pygame.mixer.music.stop()
            except Exception: pass
        self._js_bgm('stop')

    # ---------- 新規ゲーム ----------
    def _new_game(self):
        self.board        = Board()
        self.bag          = SevenBag()
        self.current      = self.bag.pop()
        self.hold_kind    = None
        self.can_hold     = True
        self.score        = 0
        self.lines        = 0
        self.level        = 1
        self.goal         = 10          # 次レベルまでのライン数
        self.fall_timer   = 0
        self.fall_speed   = FALL_NORMAL
        self.soft_drop    = False
        self.game_over    = False
        self.paused       = False
        self._attr_pid    = None   # アトラクトBot: ピース追跡リセット
        self.tetris_timer = 0
        self.move_timer   = 0
        self.move_dir     = 0
        self.bgm_muted    = False           # M キーでミュート切替（ブラウザは JS Audio API 使用）
        # --- ロックディレイ状態 ---
        self.is_landed        = False      # 現在ピースが接地中かどうか
        self.lock_timer       = 0          # 接地してからのフレーム数
        self.lock_reset_count = 0          # タイマーリセット済み回数
        # --- T-スピン状態 ---
        self.last_rotated     = False      # 最後の操作が回転だったか
        self._pending_tspin   = None       # ロック時に確定した T-スピン種別
        self.tspin_timer      = 0          # バナー表示残りフレーム
        self.tspin_text       = ""         # バナーテキスト
        # --- コンボ / Back-to-Back 状態 ---
        self.combo            = -1         # 連続ライン消去カウント（-1=コンボなし）
        self.b2b              = False      # Back-to-Back フラグ
        self.combo_timer      = 0          # コンボバナー表示残りフレーム
        self.combo_text       = ""         # コンボバナーテキスト
        # --- 詳細統計（ゲームオーバー画面用） ---
        self.stat_tspin       = 0          # T-Spin 回数（Mini + Full 合計）
        self.stat_max_combo   = 0          # 今回のプレイ最大コンボ数
        self.stat_zone_lines  = 0          # ゾーン中に消した累計ライン数
        self.stat_items_used  = 0          # アイテムブロック使用回数
        # --- エフェクト状態 ---
        self.flash_rows   = []             # フラッシュ中の行番号リスト
        self.flash_timer  = 0             # フラッシュ残りフレーム
        self.shake_timer  = 0             # シェイク残りフレーム
        self.shake_mag    = 0             # シェイクの最大振れ幅 (px)
        self.particles    = []            # アクティブなパーティクル一覧
        self.score_popups = []            # スコアポップアップ一覧
        self.levelup_timer = 0            # レベルアップ演出カウントダウン
        # --- ビジュアルテーマ ---
        self.theme_idx    = 0
        self.theme        = _theme_for_level(1)
        self.bg_particles = [
            BgParticle(self.theme['particle_type'], initial=True)
            for _ in range(self.theme['particle_count'])
        ]
        self.start_ticks  = pygame.time.get_ticks()
        self.elapsed_pause = 0
        self.pause_start  = 0
        # --- デンジャー（危険状態）検出 ---
        self.danger         = False    # 現在デンジャー中か
        self.prev_danger    = False    # 前フレームのデンジャー状態（遷移検出用）
        self.heartbeat_timer = 0       # 次の心拍まで残りフレーム
        # --- ゾーンシステム ---
        self.zone_gauge      = 0.0     # ゾーンゲージ（0〜100）
        self.is_zone_active  = False   # ゾーン発動中か
        self.zone_timer      = 0       # ゾーン残りフレーム
        self.zone_stack      = 0       # ゾーン中に蓄積したライン数
        self.zone_end_anim   = 0       # ゾーン終了演出カウントダウン
        # --- ガーベージシステム ---
        self.garbage_timer   = 0       # ガーベージ発生カウンター
        self.garbage_warning = False   # 警告中か
        self.garbage_pending = 0       # 警告中の予約行数（相殺で減らせる）

    # ---------- 次ピースをスポーン ----------
    def _spawn_next(self):
        self.current          = self.bag.pop()
        self.can_hold         = True
        self.is_landed        = False
        self.lock_timer       = 0
        self.lock_reset_count = 0
        self.last_rotated     = False
        self._pending_tspin   = None
        if not self.board.is_valid(self.current.cells()):
            self.game_over = True
            if self.score > self.hi_score:
                self.hi_score = self.score
                save_hiscore(self.hi_score)
            if not _IN_BROWSER:
                try: pygame.mixer.music.stop()
                except Exception: pass
            else:
                self._js_bgm('stop')

    # ---------- デンジャー判定 ----------
    def _is_danger(self):
        """ボードの上から4行のいずれかにブロックがあれば True"""
        for row in range(4):
            if any(self.board.grid[row]):
                return True
        return False

    # ---------- レベル依存 SFX 再構築 ----------
    def _build_level_sfx(self):
        """レベルが上がるほど回転音・ロック音を高く・鋭くする"""
        lv = self.level
        # 回転音: レベルごとに周波数+倍音を強化（最大 Lv20 を上限に）
        rot_freq   = 560 + min(lv - 1, 19) * 22          # 560〜978 Hz
        rot_fade   = max(0.10, 0.30 - (lv - 1) * 0.009)  # フェードを短くして鋭さを増す
        self.snd_rotate = _make_tone(
            rot_freq, 0.055, vol=0.15,
            harmonics=[(2, 0.2 + min(lv - 1, 19) * 0.02)],
            fade_ratio=rot_fade
        )
        # ロック音: レベルごとに音量を強化
        lock_vol = min(0.22 + (lv - 1) * 0.012, 0.42)
        self.snd_lock = _make_noise_burst(0.08, vol=lock_vol)

    # ---------- ゾーン発動 ----------
    def _start_zone(self):
        self.is_zone_active = True
        self.zone_timer     = ZONE_DURATION
        self.zone_stack     = 0
        self.zone_gauge     = 0.0
        # ロックタイマーをリセット（発動直後にロックされないよう）
        self.lock_timer     = 0
        if self.snd_zone and not self.bgm_muted:
            self.snd_zone.play()
        self._js_se('zone')
        # BGM を低音量にしてゾーン感を演出
        if not _IN_BROWSER and not self.bgm_muted:
            pygame.mixer.music.set_volume(0.10)

    # ---------- ゾーン終了 ----------
    def _end_zone(self):
        self.is_zone_active = False
        n = self.zone_stack
        self.stat_zone_lines += n   # ゾーン消去数を累積

        # ゾーン行をすべて除去して重力適用
        new_grid = [row for row in self.board.grid
                    if not all(c == ZONE_CELL for c in row)]
        while len(new_grid) < ROWS:
            new_grid.insert(0, [None] * COLS)
        self.board.grid = new_grid

        # 残ったブロックに列方向の重力を適用
        for col_x in range(COLS):
            col_data = [self.board.grid[r][col_x] for r in range(ROWS)]
            filled   = [c for c in col_data if c is not None and c != ZONE_CELL]
            empty    = [None] * (ROWS - len(filled))
            new_col  = empty + filled
            for r in range(ROWS):
                self.board.grid[r][col_x] = new_col[r]

        # ゾーン終了演出
        self.zone_end_anim  = 90
        self.shake_timer    = max(self.shake_timer, SHAKE_TETRIS * 2)
        self.shake_mag      = max(self.shake_mag, 10)

        if n > 0:
            bonus, label = self._zone_bonus(n)
            total = bonus * self.level
            self.score += total
            if self.score > self.hi_score:
                self.hi_score = self.score
                save_hiscore(self.hi_score)
            self.score_popups.append(
                ScorePopup(BOARD_X + BOARD_W // 2,
                           BOARD_Y + BOARD_H // 3,
                           text=f"{label}  +{total:,}",
                           color=(100, 210, 255)))
            # パーティクル大爆発
            for r in range(ROWS):
                for c in range(COLS):
                    if self.board.grid[r][c]:
                        px = BOARD_X + c * CELL + CELL // 2
                        py = BOARD_Y + r * CELL + CELL // 2
                        self.particles.append(Particle(px, py, (80, 160, 255)))

        # BGM 音量を戻す
        if not _IN_BROWSER and not self.bgm_muted:
            pygame.mixer.music.set_volume(0.22 if self.danger else 0.4)

        self.zone_stack = 0

    def _zone_bonus(self, n):
        """蓄積ライン数に応じたボーナス点とラベルを返す"""
        pts = n * n * 450
        if   n >= 18: label = "ULTIMATRIS!!"
        elif n >= 15: label = "ZONE PERFECT!"
        elif n >= 12: label = "ZONE MASTER!"
        elif n >=  9: label = "ZONE ULTRA!"
        elif n >=  6: label = "ZONE TETRIS!"
        elif n >=  4: label = "ZONE CLEAR!"
        else:         label = f"ZONE {n} LINE!"
        return pts, label

    # ---------- ガーベージ発生間隔・量の計算 ----------
    def _garbage_interval(self):
        """レベルに応じたガーベージ発生フレーム数（30秒→10秒に短縮）"""
        reduction = ((self.level - 1) // 5) * 300
        return max(600, 1800 - reduction)

    def _garbage_amount(self):
        """レベルに応じたガーベージ行数（1〜3）"""
        return min(3, 1 + (self.level - 1) // 10)

    # ---------- ガーベージ更新（毎フレーム呼び出し）----------
    def _update_garbage(self):
        """ガーベージタイマーを進め、警告→実行を管理する"""
        if self.is_zone_active or self.state == 'TITLE':
            return   # ゾーン中は停止

        self.garbage_timer += 1
        interval = self._garbage_interval()
        warn_at  = interval - GARBAGE_WARN_DUR

        # 警告フェーズ開始
        if self.garbage_timer == warn_at:
            self.garbage_warning = True
            self.garbage_pending = self._garbage_amount()
            if self.snd_garbage and not self.bgm_muted:
                self.snd_garbage.play()
            self._js_se('garbage')

        # ガーベージ実行
        if self.garbage_timer >= interval:
            self.garbage_timer = 0
            self.garbage_warning = False
            if self.garbage_pending > 0:
                overflow = self.board.push_garbage_lines(self.garbage_pending)
                # 上方シェイク演出
                self.shake_timer = max(self.shake_timer, 10)
                self.shake_mag   = max(self.shake_mag, 6)
                if overflow:
                    self.game_over = True
                    if not _IN_BROWSER:
                        try: pygame.mixer.music.stop()
                        except Exception: pass
                    else:
                        self._js_bgm('stop')
            self.garbage_pending = 0

    # ---------- ホールド ----------
    def _do_hold(self):
        if not self.can_hold:
            return
        self.can_hold = False
        if self.hold_kind is None:
            self.hold_kind = self.current.kind
            self._spawn_next()
        else:
            self.hold_kind, self.current = \
                self.current.kind, Piece(self.hold_kind)
        self._js_se('hold')

    # ---------- ゴースト位置 ----------
    def _ghost_dy(self):
        dy = 0
        while self.board.is_valid(self.current.cells(dy=dy+1)):
            dy += 1
        return dy

    # ---------- ロックディレイ：移動・回転後のリセット ----------
    def _lock_reset_on_action(self):
        """移動・回転が成功したとき、ロックディレイタイマーをリセットする。
        - 動いた結果ピースが浮いた → 接地状態を解除してタイマーをクリア
        - まだ接地中かつリセット上限内 → タイマーだけリセット（上限超えは無視）
        """
        if not self.is_landed:
            return
        if self.board.is_valid(self.current.cells(dy=1)):
            # 動いた先は宙に浮いている → 通常落下に戻す
            self.is_landed        = False
            self.lock_timer       = 0
            self.lock_reset_count = 0
        elif self.lock_reset_count < LOCK_RESET_MAX:
            # まだ接地しているがリセット回数が余っている
            self.lock_timer = 0
            self.lock_reset_count += 1

    # ---------- T-スピン検出 ----------
    def _detect_tspin(self):
        """現在ピースが T-スピンかどうかを判定する。
        戻り値: None（非T-スピン）/ 'mini'（T-Spin Mini）/ 'full'（T-Spin）
        条件:
          1. 現在ピースが T-ピース
          2. 最後の操作が回転（last_rotated == True）
          3. T-ピース 3×3 バウンディングボックスの四隅のうち 3 つ以上が塞がれている
          4. 前面の 2 隅がどちらも埋まっていれば full、1 つなら mini
        """
        p = self.current
        if p.kind != 'T' or not self.last_rotated:
            return None

        # T-ピース中心（3×3 ボックスの中心）
        cx, cy = p.x + 1, p.y + 1

        # 四隅: A=左上 B=右上 C=左下 D=右下
        corners = [
            (cx - 1, cy - 1),   # A
            (cx + 1, cy - 1),   # B
            (cx - 1, cy + 1),   # C
            (cx + 1, cy + 1),   # D
        ]

        def _blocked(x, y):
            if x < 0 or x >= COLS:
                return True          # 壁
            if y >= ROWS:
                return True          # 床
            if y < 0:
                return False         # 天井より上は空き
            return self.board.grid[y][x] is not None

        filled = [_blocked(x, y) for x, y in corners]
        if sum(filled) < 3:
            return None              # 3 隅未満 → T-スピンなし

        # 回転ステートごとの「前面」隅インデックス
        # North(0): 上2隅 A,B  East(1): 右2隅 B,D
        # South(2): 下2隅 C,D  West(3): 左2隅 A,C
        front_idx = {0: [0, 1], 1: [1, 3], 2: [2, 3], 3: [0, 2]}
        front_filled = sum(1 for i in front_idx[p.rot] if filled[i])

        return 'full' if front_filled == 2 else 'mini'

    # ---------- ハードドロップ ----------
    def _hard_drop(self):
        dy = self._ghost_dy()
        self.score += dy * 2
        self.current.y += dy
        # 着地の衝撃シェイク（ある程度落ちた時だけ）
        if dy >= 3:
            self.shake_timer = max(self.shake_timer, SHAKE_HARDDROP)
            self.shake_mag   = max(self.shake_mag, 3)
        self._js_se('drop')
        self._lock_piece()

    # ---------- ピース固定 ----------
    def _lock_piece(self):
        # ロックする前に T-スピンを判定（盤面にまだ置かれていない状態で判定）
        self._pending_tspin = self._detect_tspin()
        item = self.current.item_type   # アイテム種別を保存
        if self.snd_lock and not self.bgm_muted: self.snd_lock.play()
        self._js_se('lock')
        self.board.lock(self.current)

        # ── アイテム効果を発動 ──
        if item:
            self._activate_item(item, self.current.cells(), self.current.color)

        # 揃った行を検出（アイテム効果後の盤面で判定・ゾーン行は除外）
        self.flash_rows = [r for r in range(ROWS)
                           if all(c is not None for c in self.board.grid[r])
                           and not all(c == ZONE_CELL for c in self.board.grid[r])]
        if self.flash_rows:
            self.flash_timer = FLASH_DURATION   # フラッシュ開始（実際の消去は後）
        else:
            self._update_score(0)
            self._spawn_next()
        self.fall_timer = 0
        self.soft_drop  = False

    # ---------- アイテム効果発動 ----------
    def _activate_item(self, item, piece_cells, color):
        """アイテムブロックの効果を発動する"""
        self.stat_items_used += 1   # アイテム使用カウント
        if self.snd_item and not self.bgm_muted:
            self.snd_item.play()
        self._js_se('item')

        if item == 'RAINBOW':
            # ── RAINBOW: ピースが含まれる行を強制消去 ──
            rows = sorted(set(y for _, y in piece_cells if 0 <= y < ROWS))
            for r in rows:
                for c in range(COLS):
                    cell_col = self.board.grid[r][c]
                    if cell_col:
                        # パーティクルを派手に生成（通常の3倍）
                        # ZONE_CELLは文字列なので色を差し替え
                        ptcl_col = (60, 160, 255) if cell_col == ZONE_CELL else cell_col
                        px = BOARD_X + c * CELL + CELL // 2
                        py = BOARD_Y + r * CELL + CELL // 2
                        for _ in range(PARTICLE_PER_CELL * 3):
                            self.particles.append(Particle(px, py, ptcl_col))
                    self.board.grid[r][c] = None

            # 消去した行を詰める
            new_grid = [row for row in self.board.grid if any(c is not None for c in row)]
            cleared  = ROWS - len(new_grid)
            for _ in range(cleared):
                new_grid.insert(0, [None] * COLS)
            self.board.grid = new_grid

            # 派手なシェイク＋スコア加算
            self.shake_timer = max(self.shake_timer, SHAKE_TETRIS)
            self.shake_mag   = max(self.shake_mag, 7)
            bonus = 200 * len(rows) * self.level
            self.score += bonus
            self.score_popups.append(
                ScorePopup(BOARD_X + BOARD_W // 2,
                           BOARD_Y + BOARD_H // 3,
                           text=f"恵みの雨！ +{bonus:,}",
                           color=(255, 230, 60)))

        elif item == 'DRILL':
            # ── DRILL: ピース各列の真下 2〜3 マスを破壊 ──
            # 列ごとにピースの最下端行を求める
            col_bottom: dict[int, int] = {}
            for bx, by in piece_cells:
                if 0 <= bx < COLS and 0 <= by < ROWS:
                    col_bottom[bx] = max(col_bottom.get(bx, -1), by)

            drill_depth    = random.randint(2, 3)
            destroyed      = 0
            garbage_hits   = 0   # ガーベージ行を破壊した数
            for col_x, bot_y in col_bottom.items():
                for d in range(1, drill_depth + 1):
                    ty = bot_y + d
                    if 0 <= ty < ROWS and self.board.grid[ty][col_x] is not None:
                        cell_col = self.board.grid[ty][col_x]
                        if cell_col == GARBAGE_COLOR:
                            garbage_hits += 1
                        # パーティクル（ZONE_CELLは文字列なので色を差し替え）
                        ptcl_col = (60, 160, 255) if cell_col == ZONE_CELL else cell_col
                        px = BOARD_X + col_x * CELL + CELL // 2
                        py = BOARD_Y + ty   * CELL + CELL // 2
                        for _ in range(PARTICLE_PER_CELL * 2):
                            self.particles.append(Particle(px, py, ptcl_col))
                        self.board.grid[ty][col_x] = None
                        destroyed += 1

            # 重力: 穴が空いた列のブロックを下へ落下させる
            for col_x in col_bottom:
                column = [self.board.grid[r][col_x] for r in range(ROWS)]
                filled = [c for c in column if c is not None]
                empty  = [None] * (ROWS - len(filled))
                new_col = empty + filled
                for r in range(ROWS):
                    self.board.grid[r][col_x] = new_col[r]

            # シェイク＋スコア
            self.shake_timer = max(self.shake_timer, 8)
            self.shake_mag   = max(self.shake_mag, 5)
            if destroyed > 0:
                bonus = 80 * destroyed * self.level
                # ガーベージ破壊ボーナス（通常の 3 倍）
                if garbage_hits > 0:
                    g_bonus = 80 * garbage_hits * self.level * 2   # 合計 3 倍
                    bonus  += g_bonus
                    # ガーベージ予約もキャンセル
                    self.garbage_pending = max(0, self.garbage_pending - garbage_hits)
                    if self.garbage_pending == 0:
                        self.garbage_warning = False
                        self.garbage_timer   = 0
                self.score += bonus
                label = f"耕運機 一撃！ +{bonus:,}" if garbage_hits > 0 else f"耕運機！ +{bonus:,}"
                self.score_popups.append(
                    ScorePopup(BOARD_X + BOARD_W // 2,
                               BOARD_Y + BOARD_H // 2,
                               text=label,
                               color=(80, 220, 255)))

        elif item == 'COMPOST':
            # ── COMPOST (完熟堆肥): 黄金の豊作ボーナス＋ゾーンゲージ蓄積 ──
            for cx, cy in piece_cells:
                px = BOARD_X + cx * CELL + CELL // 2
                py = BOARD_Y + cy * CELL + CELL // 2
                for _ in range(PARTICLE_PER_CELL * 2):
                    self.particles.append(Particle(px, py, (255, 210, 60)))
            bonus = 350 * len(piece_cells) * self.level
            self.score += bonus
            if not self.is_zone_active:
                self.zone_gauge = min(ZONE_GAUGE_MAX, self.zone_gauge + 25.0)
            self.shake_timer = max(self.shake_timer, 6)
            self.shake_mag   = max(self.shake_mag, 4)
            self.score_popups.append(
                ScorePopup(BOARD_X + BOARD_W // 2,
                           BOARD_Y + BOARD_H // 3,
                           text=f"完熟堆肥・大豊作！ +{bonus:,}",
                           color=(255, 200, 50)))

        elif item == 'WEEDER':
            # ── WEEDER (除草・草刈機): 盤面最下部のガーベージ/雑草を一掃 ──
            garbage_rows = [r for r in range(ROWS)
                            if any(self.board.grid[r][c] == GARBAGE_COLOR for c in range(COLS))]
            target_rows = garbage_rows[-2:] if garbage_rows else []

            if not target_rows:
                bottom_occupied = [r for r in range(ROWS)
                                   if any(self.board.grid[r][c] is not None for c in range(COLS))]
                if bottom_occupied:
                    target_rows = [bottom_occupied[-1]]

            weeds_cleared = len(target_rows)
            if target_rows:
                for r in target_rows:
                    for c in range(COLS):
                        cell_col = self.board.grid[r][c]
                        if cell_col:
                            px = BOARD_X + c * CELL + CELL // 2
                            py = BOARD_Y + r * CELL + CELL // 2
                            for _ in range(PARTICLE_PER_CELL * 2):
                                self.particles.append(Particle(px, py, (100, 240, 130)))
                        self.board.grid[r][c] = None

                new_grid = [row for row in self.board.grid if any(c is not None for c in row)]
                for _ in range(ROWS - len(new_grid)):
                    new_grid.insert(0, [None] * COLS)
                self.board.grid = new_grid

                self.garbage_pending = max(0, self.garbage_pending - weeds_cleared)
                if self.garbage_pending == 0:
                    self.garbage_warning = False
                    self.garbage_timer   = 0

            self.shake_timer = max(self.shake_timer, 8)
            self.shake_mag   = max(self.shake_mag, 5)
            bonus = 250 * max(1, weeds_cleared) * self.level
            self.score += bonus
            self.score_popups.append(
                ScorePopup(BOARD_X + BOARD_W // 2,
                           BOARD_Y + BOARD_H // 2,
                           text=f"除草完了！ 草刈機 +{bonus:,}",
                           color=(100, 240, 130)))

    # ---------- フラッシュ終了→実際の消去処理 ----------
    def _do_clear(self):
        cleared = len(self.flash_rows)

        if self.is_zone_active:
            # ── ゾーンモード：完成行を消去せずゾーン行（ZONE_CELL）に変換 ──
            for r in self.flash_rows:
                for c in range(COLS):
                    self.board.grid[r][c] = ZONE_CELL
                # 青白パーティクル
                for c in range(COLS):
                    px = BOARD_X + c * CELL + CELL // 2
                    py = BOARD_Y + r * CELL + CELL // 2
                    for _ in range(PARTICLE_PER_CELL):
                        self.particles.append(Particle(px, py, (60, 160, 255)))
            self.zone_stack += cleared
            self._popup_y = BOARD_Y + (min(self.flash_rows) * CELL) - 10
            self.flash_rows = []
            self._update_score(cleared)   # コンボ・バナーは通常通り（スコアは少な目）
            self._spawn_next()
            return

        # ── 通常モード：パーティクルをセルごとに生成 ──
        for r in self.flash_rows:
            for c in range(COLS):
                col = self.board.grid[r][c]
                if col and col != ZONE_CELL:
                    px = BOARD_X + c * CELL + CELL // 2
                    py = BOARD_Y + r * CELL + CELL // 2
                    for _ in range(PARTICLE_PER_CELL):
                        self.particles.append(Particle(px, py, col))

        # 行を消去してスコア更新
        self._popup_y = BOARD_Y + (min(self.flash_rows) * CELL) - 10
        self.board.clear_lines()
        self.flash_rows = []

        # クリア数に応じてシェイク
        if cleared >= 4:
            self.shake_timer = max(self.shake_timer, SHAKE_TETRIS)
            self.shake_mag   = max(self.shake_mag, 6)
        elif cleared >= 1:
            self.shake_timer = max(self.shake_timer, 6)
            self.shake_mag   = max(self.shake_mag, 3)

        self._update_score(cleared)
        self._spawn_next()

    # ---------- スコア更新 ----------
    def _update_score(self, cleared):
        tspin = self._pending_tspin
        self._pending_tspin = None

        TSPIN_PTS  = {
            ('full', 0): 400,  ('full', 1): 800,
            ('full', 2): 1200, ('full', 3): 1600,
            ('mini', 0): 100,  ('mini', 1): 200, ('mini', 2): 400,
        }
        NORMAL_PTS = [0, 100, 300, 500, 800]

        # ── 基礎点とバナー素材を決定 ──
        if tspin:
            self.stat_tspin += 1               # T-Spin カウント
            base_pts = TSPIN_PTS.get((tspin, min(cleared, 3)), 0)
            names    = {0: '', 1: 'SINGLE', 2: 'DOUBLE', 3: 'TRIPLE'}
            prefix   = 'T-SPIN' if tspin == 'full' else 'T-SPIN MINI'
            banner   = (f"{prefix} {names.get(cleared,'')}" .strip() + '!').upper()
        else:
            base_pts = NORMAL_PTS[min(cleared, 4)]
            banner   = '大収穫！' if cleared == 4 else ''

        # ── Back-to-Back 判定 ──
        # 「難しいクリア」= テトリス(4行・非Tスピン) または Tスピンありのライン消去
        is_difficult = (cleared == 4 and not tspin) or (tspin and cleared > 0)
        b2b_bonus    = False
        if is_difficult:
            if self.b2b and cleared > 0:   # 前回も難しいクリアなら 1.5 倍
                base_pts  = int(base_pts * 1.5)
                b2b_bonus = True
            self.b2b = True
        elif cleared > 0:
            self.b2b = False               # 普通のクリアで B2B リセット

        # ── ライン消去テキスト（T-スピン無し 1〜3 ライン） ──
        if cleared in (1, 2, 3) and not tspin:
            banner = {1: 'SINGLE!', 2: 'DOUBLE!', 3: 'TRIPLE!'}[cleared]

        # ── バナー表示（B2B プレフィックスを付与） ──
        if banner:
            self.tspin_text  = ('BACK-TO-BACK ' + banner) if b2b_bonus else banner
            self.tspin_timer = 100

        # ── コンボ ──
        combo_pts = 0
        if cleared > 0:
            self.combo += 1
            if self.combo >= 1:
                combo_pts        = 50 * self.combo
                self.combo_text  = f"{self.combo} COMBO!"
                self.combo_timer = 90
                if self.combo > self.stat_max_combo:   # 最大コンボ更新
                    self.stat_max_combo = self.combo
        else:
            self.combo = -1

        # ── スコア加算（base + combo）× level ──
        total_pts   = (base_pts + combo_pts) * self.level
        self.score += total_pts
        if self.score > self.hi_score:
            self.hi_score = self.score
            save_hiscore(self.hi_score)

        # ── スコアポップアップ ──
        if total_pts > 0 and cleared > 0:
            popup_y = getattr(self, '_popup_y', BOARD_Y + BOARD_H // 2)
            self.score_popups.append(
                ScorePopup(BOARD_X + BOARD_W // 2, popup_y, total_pts)
            )

        # ── ライン・レベル更新 ──
        # ── ゾーンゲージ蓄積（ゾーン発動中は増やさない） ──
        if not self.is_zone_active:
            gauge_add = cleared * 18 + (15 if tspin else 0)
            self.zone_gauge = min(ZONE_GAUGE_MAX, self.zone_gauge + gauge_add)

        # ── ガーベージ相殺：テトリス・T-Spin で予約済みガーベージをキャンセル ──
        is_cancel = (cleared == 4 and not tspin) or (tspin and cleared > 0)
        if is_cancel and self.garbage_warning and self.garbage_pending > 0:
            cancel = min(cleared, self.garbage_pending)
            self.garbage_pending -= cancel
            if self.garbage_pending <= 0:
                self.garbage_warning = False
                self.garbage_timer   = 0   # タイマーをリセットして猶予を与える
            self.score_popups.append(
                ScorePopup(BOARD_X + BOARD_W // 2,
                           BOARD_Y + BOARD_H // 4,
                           text=f"CANCELLED! -{cancel}",
                           color=(255, 80, 80)))

        self.lines += cleared
        self.goal   = max(0, self.goal - cleared)
        if self.goal == 0:
            self.level      += 1
            self.goal        = 10
            self.fall_speed  = max(4, FALL_NORMAL - (self.level - 1) * FALL_LEVEL)
            self.levelup_timer = 75              # レベルアップ演出開始
            self._build_level_sfx()              # レベルに応じた SFX を再ビルド
            # ── テーマ切り替え ──
            new_idx = min((self.level - 1) // 5, len(THEMES) - 1)
            if new_idx != self.theme_idx:
                self.theme_idx    = new_idx
                self.theme        = THEMES[new_idx]
                self.bg_particles = [
                    BgParticle(self.theme['particle_type'], initial=True)
                    for _ in range(self.theme['particle_count'])
                ]

        # ── ライン消去 SFX（1〜3 ライン、コンボ数でピッチシフト） ──
        if 1 <= cleared <= 3:
            combo_idx = min(max(self.combo, 0), 8)
            snd = self.snd_clear_cache[cleared][combo_idx]
            if snd and not self.bgm_muted:
                snd.play()
            self._js_se(f'clear{cleared}')

        # ── TETRIS! ファンファーレ（Tスピンなし 4ライン、B2B 問わず） ──
        if cleared == 4 and not tspin:
            self.tetris_timer = 120
            self._js_se('tetris')
            if self.snd_tetris and not self.bgm_muted:
                pygame.mixer.music.set_volume(0.15)
                self.snd_tetris.play()
                if not _IN_BROWSER:
                    def _restore(game=self):
                        import time; time.sleep(0.9)
                        pygame.mixer.music.set_volume(
                            0.0 if game.bgm_muted else (0.22 if game.danger else 0.4))
                    threading.Thread(target=_restore, daemon=True).start()

    # ---------- 回転（ウォールキック）----------
    def _try_rotate(self, ccw=False):
        """SRS (Super Rotation System) ウォールキック付き回転（ccw=True で反時計回り）"""
        rotated  = self.current.rotate_ccw() if ccw else self.current.rotate()
        from_rot = self.current.rot
        to_rot   = (from_rot - 1) % 4 if ccw else (from_rot + 1) % 4

        # ピース種別に応じたキックテーブルを選択（O は回転不要）
        if self.current.kind == 'I':
            kicks = SRS_KICKS_I.get((from_rot, to_rot), [(0, 0)])
        elif self.current.kind == 'O':
            kicks = [(0, 0)]
        else:
            kicks = SRS_KICKS_JLSTZ.get((from_rot, to_rot), [(0, 0)])

        for dx, dy in kicks:
            self.current.x += dx
            self.current.y += dy
            if self.board.is_valid(self.current.cells(shape=rotated)):
                self.current.shape = rotated
                self.current.rot   = to_rot
                self.last_rotated  = True
                self._lock_reset_on_action()
                if self.snd_rotate and not self.bgm_muted: self.snd_rotate.play()
                self._js_se('rotate')
                return
            self.current.x -= dx
            self.current.y -= dy

    # ---------- 経過時間テキスト ----------
    def _time_str(self):
        if self.paused:
            ms = self.pause_start - self.start_ticks - self.elapsed_pause
        else:
            ms = pygame.time.get_ticks() - self.start_ticks - self.elapsed_pause
        s  = max(0, ms // 1000)
        return f"{s//3600:02d}:{(s%3600)//60:02d}:{s%60:02d}"

    # ---------- 画面 flip（ブラウザ: canvas に転送 / デスクトップ: display.flip） ----------
    def _flip_display(self):
        if not _IN_BROWSER:
            pygame.display.flip()
            return
        try:
            from js import Uint8ClampedArray, ImageData, document
            from pyodide.ffi import to_js
            _raw = pygame.image.tobytes(self.screen, 'RGBA', False)
            _arr = Uint8ClampedArray.new(to_js(_raw))
            _img = ImageData.new(_arr, SCREEN_W, SCREEN_H)
            document.getElementById('canvas').getContext('2d').putImageData(_img, 0, 0)
        except Exception as _fe:
            print(f"[FLIP ERR] {_fe}")

    # ---------- ブラウザ BGM 制御（JavaScript Audio API 経由） ----------
    def _js_bgm(self, action):
        if not _IN_BROWSER:
            return
        try:
            from js import window
            audio = window._bgmAudio
            if audio is not None:
                if action == 'play':
                    audio.play()
                elif action == 'stop':
                    audio.pause()
                    audio.currentTime = 0
                elif action == 'pause':
                    audio.pause()
                elif action == 'resume':
                    audio.play()
                elif action == 'mute':
                    audio.volume = 0
                elif action == 'unmute':
                    audio.volume = 0.4
            if action == 'mute':
                window._seMuted = True
            elif action == 'unmute':
                window._seMuted = False
        except Exception:
            pass

    # ---------- ブラウザ SE 再生（JavaScript Web Audio API 経由） ----------
    def _js_se(self, se_type):
        if not _IN_BROWSER or self.bgm_muted:
            return
        try:
            from js import window
            if hasattr(window, '_playSE'):
                window._playSE(se_type)
        except Exception:
            pass

    # ---------- ブラウザキー入力を pygame イベントキューに投入 ----------
    def _poll_browser_keys(self):
        if not _IN_BROWSER:
            return
        try:
            from js import window
            while window._pendingKeys.length > 0:
                kc   = int(window._pendingKeys.shift())
                ktyp = int(window._pendingKeyTypes.shift())
                evtype = pygame.KEYDOWN if ktyp == 0 else pygame.KEYUP
                pygame.event.post(pygame.event.Event(
                    evtype, {'key': kc, 'mod': 0, 'unicode': ''}))
        except Exception:
            pass

    # ---------- メインループ ----------
    async def run(self):
        print("[RUN] ゲームループ開始")

        _frame = 0
        while self._running:
            # ブラウザでは clock.tick() が同期ブロックするため asyncio.sleep で代替
            if _IN_BROWSER:
                await asyncio.sleep(1.0 / FPS)
            else:
                self.clock.tick(FPS)

            self._handle_events()

            try:
                if self.state == 'TITLE':
                    # ── アトラクトモード ──
                    if self.game_over:
                        self._new_game()   # 盤面リセット → デモ続行
                    elif not self.paused:
                        self._update()     # 通常ゲーム更新（ガーベージはスキップ済）
                        if self.flash_timer == 0 and not self.game_over:
                            self._attract_step()
                    for p in self.bg_particles:
                        p.update()
                    self._draw_title()
                else:
                    # ── ゲームプレイ ──
                    if not self.game_over and not self.paused:
                        self._update()
                    for p in self.bg_particles:
                        p.update()
                    self._draw()
            except Exception as _e:
                import traceback as _tb
                print(f"[DRAW ERROR frame={_frame}] {_e}")
                _tb.print_exc()
                # フォールバック：エラー画面を表示して続行
                try:
                    self.screen.fill((60, 10, 10))
                    _ef = pygame.font.Font(None, 18)
                    err_s = _ef.render(
                        f"Draw error: {_e}", True, (255, 100, 100))
                    self.screen.blit(err_s, (10, 10))
                    self._flip_display()
                except Exception:
                    pass

            _frame += 1
            if _IN_BROWSER and _frame % 60 == 0:
                print(f"[RUN] frame={_frame} state={self.state}")

            if not _IN_BROWSER:
                await asyncio.sleep(0)   # デスクトップではフレーム末尾に yield

    # ---------- イベント ----------
    def _handle_events(self):
        self._poll_browser_keys()   # JS からのキー入力を pygame キューに投入
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                self._running = False
                if not _IN_BROWSER:
                    sys.exit()
                return

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pass  # ESC は無効化（何もしない）

                # M キー: どの状態でもミュート切替
                if event.key == pygame.K_m:
                    self.bgm_muted = not self.bgm_muted
                    if not _IN_BROWSER:
                        pygame.mixer.music.set_volume(0.0 if self.bgm_muted else 0.4)
                    self._js_bgm('mute' if self.bgm_muted else 'unmute')

                # Tab キー: DAS/ARR プリセット切り替え（どの状態でも有効）
                if event.key == pygame.K_TAB:
                    idx = DAS_PRESET_ORDER.index(self.das_preset)
                    self.das_preset = DAS_PRESET_ORDER[(idx + 1) % len(DAS_PRESET_ORDER)]

                # ── タイトル画面 ──
                if self.state == 'TITLE':
                    if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                        self._new_game()
                        self.state = 'PLAYING'
                        if not _IN_BROWSER and not pygame.mixer.music.get_busy():
                            try:
                                pygame.mixer.music.play(-1)
                                pygame.mixer.music.set_volume(0.0 if self.bgm_muted else 0.4)
                            except Exception:
                                pass
                        if not self.bgm_muted:
                            self._js_bgm('play')
                    return

                # ── ゲーム中 (PLAYING) ──
                # ゲームオーバー中: R / Space / Enter でタイトルへ
                if self.game_over:
                    if event.key in (pygame.K_r,
                                     pygame.K_SPACE,
                                     pygame.K_RETURN,
                                     pygame.K_KP_ENTER):
                        self._go_title()
                    return

                # 通常プレイ中: R でタイトルへ
                if event.key == pygame.K_r:
                    self._go_title()
                    return

                if event.key == pygame.K_p:
                    self.paused = not self.paused
                    if self.paused:
                        self.pause_start = pygame.time.get_ticks()
                        if not _IN_BROWSER:
                            try: pygame.mixer.music.pause()
                            except Exception: pass
                        else:
                            self._js_bgm('pause')
                    else:
                        self.elapsed_pause += pygame.time.get_ticks() - self.pause_start
                        if not _IN_BROWSER:
                            try: pygame.mixer.music.unpause()
                            except Exception: pass
                        else:
                            if not self.bgm_muted:
                                self._js_bgm('resume')
                    return
                if self.paused:
                    return

                # Enter キー: ゾーン発動
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if self.zone_gauge >= ZONE_GAUGE_MAX and not self.is_zone_active:
                        self._start_zone()
                # 回転操作: ↑ または X で時計回り、Z で反時計回り
                if event.key in (pygame.K_UP, pygame.K_x):
                    self._try_rotate(ccw=False)
                if event.key == pygame.K_z:
                    self._try_rotate(ccw=True)
                if event.key == pygame.K_SPACE:
                    self._hard_drop()
                if event.key == pygame.K_DOWN:
                    self.soft_drop = True
                if event.key in (pygame.K_c, pygame.K_LSHIFT, pygame.K_RSHIFT):
                    self._do_hold()
                if event.key == pygame.K_LEFT:
                    self.move_dir   = -1
                    self.move_timer = 0
                    if self.board.is_valid(self.current.cells(dx=-1)):
                        self.current.x   -= 1
                        self.last_rotated = False
                        self._lock_reset_on_action()
                        if self.snd_move and not self.bgm_muted: self.snd_move.play()
                        self._js_se('move')
                if event.key == pygame.K_RIGHT:
                    self.move_dir   = 1
                    self.move_timer = 0
                    if self.board.is_valid(self.current.cells(dx=1)):
                        self.current.x   += 1
                        self.last_rotated = False
                        self._lock_reset_on_action()
                        if self.snd_move and not self.bgm_muted: self.snd_move.play()
                        self._js_se('move')

            if event.type == pygame.KEYUP:
                if event.key == pygame.K_DOWN:
                    self.soft_drop = False
                if event.key in (pygame.K_LEFT, pygame.K_RIGHT):
                    self.move_dir = 0

    # ---------- ゲーム更新 ----------
    def _update(self):
        # フラッシュ中はピースを止めてカウントダウン
        if self.flash_timer > 0:
            self.flash_timer -= 1
            if self.flash_timer == 0:
                self._do_clear()
            # パーティクル・ポップアップだけ更新（フラッシュ中も動き続ける）
            self.particles    = [p for p in self.particles    if p.update()]
            self.score_popups = [p for p in self.score_popups if p.update()]
            return

        # パーティクル・ポップアップ更新
        self.particles    = [p for p in self.particles    if p.update()]
        self.score_popups = [p for p in self.score_popups if p.update()]

        # 長押し連続移動（DAS / ARR）
        if self.move_dir != 0:
            das_delay, arr_speed = DAS_PRESETS[self.das_preset]
            self.move_timer += 1
            if self.move_timer > das_delay and self.move_timer % arr_speed == 0:
                if self.board.is_valid(self.current.cells(dx=self.move_dir)):
                    self.current.x   += self.move_dir
                    self.last_rotated = False
                    self._lock_reset_on_action()

        # ── ゾーンタイマー管理 ──
        if self.is_zone_active:
            self.zone_timer -= 1
            if self.zone_timer <= 0:
                self._end_zone()
        # ゾーン終了演出カウントダウン
        if self.zone_end_anim > 0:
            self.zone_end_anim -= 1

        # ゾーン中は自動落下・自動ロックを停止（手動操作は有効）
        if not self.is_zone_active:
            speed = FALL_SOFT if self.soft_drop else self.fall_speed
            self.fall_timer += 1
            if self.fall_timer >= speed:
                self.fall_timer = 0
                if self.board.is_valid(self.current.cells(dy=1)):
                    # 1 マス落下 → 接地状態をリセット
                    self.current.y        += 1
                    self.last_rotated      = False
                    self.is_landed         = False
                    self.lock_timer        = 0
                    self.lock_reset_count  = 0
                    if self.soft_drop:
                        self.score += 1
                else:
                    # 下に移動できない → 接地状態へ
                    self.is_landed = True

        # ロックディレイ：ゾーン中は自動ロックしない
        if self.is_landed and not self.is_zone_active:
            self.lock_timer += 1
            if self.lock_timer >= LOCK_DELAY:
                self._lock_piece()

        # ── ガーベージシステム更新 ──
        self._update_garbage()

        # ── デンジャー検出 & 心拍・BGM 音量制御 ──
        self.danger = self._is_danger()
        if self.danger != self.prev_danger:
            # 状態遷移時に BGM 音量を切替（ミュート中は 0 のまま）
            if not _IN_BROWSER and not self.bgm_muted:
                target_vol = 0.22 if self.danger else 0.4
                pygame.mixer.music.set_volume(target_vol)
            self.heartbeat_timer = 0   # 即座に1拍鳴らすため
        self.prev_danger = self.danger

        if self.danger and not self.paused and self.state == 'PLAYING':
            # 上端から最も高い積みブロックの行を求め、危険度に応じて間隔を変える
            highest = ROWS  # 最高積み行（小さいほど危険）
            for row in range(ROWS):
                if any(self.board.grid[row]):
                    highest = row
                    break
            # highest=0: 25 frame間隔 / highest=3: 43 frame間隔
            interval = max(25, 25 + highest * 6)
            self.heartbeat_timer -= 1
            if self.heartbeat_timer <= 0:
                if self.snd_heartbeat and not self.bgm_muted:
                    self.snd_heartbeat.play()
                self.heartbeat_timer = interval

    # ==========================================================================
    #  描画
    # ==========================================================================

    def _draw(self):
        # ─────────────────────────────────────────────────
        # シェイク演出: game_surf に全描画 → screen に offset blit
        # ─────────────────────────────────────────────────
        real_screen  = self.screen
        self.screen  = self.game_surf          # 描画先を一時的に差し替え

        self._draw_background()
        self._draw_left_panel()
        self._draw_board()
        self._draw_particles()                 # ボードの上にパーティクル
        self._draw_right_panel()

        # TETRIS! バナー
        if self.tetris_timer > 0 and not self.game_over and not self.paused:
            self._draw_tetris_banner()
            self.tetris_timer -= 1

        # T-スピン / B2B バナー
        if self.tspin_timer > 0 and not self.game_over and not self.paused:
            self._draw_tspin_banner()
            self.tspin_timer -= 1

        # コンボ バナー
        if self.combo_timer > 0 and not self.game_over and not self.paused:
            self._draw_combo_banner()
            self.combo_timer -= 1

        # レベルアップ演出
        if self.levelup_timer > 0 and not self.game_over and not self.paused:
            self._draw_levelup()
            self.levelup_timer -= 1

        # スコアポップアップ
        for p in self.score_popups:
            p.draw(self.screen, self.f_med)

        if self.paused and not self.game_over:
            das_delay, arr_speed = DAS_PRESETS[self.das_preset]
            self._draw_overlay("PAUSE",
                               f"P: 再開  /  R: リスタート  /  Tab: 操作感 [{self.das_preset}  DAS={das_delay}f ARR={arr_speed}f]",
                               (200, 200, 100))
        if self.game_over:
            self._draw_gameover()

        # ─── 描画先を元に戻してシェイクオフセットを適用 ───
        self.screen = real_screen
        ox, oy = 0, 0
        if self.shake_timer > 0:
            intensity    = max(1, int(self.shake_mag * self.shake_timer
                                      / max(SHAKE_TETRIS, 1)))
            ox = random.randint(-intensity, intensity)
            oy = random.randint(-intensity, intensity)
            self.shake_timer -= 1
            if self.shake_timer == 0:
                self.shake_mag = 0
            self.screen.fill((0, 0, 0))        # 黒でクリアしてからblit

        self.screen.blit(self.game_surf, (ox, oy))
        self._flip_display()

    # --- 背景グラデーション + テーマパーティクル ---
    def _draw_background(self):
        th  = self.theme
        top = th['bg_top']
        bot = th['bg_bot']
        for y in range(0, SCREEN_H, 3):
            f   = y / SCREEN_H
            col = tuple(max(0, min(255, int(top[i] + (bot[i] - top[i]) * f)))
                        for i in range(3))
            pygame.draw.rect(self.screen, col, (0, y, SCREEN_W, 3))
        # テーマ固有の背景パーティクル
        for p in self.bg_particles:
            p.draw(self.screen)

    # --- テーマ色でパネルボックスを描くヘルパー ---
    def _dpanel(self, rect, title=None):
        th = self.theme
        draw_panel_box(self.screen, rect, title, self.f_jp_sm,
                       th['panel'], th['border'], th['c_dim'])

    # --- 左パネル ---
    def _draw_left_panel(self):
        lx  = 8
        lcx = lx + 75   # 左パネル中心 X
        th  = self.theme

        # TETRIS ロゴ
        draw_tetris_logo(self.screen, lcx, 12, self.f_logo)

        # HOLD ボックス
        hold_rect = pygame.Rect(lx, 65, 150, 88)
        self._dpanel(hold_rect, "HOLD")
        if self.hold_kind:
            draw_mini_piece(self.screen, self.hold_kind, lcx, 112)
        else:
            t = self.f_sm.render("―", True, th['c_dim'])
            self.screen.blit(t, t.get_rect(center=(lcx, 112)))

        # TIME ボックス
        time_rect = pygame.Rect(lx, 165, 150, 50)
        self._dpanel(time_rect, "TIME")
        tv = self.f_med.render(self._time_str(), True, th['c_text'])
        self.screen.blit(tv, tv.get_rect(center=(lcx, 197)))

        # LEVEL バッジ
        draw_level_badge(self.screen, lcx, 300, self.level, self.f_lv, self.f_jp_sm,
                         th['border'], th['c_dim'])

        # GOAL ボックス
        goal_rect = pygame.Rect(lx, 360, 150, 48)
        self._dpanel(goal_rect, "GOAL")
        gv = self.f_num.render(str(self.goal), True, C_GOLD)
        self.screen.blit(gv, gv.get_rect(center=(lcx, 390)))

        # ZONE ゲージ
        zone_rect = pygame.Rect(lx, 420, 150, 68)
        self._dpanel(zone_rect, "ZONE")
        bar_x  = lx + 10
        bar_y  = 443
        bar_w  = 130
        bar_h  = 18
        ticks  = pygame.time.get_ticks()

        if self.is_zone_active:
            # ゾーン中：タイマー残量バーを水色で表示
            ratio  = self.zone_timer / ZONE_DURATION
            pulse  = 0.7 + 0.3 * abs(math.sin(ticks / 200.0))
            filled = int(bar_w * ratio)
            pygame.draw.rect(self.screen, th['panel'],  (bar_x, bar_y, bar_w, bar_h), border_radius=4)
            zc     = (int(60 * pulse), int(160 * pulse), 255)
            pygame.draw.rect(self.screen, zc,           (bar_x, bar_y, filled, bar_h), border_radius=4)
            pygame.draw.rect(self.screen, (100, 180, 255), (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)
            # ZONE 中テキスト
            zt_lbl = self.f_sm.render(f"ACTIVE  {self.zone_stack}L", True, (120, 220, 255))
            self.screen.blit(zt_lbl, zt_lbl.get_rect(center=(lcx, bar_y + bar_h + 9)))
        else:
            ratio  = self.zone_gauge / ZONE_GAUGE_MAX
            filled = int(bar_w * ratio)
            pygame.draw.rect(self.screen, th['panel'],  (bar_x, bar_y, bar_w, bar_h), border_radius=4)
            if ratio >= 1.0:
                # 満タン：金色パルス
                pulse  = 0.7 + 0.3 * abs(math.sin(ticks / 160.0))
                gc     = (int(255 * pulse), int(200 * pulse), int(30 * pulse))
                pygame.draw.rect(self.screen, gc,       (bar_x, bar_y, bar_w, bar_h), border_radius=4)
                pygame.draw.rect(self.screen, C_GOLD,   (bar_x, bar_y, bar_w, bar_h), 2, border_radius=4)
                lbl    = self.f_sm.render("READY!  [Enter]", True, C_GOLD)
            else:
                # 通常
                gc     = (40, 120, 230)
                pygame.draw.rect(self.screen, gc,       (bar_x, bar_y, filled, bar_h), border_radius=4)
                pygame.draw.rect(self.screen, th['border'], (bar_x, bar_y, bar_w, bar_h), 1, border_radius=4)
                lbl    = self.f_sm.render(f"{int(self.zone_gauge)}%", True, th['c_dim'])
            self.screen.blit(lbl, lbl.get_rect(center=(lcx, bar_y + bar_h + 9)))

    # --- ボード ---
    def _draw_board(self):
        bx, by = BOARD_X, BOARD_Y
        th     = self.theme

        # ベゼル（外枠）：border 色を少し暗くして内枠に
        border     = th['border']
        bezel_col  = tuple(max(0, c - 18) for c in border)
        bezel = pygame.Rect(bx-4, by-4, BOARD_W+8, BOARD_H+8)
        pygame.draw.rect(self.screen, bezel_col, bezel, border_radius=5)
        pygame.draw.rect(self.screen, border,    bezel, 2, border_radius=5)

        # ボード背景
        pygame.draw.rect(self.screen, th['board'],
                         (bx, by, BOARD_W, BOARD_H))

        # グリッド線
        for r in range(ROWS):
            for c in range(COLS):
                pygame.draw.rect(self.screen, th['grid'],
                                 (bx + c*CELL, by + r*CELL, CELL, CELL), 1)

        # ── ゾーンモード：深青オーバーレイをボード背景に描画 ──
        if self.is_zone_active:
            ticks  = pygame.time.get_ticks()
            z_pulse = 0.5 + 0.5 * abs(math.sin(ticks / 700.0))
            z_ov = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
            z_ov.fill((0, 20, 90, int(55 * z_pulse)))
            self.screen.blit(z_ov, (bx, by))

        # 固定ブロック（フラッシュ行は白く発光 / ゾーン行は青く発光）
        flash_set = set(self.flash_rows)
        ticks = pygame.time.get_ticks()
        for r in range(ROWS):
            for c in range(COLS):
                col = self.board.grid[r][c]
                if not col:
                    continue
                # ── ガーベージ行（グレーメタリック） ──
                if col == GARBAGE_COLOR:
                    draw_cell(self.screen, bx + c*CELL, by + r*CELL, GARBAGE_COLOR)
                    # メタリック感：中央に横線
                    if CELL >= 16:
                        lc = tuple(min(255, v + 40) for v in GARBAGE_COLOR)
                        pygame.draw.line(self.screen, lc,
                                         (bx + c*CELL + 3, by + r*CELL + CELL//2),
                                         (bx + c*CELL + CELL - 4, by + r*CELL + CELL//2), 2)
                    continue

                # ── ゾーン行（ZONE_CELL センチネル） ──
                if col == ZONE_CELL:
                    pulse = 0.55 + 0.45 * math.sin(ticks / 220.0 + r * 0.4)
                    zr = int(20  + 25  * pulse)
                    zg = int(80  + 60  * pulse)
                    zb = int(210 + 45  * pulse)
                    draw_cell(self.screen, bx + c*CELL, by + r*CELL, (zr, zg, zb))
                    # 青グロー
                    gz = pygame.Surface((CELL + 4, CELL + 4), pygame.SRCALPHA)
                    gz.fill((60, 140, 255, int(70 * pulse)))
                    self.screen.blit(gz, (bx + c*CELL - 2, by + r*CELL - 2))
                    continue
                if r in flash_set:
                    # frac: 1.0(開始直後・真っ白) → 0.0(消える直前)
                    frac = self.flash_timer / FLASH_DURATION
                    # ── グロー: 少し大きめの半透明矩形を背景に描く ──
                    glow_alpha = int(160 * frac)
                    glow = pygame.Surface((CELL + 6, CELL + 6), pygame.SRCALPHA)
                    # ゾーン中フラッシュは青白
                    glow_fill = (180, 220, 255, glow_alpha) if self.is_zone_active \
                                else (255, 255, 220, glow_alpha)
                    glow.fill(glow_fill)
                    self.screen.blit(glow, (bx + c*CELL - 3, by + r*CELL - 3))
                    # ── ブロック本体: 白→元色へフェード ──
                    wf        = 0.35 + 0.65 * frac
                    flash_col = tuple(min(255, int(255*wf + v*(1-wf))) for v in col)
                    draw_cell(self.screen, bx + c*CELL, by + r*CELL, flash_col)
                else:
                    draw_cell(self.screen, bx + c*CELL, by + r*CELL, col)

        # ── ゾーン中：蓄積ライン数カウンターを中央に表示 ──
        if self.is_zone_active and self.zone_stack > 0:
            zp = 0.7 + 0.3 * abs(math.sin(ticks / 300.0))
            za = int(220 * zp)
            zt_s = self.f_big.render(f"{self.zone_stack} LINES", True, (100, 210, 255))
            zt_s.set_alpha(za)
            self.screen.blit(zt_s, zt_s.get_rect(
                center=(bx + BOARD_W // 2, by + BOARD_H // 2 + 30)))

        # ── ゾーン終了演出フラッシュ ──
        if self.zone_end_anim > 0:
            fade = self.zone_end_anim / 90
            end_ov = pygame.Surface((BOARD_W, BOARD_H), pygame.SRCALPHA)
            end_ov.fill((120, 200, 255, int(160 * fade)))
            self.screen.blit(end_ov, (bx, by))

        # ── ガーベージ警告インジケーター（ボード右外側） ──
        if self.garbage_warning and self.garbage_pending > 0:
            pulse = 0.5 + 0.5 * abs(math.sin(ticks / 130.0))
            ind_x = bx + BOARD_W + 6
            ind_h = int(BOARD_H * 0.55)
            ind_y = by + (BOARD_H - ind_h) // 2
            ind_w = 18
            # 赤バー背景
            pygame.draw.rect(self.screen, (80, 10, 10),
                             (ind_x, ind_y, ind_w, ind_h), border_radius=4)
            # 点滅赤バー（残時間に応じた高さ）
            interval = self._garbage_interval()
            ratio    = max(0, (self.garbage_timer - (interval - GARBAGE_WARN_DUR))
                           / GARBAGE_WARN_DUR)
            fill_h   = int(ind_h * ratio)
            rc       = (int(255 * pulse), int(40 * (1 - pulse)), 0)
            if fill_h > 0:
                pygame.draw.rect(self.screen, rc,
                                 (ind_x, ind_y + ind_h - fill_h, ind_w, fill_h),
                                 border_radius=4)
            pygame.draw.rect(self.screen, (255, 60, 60),
                             (ind_x, ind_y, ind_w, ind_h), 2, border_radius=4)
            # 「！」マーク
            if not hasattr(self, '_f_warn'):
                if _IN_BROWSER:
                    self._f_warn = _get_browser_font(16)
                else:
                    self._f_warn = pygame.font.SysFont("Arial", 16, bold=True)
            warn_lbl = self._f_warn.render("!", True,
                                           (255, int(200 * pulse), int(200 * pulse)))
            self.screen.blit(warn_lbl, warn_lbl.get_rect(
                center=(ind_x + ind_w // 2, ind_y - 12)))
            # 行数バッジ
            cnt_lbl = self._f_warn.render(str(self.garbage_pending), True, (255, 180, 180))
            self.screen.blit(cnt_lbl, cnt_lbl.get_rect(
                center=(ind_x + ind_w // 2, ind_y + ind_h + 12)))

        # ゴースト
        if not self.game_over:
            dy = self._ghost_dy()
            if dy > 0:
                for x, y in self.current.cells(dy=dy):
                    if 0 <= y < ROWS:
                        draw_cell(self.screen,
                                  bx + x*CELL, by + y*CELL,
                                  self.current.color, alpha=80)

        # 現在ピース（アイテムブロックは item_type を渡してグロー＋記号を表示）
        if not self.game_over:
            for x, y in self.current.cells():
                if 0 <= y < ROWS:
                    draw_cell(self.screen,
                              bx + x*CELL, by + y*CELL,
                              self.current.color,
                              item_type=self.current.item_type)

        # ロックディレイ インジケーター
        # 接地中は各セルにカウントダウンに応じた色枠を描く（緑→黄→赤）
        if self.is_landed and not self.game_over:
            progress = min(1.0, self.lock_timer / LOCK_DELAY)   # 0.0(着地直後)→1.0(ロック寸前)
            r = int(60  + 195 * progress)
            g = int(220 - 210 * progress)
            b = 30
            alpha = int(140 + 115 * progress)
            for x, y in self.current.cells():
                if 0 <= y < ROWS:
                    ind = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
                    pygame.draw.rect(ind, (r, g, b, alpha),
                                     (0, 0, CELL, CELL), width=3, border_radius=3)
                    self.screen.blit(ind, (bx + x*CELL, by + y*CELL))

    # --- パーティクル描画 ---
    def _draw_particles(self):
        for p in self.particles:
            p.draw(self.screen)

    # --- 右パネル ---
    def _draw_right_panel(self):
        rx  = BOARD_X + BOARD_W + 10
        rcx = rx + 92    # 右パネル中心 X
        th  = self.theme

        # NEXT（3個）
        next_rect = pygame.Rect(rx, BOARD_Y, 188, 258)
        self._dpanel(next_rect, "NEXT")
        for i, kind in enumerate(self.bag.peek(3)):
            draw_mini_piece(self.screen, kind, rcx, BOARD_Y + 50 + i*75)

        # HIGH SCORE（最高収穫高）
        hi_rect = pygame.Rect(rx, BOARD_Y + 268, 188, 60)
        self._dpanel(hi_rect, "最高収穫高")
        hv = self.f_num.render(f"{self.hi_score:,}", True, C_GOLD)
        self.screen.blit(hv, hv.get_rect(center=(rcx, BOARD_Y + 304)))

        # SCORE（収穫高）
        sc_rect = pygame.Rect(rx, BOARD_Y + 338, 188, 60)
        self._dpanel(sc_rect, "収穫高")
        sv = self.f_num.render(f"{self.score:,}", True, th['c_text'])
        self.screen.blit(sv, sv.get_rect(center=(rcx, BOARD_Y + 374)))

        # LINES（出荷数）
        ln_rect = pygame.Rect(rx, BOARD_Y + 408, 188, 52)
        self._dpanel(ln_rect, "出荷数")
        lv = self.f_med.render(str(self.lines), True, th['c_text'])
        self.screen.blit(lv, lv.get_rect(center=(rcx, BOARD_Y + 438)))

        # テーマ名バッジ
        theme_surf = self.f_sm.render(f"[ {th['name']} ]", True, th['c_dim'])
        self.screen.blit(theme_surf, theme_surf.get_rect(center=(rcx, BOARD_Y + 468)))

        # 操作ガイド
        hints = [
            "C / Shift : HOLD",
            "↑ / X : 右回転   Z : 左回転",
            "↓ : 加速落下     Space : 即落下",
            "Enter : ZONE    Tab : 操作感",
            "P : ポーズ      R : リスタート",
        ]
        for i, h in enumerate(hints):
            t = self.f_sm.render(h, True, th['c_dim'])
            self.screen.blit(t, (rx + 6, BOARD_Y + 486 + i*20))

        # ミュート中アイコン表示
        if self.bgm_muted:
            mute_surf = self.f_sm.render("🔇 MUTE (M)", True, (220, 80, 80))
            self.screen.blit(mute_surf, (rx + 6, BOARD_Y + 486 + len(hints)*20 + 4))

    # --- TETRIS! バナー ---
    def _draw_tetris_banner(self):
        t = self.tetris_timer
        alpha = (int(255*(120-t)/20) if t > 100
                 else int(255*t/30)  if t < 30
                 else 255)

        hue   = (pygame.time.get_ticks() // 8) % 360
        c     = pygame.Color(0)
        c.hsva = (hue, 100, 100, 100)

        surf   = self.f_jp.render("大収穫！", True, (c.r, c.g, c.b))
        shadow = self.f_jp.render("大収穫！", True, (0, 0, 0))
        surf.set_alpha(alpha)
        shadow.set_alpha(alpha // 2)
        rect = surf.get_rect(center=(BOARD_X + BOARD_W//2, BOARD_Y + BOARD_H//2))
        self.screen.blit(shadow, rect.move(3, 3))
        self.screen.blit(surf, rect)

    # --- T-スピン バナー ---
    def _draw_tspin_banner(self):
        t = self.tspin_timer
        # フェードイン(最初10f) → 全点灯 → フェードアウト(最後20f)
        if t > 90:
            alpha = int(255 * (100 - t) / 10)
        elif t < 20:
            alpha = int(255 * t / 20)
        else:
            alpha = 255

        # T-スピン系はシアン〜マゼンタのグラデーション
        hue   = (pygame.time.get_ticks() // 6) % 360
        c     = pygame.Color(0)
        c.hsva = (hue, 90, 100, 100)

        # TETRIS! バナーより少し上に配置
        cy = BOARD_Y + BOARD_H // 2 - 60

        surf   = self.f_med.render(self.tspin_text, True, (c.r, c.g, c.b))
        shadow = self.f_med.render(self.tspin_text, True, (0, 0, 0))
        surf.set_alpha(alpha)
        shadow.set_alpha(alpha // 2)
        rect = surf.get_rect(center=(BOARD_X + BOARD_W // 2, cy))
        self.screen.blit(shadow, rect.move(2, 2))
        self.screen.blit(surf, rect)

    # --- コンボ バナー ---
    def _draw_combo_banner(self):
        t = self.combo_timer
        if t > 80:
            alpha = int(255 * (90 - t) / 10)
        elif t < 15:
            alpha = int(255 * t / 15)
        else:
            alpha = 255

        # コンボ数が多いほど明るいオレンジ〜黄に
        intensity = min(1.0, self.combo / 8)
        r = 255
        g = int(100 + 155 * intensity)
        b = int(20  * (1 - intensity))

        cy   = BOARD_Y + BOARD_H // 2 + 45   # T-SPINバナーより下
        surf   = self.f_med.render(self.combo_text, True, (r, g, b))
        shadow = self.f_med.render(self.combo_text, True, (0, 0, 0))
        surf.set_alpha(alpha)
        shadow.set_alpha(alpha // 2)
        rect = surf.get_rect(center=(BOARD_X + BOARD_W // 2, cy))
        self.screen.blit(shadow, rect.move(2, 2))
        self.screen.blit(surf, rect)

    # --- レベルアップ演出 ---
    def _draw_levelup(self):
        t        = self.levelup_timer          # 75 → 0
        progress = t / 75                      # 1.0 → 0.0（時間経過で減る）

        # フェード: 最初10f でイン、最後15f でアウト
        if t > 65:
            alpha = int(255 * (75 - t) / 10)
        elif t < 15:
            alpha = int(255 * t / 15)
        else:
            alpha = 255

        # ── ボード外枠グロー（黄→白） ──
        glow_alpha = int(180 * progress)
        glow_w     = int(8 * progress) + 2
        bx, by     = BOARD_X, BOARD_Y
        glow_rect  = pygame.Rect(bx - glow_w, by - glow_w,
                                 BOARD_W + glow_w * 2, BOARD_H + glow_w * 2)
        glow_surf  = pygame.Surface(
            (glow_rect.width, glow_rect.height), pygame.SRCALPHA)
        r = 255
        g = min(255, int(200 + 55 * progress))
        pygame.draw.rect(glow_surf, (r, g, 40, glow_alpha),
                         (0, 0, glow_rect.width, glow_rect.height),
                         width=glow_w + 4, border_radius=6)
        self.screen.blit(glow_surf, (glow_rect.x, glow_rect.y))

        # ── "LEVEL UP!" テキスト ──
        lv_str = f"LEVEL {self.level}!"
        surf   = self.f_lv.render(lv_str, True, (255, 240, 60))
        shadow = self.f_lv.render(lv_str, True, (0, 0, 0))
        surf.set_alpha(alpha)
        shadow.set_alpha(alpha // 2)
        cx   = BOARD_X + BOARD_W // 2
        cy   = BOARD_Y + BOARD_H // 2 + 80
        rect = surf.get_rect(center=(cx, cy))
        self.screen.blit(shadow, rect.move(2, 2))
        self.screen.blit(surf, rect)

    # --- ゲームオーバー詳細リザルト ---
    def _draw_gameover(self):
        """ゲームオーバー画面: スコアを大きく表示し、詳細統計をリスト形式で描画"""
        cx = SCREEN_W // 2

        # ── 半透明オーバーレイ ──
        panel = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 185))
        self.screen.blit(panel, (0, 0))

        # ── パネル枠（中央のカード） ──
        card_w, card_h = 420, 345
        card_x = cx - card_w // 2
        card_y = SCREEN_H // 2 - card_h // 2 - 10
        card_surf = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
        card_surf.fill((15, 15, 30, 220))
        self.screen.blit(card_surf, (card_x, card_y))
        pygame.draw.rect(self.screen, (255, 80, 80),
                         (card_x, card_y, card_w, card_h), 2, border_radius=8)

        # ── GAME OVER タイトル ──
        go_s = self.f_go_title.render("出荷終了", True, (255, 80, 80))
        self.screen.blit(go_s, go_s.get_rect(center=(cx, card_y + 38)))

        # ── スコア（最大表示） ──
        score_s = self.f_go_score.render(f"{self.score:,}", True, (255, 230, 60))
        self.screen.blit(score_s, score_s.get_rect(center=(cx, card_y + 100)))
        lbl_s = self.f_jp_sm.render("収穫高", True, (180, 180, 180))
        self.screen.blit(lbl_s, lbl_s.get_rect(center=(cx, card_y + 130)))

        # ── 区切り線 ──
        sep_y = card_y + 148
        pygame.draw.line(self.screen, (80, 80, 120),
                         (card_x + 20, sep_y), (card_x + card_w - 20, sep_y), 1)

        # ── 統計リスト ──
        stats = [
            ("T-Spin",        f"{self.stat_tspin}",        (120, 200, 255)),
            ("最大コンボ",    f"{self.stat_max_combo}",    (255, 180,  60)),
            ("ゾーン消去",    f"{self.stat_zone_lines} L", ( 80, 220, 255)),
            ("アイテム使用",  f"{self.stat_items_used}",   (180, 255, 120)),
        ]
        row_h  = 34
        list_y = sep_y + 14
        for i, (label, value, col) in enumerate(stats):
            ry = list_y + i * row_h
            # ラベル（左寄せ）: 日本語対応フォントを使用
            lbl = self.f_jp.render(label, True, (200, 200, 200))
            self.screen.blit(lbl, (card_x + 32, ry))
            # 値（右寄せ・カラー付き）: 数値は Arial で十分
            val = self.f_lv.render(value, True, col)
            self.screen.blit(val, val.get_rect(right=card_x + card_w - 32, y=ry))

        # ── ヒント（日本語対応フォント）──
        hint_s = self.f_jp_sm.render("R  でタイトルへ", True, (140, 140, 160))
        self.screen.blit(hint_s, hint_s.get_rect(center=(cx, card_y + card_h - 16)))

    # --- オーバーレイ ---
    def _draw_overlay(self, title, sub, title_color):
        panel = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 168))
        self.screen.blit(panel, (0, 0))
        t = self.f_big.render(title, True, title_color)
        self.screen.blit(t, t.get_rect(center=(SCREEN_W//2, SCREEN_H//2 - 28)))
        s = self.f_jp_sm.render(sub, True, C_WHITE)
        self.screen.blit(s, s.get_rect(center=(SCREEN_W//2, SCREEN_H//2 + 22)))

    # ---------- アトラクトモード AI ----------
    def _attract_find_best(self):
        """現ピースの最良配置 (rot_delta, target_x) を全探索"""
        best_score = float('inf')
        best_rdelta, best_tx = 0, self.current.x
        shape = self.current.shape
        for rdelta in range(4):
            s = shape
            for _ in range(rdelta):
                n = len(s)
                s = [[s[n-1-j][i] for j in range(n)] for i in range(n)]
            for tx in range(-3, COLS + 3):
                cells0 = [(tx+c, r) for r,row in enumerate(s)
                          for c,v in enumerate(row) if v]
                if not self.board.is_valid(cells0):
                    continue
                dy = 0
                while self.board.is_valid([(tx+c, r+dy+1)
                       for r,row in enumerate(s) for c,v in enumerate(row) if v]):
                    dy += 1
                g = [row[:] for row in self.board.grid]
                for cx, cy in [(tx+c, r+dy) for r,row in enumerate(s)
                               for c,v in enumerate(row) if v]:
                    if 0 <= cy < ROWS and 0 <= cx < COLS:
                        g[cy][cx] = (200,200,200)
                g = [row for row in g
                     if not all(cell is not None for cell in row)
                     or any(cell == ZONE_CELL for cell in row)]
                while len(g) < ROWS:
                    g.insert(0, [None]*COLS)
                # スコア: 積高 + 穴 + でこぼこ
                heights = []
                for c in range(COLS):
                    h = next((ROWS-r for r in range(ROWS)
                              if g[r][c] is not None and g[r][c] != ZONE_CELL), 0)
                    heights.append(h)
                holes = sum(1 for c in range(COLS)
                            for r in range(ROWS)
                            if g[r][c] is None
                            and any(g[rr][c] is not None and g[rr][c] != ZONE_CELL
                                    for rr in range(r)))
                bump  = sum(abs(heights[i]-heights[i+1]) for i in range(COLS-1))
                sc = sum(heights)*0.5 + max(heights) + bump*0.3 + holes*3.0
                if sc < best_score:
                    best_score = sc
                    best_rdelta, best_tx = rdelta, tx
        return best_rdelta, best_tx

    def _attract_step(self):
        """アトラクトモード: 1フレーム分のBot操作 + ゴッドモード"""
        self.fall_speed = 22   # アトラクトモード: デモ用低速落下
        self._attr_timer += 1

        # ゴッドモード: 10行目以上に積まれたら下5行を消去
        for r in range(ROWS // 2):
            if any(c is not None and c != ZONE_CELL for c in self.board.grid[r]):
                for dr in range(ROWS-5, ROWS):
                    self.board.grid[dr] = [None]*COLS
                for col in range(COLS):
                    column = [self.board.grid[rr][col] for rr in range(ROWS)]
                    filled = [c for c in column if c is not None]
                    new_col = [None]*(ROWS-len(filled)) + filled
                    for rr in range(ROWS):
                        self.board.grid[rr][col] = new_col[rr]
                if self.is_landed and self.board.is_valid(self.current.cells(dy=1)):
                    self.is_landed = False
                    self.lock_timer = 0
                    self.lock_reset_count = 0
                break

        # ゾーンゲージ満タンで発動
        if self.zone_gauge >= ZONE_GAUGE_MAX and not self.is_zone_active:
            self._start_zone()

        # 新ピース検出 → 最良配置を計算
        pid = id(self.current)
        if pid != self._attr_pid:
            self._attr_pid = pid
            self._attr_rdelta, self._attr_tx = self._attract_find_best()
            self._attr_rots_done = 0

        # 回転（5フレームごと・ゆっくり）
        if self._attr_rots_done < self._attr_rdelta:
            if self._attr_timer % 5 == 0:
                self._try_rotate()
                self._attr_rots_done += 1
            return

        # 横移動（4フレームごと）
        dx = self._attr_tx - self.current.x
        if dx != 0 and self._attr_timer % 4 == 0:
            if dx < 0 and self.board.is_valid(self.current.cells(dx=-1)):
                self.current.x -= 1
                self.last_rotated = False
                self._lock_reset_on_action()
            elif dx > 0 and self.board.is_valid(self.current.cells(dx=1)):
                self.current.x += 1
                self.last_rotated = False
                self._lock_reset_on_action()
            return

        # 目標x到達 → 自然落下に任せる（fall_speed=22で低速デモ落下）

    # ---------- タイトル画面描画 ----------
    def _draw_title(self):
        """タイトル画面: アトラクトモードの盤面+演出オーバーレイを描画"""
        # 1. 背景 + アトラクトゲームのボード
        self._draw_background()
        self._draw_board()
        self._draw_particles()

        # 2. 全画面ダークオーバーレイ
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 172))
        self.screen.blit(ov, (0, 0))

        ticks = pygame.time.get_ticks()
        cx    = SCREEN_W // 2

        # 3. 「大収穫！」ロゴ（パルシンググロー・農業テーマカラー）
        pulse  = 0.72 + 0.28 * math.sin(ticks / 700.0)
        logo_y = SCREEN_H // 2 - 160
        logo_text = "大収穫！"

        # 影（深い緑でアース感）
        shd = self.f_ja_title.render(logo_text, True, (20, 60, 10))
        self.screen.blit(shd, shd.get_rect(center=(cx+5, logo_y+5)))
        # 外グロー（稲穂ゴールド）
        glow_col = tuple(min(255, int(c * pulse)) for c in (220, 180, 0))
        for gox, goy in ((-3,0),(3,0),(0,-3),(0,3),(-2,-2),(2,-2),(-2,2),(2,2)):
            g = self.f_ja_title.render(logo_text, True, glow_col)
            g.set_alpha(90)
            self.screen.blit(g, g.get_rect(center=(cx+gox, logo_y+goy)))
        # メインテキスト（グラデーション風：黄緑→ゴールド）
        bright = tuple(min(255, int(c * pulse)) for c in (200, 240, 60))
        logo_s = self.f_ja_title.render(logo_text, True, bright)
        self.screen.blit(logo_s, logo_s.get_rect(center=(cx, logo_y)))

        # 4. サブタイトル（農業テーマ）
        sub_s = self.f_jp.render("農業テトリス", True, (170, 210, 150))
        self.screen.blit(sub_s, sub_s.get_rect(center=(cx, logo_y + 80)))

        # 5. ハイスコア
        hi_s = self.f_num.render(f"HI-SCORE  {self.hi_score:,}", True, C_GOLD)
        self.screen.blit(hi_s, hi_s.get_rect(center=(cx, logo_y + 130)))

        # 6. 点滅テキスト（600ms 周期）
        if (ticks // 550) % 2 == 0:
            blink_col = (255, 255, 255)
            blink_s = self.f_big.render("PRESS  SPACE  TO  START", True, blink_col)
            blink_shd = self.f_big.render("PRESS  SPACE  TO  START", True, (0,0,0))
            y_blink = logo_y + 205
            self.screen.blit(blink_shd, blink_shd.get_rect(center=(cx+2, y_blink+2)))
            self.screen.blit(blink_s,   blink_s.get_rect(center=(cx,     y_blink)))

        # 7. 操作ガイド（日本語対応フォント使用）
        controls = [
            "← →: 移動   ↑ / X: 右回転   Z: 左回転   Space: 即落下",
            "C / Shift: ホールド   Enter: ZONE発動   M: 消音   P: ポーズ",
        ]
        for i, line in enumerate(controls):
            ctrl_s = self.f_jp_sm.render(line, True, (140, 140, 165))
            self.screen.blit(ctrl_s, ctrl_s.get_rect(center=(cx, logo_y + 285 + i*24)))

        # 8. DAS/ARR プリセット表示 (Tab で切替)
        das_delay, arr_speed = DAS_PRESETS[self.das_preset]
        preset_colors = {'NORMAL': (180, 220, 180), 'FAST': (255, 210, 80), 'PRO': (255, 110, 110)}
        pcol = preset_colors[self.das_preset]
        preset_s = self.f_jp_sm.render(
            f"操作感: {self.das_preset}  (DAS={das_delay}f / ARR={arr_speed}f)   Tab で変更",
            True, pcol)
        self.screen.blit(preset_s, preset_s.get_rect(center=(cx, logo_y + 340)))

        self._flip_display()


# =============================================================================
#  エントリポイント
# =============================================================================

if __name__ == "__main__":
    game = Tetris()
    if _IN_BROWSER:
        # Pyodide はすでにイベントループが動いているため ensure_future で登録する
        asyncio.ensure_future(game.run())
    else:
        asyncio.run(game.run())