#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tangerine Gen — Discord Bot  v1.0
Uses py-cord (pip install py-cord)
Host on Railway.app / Render.com / any VPS where tls-client works.

Required env vars (Railway / .env):
  DISCORD_BOT_TOKEN   — bot token from discord.com/developers
  NONECAP_API_KEY     — nc_live_... from nonecap.com/dashboard
  OWNER_ID            — your Discord user ID (right-click yourself → Copy User ID)
  GUILD_ID            — your server ID (optional, makes commands register instantly)
"""
from __future__ import annotations

import os, sys, re, io, asyncio, logging, time
from datetime import datetime
from pathlib import Path
from threading import Thread

try:
    import discord
    from discord.ext import commands
    from discord import option
except ImportError:
    print("[!] pip install py-cord"); sys.exit(1)

# ── Import our engine ─────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))
from tangerine_gen import (
    TokenGenerator, ServerJoiner, NitroTrialTrigger, ServerBooster,
    ProxyRotator, load_env, TLS_AVAILABLE
)

logging.basicConfig(format="%(asctime)s [%(levelname)s] %(message)s",
                    level=logging.INFO)
log = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────────────────────
env           = load_env()
BOT_TOKEN     = os.getenv("DISCORD_BOT_TOKEN") or env.get("DISCORD_BOT_TOKEN", "")
NONECAP_KEY   = os.getenv("NONECAP_API_KEY")   or env.get("NONECAP_API_KEY",   "")
OWNER_ID_STR  = os.getenv("OWNER_ID")          or env.get("OWNER_ID",          "0")
GUILD_ID_STR  = os.getenv("GUILD_ID")          or env.get("GUILD_ID",          "0")

if not BOT_TOKEN:
    print("[!] Set DISCORD_BOT_TOKEN in env or .env"); sys.exit(1)

OWNER_ID = int(OWNER_ID_STR) if OWNER_ID_STR.isdigit() else 0
GUILD_ID = int(GUILD_ID_STR) if GUILD_ID_STR.isdigit() else None

DATA_DIR     = Path(os.getenv("DATA_DIR", "."))
TOKENS_FILE  = DATA_DIR / "tangerine_tokens.txt"
PROXIES_FILE = DATA_DIR / "proxies.txt"

# ─────────────────────────────────────────────────────────────────────────────
#  BOT SETUP
# ─────────────────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Bot(intents=intents)

debug_guilds = [GUILD_ID] if GUILD_ID else None   # instant slash registration

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def is_owner(ctx: discord.ApplicationContext) -> bool:
    return OWNER_ID == 0 or ctx.author.id == OWNER_ID

def load_proxies() -> ProxyRotator:
    return ProxyRotator(str(PROXIES_FILE))

def read_tokens() -> list[str]:
    if not TOKENS_FILE.exists(): return []
    tokens = []
    with open(TOKENS_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): continue
            line = re.sub(r'^\[.*?\]\s*', '', line)
            tok  = line.split("|")[0].strip()
            if tok: tokens.append(tok)
    return tokens

def count_verified() -> tuple[int, int]:
    verified = unverified = 0
    if not TOKENS_FILE.exists(): return 0, 0
    with open(TOKENS_FILE, encoding="utf-8") as f:
        for line in f:
            if "[VERIFIED]"   in line: verified   += 1
            if "[UNVERIFIED]" in line: unverified += 1
    return verified, unverified

def save_text_as_tokens(text: str) -> int:
    added = 0
    with open(TOKENS_FILE, "a", encoding="utf-8") as f:
        for line in text.splitlines():
            line = line.strip()
            if line: f.write(line + "\n"); added += 1
    return added

class OutputCapture:
    """Capture print() output from sync tool calls."""
    def __init__(self):
        self.lines: list[str] = []

    def __enter__(self):
        import builtins
        self._orig = builtins.print
        cap = self
        def patched(*args, **kw):
            sep  = kw.get("sep", " ")
            text = sep.join(str(a) for a in args)
            clean = re.sub(r'\x1b\[[0-9;]*[A-Za-z]', '', text).strip()
            if clean: cap.lines.append(clean)
            self._orig(*args, **kw)
        builtins.print = patched
        return self

    def __exit__(self, *_):
        import builtins
        builtins.print = self._orig

    def get(self, limit=3800) -> str:
        return "\n".join(self.lines)[-limit:] or "(no output)"

async def run_blocking(func, *args):
    return await asyncio.get_event_loop().run_in_executor(None, func, *args)

def chunk_message(text: str, size=1900) -> list[str]:
    """Split long text into Discord-safe chunks."""
    lines  = text.splitlines()
    chunks = []
    cur    = []
    cur_len = 0
    for line in lines:
        if cur_len + len(line) + 1 > size:
            chunks.append("\n".join(cur))
            cur = []; cur_len = 0
        cur.append(line); cur_len += len(line) + 1
    if cur: chunks.append("\n".join(cur))
    return chunks or ["(no output)"]

def status_embed() -> discord.Embed:
    tls  = "✅ chrome_120" if TLS_AVAILABLE else "❌ Not installed — `pip install tls-client`"
    nc   = f"✅ `{NONECAP_KEY[:14]}...`" if NONECAP_KEY else "❌ Not set"
    px   = len(load_proxies().proxies)
    toks = read_tokens()
    v, u = count_verified()
    e = discord.Embed(title="🍊 Tangerine Gen — Status", color=0xFF8C00)
    e.add_field(name="tls-client",    value=tls,              inline=False)
    e.add_field(name="NoneCap",       value=nc,               inline=False)
    e.add_field(name="Proxies",       value=f"`{px}` loaded", inline=True)
    e.add_field(name="Tokens",        value=f"`{len(toks)}` total  ·  `{v}` verified  ·  `{u}` unverified", inline=False)
    e.set_footer(text=f"Platform: {sys.platform}  |  Python {sys.version.split()[0]}")
    return e


# ─────────────────────────────────────────────────────────────────────────────
#  /status
# ─────────────────────────────────────────────────────────────────────────────
@bot.slash_command(name="status", description="Show bot config and token counts",
                   guild_ids=debug_guilds)
async def cmd_status(ctx: discord.ApplicationContext):
    if not is_owner(ctx): await ctx.respond("🚫 Unauthorized.", ephemeral=True); return
    await ctx.respond(embed=status_embed())


# ─────────────────────────────────────────────────────────────────────────────
#  /gen
# ─────────────────────────────────────────────────────────────────────────────
@bot.slash_command(name="gen",
                   description="Generate email-verified Discord tokens",
                   guild_ids=debug_guilds)
@option("count",   description="Number of tokens to generate", type=int, default=1,  min_value=1, max_value=50)
@option("threads", description="Concurrent threads",           type=int, default=1,  min_value=1, max_value=5)
async def cmd_gen(ctx: discord.ApplicationContext, count: int, threads: int):
    if not is_owner(ctx): await ctx.respond("🚫 Unauthorized.", ephemeral=True); return
    if not NONECAP_KEY:
        await ctx.respond("❌ **No NoneCap key.** Set `NONECAP_API_KEY` in Railway env vars.",
                          ephemeral=True); return

    await ctx.defer()

    e = discord.Embed(title="🔑 Token Generator", color=0xFF8C00)
    e.description = (
        f"Generating `{count}` token(s) with `{threads}` thread(s)...\n"
        f"tls-client: {'✅' if TLS_AVAILABLE else '⚠️ missing (lower success rate)'}\n"
        f"NoneCap: ✅\n\n"
        f"*This takes 2–5 minutes per token. Hang tight.*"
    )
    msg = await ctx.respond(embed=e)

    gen = TokenGenerator(captcha_key=NONECAP_KEY, proxies=load_proxies())
    with OutputCapture() as cap:
        await run_blocking(gen.run, count, threads)
    output = cap.get()

    tokens     = read_tokens()
    v, u       = count_verified()
    new_ok     = output.count("✓")

    result = discord.Embed(title="✅ Generation Complete", color=0x57F287)
    result.add_field(name="Generated",  value=f"`{new_ok}` verified this run", inline=True)
    result.add_field(name="Total File", value=f"`{len(tokens)}`",              inline=True)
    result.add_field(name="Breakdown",  value=f"Verified: `{v}` · Unverified: `{u}`", inline=False)

    for i, chunk in enumerate(chunk_message(output)):
        result.add_field(name=f"Log {i+1}", value=f"```\n{chunk}\n```", inline=False)

    await msg.edit(embed=result)

    # Attach token file
    if TOKENS_FILE.exists() and TOKENS_FILE.stat().st_size > 0:
        await ctx.followup.send(
            content="🔑 Token file:",
            file=discord.File(str(TOKENS_FILE), filename="tangerine_tokens.txt"))


# ─────────────────────────────────────────────────────────────────────────────
#  /join
# ─────────────────────────────────────────────────────────────────────────────
@bot.slash_command(name="join",
                   description="Join a Discord server with all saved tokens",
                   guild_ids=debug_guilds)
@option("invite",    description="Invite link or code  e.g. discord.gg/xxxx", type=str)
@option("delay_min", description="Min delay between joins (seconds)",          type=float, default=3.0)
@option("delay_max", description="Max delay between joins (seconds)",          type=float, default=8.0)
async def cmd_join(ctx: discord.ApplicationContext,
                   invite: str, delay_min: float, delay_max: float):
    if not is_owner(ctx): await ctx.respond("🚫 Unauthorized.", ephemeral=True); return
    tokens = read_tokens()
    if not tokens:
        await ctx.respond("❌ No tokens saved. Run `/gen` first.", ephemeral=True); return

    await ctx.defer()

    e = discord.Embed(title="🚀 Server Joiner", color=0xFF8C00)
    e.description = (
        f"Joining with `{len(tokens)}` token(s)\n"
        f"Invite: `{invite}`\n"
        f"Delay: `{delay_min:.0f}–{delay_max:.0f}s` (humanizer)"
    )
    msg = await ctx.respond(embed=e)

    joiner = ServerJoiner(proxies=load_proxies())
    with OutputCapture() as cap:
        await run_blocking(joiner.run, tokens, invite, delay_min, delay_max)
    output = cap.get()

    joined  = output.count("Joined")
    failed  = len(re.findall(r'\[-\]', output))
    unverif = output.count("NOT email-verified")

    result = discord.Embed(title="✅ Join Complete", color=0x57F287)
    result.add_field(name="Joined",             value=f"`{joined}`",   inline=True)
    result.add_field(name="Failed",             value=f"`{failed}`",   inline=True)
    result.add_field(name="Unverified tokens",  value=f"`{unverif}`",  inline=True)
    for i, chunk in enumerate(chunk_message(output)):
        result.add_field(name=f"Log {i+1}", value=f"```\n{chunk}\n```", inline=False)
    await msg.edit(embed=result)


# ─────────────────────────────────────────────────────────────────────────────
#  /nitro
# ─────────────────────────────────────────────────────────────────────────────
@bot.slash_command(name="nitro",
                   description="Trigger Nitro trials or redeem a gift code",
                   guild_ids=debug_guilds)
@option("mode", description="auto = check trials | redeem = use a gift code",
        choices=["auto", "redeem"], default="auto")
@option("code", description="Gift/promo code (only needed for redeem mode)",
        type=str, default="")
async def cmd_nitro(ctx: discord.ApplicationContext, mode: str, code: str):
    if not is_owner(ctx): await ctx.respond("🚫 Unauthorized.", ephemeral=True); return
    tokens = read_tokens()
    if not tokens:
        await ctx.respond("❌ No tokens. Run `/gen` first.", ephemeral=True); return
    if mode == "redeem" and not code:
        await ctx.respond("❌ Provide a `code` for redeem mode.", ephemeral=True); return

    await ctx.defer()

    e = discord.Embed(title="💎 Nitro Trial Trigger", color=0xFF8C00)
    e.description = (
        f"Mode: `{mode}`" +
        (f"\nCode: `{code}`" if mode == "redeem" else "") +
        f"\nTokens: `{len(tokens)}`"
    )
    msg = await ctx.respond(embed=e)

    trig = NitroTrialTrigger(proxies=load_proxies())
    with OutputCapture() as cap:
        if mode == "redeem":
            await run_blocking(trig.run_redeem, tokens, code)
        else:
            await run_blocking(trig.run_auto, tokens)
    output = cap.get()

    claimed = len(re.findall(r'Claimed|Redeemed', output))

    result = discord.Embed(title="✅ Nitro Done", color=0x57F287)
    result.add_field(name="Claimed/Redeemed", value=f"`{claimed}`", inline=True)
    for i, chunk in enumerate(chunk_message(output)):
        result.add_field(name=f"Log {i+1}", value=f"```\n{chunk}\n```", inline=False)
    await msg.edit(embed=result)


# ─────────────────────────────────────────────────────────────────────────────
#  /boost
# ─────────────────────────────────────────────────────────────────────────────
@bot.slash_command(name="boost",
                   description="Boost a server using saved Nitro tokens",
                   guild_ids=debug_guilds)
@option("guild_id", description="Target server/guild ID", type=str)
async def cmd_boost(ctx: discord.ApplicationContext, guild_id: str):
    if not is_owner(ctx): await ctx.respond("🚫 Unauthorized.", ephemeral=True); return
    if not guild_id.isdigit():
        await ctx.respond("❌ Invalid guild ID (numbers only).", ephemeral=True); return
    tokens = read_tokens()
    if not tokens:
        await ctx.respond("❌ No tokens. Run `/gen` first.", ephemeral=True); return

    await ctx.defer()

    e = discord.Embed(title="⚡ Server Booster", color=0xFF8C00)
    e.description = f"Boosting guild `{guild_id}` with `{len(tokens)}` token(s)..."
    msg = await ctx.respond(embed=e)

    booster = ServerBooster(proxies=load_proxies())
    with OutputCapture() as cap:
        await run_blocking(booster.run, tokens, guild_id)
    output = cap.get()

    boost_nums = re.findall(r'Boosted.*?(\d+)\s+slot', output)
    total = sum(int(n) for n in boost_nums) if boost_nums else 0

    result = discord.Embed(title="✅ Boost Complete", color=0x57F287)
    result.add_field(name="Total Boosts Applied", value=f"`{total}`", inline=True)
    for i, chunk in enumerate(chunk_message(output)):
        result.add_field(name=f"Log {i+1}", value=f"```\n{chunk}\n```", inline=False)
    await msg.edit(embed=result)


# ─────────────────────────────────────────────────────────────────────────────
#  /tokens
# ─────────────────────────────────────────────────────────────────────────────
@bot.slash_command(name="tokens",
                   description="View saved tokens and download the token file",
                   guild_ids=debug_guilds)
async def cmd_tokens(ctx: discord.ApplicationContext):
    if not is_owner(ctx): await ctx.respond("🚫 Unauthorized.", ephemeral=True); return
    tokens = read_tokens()
    v, u   = count_verified()

    e = discord.Embed(title="🔑 Saved Tokens", color=0xFF8C00)
    e.add_field(name="Total",      value=f"`{len(tokens)}`", inline=True)
    e.add_field(name="Verified",   value=f"`{v}`",           inline=True)
    e.add_field(name="Unverified", value=f"`{u}`",           inline=True)

    if not tokens:
        e.description = "No tokens saved yet. Run `/gen` to generate some."
        await ctx.respond(embed=e); return

    # Show first 10 tokens (masked)
    preview = []
    for tok in tokens[:10]:
        masked = tok[:20] + "..." + tok[-5:] if len(tok) > 25 else tok
        preview.append(f"`{masked}`")
    if len(tokens) > 10:
        preview.append(f"*...and {len(tokens) - 10} more*")
    e.add_field(name="Preview", value="\n".join(preview), inline=False)

    await ctx.respond(embed=e)

    if TOKENS_FILE.exists() and TOKENS_FILE.stat().st_size > 0:
        await ctx.followup.send(
            content="📥 Full token file:",
            file=discord.File(str(TOKENS_FILE), filename="tangerine_tokens.txt"))


# ─────────────────────────────────────────────────────────────────────────────
#  /addtokens  (upload a .txt file of tokens)
# ─────────────────────────────────────────────────────────────────────────────
@bot.slash_command(name="addtokens",
                   description="Upload a .txt file of tokens to add to the pool",
                   guild_ids=debug_guilds)
@option("file", description="Token file (.txt)", type=discord.Attachment)
async def cmd_addtokens(ctx: discord.ApplicationContext, file: discord.Attachment):
    if not is_owner(ctx): await ctx.respond("🚫 Unauthorized.", ephemeral=True); return
    await ctx.defer(ephemeral=True)
    content = (await file.read()).decode("utf-8", errors="ignore")
    added   = save_text_as_tokens(content)
    total   = len(read_tokens())
    await ctx.respond(
        f"✅ Added `{added}` line(s). Total tokens: `{total}`",
        ephemeral=True)


# ─────────────────────────────────────────────────────────────────────────────
#  /addproxies  (upload proxies.txt)
# ─────────────────────────────────────────────────────────────────────────────
@bot.slash_command(name="addproxies",
                   description="Upload a proxies.txt file (ip:port or user:pass@ip:port)",
                   guild_ids=debug_guilds)
@option("file", description="Proxy file (.txt)", type=discord.Attachment)
async def cmd_addproxies(ctx: discord.ApplicationContext, file: discord.Attachment):
    if not is_owner(ctx): await ctx.respond("🚫 Unauthorized.", ephemeral=True); return
    await ctx.defer(ephemeral=True)
    content = (await file.read()).decode("utf-8", errors="ignore")
    with open(PROXIES_FILE, "w", encoding="utf-8") as f: f.write(content)
    count = len([l for l in content.splitlines()
                 if l.strip() and not l.strip().startswith("#")])
    await ctx.respond(f"✅ Saved `{count}` proxies.", ephemeral=True)


# ─────────────────────────────────────────────────────────────────────────────
#  /cleartokens
# ─────────────────────────────────────────────────────────────────────────────
@bot.slash_command(name="cleartokens",
                   description="Wipe the saved tokens file",
                   guild_ids=debug_guilds)
async def cmd_cleartokens(ctx: discord.ApplicationContext):
    if not is_owner(ctx): await ctx.respond("🚫 Unauthorized.", ephemeral=True); return
    TOKENS_FILE.write_text("") if TOKENS_FILE.exists() else None
    await ctx.respond("🗑️ Tokens file cleared.", ephemeral=True)


# ─────────────────────────────────────────────────────────────────────────────
#  /help
# ─────────────────────────────────────────────────────────────────────────────
@bot.slash_command(name="help",
                   description="Show all commands",
                   guild_ids=debug_guilds)
async def cmd_help(ctx: discord.ApplicationContext):
    if not is_owner(ctx): await ctx.respond("🚫 Unauthorized.", ephemeral=True); return
    e = discord.Embed(title="🍊 Tangerine Gen — Commands", color=0xFF8C00)
    cmds = [
        ("/gen [count] [threads]",          "Generate email-verified tokens"),
        ("/join [invite] [min] [max]",       "Join a server with all saved tokens"),
        ("/nitro [auto|redeem] [code]",      "Claim Nitro trials or redeem a code"),
        ("/boost [guild_id]",                "Boost a server with Nitro tokens"),
        ("/tokens",                          "View + download saved tokens"),
        ("/addtokens [file]",                "Upload a token .txt file"),
        ("/addproxies [file]",               "Upload a proxies.txt file"),
        ("/cleartokens",                     "Wipe the tokens file"),
        ("/status",                          "Show config and runtime info"),
    ]
    for name, desc in cmds:
        e.add_field(name=f"`{name}`", value=desc, inline=False)
    await ctx.respond(embed=e)


# ─────────────────────────────────────────────────────────────────────────────
#  BOT EVENTS
# ─────────────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    tls = "tls-client ✅" if TLS_AVAILABLE else "tls-client ❌ (install it!)"
    nc  = "NoneCap ✅"     if NONECAP_KEY  else "NoneCap ❌"
    log.info(f"Tangerine Gen Bot online as {bot.user}  |  {tls}  |  {nc}")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="tokens generate 🍊"))

@bot.event
async def on_application_command_error(ctx, error):
    log.error(f"Command error: {error}")
    try:
        await ctx.respond(f"❌ Error: `{error}`", ephemeral=True)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if not TLS_AVAILABLE:
        log.warning("tls-client not installed → token gen success rate will be low")
        log.warning("Fix: pip install tls-client")
    bot.run(BOT_TOKEN)
