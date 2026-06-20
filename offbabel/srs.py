"""Spaced-repetition engine (Leitner). The scheduler + source of truth for what to practice.

One shared `items` table serves BOTH modes (a Speak phrase or a Sign letter/word is an "item").
Leitner boxes 1..5 with expanding intervals; a miss drops to box 1, mastery = box 5.
Cognee (cognee_memory.py) layers semantic insight ON TOP of this; it does not replace it.
"""
import os
import sqlite3
import time

from . import config

# box -> days to wait before the item is due again. Box 1 = 0 days (resurfaces same/next session).
BOX_INTERVAL_DAYS = {1: 0, 2: 1, 3: 3, 4: 7, 5: 16}
DAY = 86400
MASTER_BOX = 5


def _conn():
    os.makedirs(config.DATA_DIR, exist_ok=True)
    c = sqlite3.connect(config.MEMORY_DB)
    c.row_factory = sqlite3.Row
    return c


def init():
    with _conn() as c:
        c.execute(
            """CREATE TABLE IF NOT EXISTS items(
                id INTEGER PRIMARY KEY,
                key TEXT UNIQUE NOT NULL,      -- mode:scenario:prompt
                mode TEXT NOT NULL,            -- 'speak' | 'sign'
                scenario TEXT NOT NULL,        -- scenario id or sign level id
                level TEXT,                    -- A1/A2/B1 or sign level id
                prompt TEXT NOT NULL,          -- target phrase, or letter/word
                box INTEGER NOT NULL DEFAULT 1,
                miss_count INTEGER NOT NULL DEFAULT 0,
                seen_count INTEGER NOT NULL DEFAULT 0,
                last_seen REAL NOT NULL DEFAULT 0,
                due_at REAL NOT NULL DEFAULT 0,
                mastered INTEGER NOT NULL DEFAULT 0
            )"""
        )
        c.execute("CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT)")


def _key(mode, scenario, prompt):
    return f"{mode}:{scenario}:{prompt}"


def ensure_item(mode, scenario, level, prompt):
    with _conn() as c:
        c.execute(
            """INSERT OR IGNORE INTO items(key, mode, scenario, level, prompt, due_at)
               VALUES(?, ?, ?, ?, ?, 0)""",
            (_key(mode, scenario, prompt), mode, scenario, level, prompt),
        )


def record_result(mode, scenario, level, prompt, correct):
    """Update an item's Leitner state from one attempt. Returns the new state dict."""
    ensure_item(mode, scenario, level, prompt)
    now = time.time()
    with _conn() as c:
        row = c.execute("SELECT * FROM items WHERE key=?", (_key(mode, scenario, prompt),)).fetchone()
        box = row["box"]
        miss = row["miss_count"]
        if correct:
            box = min(box + 1, MASTER_BOX)
        else:
            box = 1
            miss += 1
        mastered = 1 if box >= MASTER_BOX else 0
        due = now + BOX_INTERVAL_DAYS[box] * DAY
        c.execute(
            """UPDATE items SET box=?, miss_count=?, seen_count=seen_count+1,
               last_seen=?, due_at=?, mastered=? WHERE key=?""",
            (box, miss, now, due, mastered, _key(mode, scenario, prompt)),
        )
    _touch_streak(now)
    return {"box": box, "miss_count": miss, "mastered": bool(mastered)}


def due_items(mode=None, limit=20, now=None):
    """Items due for review, weakest first. The review queue."""
    now = time.time() if now is None else now
    q = "SELECT * FROM items WHERE mastered=0 AND due_at<=?"
    args = [now]
    if mode:
        q += " AND mode=?"
        args.append(mode)
    q += " ORDER BY box ASC, miss_count DESC LIMIT ?"
    args.append(limit)
    with _conn() as c:
        return [dict(r) for r in c.execute(q, args).fetchall()]


def due_count(mode=None, now=None):
    return len(due_items(mode=mode, limit=9999, now=now))


def mastery(mode=None):
    """pct = average progress toward mastery (box 1 -> 0%, box 5 -> 100%), so the bar moves
    as you practice. `mastered` counts fully-mastered (box 5) items."""
    q = "SELECT box, mastered FROM items"
    args = []
    if mode:
        q += " WHERE mode=?"
        args.append(mode)
    with _conn() as c:
        rows = c.execute(q, args).fetchall()
    total = len(rows)
    if not total:
        return {"total": 0, "mastered": 0, "pct": 0}
    mastered = sum(1 for r in rows if r["mastered"])
    pct = round(100 * sum((r["box"] - 1) / (MASTER_BOX - 1) for r in rows) / total)
    return {"total": total, "mastered": mastered, "pct": pct}


def needs_review(limit=10):
    """For the UI 'needs review' list: most-missed, due first."""
    with _conn() as c:
        rows = c.execute(
            """SELECT mode, scenario, level, prompt, miss_count, box
               FROM items WHERE miss_count>0 AND mastered=0
               ORDER BY miss_count DESC, box ASC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def stats():
    with _conn() as c:
        speak = c.execute("SELECT COUNT(*) FROM items WHERE mode='speak'").fetchone()[0]
        sign = c.execute("SELECT COUNT(*) FROM items WHERE mode='sign'").fetchone()[0]
    return {"speak": speak, "sign": sign}


def summary():
    """The Home/Progress snapshot the UI shows: streak, due-today, mastery per mode."""
    return {
        "streak": streak(),
        "dueToday": due_count(),
        "masterySpeak": mastery("speak")["pct"],
        "masterySign": mastery("sign")["pct"],
    }


def all_items():
    with _conn() as c:
        return [dict(r) for r in c.execute("SELECT mode, scenario, level, prompt, miss_count, box, mastered FROM items").fetchall()]


# ---- streak (one of the few gamification bits worth shipping) ----
def _today():
    return time.strftime("%Y-%m-%d", time.localtime())


def _touch_streak(now):
    today = time.strftime("%Y-%m-%d", time.localtime(now))
    with _conn() as c:
        last = c.execute("SELECT v FROM meta WHERE k='streak_day'").fetchone()
        cur = c.execute("SELECT v FROM meta WHERE k='streak_count'").fetchone()
        last_day = last["v"] if last else None
        count = int(cur["v"]) if cur else 0
        if last_day == today:
            return
        # consecutive day -> +1, otherwise reset to 1
        y = time.strftime("%Y-%m-%d", time.localtime(now - DAY))
        count = count + 1 if last_day == y else 1
        c.execute("INSERT OR REPLACE INTO meta(k, v) VALUES('streak_day', ?)", (today,))
        c.execute("INSERT OR REPLACE INTO meta(k, v) VALUES('streak_count', ?)", (str(count),))


def streak():
    with _conn() as c:
        cur = c.execute("SELECT v FROM meta WHERE k='streak_count'").fetchone()
        day = c.execute("SELECT v FROM meta WHERE k='streak_day'").fetchone()
    if not cur or not day:
        return 0
    # streak only counts if last practice was today or yesterday
    if day["v"] in (_today(), time.strftime("%Y-%m-%d", time.localtime(time.time() - DAY))):
        return int(cur["v"])
    return 0


if __name__ == "__main__":
    # smoke test
    init()
    record_result("speak", "greetings", "A1", "say hello", True)
    record_result("speak", "greetings", "A1", "ask how someone is", False)
    record_result("sign", "L1_vowels", "L1_vowels", "O", False)
    print("stats:", stats())
    print("mastery(speak):", mastery("speak"))
    print("due now:", [(i["prompt"], i["box"]) for i in due_items()])
    print("needs_review:", [(i["prompt"], i["miss_count"]) for i in needs_review()])
    print("streak:", streak())
