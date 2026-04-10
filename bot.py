# =============================================
# MAC GAME AUTOMATION BOT - KNIGHT EDITION
# Full source code - Ready to run (macOS only)
# =============================================
#
# requirements.txt (paste into requirements.txt or install manually):
# pyautogui>=0.9.54
# opencv-python>=4.8.0
# numpy>=1.24.0
# mss>=9.0.1
# Pillow>=10.0.0
# pynput>=1.7.6
#
# MACOS PERMISSIONS REQUIRED:
# 1. System Settings → Privacy & Security → Accessibility → Add Terminal (or your IDE)
# 2. System Settings → Privacy & Security → Screen Recording → Add Terminal (or your IDE)
# Without both permissions, screen capture and keyboard/mouse control WILL fail silently.
#
# Run with: python3 bot.py
# Capture templates: python3 bot.py --capture
# =============================================

import sys
import os
import time
import random
import signal
import argparse
import logging
import threading
from datetime import datetime
from pathlib import Path

import numpy as np
import cv2
import mss
import mss.tools
import pyautogui
from pynput import keyboard as pynput_keyboard

# ========================= SAFETY =========================
pyautogui.FAILSAFE = True   # Move mouse to top-left corner to emergency-stop
pyautogui.PAUSE = 0.0       # We handle all delays manually for randomization
# ==========================================================

# ========================= LOGGING ========================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot_session.log", mode="a"),
    ],
)
log = logging.getLogger("KnightBot")
# ==========================================================

# ========================= CONFIGURATION ==================
# Edit this section to match YOUR game window and keybinds.
# Use Activity Monitor or run: python3 -c "import pyautogui; print(pyautogui.size())"
# to find your screen resolution. Then drag your game window to a known position.

GAME_WINDOW = {
    "left": 0,       # X pixel of the game window's left edge
    "top":  45,      # Y pixel of the game window's top edge (45 accounts for macOS menu bar)
    "width":  1280,  # Width of the game window
    "height": 800,   # Height of the game window
}

# --- Detection ---
CONFIDENCE = 0.78           # Template matching threshold (0.0–1.0). Raise if false positives.
SCALE_FACTORS = [1.0, 0.9, 1.1]  # Multi-scale matching for resolution variance

# --- HP / Mana bar regions (relative to GAME_WINDOW top-left) ---
# Adjust these bounding boxes to cover only the colored part of each bar.
# Example: HP bar spanning x=10–210, y=15–25 relative to game window.
HP_BAR_REGION   = {"x": 10, "y": 15, "w": 200, "h": 12}   # Region of HP bar pixels
MANA_BAR_REGION = {"x": 10, "y": 30, "w": 200, "h": 12}   # Region of Mana bar pixels

# HP bar filled color range in BGR (OpenCV uses BGR, not RGB!)
# Calibrate by running: python3 bot.py --colorpick  (prints BGR under cursor)
HP_COLOR_LOW_BGR   = np.array([20,  20, 150], dtype=np.uint8)   # Dark red
HP_COLOR_HIGH_BGR  = np.array([60,  60, 255], dtype=np.uint8)   # Bright red
MANA_COLOR_LOW_BGR = np.array([120, 60,  20], dtype=np.uint8)   # Dark blue
MANA_COLOR_HIGH_BGR= np.array([255, 160, 80], dtype=np.uint8)   # Bright blue

# --- Thresholds ---
HEAL_HP_THRESHOLD  = 0.60   # Use HP potion if HP% drops below this (60%)
MANA_THRESHOLD     = 0.40   # Use Mana potion if Mana% drops below this (40%)
HP_SPELL_THRESHOLD = 0.35   # Fallback: use heal spell if HP% below this (35%)

# --- Hotkeys (keyboard keys as strings) ---
HOTKEYS = {
    "hp_potion":    "1",    # Press '1' to use HP potion
    "mana_potion":  "2",    # Press '2' to use Mana potion
    "heal_spell":   "3",    # Press '3' for heal spell (fallback)
    "attack_spell": "f1",   # Press F1 for melee/attack skill (optional)
    "loot":         "f2",   # Press F2 for auto-loot toggle (optional)
}

# --- Template image paths ---
# Run with --capture to create these interactively.
TEMPLATE_PATHS = {
    "hp_low":   "templates/hp_low.png",    # HP bar at ~30% (red, nearly empty)
    "mana_low": "templates/mana_low.png",  # Mana bar at ~30% (blue, nearly empty)
    "monster":  "templates/monster.png",   # Monster name plate or highlight
    "corpse":   "templates/corpse.png",    # Lootable corpse appearance
}

# --- Timing (seconds) ---
MAIN_LOOP_SLEEP   = 0.15    # Base delay between each main loop tick
LOG_INTERVAL      = 10.0    # Print status every N seconds
BREAK_MIN_INTERVAL= 240     # Minimum seconds between AFK breaks (4 min)
BREAK_MAX_INTERVAL= 480     # Maximum seconds between AFK breaks (8 min)
BREAK_MIN_DURATION= 15      # Minimum AFK break length (seconds)
BREAK_MAX_DURATION= 45      # Maximum AFK break length (seconds)

# --- Session ---
SESSION_MIN = 25 * 60       # Minimum session length in seconds (25 min)
SESSION_MAX = 30 * 60       # Maximum session length in seconds (30 min)

# --- Loot ---
AUTO_LOOT_KEY     = None    # Set to a hotkey string if game has auto-loot key, else None
LOOT_RADIUS_PX    = 200     # Search radius (pixels) for corpse near last kill
LOOT_RIGHT_CLICK  = True    # True = right-click corpse; False = use AUTO_LOOT_KEY
# ==========================================================


# ========================= GLOBALS ========================
_session_start    = None
_session_duration = None
_last_break_time  = None
_last_log_time    = None
_last_target_pos  = None     # (abs_x, abs_y) of last attacked monster
_looted_positions = set()    # Set of (x,y) tuples already looted
_stop_event       = threading.Event()
_templates        = {}       # Loaded OpenCV templates (name → ndarray)
_potion_cooldown  = {}       # Last time each hotkey was pressed
# ==========================================================


# ==================== SCREEN CAPTURE ======================
def capture_screen(region: dict | None = None) -> np.ndarray:
    """
    Fast screen capture using mss (significantly faster than PyAutoGUI on macOS).
    region: dict with keys left, top, width, height (absolute screen coords).
            If None, captures the full GAME_WINDOW region.
    Returns: BGR numpy array ready for OpenCV.
    """
    cap_region = region if region else GAME_WINDOW
    with mss.mss() as sct:
        raw = sct.grab(cap_region)
        img = np.array(raw, dtype=np.uint8)  # BGRA
    return cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)


def capture_game_subregion(rel_x: int, rel_y: int, w: int, h: int) -> np.ndarray:
    """
    Capture a sub-region relative to GAME_WINDOW top-left.
    """
    abs_region = {
        "left":   GAME_WINDOW["left"] + rel_x,
        "top":    GAME_WINDOW["top"]  + rel_y,
        "width":  w,
        "height": h,
    }
    return capture_screen(abs_region)
# ==========================================================


# ==================== TEMPLATE LOADING ====================
def load_templates() -> None:
    """
    Load all template images from disk into _templates dict.
    Templates must be BGR PNG images captured from YOUR game at YOUR resolution.
    Missing templates are skipped with a warning (bot continues without that feature).
    """
    for name, path in TEMPLATE_PATHS.items():
        if os.path.exists(path):
            img = cv2.imread(path, cv2.IMREAD_COLOR)
            if img is not None:
                _templates[name] = img
                log.info(f"✅ Template loaded: {name} ({img.shape[1]}×{img.shape[0]}px)")
            else:
                log.warning(f"⚠️  Failed to read template image: {path}")
        else:
            log.warning(f"⚠️  Template not found (skipping '{name}'): {path}")


def find_template(
    screen_bgr: np.ndarray,
    template_name: str,
    confidence: float = CONFIDENCE,
    search_region: tuple | None = None,
) -> tuple[int, int, float] | None:
    """
    Find a template in the given screen image using multi-scale matchTemplate.

    Args:
        screen_bgr:    Full BGR screenshot (or sub-region).
        template_name: Key in _templates dict.
        confidence:    Minimum match score (0–1).
        search_region: Optional (x, y, w, h) crop of screen_bgr to limit search area.

    Returns:
        (center_x, center_y, score) in screen_bgr pixel coords, or None if not found.
        Coordinates are relative to screen_bgr top-left.
    """
    if template_name not in _templates:
        return None

    template = _templates[template_name]
    haystack = screen_bgr

    if search_region:
        sx, sy, sw, sh = search_region
        haystack = screen_bgr[sy:sy+sh, sx:sx+sw]

    best_val   = -1.0
    best_loc   = None
    best_scale = 1.0
    th, tw     = template.shape[:2]

    for scale in SCALE_FACTORS:
        if scale != 1.0:
            new_w = int(tw * scale)
            new_h = int(th * scale)
            if new_w < 5 or new_h < 5:
                continue
            scaled_tmpl = cv2.resize(template, (new_w, new_h))
        else:
            scaled_tmpl = template
            new_h, new_w = th, tw

        if haystack.shape[0] < new_h or haystack.shape[1] < new_w:
            continue

        result = cv2.matchTemplate(haystack, scaled_tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_val:
            best_val   = max_val
            best_loc   = max_loc
            best_scale = scale

    if best_val >= confidence and best_loc is not None:
        tmpl_h = int(th * best_scale)
        tmpl_w = int(tw * best_scale)
        cx = best_loc[0] + tmpl_w // 2
        cy = best_loc[1] + tmpl_h // 2
        if search_region:
            cx += search_region[0]
            cy += search_region[1]
        return (cx, cy, best_val)

    return None
# ==========================================================


# ==================== HP / MANA DETECTION =================
def _bar_fill_percent(bar_region: dict, low_bgr: np.ndarray, high_bgr: np.ndarray) -> float:
    """
    Estimate fill % of a colored bar using color masking.
    Counts pixels matching the bar's fill color and divides by total bar width.

    Returns: float 0.0–1.0 (1.0 = full, 0.0 = empty).
    """
    img = capture_game_subregion(
        bar_region["x"], bar_region["y"],
        bar_region["w"], bar_region["h"]
    )
    mask     = cv2.inRange(img, low_bgr, high_bgr)
    filled_x = np.where(mask.any(axis=0))[0]   # columns with any matching pixel

    if len(filled_x) == 0:
        return 0.0

    # Rightmost filled column as fraction of total bar width
    rightmost = int(filled_x.max())
    return min(1.0, (rightmost + 1) / bar_region["w"])


def get_hp_percent() -> float:
    return _bar_fill_percent(HP_BAR_REGION, HP_COLOR_LOW_BGR, HP_COLOR_HIGH_BGR)


def get_mana_percent() -> float:
    return _bar_fill_percent(MANA_BAR_REGION, MANA_COLOR_LOW_BGR, MANA_COLOR_HIGH_BGR)
# ==========================================================


# ==================== HUMAN-LIKE MOUSE ===================
def _bezier_point(t: float, pts: list[tuple]) -> tuple[float, float]:
    """
    Evaluate a Bézier curve at parameter t ∈ [0,1] given control points.
    Supports any degree (2 = quadratic, 3 = cubic, etc.).
    """
    n = len(pts) - 1
    x = sum(
        (np.math.comb(n, i) * (1 - t) ** (n - i) * t ** i * pts[i][0])
        for i in range(n + 1)
    )
    y = sum(
        (np.math.comb(n, i) * (1 - t) ** (n - i) * t ** i * pts[i][1])
        for i in range(n + 1)
    )
    return (x, y)


def human_mouse_move(target_x: int, target_y: int, duration_range=(0.25, 0.65)) -> None:
    """
    Move mouse from current position to (target_x, target_y) along a randomized
    cubic Bézier curve that mimics natural human hand movement.

    Adds slight random jitter to the destination for micro-variation.
    """
    start_x, start_y = pyautogui.position()

    # Optional micro-miss: occasionally aim slightly off, then correct
    miss = random.random() < 0.12  # 12% chance of a small miss
    if miss:
        jitter_x = target_x + random.randint(-12, 12)
        jitter_y = target_y + random.randint(-8,  8)
    else:
        jitter_x = target_x + random.randint(-3, 3)
        jitter_y = target_y + random.randint(-3, 3)

    # Two random control points for a cubic Bézier
    mid_x = (start_x + jitter_x) / 2 + random.randint(-80, 80)
    mid_y = (start_y + jitter_y) / 2 + random.randint(-60, 60)
    cp1 = (start_x + random.randint(-40, 40), start_y + random.randint(-30, 30))
    cp2 = (mid_x,  mid_y)
    cp3 = (jitter_x + random.randint(-15, 15), jitter_y + random.randint(-10, 10))

    control_pts = [(start_x, start_y), cp1, cp2, cp3, (jitter_x, jitter_y)]

    steps    = random.randint(25, 60)
    duration = random.uniform(*duration_range)
    sleep_t  = duration / steps

    for i in range(steps + 1):
        t  = i / steps
        pt = _bezier_point(t, control_pts)
        pyautogui.moveTo(int(pt[0]), int(pt[1]), _pause=False)
        time.sleep(sleep_t)

    # Correction move if we initially missed
    if miss:
        time.sleep(random.uniform(0.05, 0.12))
        pyautogui.moveTo(target_x, target_y, _pause=False)


def click_at(x: int, y: int, button: str = "left", move: bool = True) -> None:
    """
    Human-like click: move then click with random pre/post delays.
    """
    if move:
        human_mouse_move(x, y)
    time.sleep(random.uniform(0.08, 0.25))
    pyautogui.click(x, y, button=button, _pause=False)
    time.sleep(random.uniform(0.10, 0.30))


def press_key(key: str) -> None:
    """
    Press a keyboard hotkey with a small random delay.
    Handles both single characters and special keys like 'f1'.
    """
    time.sleep(random.uniform(0.05, 0.15))
    pyautogui.press(key)
    time.sleep(random.uniform(0.05, 0.20))


def random_wiggle(n_moves: int = 3) -> None:
    """
    Perform small random mouse wiggles within the game window.
    Used during idle moments to appear human.
    """
    gx = GAME_WINDOW["left"]
    gy = GAME_WINDOW["top"]
    gw = GAME_WINDOW["width"]
    gh = GAME_WINDOW["height"]
    margin = 80

    for _ in range(n_moves):
        rx = random.randint(gx + margin, gx + gw - margin)
        ry = random.randint(gy + margin, gy + gh - margin)
        human_mouse_move(rx, ry, duration_range=(0.3, 0.8))
        time.sleep(random.uniform(0.2, 0.6))
# ==========================================================


# ==================== HEAL LOGIC ==========================
def _on_cooldown(key: str, cooldown_s: float = 0.8) -> bool:
    """Return True if this hotkey was pressed too recently."""
    last = _potion_cooldown.get(key, 0.0)
    return (time.time() - last) < cooldown_s


def _record_press(key: str) -> None:
    _potion_cooldown[key] = time.time()


def check_and_heal() -> None:
    """
    Monitor HP and Mana; use potions/spells as needed.
    Priority: potions first → spells as fallback.
    """
    hp   = get_hp_percent()
    mana = get_mana_percent()

    # --- HP ---
    if hp < HP_SPELL_THRESHOLD:
        # Critical HP: use spell immediately if not on cooldown
        if not _on_cooldown(HOTKEYS["heal_spell"], 2.0):
            log.info(f"❤️  CRITICAL HP {hp:.0%} → casting heal spell")
            press_key(HOTKEYS["heal_spell"])
            _record_press(HOTKEYS["heal_spell"])
            time.sleep(random.uniform(0.3, 0.6))

    if hp < HEAL_HP_THRESHOLD:
        if not _on_cooldown(HOTKEYS["hp_potion"], 1.0):
            log.info(f"🧪 HP low ({hp:.0%}) → using HP potion [{HOTKEYS['hp_potion']}]")
            press_key(HOTKEYS["hp_potion"])
            _record_press(HOTKEYS["hp_potion"])
            time.sleep(random.uniform(0.3, 0.8))

    # --- Mana ---
    if mana < MANA_THRESHOLD:
        if not _on_cooldown(HOTKEYS["mana_potion"], 1.0):
            log.info(f"💧 Mana low ({mana:.0%}) → using Mana potion [{HOTKEYS['mana_potion']}]")
            press_key(HOTKEYS["mana_potion"])
            _record_press(HOTKEYS["mana_potion"])
            time.sleep(random.uniform(0.3, 0.8))
# ==========================================================


# ==================== ATTACK LOGIC ========================
def find_and_attack() -> bool:
    """
    Scan the center 70% of the game window for a monster template.
    If found, move mouse there and click to attack.

    Returns: True if a target was found and attacked, False otherwise.
    """
    global _last_target_pos

    if "monster" not in _templates:
        return False

    gw = GAME_WINDOW["width"]
    gh = GAME_WINDOW["height"]

    # Search region: center 70% of screen (avoid UI edges)
    margin_x = int(gw * 0.15)
    margin_y = int(gh * 0.15)
    search = (margin_x, margin_y, gw - 2 * margin_x, gh - 2 * margin_y)

    screen = capture_screen()
    result = find_template(screen, "monster", search_region=search)

    if result is None:
        return False

    rel_x, rel_y, score = result
    abs_x = GAME_WINDOW["left"] + rel_x
    abs_y = GAME_WINDOW["top"]  + rel_y

    log.info(f"⚔️  Monster detected at ({abs_x},{abs_y}) [conf={score:.2f}] — attacking")

    click_at(abs_x, abs_y, button="left")
    _last_target_pos = (abs_x, abs_y)

    # Optional attack skill hotkey
    if HOTKEYS.get("attack_spell"):
        time.sleep(random.uniform(0.2, 0.5))
        press_key(HOTKEYS["attack_spell"])

    time.sleep(random.uniform(0.8, 1.8))   # Wait for attack animation
    return True
# ==========================================================


# ==================== LOOT LOGIC ==========================
def _pos_already_looted(x: int, y: int, radius: int = 30) -> bool:
    for lx, ly in _looted_positions:
        if abs(lx - x) < radius and abs(ly - y) < radius:
            return True
    return False


def loot_corpses() -> None:
    """
    After a kill, scan near the last target position for a corpse template.
    Right-click to open loot window (or use auto-loot key).
    """
    global _looted_positions

    if "corpse" not in _templates or _last_target_pos is None:
        return

    lx, ly = _last_target_pos

    # Search within LOOT_RADIUS_PX of last target (relative coords)
    rel_lx = lx - GAME_WINDOW["left"]
    rel_ly = ly - GAME_WINDOW["top"]
    sx = max(0, rel_lx - LOOT_RADIUS_PX)
    sy = max(0, rel_ly - LOOT_RADIUS_PX)
    sw = min(GAME_WINDOW["width"]  - sx, LOOT_RADIUS_PX * 2)
    sh = min(GAME_WINDOW["height"] - sy, LOOT_RADIUS_PX * 2)

    screen = capture_screen()
    result = find_template(screen, "corpse", search_region=(sx, sy, sw, sh))

    if result is None:
        return

    rel_x, rel_y, score = result
    abs_x = GAME_WINDOW["left"] + rel_x
    abs_y = GAME_WINDOW["top"]  + rel_y

    if _pos_already_looted(abs_x, abs_y):
        return

    log.info(f"💀 Corpse found at ({abs_x},{abs_y}) [conf={score:.2f}] — looting")

    if LOOT_RIGHT_CLICK:
        click_at(abs_x, abs_y, button="right")
        time.sleep(random.uniform(0.35, 0.65))
        # Click the "Loot" option which typically appears below the right-click menu
        # Adjust the Y offset to match your game's context menu
        click_at(abs_x, abs_y + 22, button="left")
    elif AUTO_LOOT_KEY:
        human_mouse_move(abs_x, abs_y)
        press_key(AUTO_LOOT_KEY)

    _looted_positions.add((abs_x, abs_y))
    time.sleep(random.uniform(0.5, 1.0))

    # Prune old looted positions to avoid unbounded memory growth
    if len(_looted_positions) > 200:
        _looted_positions = set(list(_looted_positions)[-100:])
# ==========================================================


# ==================== AFK BREAK LOGIC =====================
def take_afk_break() -> None:
    """
    Simulate an AFK break: move mouse around randomly, pause all actions.
    Helps evade simple bot-detection heuristics.
    """
    duration = random.uniform(BREAK_MIN_DURATION, BREAK_MAX_DURATION)
    log.info(f"☕ Taking AFK break for {duration:.0f}s ...")

    end = time.time() + duration
    while time.time() < end and not _stop_event.is_set():
        random_wiggle(n_moves=random.randint(1, 3))
        time.sleep(random.uniform(2.0, 8.0))

    log.info("▶️  Resuming after break.")
# ==========================================================


# ==================== TEMPLATE CAPTURE MODE ===============
def create_templates() -> None:
    """
    Interactive template capture utility.
    Run with: python3 bot.py --capture

    Instructions printed to console. Press S over any UI element to save a 100×60 screenshot
    centered on the current mouse cursor position as a template image.

    HOW TO CALIBRATE:
      1. Launch your game and position your character as normal.
      2. Run this mode: python3 bot.py --capture
      3. Lower HP to ~30%, hover over the HP bar → press S  → saves templates/hp_low.png
      4. Lower Mana to ~30%, hover over mana bar → press S  → saves templates/mana_low.png
      5. Stand near a monster, hover its name/body  → press S  → saves templates/monster.png
      6. Kill a monster, hover over the corpse       → press S  → saves templates/corpse.png
      7. Press Q to quit capture mode.
    """
    Path("templates").mkdir(exist_ok=True)

    capture_names = ["hp_low", "mana_low", "monster", "corpse"]
    idx           = [0]  # mutable for closure

    def _on_press(key):
        try:
            ch = key.char.lower() if hasattr(key, "char") and key.char else ""
        except AttributeError:
            ch = ""

        if ch == "s":
            cx, cy   = pyautogui.position()
            half_w, half_h = 60, 40
            region = {
                "left":   max(0, cx - half_w),
                "top":    max(0, cy - half_h),
                "width":  half_w * 2,
                "height": half_h * 2,
            }
            img     = capture_screen(region)
            name    = capture_names[idx[0] % len(capture_names)]
            outpath = TEMPLATE_PATHS[name]
            cv2.imwrite(outpath, img)
            log.info(f"📸 Saved template '{name}' → {outpath}")
            idx[0] += 1
            if idx[0] < len(capture_names):
                log.info(f"👉 Next: hover over [{capture_names[idx[0]]}] and press S")
            else:
                log.info("✅ All templates captured! Press Q to exit.")

        elif ch == "q":
            log.info("👋 Exiting capture mode.")
            return False   # Stop listener

    log.info("=" * 60)
    log.info("TEMPLATE CAPTURE MODE")
    log.info("=" * 60)
    log.info(f"First target: hover over [{capture_names[0]}] and press S")
    log.info("Press Q to quit at any time.")
    log.info("=" * 60)

    with pynput_keyboard.Listener(on_press=_on_press) as listener:
        listener.join()
# ==========================================================


# ==================== COLOR PICKER UTIL ===================
def color_picker_mode() -> None:
    """
    Run with: python3 bot.py --colorpick
    Continuously prints the BGR color under the mouse cursor.
    Use this to calibrate HP_COLOR_LOW/HIGH_BGR and MANA_COLOR_LOW/HIGH_BGR.
    Press Ctrl+C to stop.
    """
    log.info("🎨 Color picker mode — move mouse over bar colors. Ctrl+C to stop.")
    try:
        while True:
            x, y   = pyautogui.position()
            region = {"left": x, "top": y, "width": 1, "height": 1}
            with mss.mss() as sct:
                raw = np.array(sct.grab(region))
            b, g, r = int(raw[0, 0, 0]), int(raw[0, 0, 1]), int(raw[0, 0, 2])
            print(f"\r  Cursor ({x:4d},{y:4d}) → BGR=({b:3d},{g:3d},{r:3d})    ", end="", flush=True)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print()
        log.info("Color picker stopped.")
# ==========================================================


# ==================== STATUS LOGGING ======================
def log_status() -> None:
    """Print a concise status line every LOG_INTERVAL seconds."""
    global _last_log_time
    now = time.time()
    if _last_log_time and (now - _last_log_time) < LOG_INTERVAL:
        return
    _last_log_time = now

    elapsed   = now - _session_start
    remaining = max(0, _session_duration - elapsed)
    hp        = get_hp_percent()
    mana      = get_mana_percent()

    log.info(
        f"📊 HP:{hp:.0%}  💧Mana:{mana:.0%}  "
        f"⏱ {elapsed/60:.1f}min elapsed  ⏳{remaining/60:.1f}min left  "
        f"💀 Looted:{len(_looted_positions)}"
    )
# ==========================================================


# ==================== CTRL+C HANDLER =====================
def _graceful_exit(signum=None, frame=None) -> None:
    """Catch Ctrl+C: 3-second countdown before exit."""
    print()
    log.info("🛑 Ctrl+C detected. Shutting down in 3 seconds ...")
    for i in range(3, 0, -1):
        print(f"  {i}...", flush=True)
        time.sleep(1.0)
    _stop_event.set()
    log.info("👋 Bot stopped by user.")
    sys.exit(0)


signal.signal(signal.SIGINT, _graceful_exit)
# ==========================================================


# ==================== MAIN LOOP ===========================
def main() -> None:
    global _session_start, _session_duration, _last_break_time, _last_log_time

    # ---- macOS permission reminder ----
    log.info("=" * 60)
    log.info("MAC GAME AUTOMATION BOT — KNIGHT EDITION")
    log.info("=" * 60)
    log.info("⚠️  macOS PERMISSIONS REQUIRED:")
    log.info("   System Settings → Privacy & Security → Accessibility")
    log.info("   System Settings → Privacy & Security → Screen Recording")
    log.info("   Add your Terminal (or IDE) to BOTH lists.")
    log.info("=" * 60)
    time.sleep(1.5)

    # ---- Load templates ----
    load_templates()
    if not _templates:
        log.warning("⚠️  No templates loaded. Run: python3 bot.py --capture first.")

    # ---- Session setup ----
    _session_duration = random.uniform(SESSION_MIN, SESSION_MAX)
    _session_start    = time.time()
    _last_break_time  = time.time()
    _last_log_time    = time.time()
    no_target_since   = time.time()

    log.info(f"🚀 Session started. Duration: {_session_duration/60:.1f} min")
    log.info("   Move mouse to TOP-LEFT CORNER to emergency stop (PyAutoGUI failsafe).")

    # ---- Main loop ----
    while not _stop_event.is_set():

        # Session expiry check
        elapsed = time.time() - _session_start
        if elapsed >= _session_duration:
            log.info("✅ Session complete. Shutting down safely.")
            break

        # Periodic status log
        log_status()

        # --- AFK break check ---
        time_since_break = time.time() - _last_break_time
        next_break_in    = random.uniform(BREAK_MIN_INTERVAL, BREAK_MAX_INTERVAL)
        if time_since_break >= next_break_in:
            take_afk_break()
            _last_break_time = time.time()
            continue

        # --- Healing (highest priority) ---
        try:
            check_and_heal()
        except Exception as exc:
            log.error(f"Heal error: {exc}")

        # --- Attack ---
        attacked = False
        try:
            attacked = find_and_attack()
        except pyautogui.FailSafeException:
            log.info("🛑 Failsafe triggered (mouse corner). Exiting.")
            break
        except Exception as exc:
            log.error(f"Attack error: {exc}")

        if attacked:
            no_target_since = time.time()
        else:
            # No target found: idle behavior
            idle_duration = time.time() - no_target_since

            if idle_duration > 30.0:
                # 30s with no target → small random wiggle
                random_wiggle(n_moves=random.randint(1, 2))
                no_target_since = time.time()   # Reset so we don't spam wiggle

        # --- Loot ---
        try:
            loot_corpses()
        except Exception as exc:
            log.error(f"Loot error: {exc}")

        # --- Main loop sleep with slight randomization ---
        time.sleep(MAIN_LOOP_SLEEP + random.uniform(0.0, 0.08))

    log.info("🏁 Bot session ended. Goodbye!")
# ==========================================================


# ==================== ENTRY POINT =========================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mac MMORPG Knight Bot")
    parser.add_argument("--capture",   action="store_true", help="Run template capture mode")
    parser.add_argument("--colorpick", action="store_true", help="Run color picker utility")
    args = parser.parse_args()

    if args.capture:
        create_templates()
    elif args.colorpick:
        color_picker_mode()
    else:
        main()
# ==========================================================
