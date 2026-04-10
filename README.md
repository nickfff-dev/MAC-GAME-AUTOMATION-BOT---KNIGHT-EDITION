# 🛡️ Mac MMORPG Knight Bot

> A macOS-only, screen-reading automation bot for classic MMORPGs (Tibia-style).  
> Built with PyAutoGUI + OpenCV. No memory reading. No injection. No client modification.

---

## ⚠️ Disclaimer

This bot is provided **for educational and personal research purposes only**.  
Using automation software may violate your game's Terms of Service and result in account suspension or permanent banning. **Use at your own risk.** The author accepts no responsibility for any consequences arising from use of this software.

---

## 📋 Table of Contents

- [Features](#-features)
- [Requirements](#-requirements)
- [Installation](#-installation)
- [macOS Permissions Setup](#-macos-permissions-setup)
- [Quick Start](#-quick-start)
- [Template Capture Guide](#-template-capture-guide)
- [Configuration Reference](#-configuration-reference)
- [How It Works](#-how-it-works)
- [Utilities](#-utilities)
- [Safety & Anti-Detection](#-safety--anti-detection)
- [Troubleshooting](#-troubleshooting)
- [Project Structure](#-project-structure)
- [FAQ](#-faq)

---

## ✨ Features

| Feature | Description |
|---|---|
| ❤️ **Auto HP Heal** | Uses HP potions when HP drops below 60%. Falls back to heal spell at 35%. |
| 💧 **Auto Mana Heal** | Uses Mana potions when Mana drops below 40%. |
| ⚔️ **Auto Attack** | Scans screen center for monsters, clicks and attacks with optional skill hotkey. |
| 💀 **Auto Loot** | Detects corpses near the last kill and right-clicks to loot. |
| 🧠 **Human-like Behavior** | Bézier curve mouse movement, randomized delays, micro-misses, and idle wiggles. |
| ☕ **AFK Breaks** | Random 15–45 second breaks every 4–8 minutes. |
| ⏱️ **Session Limit** | Auto-stops after 25–30 minutes (randomized). |
| 📸 **Template Capture Mode** | Built-in interactive tool to capture your own UI templates. |
| 🎨 **Color Picker Mode** | Real-time BGR pixel inspector for calibrating HP/Mana bar colors. |
| 📝 **Session Logging** | Full timestamped log saved to `bot_session.log`. |

---

## 📦 Requirements

- **macOS** (Ventura 13+ recommended; no Windows support)
- **Python 3.11+**
- The following Python libraries:

```
pyautogui>=0.9.54
opencv-python>=4.8.0
numpy>=1.24.0
mss>=9.0.1
Pillow>=10.0.0
pynput>=1.7.6
```

---

## 🔧 Installation

### 1. Clone or download the project

```bash
git clone https://github.com/yourname/knight-bot.git
cd knight-bot
```

Or simply place `bot.py` in a folder of your choice.

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install pyautogui opencv-python numpy mss pillow pynput
```

Or using the requirements file if provided:

```bash
pip install -r requirements.txt
```

### 4. Create the templates folder

```bash
mkdir templates
```

---

## 🔐 macOS Permissions Setup

> **Both permissions are required. The bot will fail silently without them.**

### Accessibility Permission
Allows the bot to control the keyboard and mouse.

1. Open **System Settings** → **Privacy & Security** → **Accessibility**
2. Click the **+** button
3. Navigate to and add your **Terminal** app (or IDE, e.g. iTerm2, VS Code)
4. Toggle it **ON**

### Screen Recording Permission
Allows the bot to capture screen pixels with `mss`.

1. Open **System Settings** → **Privacy & Security** → **Screen Recording**
2. Click the **+** button
3. Add your **Terminal** app (same one you run the bot from)
4. Toggle it **ON**
5. **Restart Terminal** after granting both permissions

> 💡 **Tip:** If you use iTerm2, PyCharm, or another terminal, add that specific app — not the default Terminal.

---

## 🚀 Quick Start

### Step 1 — Find your game window coordinates

```bash
python3 -c "import pyautogui; import time; time.sleep(3); print(pyautogui.position())"
```

Move your mouse to the **top-left corner** of your game window while the script counts down. Note the `(x, y)` output.

### Step 2 — Edit `GAME_WINDOW` in `bot.py`

```python
GAME_WINDOW = {
    "left":   100,   # X of game window top-left corner
    "top":    50,    # Y of game window top-left corner
    "width":  1280,  # Width of the game window
    "height": 800,   # Height of the game window
}
```

### Step 3 — Capture your templates

```bash
python3 bot.py --capture
```

Follow the on-screen instructions to save HP bar, Mana bar, Monster, and Corpse templates. Full guide [below](#-template-capture-guide).

### Step 4 — Calibrate bar colors (optional but recommended)

```bash
python3 bot.py --colorpick
```

Hover over the filled portion of your HP and Mana bars while the script prints BGR values. Update `HP_COLOR_LOW/HIGH_BGR` and `MANA_COLOR_LOW/HIGH_BGR` in the config.

### Step 5 — Run the bot

```bash
python3 bot.py
```

The bot will:
- Print a permission reminder
- Load templates
- Start a 25–30 minute session
- Handle healing, attacking, and looting automatically

### Emergency Stop

Move your mouse to the **very top-left corner** of your screen (pixel `0,0`).  
PyAutoGUI's built-in failsafe will raise an exception and stop the bot immediately.

Or press `Ctrl+C` for a graceful 3-second countdown shutdown.

---

## 📸 Template Capture Guide

Templates are small PNG screenshots of specific UI elements in **your game at your resolution**. They are used by OpenCV's `matchTemplate` to locate things on screen.

### Run capture mode

```bash
python3 bot.py --capture
```

You will be prompted for 4 templates in order:

| # | Template | What to hover over | When to capture |
|---|---|---|---|
| 1 | `hp_low.png` | The HP bar | When HP is at ~25–35% |
| 2 | `mana_low.png` | The Mana bar | When Mana is at ~25–35% |
| 3 | `monster.png` | A monster's name plate or body highlight | While standing next to a live monster |
| 4 | `corpse.png` | A dead monster's corpse | Immediately after killing one |

### Controls in capture mode

| Key | Action |
|---|---|
| `S` | Save a 120×80px screenshot centered on your cursor as the current template |
| `Q` | Quit capture mode |

### Tips for good templates

- **HP/Mana bars:** Capture at a consistent low percentage — not full (the bot only needs to trigger below a threshold).
- **Monsters:** Use a distinctive part of the name text or a colored highlight. Avoid capturing parts of the background.
- **Corpses:** Capture the glowing outline or gray body — something visually unique to dead monsters.
- **Avoid UI overlap:** Make sure no other window overlaps your game during capture.
- **Re-capture if bot misses:** If false positives or misses occur, delete the template PNG and re-capture.

Templates are saved to:
```
templates/
  hp_low.png
  mana_low.png
  monster.png
  corpse.png
```

---

## ⚙️ Configuration Reference

All configuration lives at the top of `bot.py` under the `CONFIGURATION` block.

### Game Window

```python
GAME_WINDOW = {
    "left": 0,       # Absolute X of the game window's left edge
    "top":  45,      # Absolute Y (45 accounts for macOS menu bar)
    "width":  1280,
    "height": 800,
}
```

### Detection Thresholds

```python
CONFIDENCE = 0.78       # Template match minimum score (0.0–1.0)
                        # Raise to 0.85–0.90 if you get false positives
                        # Lower to 0.70–0.75 if templates aren't being found
SCALE_FACTORS = [1.0, 0.9, 1.1]  # Multi-scale search (handles slight size differences)
```

### HP / Mana Bar Regions

These define the pixel area of each bar, **relative to GAME_WINDOW top-left**:

```python
HP_BAR_REGION   = {"x": 10, "y": 15, "w": 200, "h": 12}
MANA_BAR_REGION = {"x": 10, "y": 30, "w": 200, "h": 12}
```

> 💡 Use the color picker (`python3 bot.py --colorpick`) to find the exact x/y and color of your bars.

### Bar Fill Colors (BGR format)

OpenCV uses **BGR** (not RGB). Blue and Red are swapped compared to standard color pickers.

```python
HP_COLOR_LOW_BGR   = np.array([20,  20, 150])   # Darkest red considered "HP filled"
HP_COLOR_HIGH_BGR  = np.array([60,  60, 255])   # Brightest red considered "HP filled"
MANA_COLOR_LOW_BGR = np.array([120, 60,  20])   # Darkest blue considered "Mana filled"
MANA_COLOR_HIGH_BGR= np.array([255, 160, 80])   # Brightest blue considered "Mana filled"
```

### Heal Thresholds

```python
HEAL_HP_THRESHOLD  = 0.60   # Use HP potion if HP% < 60%
MANA_THRESHOLD     = 0.40   # Use Mana potion if Mana% < 40%
HP_SPELL_THRESHOLD = 0.35   # Use heal SPELL if HP% < 35% (critical fallback)
```

### Hotkeys

```python
HOTKEYS = {
    "hp_potion":    "1",    # Key to press for HP potion
    "mana_potion":  "2",    # Key to press for Mana potion
    "heal_spell":   "3",    # Key to press for heal spell (fallback)
    "attack_spell": "f1",   # Optional melee/attack skill hotkey
    "loot":         "f2",   # Optional auto-loot toggle key
}
```

Special keys: use `"f1"` through `"f12"` for function keys, `"space"`, `"enter"`, etc.  
See [PyAutoGUI key docs](https://pyautogui.readthedocs.io/en/latest/keyboard.html#keyboard-keys) for the full list.

### Session Timing

```python
SESSION_MIN = 25 * 60    # 25 minutes minimum session
SESSION_MAX = 30 * 60    # 30 minutes maximum session
```

### AFK Breaks

```python
BREAK_MIN_INTERVAL = 240   # Minimum seconds between breaks (4 min)
BREAK_MAX_INTERVAL = 480   # Maximum seconds between breaks (8 min)
BREAK_MIN_DURATION = 15    # Minimum break length in seconds
BREAK_MAX_DURATION = 45    # Maximum break length in seconds
```

### Loot Settings

```python
AUTO_LOOT_KEY   = None    # Set to a key string for auto-loot hotkey, or None
LOOT_RADIUS_PX  = 200     # Pixel radius to search for corpses around last kill
LOOT_RIGHT_CLICK = True   # True = right-click corpse; False = use AUTO_LOOT_KEY
```

---

## 🧠 How It Works

### Main Loop (every ~0.15s)

```
┌─────────────────────────────────┐
│         Session Timer           │  ← Stops after 25–30 min
└────────────────┬────────────────┘
                 ▼
        ┌────────────────┐
        │  Check & Heal  │  ← HP/Mana bars via color detection
        └────────┬───────┘
                 ▼
        ┌────────────────┐
        │ Find & Attack  │  ← OpenCV template match for monster
        └────────┬───────┘
                 ▼
        ┌────────────────┐
        │  Loot Corpses  │  ← Template match near last kill position
        └────────┬───────┘
                 ▼
        ┌────────────────┐
        │  Break Check?  │  ← Random 4–8 min interval AFK break
        └────────┬───────┘
                 ▼
        ┌────────────────┐
        │  Idle Wiggle?  │  ← If no target for 30s, random mouse move
        └────────────────┘
```

### HP / Mana Detection

Bar fill percentage is calculated by color masking — it counts all pixel columns in the bar region that match the configured fill color, then finds the rightmost filled column as a fraction of total bar width.

### Template Matching

Uses OpenCV's `TM_CCOEFF_NORMED` algorithm across multiple scales (`[0.9×, 1.0×, 1.1×]`) to handle minor resolution differences. The best match across all scales is used.

### Human-like Mouse Movement

Mouse paths follow a **cubic Bézier curve** with two randomized control points, producing natural arcing movements. Additional randomization includes:

- ±3px random destination jitter on every move
- 12% chance of a deliberate micro-miss (5–12px off), followed by a correction move
- Step count: 25–60 random steps per movement
- Duration: 0.25–0.65 seconds per movement (configurable per action)

---

## 🛠️ Utilities

### Template Capture Mode

```bash
python3 bot.py --capture
```

Interactive mode to save template PNGs from your live game screen.

### Color Picker Mode

```bash
python3 bot.py --colorpick
```

Prints the BGR color under your mouse cursor in real time. Use this to set accurate `HP_COLOR_*_BGR` and `MANA_COLOR_*_BGR` values.

```
Cursor ( 342, 198) → BGR=(  32,  41, 218)
```

Press `Ctrl+C` to exit.

---

## 🛡️ Safety & Anti-Detection

The bot includes several measures designed to reduce behavioral fingerprinting:

| Measure | Details |
|---|---|
| **Bézier mouse paths** | Non-linear curved trajectories mimic real hand movement |
| **Randomized delays** | Every action uses `random.uniform(min, max)` — no fixed intervals |
| **Micro-misses** | 12% of clicks aim slightly off-target before correcting |
| **AFK breaks** | 15–45s idle periods with random mouse wandering every 4–8 min |
| **Session limits** | Hard stop after 25–30 min; do not chain sessions |
| **Idle wiggle** | Small random mouse movements when no target is found for 30s |
| **Potion cooldowns** | Tracks time since last key press to avoid spamming potions |

**These measures reduce, but do not eliminate, detection risk.**

---

## ❓ Troubleshooting

### Bot can't control mouse/keyboard

→ Grant **Accessibility** permission in System Settings → Privacy & Security → Accessibility.  
→ Restart your Terminal after granting permission.

### Bot can't capture screen (black screenshots)

→ Grant **Screen Recording** permission in System Settings → Privacy & Security → Screen Recording.  
→ Make sure you added the exact terminal app you're launching the bot from.

### Template not found / always returns None

→ Re-run `python3 bot.py --capture` and recapture the template with your game at the exact game resolution.  
→ Lower `CONFIDENCE` to `0.70` and test.  
→ Make sure `GAME_WINDOW` coordinates exactly match your actual game window position.  
→ Verify the template PNG was saved correctly by opening it in Preview.

### HP/Mana always reads 0% or 100%

→ Run `python3 bot.py --colorpick` and hover directly over the **filled color** of each bar.  
→ Update `HP_COLOR_LOW/HIGH_BGR` and `MANA_COLOR_LOW/HIGH_BGR` with the observed BGR values.  
→ Verify `HP_BAR_REGION` / `MANA_BAR_REGION` x/y/w/h covers only the colored fill of the bar.

### Bot clicks wrong location

→ Double-check `GAME_WINDOW["left"]` and `GAME_WINDOW["top"]`. Use:
```bash
python3 -c "import pyautogui; import time; time.sleep(3); print(pyautogui.position())"
```
and hover over the game window's top-left corner during the countdown.

### Failsafe triggered unexpectedly

→ Your mouse passed through the top-left corner (`0,0`) of the screen.  
→ Adjust `GAME_WINDOW` so it doesn't require the mouse to cross the corner, or move your game window away from that corner.

### `ModuleNotFoundError`

→ Make sure your virtual environment is activated:
```bash
source venv/bin/activate
pip install pyautogui opencv-python numpy mss pillow pynput
```

---

## 📁 Project Structure

```
knight-bot/
├── bot.py                  # Main bot script (single-file)
├── requirements.txt        # Python dependencies
├── bot_session.log         # Auto-generated session log
├── templates/
│   ├── hp_low.png          # HP bar template (captured by user)
│   ├── mana_low.png        # Mana bar template
│   ├── monster.png         # Monster template
│   └── corpse.png          # Corpse template
└── README.md               # This file
```

---

## ❓ FAQ

**Q: Does this work on Windows or Linux?**  
A: No. The bot is macOS-only. It uses `mss` for screen capture with macOS-specific assumptions, and all coordinates are tuned for macOS display scaling. No Windows code is included by design.

**Q: Which games does this work with?**  
A: Any classic MMORPG with visible HP/mana bars, monsters with a consistent visual appearance, and lootable corpses — e.g. Tibia, old-school RuneScape (with modifications), or similar. You provide the templates; the bot adapts to your game.

**Q: Will I get banned?**  
A: Possibly. Most MMORPGs have anti-cheat systems. Session limits and human-like behavior reduce risk but do not eliminate it. Never run overnight or for extended continuous periods.

**Q: Can I run multiple sessions back-to-back?**  
A: It is strongly discouraged. Take breaks between sessions matching or exceeding the session length. Never automate 24/7 play.

**Q: The bot attacks the wrong things. How do I fix it?**  
A: Re-capture the `monster.png` template more precisely. Crop it tightly to the most unique visual element (e.g. the red name text only) and raise `CONFIDENCE` to `0.82–0.88`.

**Q: Can I change the session duration?**  
A: Yes. Edit `SESSION_MIN` and `SESSION_MAX` in the configuration block.

**Q: How do I add support for a second attack skill?**  
A: Add the key to `HOTKEYS` and call `press_key(HOTKEYS["your_key"])` inside `find_and_attack()` after the first skill press.
