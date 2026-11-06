import base64
import os
import secrets
import string
import sys

from flask import Flask, abort, redirect, render_template, request, session, url_for

def require_env(name):
    value = os.environ.get(name)
    if not value:
        sys.exit(f"FATAL: environment variable {name} is not set")
    return value

def require_flag(n):
    value = os.environ.get(f"LAB_KEY_{n}") or os.environ.get(f"FLAG_{n}")
    if not value:
        sys.exit(f"FATAL: neither LAB_KEY_{n} nor FLAG_{n} is set")
    return value

LEVELS = [
    {"title": "Just Press It", "flag": require_flag(1)},
    {"title": "Flag Removed", "flag": require_flag(2)},
    {"title": "Parrot", "flag": require_flag(3)},
    {"title": "Twitchy", "flag": require_flag(4)},
    {"title": "Corner Shop", "flag": require_flag(5)},
]
FINISH = len(LEVELS) + 1

SHOP_BALANCE = 100
SHOP_ITEMS = [
    {"id": "water", "name": "Water", "price": 20},
    {"id": "juice", "name": "Juice", "price": 30},
    {"id": "cola", "name": "Cola", "price": 50},
    {"id": "beer", "name": "Beer", "price": 1000},
]
SHOP_TARGET = "beer"

def _rand_token(n=8):
    return "".join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(n))

def build_level4_notes():
    real = LEVELS[3]["flag"]
    values = [real] + [f"COLO_FLAG{{fake_{i:02d}}}" for i in range(1, 50)]
    secrets.SystemRandom().shuffle(values)
    return [{"secret": base64.b64encode(v.encode()).decode()} for v in values]

def level5_captcha():
    return {
        "question": "To continue, select every square that contains Alice's true feelings, "
                    "then type the 7th prime number expressed in base-3.",
        "answer": _rand_token(6),
        "flag_b64": base64.b64encode(LEVELS[4]["flag"].encode()).decode(),
    }
LOGIN_PASSWORD = require_env("LOGIN_PASSWORD")

app = Flask(__name__)
app.secret_key = require_env("SECRET_KEY")

LAB_RUN_ID = os.environ.get("LAB_RUN_ID")
if LAB_RUN_ID:
    print(f"Colo lab run: LAB_RUN_ID={LAB_RUN_ID}", file=sys.stderr, flush=True)

@app.get("/colo-health")
def colo_health():
    return "ok", 200

def is_unlocked(n):
    return n <= session.get("unlocked", 1)

def locked_page(n, error=None):
    return render_template("locked.html", n=n, error=error), 403

def furthest_level_url():
    return url_for("level", n=session.get("unlocked", 1))

@app.before_request
def require_login():
    if request.path.startswith("/level/") and not session.get("logged_in"):
        return redirect(url_for("login"))

@app.get("/")
def index():
    start_url = furthest_level_url() if session.get("logged_in") else url_for("welcome")
    return render_template("intro.html", start_url=start_url)

@app.get("/welcome")
def welcome():
    scenes = [{
        "gif": url_for("static", filename="welcome.gif"),
        "lines": [
            {"who": "Alice", "text": "My name is Alice and you only job is to entertain me while my human is busy"},
            {"who": "Alice", "text": "And do not even dare to touch her computer!"},
        ],
    }]
    return render_template("cutscene.html", scenes=scenes, next_url=url_for("login"),
                           portrait="ascii", title="Welcome")

@app.get("/login")
def login():
    if session.get("logged_in"):
        return redirect(furthest_level_url())
    return render_template("login.html", password=LOGIN_PASSWORD)

@app.post("/login")
def login_submit():
    name = request.form.get("name", "")
    if name != "Alice" or request.form.get("password", "") != LOGIN_PASSWORD:
        return render_template("login.html", password=LOGIN_PASSWORD, error=True, name=name), 401
    session["logged_in"] = True
    return redirect(furthest_level_url())

@app.get("/level/<int:n>")
def level(n):
    if not 1 <= n <= FINISH:
        abort(404)
    if not is_unlocked(n):
        return locked_page(n)
    if n == FINISH:
        return render_template("finish.html")
    kwargs = {}
    if n == 3:
        key = [secrets.randbelow(255) + 1 for _ in range(6)]
        flag = LEVELS[n - 1]["flag"]
        kwargs["secret_key"] = key
        kwargs["secret_cipher"] = [ord(c) ^ key[i % len(key)] for i, c in enumerate(flag)]
    if n == 4:
        kwargs["notes"] = build_level4_notes()
    if n == 5:
        kwargs["items"] = SHOP_ITEMS
        kwargs["balance"] = SHOP_BALANCE
    return render_template(f"levels/{n}.html", n=n, next_level=n + 1,
                           title=LEVELS[n - 1]["title"], **kwargs)

@app.post("/level/<int:n>/unlock")
def unlock(n):
    if not 2 <= n <= FINISH:
        abort(404)
    if request.form.get("flag", "").strip() != LEVELS[n - 2]["flag"]:
        return locked_page(n, error="Wrong flag, try again")
    session["unlocked"] = max(session.get("unlocked", 1), n)
    return redirect(url_for("level", n=n))

@app.get("/level/5/intro")
def level5_intro():
    if not is_unlocked(4):
        return locked_page(4)
    scenes = [
        {"gif": url_for("static", filename="level5.gif"), "lines": [
            {"who": "You", "text": "where am I.. where did you bring me!?!?!!"},
            {"who": "Alice", "text": "We already worked a lot today. I just thought we could have some food..."},
        ]},
        {"gif": url_for("static", filename="level5c.gif"), "auto_ms": 2200, "lines": [
            {"who": "Alice", "text": "..."},
        ]},
        {"gif": url_for("static", filename="level5b.gif"), "start_delay_ms": 2000, "lines": [
            {"who": "You", "text": "oh, um...I'd prefer some water..."},
            {"who": "Alice", "text": "I don't care. I want BEER."},
        ]},
    ]
    return render_template("cutscene.html", scenes=scenes, next_url=url_for("level", n=5),
                           portrait="tags", title="Interlude", fade_in=True)

@app.post("/level/5/buy")
def level5_buy():
    if not is_unlocked(5):
        return locked_page(5)
    item = request.form.get("item", "")
    if item not in {i["id"] for i in SHOP_ITEMS}:
        return {"ok": False, "msg": "Unknown item"}, 400
    try:
        price = float(request.form.get("price", ""))
    except ValueError:
        return {"ok": False, "msg": "Invalid price"}, 400
    if price > SHOP_BALANCE:
        return {"ok": False, "msg": f"Not enough balance: {price:g} > {SHOP_BALANCE} ₴"}
    if item == SHOP_TARGET:
        return {"ok": True, "msg": "\U0001f37a Beer unlocked! One more step...",
                "captcha": level5_captcha()}
    return {"ok": True, "msg": f"Bought {item}. Alice is still thirsty for beer."}

@app.get("/level/1/flag")
def level1_flag_hint():
    return "Just press the button 😉\n", 405

@app.post("/level/1/flag")
def level1_flag():
    return {"flag": LEVELS[0]["flag"]}

@app.get("/level/2/v1/")
def level2_old_version():
    if not is_unlocked(2):
        return locked_page(2)
    return render_template("levels/2_v1.html", title=LEVELS[1]["title"], flag=LEVELS[1]["flag"])

@app.get("/level/2/sw.js")
def level2_service_worker():
    if not is_unlocked(2):
        return locked_page(2)
    return app.send_static_file("sw.js")
