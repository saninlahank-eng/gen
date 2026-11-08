#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
 ████████╗ █████╗ ███╗   ██╗ ██████╗ ███████╗██████╗ ██╗███╗   ██╗███████╗
    ██╔══╝██╔══██╗████╗  ██║██╔════╝ ██╔════╝██╔══██╗██║████╗  ██║██╔════╝
    ██║   ███████║██╔██╗ ██║██║  ███╗█████╗  ██████╔╝██║██╔██╗ ██║█████╗
    ██║   ██╔══██║██║╚██╗██║██║   ██║██╔══╝  ██╔══██╗██║██║╚██╗██║██╔══╝
    ██║   ██║  ██║██║ ╚████║╚██████╔╝███████╗██║  ██║██║██║ ╚████║███████╗
    ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝
                      ██████╗ ███████╗███╗   ██╗
                     ██╔════╝ ██╔════╝████╗  ██║
                     ██║  ███╗█████╗  ██╔██╗ ██║
                     ██║   ██║██╔══╝  ██║╚██╗██║
                     ╚██████╔╝███████╗██║ ╚████║
                      ╚═════╝ ╚══════╝╚═╝  ╚═══╝
  Discord Terminal Tool Hub  v3.0
"""
from __future__ import annotations

import os, sys, re, time, json, random, string, base64
from datetime import datetime
from threading import Thread, Lock
from queue import Queue, Empty

try:
    import requests
except ImportError:
    print("[!] pip install requests"); sys.exit(1)

try:
    import colorama; colorama.init(autoreset=True)
except ImportError:
    pass

# ── tls_client (critical for Discord TLS bypass) ─────────────────────────────
TLS_AVAILABLE = False
try:
    from tls_client import Session as TLSSession
    TLS_AVAILABLE = True
except ImportError:
    pass

# ── colors ────────────────────────────────────────────────────────────────────
ORANGE='\033[38;5;208m'; YELLOW='\033[93m'; GREEN='\033[92m'; RED='\033[91m'
CYAN='\033[96m'; BOLD='\033[1m'; DIM='\033[2m'; RESET='\033[0m'

_print_lock = Lock()
def ok(m):
    with _print_lock: print(f"  {GREEN}[+]{RESET} {m}")
def err(m):
    with _print_lock: print(f"  {RED}[-]{RESET} {m}")
def info(m):
    with _print_lock: print(f"  {CYAN}[*]{RESET} {m}")
def warn(m):
    with _print_lock: print(f"  {YELLOW}[!]{RESET} {m}")
def inp(p):  return input(f"  {ORANGE}[>]{RESET} {p}")
def sep():
    with _print_lock: print(f"  {DIM}{'─'*54}{RESET}")

BANNER = f"""
{ORANGE}{BOLD}
  ████████╗ █████╗ ███╗   ██╗ ██████╗ ███████╗██████╗ ██╗███╗   ██╗███████╗
     ██╔══╝██╔══██╗████╗  ██║██╔════╝ ██╔════╝██╔══██╗██║████╗  ██║██╔════╝
     ██║   ███████║██╔██╗ ██║██║  ███╗█████╗  ██████╔╝██║██╔██╗ ██║█████╗
     ██║   ██╔══██║██║╚██╗██║██║   ██║██╔══╝  ██╔══██╗██║██║╚██╗██║██╔══╝
     ██║   ██║  ██║██║ ╚████║╚██████╔╝███████╗██║  ██║██║██║ ╚████║███████╗
     ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝
{YELLOW}
                       ██████╗ ███████╗███╗   ██╗
                      ██╔════╝ ██╔════╝████╗  ██║
                      ██║  ███╗█████╗  ██╔██╗ ██║
                      ██║   ██║██╔══╝  ██║╚██╗██║
                      ╚██████╔╝███████╗██║ ╚████║
                       ╚═════╝ ╚══════╝╚═╝  ╚═══╝
{RESET}{DIM}  ──────────────────────────────────────────────────────────
              Discord Terminal Tool Hub  •  v3.0
  ──────────────────────────────────────────────────────────{RESET}
"""

# ─────────────────────────────────────────────────────────────────────────────
#  ENV + PROXY
# ─────────────────────────────────────────────────────────────────────────────
def load_env(path=".env"):
    env = {}
    if not os.path.exists(path): return env
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line: continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env

class ProxyRotator:
    def __init__(self, path="proxies.txt"):
        self.proxies = []
        self._idx = 0
        if os.path.exists(path):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"): continue
                    if not line.startswith("http"): line = f"http://{line}"
                    self.proxies.append(line)
            if self.proxies: ok(f"Loaded {len(self.proxies)} proxies")

    def next(self) -> dict | None:
        if not self.proxies: return None
        p = self.proxies[self._idx % len(self.proxies)]
        self._idx += 1
        return {"http": p, "https": p}

    def __bool__(self): return bool(self.proxies)

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]
ADJ  = ["dark","swift","bright","silent","night","storm","cool","deep","bold","iron","ghost","cyber","neon","void"]
NOUN = ["wolf","hawk","fox","bear","lion","eagle","shark","raven","blade","viper","drift","pulse","crypt","zero"]

def rand_ua():  return random.choice(USER_AGENTS)
def rand_str(n, cs=string.ascii_lowercase+string.digits): return ''.join(random.choices(cs, k=n))
def rand_username(): return f"{random.choice(ADJ)}{random.choice(NOUN)}{random.randint(100,9999)}"
def rand_password(): return rand_str(10, string.ascii_letters+string.digits) + "Aa1@"
def rand_dob():  return f"{random.randint(1993,2001)}-{random.randint(1,12):02d}-{random.randint(1,28):02d}"
def human_delay(mn=0.5, mx=1.5): time.sleep(random.uniform(mn, mx))

# X-Super-Properties — base64 encoded browser context
def build_xsp(ua):
    props = {
        "os": "Windows", "browser": "Chrome", "device": "",
        "system_locale": "en-US", "browser_user_agent": ua,
        "browser_version": "120.0.0.0", "os_version": "10",
        "referrer": "", "referring_domain": "",
        "referrer_current": "", "referring_domain_current": "",
        "release_channel": "stable", "client_build_number": 269547,
        "client_event_source": None
    }
    return base64.b64encode(json.dumps(props, separators=(',',':')).encode()).decode()

def discord_headers(token=None, ua=None, fingerprint=None, content_len=None):
    if ua is None: ua = rand_ua()
    h = {
        "Content-Type":         "application/json",
        "User-Agent":           ua,
        "X-Super-Properties":   build_xsp(ua),
        "X-Discord-Locale":     "en-US",
        "X-Discord-Timezone":   "America/New_York",
        "Accept":               "*/*",
        "Accept-Language":      "en-US,en;q=0.9",
        "Accept-Encoding":      "gzip, deflate, br",
        "Origin":               "https://discord.com",
        "Referer":              "https://discord.com/",
        "Sec-Ch-Ua":            '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile":     "?0",
        "Sec-Ch-Ua-Platform":   '"Windows"',
        "Sec-Fetch-Dest":       "empty",
        "Sec-Fetch-Mode":       "cors",
        "Sec-Fetch-Site":       "same-origin",
    }
    if token:        h["Authorization"]  = token
    if fingerprint:  h["X-Fingerprint"]  = fingerprint
    if content_len:  h["Content-Length"] = str(content_len)
    return h

def clear(): os.system("cls" if os.name == "nt" else "clear")
def save_line(fn, line):
    with open(fn, "a", encoding="utf-8") as f: f.write(line + "\n")

def load_tokens(path="tangerine_tokens.txt"):
    if not os.path.exists(path):
        err(f"File not found: {path}"); return []
    tokens = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            line = re.sub(r'^\[.*?\]\s*', '', line)
            tok = line.split("|")[0].strip()
            if tok: tokens.append(tok)
    ok(f"Loaded {len(tokens)} token(s) from {CYAN}{path}{RESET}")
    return tokens

def extract_invite_code(invite):
    return invite.strip().rstrip("/").split("/")[-1]


# ─────────────────────────────────────────────────────────────────────────────
#  SESSION FACTORY  (tls_client → Chrome TLS fingerprint; fallback → requests)
# ─────────────────────────────────────────────────────────────────────────────
def make_session(proxy_dict=None):
    """
    Returns a session that mimics Chrome's TLS fingerprint.
    tls_client is strongly preferred — Discord detects Python requests at TLS level.
    Install: pip install tls-client
    """
    if TLS_AVAILABLE:
        sess = TLSSession(
            client_identifier="chrome_120",
            random_tls_extension_order=True
        )
        if proxy_dict:
            sess.proxies = proxy_dict
    else:
        sess = requests.Session()
        if proxy_dict:
            sess.proxies = proxy_dict
    return sess


# ─────────────────────────────────────────────────────────────────────────────
#  DISCORD WARMUP  — gets Cloudflare cookies + fingerprint in one shot
# ─────────────────────────────────────────────────────────────────────────────
def warmup(sess, ua) -> tuple[str | None, dict]:
    """
    GET /api/v9/experiments with the session.
    Returns (fingerprint, cf_cookies_dict).
    The CF cookies (+ fingerprint) must travel with the register POST.
    """
    headers = {
        "User-Agent":        ua,
        "Accept":            "*/*",
        "Accept-Language":   "en-US,en;q=0.9",
        "Accept-Encoding":   "gzip, deflate, br",
        "Connection":        "keep-alive",
        "Referer":           "https://discord.com/",
        "Sec-Fetch-Dest":    "empty",
        "Sec-Fetch-Mode":    "cors",
        "Sec-Fetch-Site":    "same-origin",
        "Sec-GPC":           "1",
        "X-Super-Properties": build_xsp(ua),
    }
    try:
        # First hit the register page so CF sets cookies
        sess.get("https://discord.com/register", headers={
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://discord.com/",
        }, timeout=15)
        human_delay(0.3, 0.8)

        # Then hit /experiments to get fingerprint + more CF cookies
        r = sess.get("https://discord.com/api/v9/experiments",
                     headers=headers, timeout=15)
        fp = r.json().get("fingerprint")
        cf = {
            "__dcfduid":  r.cookies.get("__dcfduid",  ""),
            "__sdcfduid": r.cookies.get("__sdcfduid", ""),
            "__cfruid":   r.cookies.get("__cfruid",   ""),
            "locale":     "en-US",
        }
        # Filter empty values
        cf = {k: v for k, v in cf.items() if v}
        return fp, cf
    except Exception as e:
        err(f"Warmup failed: {e}")
        return None, {}


# ─────────────────────────────────────────────────────────────────────────────
#  TEMP MAIL  (mail.tm)
# ─────────────────────────────────────────────────────────────────────────────
class TempMail:
    BASE = "https://api.mail.tm"

    def __init__(self):
        self.session = requests.Session()
        self.email = self.password = self.token = self.account_id = None

    def _domain(self):
        for _ in range(3):
            try:
                r = self.session.get(f"{self.BASE}/domains", timeout=15)
                m = r.json().get("hydra:member", [])
                if m: return m[0]["domain"]
            except Exception: pass
            time.sleep(2)
        return None

    def create(self):
        domain = self._domain()
        if not domain: return None, None
        self.email    = f"{rand_str(12)}@{domain}"
        self.password = rand_str(14) + "Aa1!"
        for attempt in range(3):
            try:
                r = self.session.post(f"{self.BASE}/accounts",
                    json={"address": self.email, "password": self.password},
                    timeout=15)
                if r.status_code == 201:
                    self.account_id = r.json().get("id")
                    ok(f"Temp email: {CYAN}{self.email}{RESET}")
                    self._auth()
                    return self.email, self.password
                elif r.status_code == 422:
                    # address taken, try another
                    self.email = f"{rand_str(14)}@{domain}"
                else:
                    err(f"mail.tm {r.status_code}: {r.text[:80]}")
                    break
            except Exception as e:
                err(f"mail.tm create attempt {attempt+1}: {e}")
            time.sleep(2)
        return None, None

    def _auth(self):
        try:
            r = self.session.post(f"{self.BASE}/token",
                json={"address": self.email, "password": self.password}, timeout=15)
            if r.status_code == 200:
                self.token = r.json().get("token")
        except Exception as e:
            err(f"mail.tm auth: {e}")

    def wait_for_email(self, keyword="verify", max_wait=120):
        if not self.token: return None
        info(f"Waiting for verification email (up to {max_wait}s)...")
        hdrs = {"Authorization": f"Bearer {self.token}"}
        deadline = time.time() + max_wait
        while time.time() < deadline:
            try:
                r = self.session.get(f"{self.BASE}/messages", headers=hdrs, timeout=15)
                if r.status_code == 200:
                    for msg in r.json().get("hydra:member", []):
                        subj = msg.get("subject", "").lower()
                        if keyword.lower() in subj or "discord" in subj:
                            full = self.session.get(
                                f"{self.BASE}/messages/{msg['id']}",
                                headers=hdrs, timeout=15)
                            if full.status_code == 200:
                                print(); ok("Verification email received")
                                return full.json()
            except Exception: pass
            time.sleep(5); sys.stdout.write("."); sys.stdout.flush()
        print(); warn("No verification email within timeout")
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  NONECAP  (https://nonecap.com | nc_live_xxx)
# ─────────────────────────────────────────────────────────────────────────────
class CaptchaSolver:
    BASE    = "https://api.nonecap.com/v1/solves"
    WAIT    = 30

    def __init__(self, api_key: str):
        self.api_key = api_key.strip()

    def solve_hcaptcha(self, sitekey: str, pageurl: str,
                       rqdata: str = None, max_wait: int = 65) -> str | None:
        headers = {"Authorization": f"Bearer {self.api_key}",
                   "Content-Type":  "application/json"}
        payload = {"type": "hcaptcha", "sitekey": sitekey, "url": pageurl}
        if rqdata: payload["rqdata"] = rqdata

        info(f"NoneCap: solving hCaptcha (rqdata={'yes' if rqdata else 'no'})...")
        try:
            r = requests.post(f"{self.BASE}?wait={self.WAIT}",
                headers=headers, json=payload, timeout=max_wait)
        except requests.exceptions.Timeout:
            err("NoneCap: timed out"); return None
        except requests.exceptions.RequestException as e:
            err(f"NoneCap: {e}"); return None

        if r.status_code in (200, 201):
            d = r.json()
            tok = d.get("token") or d.get("solution") or d.get("response")
            if tok: ok("NoneCap: solved"); return tok
            err(f"NoneCap: no token field — {d}"); return None
        elif r.status_code == 401: err("NoneCap: invalid API key"); return None
        elif r.status_code == 402: err("NoneCap: out of credits"); return None
        elif r.status_code in (408, 504):
            warn("NoneCap: server timeout — retry once...")
            try:
                r2 = requests.post(f"{self.BASE}?wait={self.WAIT}",
                    headers=headers, json=payload, timeout=max_wait)
                if r2.status_code in (200, 201):
                    d2 = r2.json()
                    t = d2.get("token") or d2.get("solution") or d2.get("response")
                    if t: ok("NoneCap: solved (retry)"); return t
            except Exception: pass
            err("NoneCap: retry failed"); return None
        elif r.status_code == 429:
            ra = int(r.headers.get("Retry-After", 8))
            warn(f"NoneCap: rate limited {ra}s"); time.sleep(ra)
            return self.solve_hcaptcha(sitekey, pageurl, rqdata, max_wait)
        else:
            err(f"NoneCap: HTTP {r.status_code} — {r.text[:100]}")
        return None


# ─────────────────────────────────────────────────────────────────────────────
#  DISCORD REGISTER  (single account, returns verified token or None)
# ─────────────────────────────────────────────────────────────────────────────
class AccountCreator:
    """
    One instance per account creation attempt.
    Uses a dedicated tls_client session per account to avoid session bleed.
    """
    DISCORD_BASE = "https://discord.com/api/v9"

    def __init__(self, captcha_key: str | None, proxy_dict: dict | None):
        self.captcha_key = captcha_key
        self.proxy_dict  = proxy_dict
        self.ua          = rand_ua()
        self.sess        = make_session(proxy_dict)

    def create(self) -> tuple[str | None, str, str, bool]:
        """
        Returns (token, email, username, is_verified).
        token is None on failure.
        """
        # ── 1. temp email ──────────────────────────────────────────────────────
        tm = TempMail()
        email, _ = tm.create()
        if not email:
            err("Could not create temp email"); return None, "", "", False
        username = rand_username()
        password = rand_password()

        # ── 2. session warmup — CF cookies + fingerprint ───────────────────────
        info(f"Warming up session ({('tls_client' if TLS_AVAILABLE else 'requests')})...")
        fingerprint, cf_cookies = warmup(self.sess, self.ua)
        if not fingerprint:
            err("Could not get fingerprint"); return None, email, username, False
        info(f"Fingerprint: {DIM}{fingerprint[:32]}...{RESET}")
        human_delay(0.5, 1.2)

        # ── 3. first register attempt (no captcha) ─────────────────────────────
        info("Register attempt 1 (no captcha)...")
        status, data, raw_token = self._post_register(
            email, username, password, fingerprint, cf_cookies)
        info(f"HTTP {status}")

        # ── 4. handle captcha challenge ────────────────────────────────────────
        if status == 400 and isinstance(data, dict) and "captcha_key" in data:
            sitekey  = data.get("captcha_sitekey",  "4c672d35-0701-42b2-88c3-78380b0db560")
            rqdata   = data.get("captcha_rqdata")
            rqtoken  = data.get("captcha_rqtoken")
            info(f"Captcha sitekey: {DIM}{sitekey}{RESET}")
            if rqdata:  info(f"rqdata: {len(rqdata)} chars (enterprise)")
            if rqtoken: info(f"rqtoken: {len(rqtoken)} chars")

            if not self.captcha_key:
                err("Captcha required — no NoneCap key provided"); return None, email, username, False

            solver = CaptchaSolver(self.captcha_key)
            cap_token = solver.solve_hcaptcha(
                sitekey=sitekey,
                pageurl="https://discord.com/register",
                rqdata=rqdata)
            if not cap_token:
                err("Captcha solve failed"); return None, email, username, False

            ok("Captcha solved — retrying register immediately...")
            status, data, raw_token = self._post_register(
                email, username, password, fingerprint, cf_cookies,
                captcha_key=cap_token, captcha_rqtoken=rqtoken)
            info(f"Register attempt 2: HTTP {status}")

        # ── 5. check result ────────────────────────────────────────────────────
        if status != 201 or not raw_token:
            if status == 400:
                if isinstance(data, dict) and "captcha_key" in data:
                    err(f"Captcha rejected — rqdata may have expired. Try again.")
                elif isinstance(data, dict) and "email" in str(data):
                    err(f"Email rejected: {data}")
                else:
                    err(f"Register 400: {data}")
            elif status == 429:
                ra = data.get("retry_after", 10) if isinstance(data, dict) else 10
                err(f"Rate limited — retry after {ra:.1f}s")
            else:
                err(f"Register failed ({status}): {str(data)[:120]}")
            return None, email, username, False

        ok(f"Account registered: {CYAN}{username}{RESET}")

        # ── 6. check if token is usable (unlocked) ─────────────────────────────
        if not self._is_unlocked(raw_token):
            warn("Token is locked by Discord — account flagged at creation")
            # Still try email verification, sometimes verification unlocks it
        
        # ── 7. email verification ──────────────────────────────────────────────
        msg = tm.wait_for_email("verify", max_wait=120)
        if not msg:
            warn("No verification email — saving as UNVERIFIED")
            return raw_token, email, username, False

        verified_token = self._do_email_verify(msg, raw_token)
        if verified_token:
            ok(f"Email verified ✓")
            # Re-check lock status after verification
            if not self._is_unlocked(verified_token):
                warn("Token locked even after verification — Discord flagged this session")
                warn("Use better proxies / tls_client to avoid flags")
            return verified_token, email, username, True
        else:
            warn("Email verification failed — saving as UNVERIFIED")
            return raw_token, email, username, False

    def _post_register(self, email, username, password, fingerprint,
                       cf_cookies, captcha_key=None, captcha_rqtoken=None):
        payload = {
            "consent":                  True,
            "fingerprint":              fingerprint,   # REQUIRED in body
            "username":                 username,
            "email":                    email,
            "password":                 password,
            "date_of_birth":            rand_dob(),
            "gift_code_sku_id":         None,
            "invite":                   None,
            "promotional_email_opt_in": False,
        }
        if captcha_key:    payload["captcha_key"]    = captcha_key
        if captcha_rqtoken: payload["captcha_rqtoken"] = captcha_rqtoken

        body_bytes = json.dumps(payload, separators=(',', ':')).encode()
        headers = discord_headers(
            ua=self.ua,
            fingerprint=fingerprint,
            content_len=len(body_bytes)
        )
        headers["Referer"] = "https://discord.com/register"

        try:
            r = self.sess.post(
                f"{self.DISCORD_BASE}/auth/register",
                headers=headers,
                cookies=cf_cookies if cf_cookies else None,
                json=payload,
                timeout=25)
            try:
                d = r.json()
            except Exception:
                d = {"raw": r.text[:200]}
            token = d.get("token") if isinstance(d, dict) else None
            return r.status_code, d, token
        except Exception as e:
            return 0, {"error": str(e)}, None

    def _is_unlocked(self, token) -> bool:
        """
        Check /users/@me/library — 200 = unlocked, anything else = locked.
        Locked tokens can't join servers or use most features.
        """
        try:
            headers = discord_headers(token=token, ua=self.ua)
            r = requests.get(
                f"{self.DISCORD_BASE}/users/@me/library",
                headers=headers, timeout=15)
            if r.status_code == 200:
                return True
            info(f"Lock check: HTTP {r.status_code} — token may be restricted")
            return False
        except Exception:
            return True  # assume unlocked on network error

    def _do_email_verify(self, msg: dict, fallback: str) -> str | None:
        body = msg.get("html", msg.get("text", ""))
        if isinstance(body, list): body = "".join(body)

        verify_token = None

        # Pattern 1: direct fragment  https://discord.com/verify#token=XXX
        m = re.search(r'https://discord\.com/verify#token=([A-Za-z0-9._\-]+)', body)
        if m: verify_token = m.group(1)

        # Pattern 2: href with fragment or query
        if not verify_token:
            m = re.search(
                r'href=["\']https://discord\.com/verify[?#]token=([A-Za-z0-9._\-]+)', body)
            if m: verify_token = m.group(1)

        # Pattern 3: click.discord.com tracked link — follow redirect
        if not verify_token:
            m = re.search(
                r'(https://click\.discord\.com/ls/click\?upn=[A-Za-z0-9%_\-&=+./]+)', body)
            if m:
                info("Following Discord email redirect...")
                try:
                    redir = requests.get(m.group(1), allow_redirects=True, timeout=15)
                    search_src = redir.url + " " + redir.text
                    m2 = re.search(r'token=([A-Za-z0-9._\-]{20,})', search_src)
                    if m2: verify_token = m2.group(1)
                except Exception as e:
                    warn(f"Redirect failed: {e}")

        # Pattern 4: any token= ≥ 30 chars
        if not verify_token:
            m = re.search(r'token=([A-Za-z0-9._\-]{30,})', body)
            if m: verify_token = m.group(1)

        if not verify_token:
            warn("Could not extract verify token from email"); return None

        info(f"Calling /auth/verify ({len(verify_token)} char token)...")
        try:
            headers = discord_headers(ua=self.ua)
            headers["Referer"] = "https://discord.com/verify"
            r = self.sess.post(
                f"{self.DISCORD_BASE}/auth/verify",
                json={"token": verify_token},
                headers=headers, timeout=20)
            if r.status_code == 200:
                new_token = r.json().get("token")
                return new_token if new_token else fallback
            else:
                warn(f"/auth/verify returned {r.status_code}: {r.text[:80]}")
                return None
        except Exception as e:
            err(f"Verify request failed: {e}"); return None


# ─────────────────────────────────────────────────────────────────────────────
#  TOOL 1 — TOKEN GENERATOR  (single + mass threaded)
# ─────────────────────────────────────────────────────────────────────────────
class TokenGenerator:
    OUT_FILE = "tangerine_tokens.txt"

    def __init__(self, captcha_key=None, proxies: ProxyRotator = None):
        self.captcha_key = captcha_key
        self.proxies     = proxies

    def run(self, count=1, threads=1):
        if not TLS_AVAILABLE:
            warn("tls_client NOT installed — success rate will be lower")
            warn("Fix: pip install tls-client   (Termux: pip install tls-client)")

        if threads > 1 and count > 1:
            self._run_threaded(count, threads)
        else:
            self._run_serial(count)

    def _run_serial(self, count):
        ok_count = 0
        for i in range(count):
            print(); info(f"Token {i+1}/{count}"); sep()
            token, email, username, verified = self._gen_one()
            if token:
                ok_count += 1
                ok(f"Token: {GREEN}{token[:42]}...{RESET}")
                ok(f"Verified: {'✓' if verified else '✗ (UNVERIFIED)'}")
            else:
                err(f"Token {i+1} failed")
            if i < count - 1:
                d = random.uniform(3, 6)
                info(f"Cooldown {d:.1f}s..."); time.sleep(d)
        sep()
        ok(f"Done — {ok_count}/{count} tokens | saved to {CYAN}{self.OUT_FILE}{RESET}")

    def _run_threaded(self, count, thread_count):
        queue   = Queue()
        results = {"ok": 0, "fail": 0}
        lock    = Lock()

        for _ in range(count): queue.put(1)

        def worker(n):
            while True:
                try: queue.get_nowait()
                except Empty: return
                token, email, username, verified = self._gen_one()
                with lock:
                    if token:
                        results["ok"] += 1
                        ok(f"[Thread-{n}] Token: {GREEN}{token[:38]}...{RESET} | verified={'✓' if verified else '✗'}")
                    else:
                        results["fail"] += 1
                        err(f"[Thread-{n}] Failed")
                time.sleep(random.uniform(1, 3))

        ts = [Thread(target=worker, args=(i+1,), daemon=True)
              for i in range(min(thread_count, count))]
        for t in ts: t.start()
        for t in ts: t.join()
        sep()
        ok(f"Done — {results['ok']}/{count} | saved to {CYAN}{self.OUT_FILE}{RESET}")

    def _gen_one(self) -> tuple[str | None, str, str, bool]:
        proxy_dict = self.proxies.next() if self.proxies else None
        creator    = AccountCreator(self.captcha_key, proxy_dict)
        token, email, username, verified = creator.create()
        if token:
            tag = "VERIFIED" if verified else "UNVERIFIED"
            ts  = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_line(self.OUT_FILE,
                f"[{tag}] {token} | {email} | {username} | {ts}")
        return token, email, username, verified


# ─────────────────────────────────────────────────────────────────────────────
#  DISCORD API  (for tools 2-4 — uses regular requests, tokens already exist)
# ─────────────────────────────────────────────────────────────────────────────
class DiscordAPI:
    BASE = "https://discord.com/api/v9"

    def __init__(self, token=None, proxies=None):
        self.token   = token
        self.ua      = rand_ua()
        self.session = requests.Session()
        if proxies: self.session.proxies = proxies

    def _h(self, auth=True):
        return discord_headers(token=self.token if auth else None, ua=self.ua)

    def get_me(self):
        try:
            r = self.session.get(f"{self.BASE}/users/@me", headers=self._h(), timeout=15)
            return r.status_code, r.json()
        except Exception as e: return 0, {"error": str(e)}

    def get_invite(self, code):
        try:
            r = self.session.get(f"{self.BASE}/invites/{code}?with_counts=true",
                headers={"User-Agent": self.ua}, timeout=15)
            return r.status_code, r.json()
        except Exception as e: return 0, {"error": str(e)}

    def join_server(self, code):
        try:
            r = self.session.post(f"{self.BASE}/invites/{code}",
                json={}, headers=self._h(), timeout=20)
            return r.status_code, r.json()
        except Exception as e: return 0, {"error": str(e)}

    def get_guild_channels(self, guild_id):
        try:
            r = self.session.get(f"{self.BASE}/guilds/{guild_id}/channels",
                headers=self._h(), timeout=15)
            return r.status_code, r.json()
        except Exception as e: return 0, {"error": str(e)}

    def send_typing(self, channel_id):
        try:
            self.session.post(f"{self.BASE}/channels/{channel_id}/typing",
                headers=self._h(), timeout=10)
        except Exception: pass

    def get_billing_trials(self):
        try:
            r = self.session.get(f"{self.BASE}/users/@me/billing/trials",
                headers=self._h(), timeout=15)
            return r.status_code, r.json()
        except Exception as e: return 0, {"error": str(e)}

    def get_subscriptions(self):
        try:
            r = self.session.get(f"{self.BASE}/users/@me/billing/subscriptions",
                headers=self._h(), timeout=15)
            return r.status_code, r.json()
        except Exception as e: return 0, {"error": str(e)}

    def claim_trial(self, trial_id, plan_id="premium_month_tier_0"):
        try:
            r = self.session.post(f"{self.BASE}/users/@me/billing/subscriptions",
                json={"trial_id": trial_id, "payment_gateway_plan_id": plan_id},
                headers=self._h(), timeout=20)
            return r.status_code, r.json()
        except Exception as e: return 0, {"error": str(e)}

    def check_gift_code(self, code):
        try:
            r = self.session.get(
                f"{self.BASE}/entitlements/gift-codes/{code}"
                "?with_application=false&with_subscription_plan=true",
                headers={"User-Agent": self.ua}, timeout=15)
            return r.status_code, r.json()
        except Exception as e: return 0, {"error": str(e)}

    def redeem_gift_code(self, code):
        try:
            r = self.session.post(
                f"{self.BASE}/entitlements/gift-codes/{code}/redeem",
                json={"channel_id": None, "payment_source_id": None},
                headers=self._h(), timeout=20)
            return r.status_code, r.json()
        except Exception as e: return 0, {"error": str(e)}

    def get_subscription_slots(self):
        try:
            r = self.session.get(
                f"{self.BASE}/users/@me/guilds/premium/subscription-slots",
                headers=self._h(), timeout=15)
            return r.status_code, r.json()
        except Exception as e: return 0, {"error": str(e)}

    def boost_guild(self, guild_id, slot_ids):
        try:
            r = self.session.put(
                f"{self.BASE}/guilds/{guild_id}/premium/subscriptions",
                json={"user_premium_guild_subscription_slot_ids": slot_ids},
                headers=self._h(), timeout=20)
            return r.status_code, r.json()
        except Exception as e: return 0, {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
#  TOOL 2 — SERVER JOINER
# ─────────────────────────────────────────────────────────────────────────────
class ServerJoiner:
    def __init__(self, proxies: ProxyRotator = None):
        self.proxies = proxies

    def run(self, tokens, invite, delay_min=3.0, delay_max=8.0):
        code = extract_invite_code(invite)
        print(); info(f"Invite: {CYAN}{code}{RESET}")
        info(f"Tokens: {len(tokens)} | Delay: {delay_min:.0f}–{delay_max:.0f}s")
        sep()

        probe = DiscordAPI()
        istatus, idata = probe.get_invite(code)
        if istatus == 404: err("Invite not found — aborting"); return
        if istatus == 200:
            gname   = idata.get("guild", {}).get("name", "?")
            members = idata.get("approximate_member_count", "?")
            ok(f"Server: {CYAN}{gname}{RESET} ({members} members)")
        sep()

        joined = failed = 0
        for i, token in enumerate(tokens):
            token = token.strip()
            if not token: continue
            proxy = self.proxies.next() if self.proxies else None
            api   = DiscordAPI(token=token, proxies=proxy)
            api.ua = rand_ua()
            tag   = f"[{i+1}/{len(tokens)}]"
            human_delay(0.5, 1.5)
            status, data = api.join_server(code)

            if status == 200:
                gname = data.get("guild", {}).get("name", "?")
                ok(f"{tag} Joined {CYAN}{gname}{RESET}"); joined += 1
                self._post_join(api, data)
            elif status == 429:
                ra = float(data.get("retry_after", 8))
                warn(f"{tag} Rate limited {ra:.1f}s"); time.sleep(ra + 2)
                s2, d2 = api.join_server(code)
                if s2 == 200: ok(f"{tag} Joined (retry)"); joined += 1
                else: err(f"{tag} Retry failed ({s2})"); failed += 1
            elif status == 401:
                err(f"{tag} Invalid/expired token"); failed += 1
            elif status == 403:
                code_val = data.get("code", 0)
                msg      = data.get("message", "")
                if code_val == 40002:
                    err(f"{tag} NOT email-verified — verify this account first")
                elif code_val == 40007:
                    err(f"{tag} Banned from this server")
                elif code_val == 50013:
                    err(f"{tag} Missing permissions")
                else:
                    err(f"{tag} Forbidden ({code_val}): {msg}")
                failed += 1
            elif status == 404:
                err(f"{tag} Invite expired — stopping")
                failed += len(tokens) - i; break
            else:
                err(f"{tag} {status}: {str(data)[:80]}"); failed += 1

            if i < len(tokens) - 1:
                d = random.uniform(delay_min, delay_max)
                info(f"Gap: {d:.1f}s..."); time.sleep(d)

        sep()
        print(f"  {GREEN}Joined: {joined}{RESET}   {RED}Failed: {failed}{RESET}")
        if joined:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M")
            save_line("tangerine_joins.txt",
                f"[{ts}] invite:{code} | joined:{joined} | failed:{failed}")

    def _post_join(self, api, join_data):
        try:
            gid = join_data.get("guild", {}).get("id")
            if not gid: return
            time.sleep(random.uniform(1.0, 2.5))
            s, chs = api.get_guild_channels(gid)
            if s == 200 and isinstance(chs, list):
                tchs = [c for c in chs if c.get("type") == 0]
                if tchs:
                    time.sleep(random.uniform(0.4, 1.0))
                    api.send_typing(random.choice(tchs)["id"])
        except Exception: pass


# ─────────────────────────────────────────────────────────────────────────────
#  TOOL 3 — NITRO TRIAL TRIGGER
# ─────────────────────────────────────────────────────────────────────────────
class NitroTrialTrigger:
    def __init__(self, proxies: ProxyRotator = None):
        self.proxies = proxies

    def run_auto(self, tokens):
        print(); info("Mode: Auto-claim trials"); sep()
        claimed = 0
        for i, token in enumerate(tokens):
            token = token.strip()
            if not token: continue
            proxy = self.proxies.next() if self.proxies else None
            api   = DiscordAPI(token=token, proxies=proxy)
            us, ud = api.get_me()
            if us != 200: err(f"[{i+1}] Invalid token ({us})"); continue
            username  = ud.get("username", "?")
            nitro     = ud.get("premium_type", 0)
            verified  = ud.get("verified", False)
            info(f"[{i+1}] {CYAN}{username}{RESET} | Nitro: {nitro} | Verified: {'✓' if verified else '✗'}")
            if not verified: warn("  Not email-verified — trials rarely available")

            ts, td = api.get_billing_trials()
            if ts == 200 and isinstance(td, list) and td:
                ok(f"  {len(td)} trial(s) available!")
                for trial in td:
                    tid  = trial.get("id") or trial.get("trial_id")
                    plan = trial.get("payment_gateway_plan_id", "premium_month_tier_0")
                    if not tid: continue
                    cs, cd = api.claim_trial(tid, plan)
                    if cs in (200, 201):
                        ok(f"  Claimed: {GREEN}{tid}{RESET}"); claimed += 1
                        save_line("tangerine_nitro.txt",
                            f"[CLAIMED] {token} | {username} | {tid} | "
                            f"{datetime.now().strftime('%Y-%m-%d %H:%M')}")
                    else:
                        warn(f"  Failed ({cs}): {cd.get('message', str(cd)[:60])}")
            elif ts == 200:
                warn(f"  No trials for {username}")
                ss, sd = api.get_subscriptions()
                if ss == 200 and isinstance(sd, list) and sd:
                    info(f"  Already has sub: {sd[0].get('type','?')}")
                else:
                    info("  No subs — account eligible but no trial offered currently")
                info("  Best candidates: verified accounts, never had Nitro, >24h old")
            elif ts == 401: err("  Token unauthorized")
            else: warn(f"  Trials HTTP {ts}: {str(td)[:80]}")
            time.sleep(random.uniform(1.5, 3.0))

        sep(); ok(f"Trials claimed: {GREEN}{claimed}{RESET}")

    def run_redeem(self, tokens, code):
        print(); info(f"Mode: Redeem — {CYAN}{code}{RESET}"); sep()
        api0 = DiscordAPI()
        vs, vd = api0.check_gift_code(code)
        if vs == 404: err("Code invalid/consumed"); return
        if vs == 200:
            plan     = vd.get("subscription_plan", {}).get("name", "?")
            uses     = vd.get("uses", 0); max_uses = vd.get("max_uses", 1)
            ok(f"Valid: {CYAN}{plan}{RESET} | {uses}/{max_uses} uses")
            if vd.get("redeemed"): warn("Fully redeemed already"); return

        success = 0
        for i, token in enumerate(tokens):
            token = token.strip()
            if not token: continue
            proxy = self.proxies.next() if self.proxies else None
            api   = DiscordAPI(token=token, proxies=proxy)
            us, ud = api.get_me()
            if us != 200: err(f"[{i+1}] Invalid token"); continue
            username = ud.get("username", "?")
            rs, rd   = api.redeem_gift_code(code)
            if rs == 200:
                ok(f"[{i+1}] {CYAN}{username}{RESET} — Redeemed!"); success += 1
                save_line("tangerine_nitro.txt",
                    f"[REDEEMED] {token} | {username} | gift:{code} | "
                    f"{datetime.now().strftime('%Y-%m-%d %H:%M')}")
            elif rs == 400:
                msg = rd.get("message","")
                if "already" in msg.lower() or "purchased" in msg.lower():
                    warn(f"[{i+1}] {username} — Already has Nitro")
                else: err(f"[{i+1}] {username} — {msg}")
            elif rs == 404: err(f"[{i+1}] Code consumed — stopping"); break
            elif rs == 429:
                ra = float(rd.get("retry_after", 5))
                warn(f"[{i+1}] Rate limited {ra:.1f}s"); time.sleep(ra + 1)
            else: err(f"[{i+1}] {rs}: {str(rd)[:80]}")
            time.sleep(random.uniform(1.0, 2.5))
        sep(); ok(f"Redeemed: {success}/{len(tokens)}")


# ─────────────────────────────────────────────────────────────────────────────
#  TOOL 4 — SERVER BOOSTER
# ─────────────────────────────────────────────────────────────────────────────
class ServerBooster:
    def __init__(self, proxies: ProxyRotator = None):
        self.proxies = proxies

    def run(self, tokens, guild_id):
        print(); info(f"Target guild: {CYAN}{guild_id}{RESET}"); sep()
        total = 0
        for i, token in enumerate(tokens):
            token = token.strip()
            if not token: continue
            proxy = self.proxies.next() if self.proxies else None
            api   = DiscordAPI(token=token, proxies=proxy)
            us, ud = api.get_me()
            if us != 200: err(f"[{i+1}] Invalid token"); continue
            username  = ud.get("username", "?")
            nitro     = ud.get("premium_type", 0)
            if nitro == 0: warn(f"[{i+1}] {username} — no Nitro"); continue
            info(f"[{i+1}] {CYAN}{username}{RESET} — Nitro type {nitro}")
            ss, sd = api.get_subscription_slots()
            if ss != 200 or not isinstance(sd, list): err(f"  Slots: {ss}"); continue
            if not sd: warn("  No boost slots"); continue
            avail = [s for s in sd
                     if s.get("premium_guild_subscription") is None
                     and not s.get("canceled")]
            if not avail:
                in_use = next((s.get("premium_guild_subscription",{}).get("guild_id")
                               for s in sd if s.get("premium_guild_subscription")), None)
                if in_use == guild_id: warn("  Already boosting this server")
                else: warn(f"  All slots in use (guild {in_use})")
                continue
            slot_ids = [s["id"] for s in avail]
            info(f"  {len(slot_ids)} slot(s) — boosting...")
            bs, bd = api.boost_guild(guild_id, slot_ids)
            if bs in (200, 201):
                n = len(bd) if isinstance(bd, list) else len(slot_ids)
                ok(f"  Boosted {GREEN}{n} slot(s){RESET} ✓"); total += n
                ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                save_line("tangerine_boosts.txt",
                    f"{token} | {username} | guild:{guild_id} | boosts:{n} | {ts}")
            elif bs == 429:
                ra = float(bd.get("retry_after", 5))
                warn(f"  Rate limited {ra:.0f}s"); time.sleep(ra + 2)
            elif bs == 403: warn(f"  Forbidden: {bd.get('message','')}")
            else: err(f"  Boost failed ({bs}): {str(bd)[:80]}")
            time.sleep(random.uniform(1.5, 3.0))
        sep(); print(f"  {GREEN}Total boosts: {total}{RESET}")


# ─────────────────────────────────────────────────────────────────────────────
#  MENUS + MAIN
# ─────────────────────────────────────────────────────────────────────────────
def _tokens(default="tangerine_tokens.txt"):
    path = inp(f"Token file [{default}]: ").strip() or default
    return load_tokens(path)

def menu_token_gen(cap_key, proxies):
    clear(); print(BANNER)
    print(f"  {ORANGE}{BOLD}[1] Email-Verified Token Generator{RESET}\n")
    print(f"  {DIM}Session: {'tls_client (Chrome TLS) ✓' if TLS_AVAILABLE else 'requests (basic) — install tls-client!'}{RESET}")
    if cap_key: ok(f"NoneCap key: .env ✓")
    if proxies: ok(f"Proxies: {len(proxies.proxies)} loaded")
    print(); sep()
    count_s   = inp("How many tokens [1]: ").strip()
    count     = int(count_s) if count_s.isdigit() and int(count_s) > 0 else 1
    threads_s = inp("Threads [1]: ").strip()
    threads   = int(threads_s) if threads_s.isdigit() and int(threads_s) > 0 else 1
    if not cap_key:
        cap_key = inp("NoneCap API key (nc_live_...): ").strip() or None
        if not cap_key: warn("No key — will fail if Discord demands captcha")
    TokenGenerator(captcha_key=cap_key, proxies=proxies).run(count, threads)

def menu_server_joiner(proxies):
    clear(); print(BANNER)
    print(f"  {ORANGE}{BOLD}[2] Server Joiner with Humanizer{RESET}\n"); sep()
    tokens = _tokens()
    if not tokens: return
    invite = inp("Invite (link or code): ").strip()
    if not invite: return
    dmin = float(inp("Min delay [3]: ").strip() or 3)
    dmax = float(inp("Max delay [8]: ").strip() or 8)
    ServerJoiner(proxies=proxies).run(tokens, invite, dmin, dmax)

def menu_nitro(proxies):
    clear(); print(BANNER)
    print(f"  {ORANGE}{BOLD}[3] Nitro Trial Trigger{RESET}\n")
    print(f"  {DIM}[a] Auto-claim trials via /billing/trials{RESET}")
    print(f"  {DIM}[b] Redeem a gift / promo code{RESET}\n"); sep()
    mode   = inp("Mode [a/b]: ").strip().lower()
    tokens = _tokens()
    if not tokens: return
    trig   = NitroTrialTrigger(proxies=proxies)
    if mode == "b":
        code = inp("Code: ").strip()
        if not code: return
        trig.run_redeem(tokens, code)
    else:
        trig.run_auto(tokens)

def menu_booster(proxies):
    clear(); print(BANNER)
    print(f"  {ORANGE}{BOLD}[4] Server Booster{RESET}\n"); sep()
    tokens = _tokens()
    if not tokens: return
    gid = inp("Guild/Server ID: ").strip()
    if not gid or not gid.isdigit(): err("Invalid guild ID"); return
    ServerBooster(proxies=proxies).run(tokens, gid)

def main():
    env     = load_env()
    cap_key = env.get("NONECAP_API_KEY", "").strip() or None
    if cap_key: ok(f".env: NONECAP_API_KEY loaded ({cap_key[:12]}...)")

    proxies = ProxyRotator("proxies.txt")
    if not proxies: info("No proxies.txt — running without proxies")

    while True:
        clear(); print(BANNER)
        tls_status = f"{GREEN}tls_client ✓{RESET}" if TLS_AVAILABLE else f"{RED}tls_client ✗ (install it!){RESET}"
        print(f"  {DIM}Session: {tls_status}  |  NoneCap: {'✓' if cap_key else '✗'}  |  Proxies: {len(proxies.proxies)}{RESET}\n")
        print(f"  {ORANGE}[1]{RESET}  Email-Verified Token Generator")
        print(f"  {ORANGE}[2]{RESET}  Server Joiner with Humanizer")
        print(f"  {ORANGE}[3]{RESET}  Nitro Trial Trigger")
        print(f"  {ORANGE}[4]{RESET}  Server Booster")
        print(f"  {DIM}[0]{RESET}  Exit\n")
        choice = inp("Select: ").strip()

        if   choice == "1": menu_token_gen(cap_key, proxies)
        elif choice == "2": menu_server_joiner(proxies)
        elif choice == "3": menu_nitro(proxies)
        elif choice == "4": menu_booster(proxies)
        elif choice == "0": print(f"\n  {ORANGE}Tangerine Gen closed.{RESET}\n"); sys.exit(0)
        else: err("Invalid option")
        print(); inp("Press Enter to return...")

if __name__ == "__main__":
    main()
