#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔══════════════════════════════════════════════════════════════╗
║           F R E E   F I R E   L E V E L   B O T              ║
║           D E F I N E   X   A U R A                          ║
║           Ultra Low Delay · Pro Grade · Premium UI           ║
╚══════════════════════════════════════════════════════════════╝
"""

import asyncio
import aiohttp
import json
import os
import time
import ssl
from datetime import datetime
from typing import Optional, Tuple, Any

import urllib3
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from protobuf_decoder.protobuf_decoder import Parser

# Protobuf definitions
from Pb2 import (
    DEcwHisPErMsG_pb2,
    MajoRLoGinrEs_pb2,
    PorTs_pb2,
    MajoRLoGinrEq_pb2,
)

# Custom modules (provided by you)
from xDL import *
from autoup import *

# Rich UI
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich.traceback import install as rich_traceback_install

# ------------------------------------------------------------------
#  INITIALIZATION
# ------------------------------------------------------------------
rich_traceback_install(show_locals=False, suppress=[aiohttp])
console = Console()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ------------------------------------------------------------------
#  CONSTANTS & UTILITIES
# ------------------------------------------------------------------
def rot13(text: str) -> str:
    result = []
    for ch in text:
        if 'a' <= ch <= 'z':
            result.append(chr((ord(ch) - ord('a') + 13) % 26 + ord('a')))
        elif 'A' <= ch <= 'Z':
            result.append(chr((ord(ch) - ord('A') + 13) % 26 + ord('A')))
        else:
            result.append(ch)
    return ''.join(result)

LEVEL_UP = "DEFINE X AURA [ D E F ]"

# ------------------------------------------------------------------
#  PROTOBUF HELPER FUNCTIONS (re‑defined to avoid naming conflicts)
# ------------------------------------------------------------------
async def decode_major_login_response(data: bytes):
    proto = MajoRLoGinrEs_pb2.MajorLoginRes()
    proto.ParseFromString(data)
    return proto

async def decode_get_login_data_response(data: bytes):
    proto = PorTs_pb2.GetLoginData()
    proto.ParseFromString(data)
    return proto

async def decode_whisper_message(hex_packet: str):
    """Safely decode an incoming whisper packet."""
    packet_bytes = bytes.fromhex(hex_packet)
    proto = DEcwHisPErMsG_pb2.DecodeWhisper()
    proto.ParseFromString(packet_bytes)
    return proto

# ------------------------------------------------------------------
#  PREMIUM IN‑GAME MESSAGING (styled)
# ------------------------------------------------------------------
def premium_message(title: str, body_lines: list, footer: str = None, style: str = "default") -> str:
    BORDER = "FF69B4"
    TITLE_COLOR = "FFD700"
    BODY_COLOR = "FFFFFF"
    FOOTER_COLOR = "FFA500"

    if style == "glow":
        top = f"[B][C][#FF4500]◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤◢◤[/C][/B]"
        bottom = f"[B][C][#FF4500]◥◣◥◣◥◣◥◣◥◣◥◣◥◣◥◣◥◣◥◣[/C][/B]"
    elif style == "double":
        top = f"[B][C][{BORDER}]╔══════════════════════════════════════╗[/C][/B]"
        bottom = f"[B][C][{BORDER}]╚══════════════════════════════════════╝[/C][/B]"
    elif style == "minimal":
        top = f"[C][{BORDER}]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/C]"
        bottom = f"[C][{BORDER}]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/C]"
    else:
        top = f"[B][C][{BORDER}]◤━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━◥[/C][/B]"
        bottom = f"[B][C][{BORDER}]◣━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━◢[/C][/B]"

    title_line = f"[B][C][{TITLE_COLOR}]✨ {title} ✨[/C][/B]"
    body = "\n".join(f"[C][{BODY_COLOR}]  ➤ {line}[/C]" for line in body_lines)
    footer_str = f"\n[C][{FOOTER_COLOR}]◆ {footer} ◆[/C]" if footer else ""
    return f"{top}\n{title_line}\n{top}\n{body}\n{bottom}{footer_str}"

# ------------------------------------------------------------------
#  NETWORK & CRYPTO
# ------------------------------------------------------------------
async def send_packet(chat_writer, online_writer, packet_type: str, packet_data: bytes):
    if packet_type == 'Chat' and chat_writer:
        chat_writer.write(packet_data)
        await chat_writer.drain()
    elif packet_type == 'Online' and online_writer:
        online_writer.write(packet_data)
        await online_writer.drain()

async def generate_access_token(uid: str, password: str) -> Tuple[Optional[str], Optional[str]]:
    url = "https://100067.connect.garena.com/oauth/guest/token/grant"
    headers = {
        "Host": "100067.connect.garena.com",
        "User-Agent": await Ua(),
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "close",
    }
    data = {
        "uid": uid,
        "password": password,
        "response_type": "token",
        "client_type": "2",
        "client_secret": "2ee44819e9b4598845141067b281621874d0d5d7af9d8f7e00c1e54715b7d1e3",
        "client_id": "100067",
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=data) as resp:
            if resp.status == 200:
                js = await resp.json()
                return js.get("open_id"), js.get("access_token")
    return None, None

async def encrypt_proto(proto_serialized: bytes) -> bytes:
    key = b'Yg&tc%DEuh6%Zc^8'
    iv = b'6oyZDr22E3ychjM%'
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded = pad(proto_serialized, AES.block_size)
    return cipher.encrypt(padded)

async def build_major_login_request(open_id: str, access_token: str, version: str) -> bytes:
    ml = MajoRLoGinrEq_pb2.MajorLogin()
    ml.event_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ml.game_name = "free fire"
    ml.platform_id = 1
    ml.client_version = version
    ml.system_software = "Android OS 9 / API-28 (PQ3B.190801.10101846/G9650ZHU2ARC6)"
    ml.system_hardware = "Handheld"
    ml.telecom_operator = "Verizon"
    ml.network_type = "WIFI"
    ml.screen_width = 1920
    ml.screen_height = 1080
    ml.screen_dpi = "280"
    ml.processor_details = "ARM64 FP ASIMD AES VMH | 2865 | 4"
    ml.memory = 3003
    ml.gpu_renderer = "Adreno (TM) 640"
    ml.gpu_version = "OpenGL ES 3.1 v1.46"
    ml.unique_device_id = "Google|34a7dcdf-a7d5-4cb6-8d7e-3b0e448a0c57"
    ml.client_ip = "223.191.51.89"
    ml.language = "en"
    ml.open_id = open_id
    ml.open_id_type = "4"
    ml.device_type = "Handheld"
    ml.memory_available.version = 55
    ml.memory_available.hidden_value = 81
    ml.access_token = access_token
    ml.platform_sdk_id = 1
    ml.network_operator_a = "Verizon"
    ml.network_type_a = "WIFI"
    ml.client_using_version = "7428b253defc164018c604a1ebbfebdf"
    ml.external_storage_total = 36235
    ml.external_storage_available = 31335
    ml.internal_storage_total = 2519
    ml.internal_storage_available = 703
    ml.game_disk_storage_available = 25010
    ml.game_disk_storage_total = 26628
    ml.external_sdcard_avail_storage = 32992
    ml.external_sdcard_total_storage = 36235
    ml.login_by = 3
    ml.library_path = "/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/lib/arm64"
    ml.reg_avatar = 1
    ml.library_token = "5b892aaabd688e571f688053118a162b|/data/app/com.dts.freefireth-YPKM8jHEwAJlhpmhDhv5MQ==/base.apk"
    ml.channel_type = 3
    ml.cpu_type = 2
    ml.cpu_architecture = "64"
    ml.client_version_code = "2019118695"
    ml.graphics_api = "OpenGLES2"
    ml.supported_astc_bitset = 16383
    ml.login_open_id_type = 4
    ml.analytics_detail = b"FwQVTgUPX1UaUllDDwcWCRBpWAUOUgsvA1snWlBaO1kFYg=="
    ml.loading_time = 13564
    ml.release_channel = "android"
    ml.extra_info = "KqsHTymw5/5GB23YGniUYN2/q47GATrq7eFeRatf0NkwLKEMQ0PK5BKEk72dPflAxUlEBir6Vtey83XqF593qsl8hwY="
    ml.android_engine_init_flag = 110009
    ml.if_push = 1
    ml.is_vpn = 1
    ml.origin_platform_type = "4"
    ml.primary_platform_type = "4"
    return await encrypt_proto(ml.SerializeToString())

async def perform_major_login(payload: bytes, login_url: str, headers: dict) -> Optional[bytes]:
    url = f"{login_url}MajorLogin"
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=headers, ssl=ssl_ctx) as resp:
            if resp.status == 200:
                return await resp.read()
    return None

async def fetch_login_data(base_url: str, payload: bytes, token: str, headers: dict) -> Optional[bytes]:
    url = f"{base_url}/GetLoginData"
    headers["Authorization"] = f"Bearer {token}"
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=payload, headers=headers, ssl=ssl_ctx) as resp:
            if resp.status == 200:
                return await resp.read()
    return None

async def build_auth_token(target_uid: int, token: str, timestamp: int, key: bytes, iv: bytes) -> str:
    uid_hex = hex(target_uid)[2:]
    uid_len = len(uid_hex)
    enc_ts = await DecodE_HeX(timestamp)
    enc_token = token.encode().hex()
    enc_packet = await EnC_PacKeT(enc_token, key, iv)
    enc_len = hex(len(enc_packet) // 2)[2:]
    padding = {
        9: '0000000',
        8: '00000000',
        10: '000000',
        7: '000000000'
    }.get(uid_len, '0000000')
    return f"0115{padding}{uid_hex}{enc_ts}00000{enc_len}{enc_packet}"

# ------------------------------------------------------------------
#  PACKET CONSTRUCTION FOR AUTO START
# ------------------------------------------------------------------
async def join_team_packet(team_code: str, key: bytes, iv: bytes, region: str) -> bytes:
    fields = {
        1: 4,
        2: {
            4: bytes.fromhex("01090a0b121920"),
            5: str(team_code),
            6: 6,
            8: 1,
            9: {2: 800, 6: 11, 8: "1.111.1", 9: 5, 10: 1}
        }
    }
    ptype = "0514" if region.lower() == "ind" else ("0519" if region.lower() == "bd" else "0515")
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), ptype, key, iv)

async def start_match_packet(key: bytes, iv: bytes, region: str) -> bytes:
    fields = {1: 9, 2: {1: 12480598706}}
    ptype = "0514" if region.lower() == "ind" else ("0519" if region.lower() == "bd" else "0515")
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), ptype, key, iv)

async def leave_squad_packet(key: bytes, iv: bytes, region: str) -> bytes:
    fields = {1: 7, 2: {1: 12480598706}}
    ptype = "0514" if region.lower() == "ind" else ("0519" if region.lower() == "bd" else "0515")
    return await GeneRaTePk((await CrEaTe_ProTo(fields)).hex(), ptype, key, iv)

# ------------------------------------------------------------------
#  AUTO LOOP LOGIC (with working /stop)
# ------------------------------------------------------------------
auto_running = False
stop_auto = False
auto_task = None
START_DURATION = 18
WAIT_AFTER_MATCH = 5
SPAM_DELAY = 0.10

async def auto_start_loop(team_code: str, uid: int, chat_id: int, chat_type: int,
                          key: bytes, iv: bytes, region: str):
    global auto_running, stop_auto
    console.log(f"[bold yellow]🚀 Auto-start loop started for team {team_code}[/]")
    while not stop_auto:
        try:
            # Join squad
            await send_packet(None, online_writer, 'Online',
                              await join_team_packet(team_code, key, iv, region))
            await asyncio.sleep(0.5)

            # Spam start packets
            start_pkt = await start_match_packet(key, iv, region)
            end_time = time.time() + START_DURATION
            with console.status("[cyan]Spamming START packets...[/]") as status:
                while time.time() < end_time and not stop_auto:
                    await send_packet(None, online_writer, 'Online', start_pkt)
                    await asyncio.sleep(SPAM_DELAY)
                    remaining = int(end_time - time.time())
                    if remaining > 0:
                        status.update(f"[green]Spamming... {remaining}s left[/]")

            if stop_auto:
                break

            # Wait after match
            for _ in range(WAIT_AFTER_MATCH):
                if stop_auto:
                    break
                await asyncio.sleep(1)

            if stop_auto:
                break

            # Leave squad
            await send_packet(None, online_writer, 'Online',
                              await leave_squad_packet(key, iv, region))
            await asyncio.sleep(0.5)

        except Exception as e:
            console.log(f"[red]Auto-loop error: {e}[/]")
            break

    auto_running = False
    stop_auto = False
    console.log("[red]🛑 Auto-start loop terminated[/]")

async def stop_auto_loop():
    global stop_auto, auto_task, auto_running
    stop_auto = True
    if auto_task and not auto_task.done():
        auto_task.cancel()
        try:
            await auto_task
        except asyncio.CancelledError:
            pass
    auto_running = False

# ------------------------------------------------------------------
#  MESSAGE SENDING
# ------------------------------------------------------------------
async def safe_send_message(chat_type: int, message: str, target_uid: int,
                            chat_id: int, key: bytes, iv: bytes, max_retries=2) -> bool:
    for attempt in range(max_retries):
        try:
            pkt = await SEndMsG(chat_type, message, target_uid, chat_id, key, iv, region)
            await send_packet(whisper_writer, None, 'Chat', pkt)
            return True
        except Exception:
            if attempt < max_retries - 1:
                await asyncio.sleep(0.2)
    return False

# ------------------------------------------------------------------
#  TCP CONNECTIONS
# ------------------------------------------------------------------
online_writer = None
whisper_writer = None

async def tcp_online(ip: str, port: int, auth_token_hex: str, reconnect_delay=0.5):
    global online_writer
    while True:
        try:
            reader, writer = await asyncio.open_connection(ip, int(port))
            online_writer = writer
            writer.write(bytes.fromhex(auth_token_hex))
            await writer.drain()
            # Keep connection alive
            while True:
                data = await reader.read(8192)
                if not data:
                    break
        except Exception as e:
            console.log(f"[red]Online connection lost: {e}[/]")
        finally:
            if online_writer:
                online_writer.close()
                await online_writer.wait_closed()
                online_writer = None
        await asyncio.sleep(reconnect_delay)

async def tcp_chat(ip: str, port: int, auth_token_hex: str, key: bytes, iv: bytes,
                   login_data_proto, region: str, reconnect_delay=0.5):
    global whisper_writer, online_writer, auto_running, auto_task, stop_auto
    while True:
        try:
            reader, writer = await asyncio.open_connection(ip, int(port))
            whisper_writer = writer
            writer.write(bytes.fromhex(auth_token_hex))
            await writer.drain()

            # Clan authentication
            if hasattr(login_data_proto, 'Clan_ID') and login_data_proto.Clan_ID:
                clan_pkt = await AuthClan(login_data_proto.Clan_ID,
                                          login_data_proto.Clan_Compiled_Data,
                                          key, iv)
                writer.write(clan_pkt)
                await writer.drain()

            # Main read loop
            while True:
                data = await reader.read(8192)
                if not data:
                    break

                # Detect whisper packet
                hex_data = data.hex()
                if hex_data.startswith("120000"):
                    try:
                        whisper = await decode_whisper_message(hex_data[10:])
                        msg = whisper.Data.msg.strip().lower()
                        uid = whisper.Data.uid
                        chat_id = whisper.Data.Chat_ID
                        chat_type = whisper.Data.chat_type

                        # Display incoming message in console
                        console.print(Panel(
                            f"[white]{msg}[/]\n[dim]from UID: {uid}[/]",
                            title="[bold magenta]📨 WHISPER[/]",
                            border_style="cyan"
                        ))

                        # ---------- COMMAND HANDLING ----------
                        # /lw command
                        if msg.startswith('/lw '):
                            parts = msg.split()
                            if len(parts) < 2:
                                await safe_send_message(
                                    chat_type,
                                    premium_message("❌ INVALID USAGE",
                                                    ["Use: /lw <team_code>",
                                                     "Example: /lw 12345678"]),
                                    uid, chat_id, key, iv
                                )
                                continue
                            team_code = parts[1]
                            if not team_code.isdigit():
                                await safe_send_message(
                                    chat_type,
                                    premium_message("❌ INVALID TEAM CODE",
                                                    ["Numbers only."]),
                                    uid, chat_id, key, iv
                                )
                                continue
                            if auto_running:
                                await safe_send_message(
                                    chat_type,
                                    premium_message("⚠️ ALREADY RUNNING",
                                                    ["Use /stop to halt the current loop."]),
                                    uid, chat_id, key, iv
                                )
                                continue
                            # Start new loop
                            stop_auto = False
                            auto_running = True
                            auto_task = asyncio.create_task(
                                auto_start_loop(team_code, uid, chat_id, chat_type,
                                                key, iv, region)
                            )
                            await safe_send_message(
                                chat_type,
                                premium_message("✅ AUTO START ACTIVATED",
                                                [f"Team: {team_code}",
                                                 "Spamming start packets...",
                                                 "Use /stop to halt"],
                                                footer="🔥 DEF 🔥"),
                                uid, chat_id, key, iv
                            )

                        # /stop command
                        elif msg.strip() == '/stop':
                            if auto_running:
                                await stop_auto_loop()
                                await safe_send_message(
                                    chat_type,
                                    premium_message("🛑 AUTO STOPPED",
                                                    ["Level‑up loop terminated."]),
                                    uid, chat_id, key, iv
                                )
                            else:
                                await safe_send_message(
                                    chat_type,
                                    premium_message("⚠️ NOTHING TO STOP",
                                                    ["No active auto-start."]),
                                    uid, chat_id, key, iv
                                )

                        # /help
                        elif msg.strip() in ('/help', 'help', '/menu'):
                            help_txt = premium_message(
                                "🤖 BOT COMMANDS",
                                [
                                    "[B]/lw <code>[/B]  → Start auto level‑up",
                                    "[B]/stop[/B]       → Stop the loop",
                                    "[B]/info[/B]       → Bot status",
                                    "[B]/help[/B]       → This menu"
                                ],
                                footer=f"⚡ {LEVEL_UP}",
                                style="double"
                            )
                            await safe_send_message(chat_type, help_txt, uid, chat_id, key, iv)

                        # /info
                        elif msg.strip() in ('/info', 'info'):
                            await safe_send_message(
                                chat_type,
                                "BOT STATUS\nDeveloper: Syrexxy X Horimiya\nBot is online",
                                uid,
                                chat_id,
                                key,
                                iv
                            )
                            

                    except Exception as e:
                        console.log(f"[red]Whisper decode error: {type(e).__name__}: {e}[/]")

        except Exception as e:
            console.log(f"[red]Chat connection error: {e}[/]")
        finally:
            if whisper_writer:
                whisper_writer.close()
                await whisper_writer.wait_closed()
                whisper_writer = None
        await asyncio.sleep(reconnect_delay)

# ------------------------------------------------------------------
#  MAIN BOT ROUTINE
# ------------------------------------------------------------------
CURRENT_BOT_UID = None
region = 'IN'
login_url, ob, version = AuToUpDaTE()
headers = {
    'User-Agent': Uaa(),
    'Connection': "Keep-Alive",
    'Accept-Encoding': "gzip",
    'Content-Type': "application/x-www-form-urlencoded",
    'Expect': "100-continue",
    'X-Unity-Version': "2018.4.11f1",
    'X-GA': "v1 1",
    'ReleaseVersion': ob,
}

async def main():
    global CURRENT_BOT_UID, region, whisper_writer, online_writer

    # Display banner
    banner = Text("""
╔══════════════════════════════════════════════════════════════╗
║                    🔥 FREE FIRE BOT 🔥                       ║
║                   DEFINE AURA LIKE BOT V 1.0                 ║
║          Ultra Low Delay · Pro Grade · Premium UI            ║
╚══════════════════════════════════════════════════════════════╝
""", style="bold cyan")
    console.print(banner)
    console.print(Panel.fit(
        f"[yellow]Version {version}[/] | [green]Optimized for max speed[/] | [red]© 2026[/]",
        border_style="blue"
    ))
    console.print()

    # Load credentials
    if not os.path.exists("bot.txt"):
        console.log("[red]❌ bot.txt missing. Create: {\"UID\":\"PASSWORD\"}[/]")
        return

    with open("bot.txt") as f:
        creds = json.load(f)
    if not creds:
        console.log("[red]❌ bot.txt empty[/]")
        return

    uid, pwd = list(creds.items())[0]
    console.log(f"[bold cyan]📱 Logging in UID: {uid}[/]")

    # Get access token
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  console=console, transient=True) as prog:
        prog.add_task("Authenticating...", total=None)
        open_id, access_token = await generate_access_token(uid, pwd)

    if not open_id:
        console.log("[red]❌ Auth failed[/]")
        return
    console.log("[green]✔ Access granted[/]")

    # MajorLogin
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  console=console, transient=True) as prog:
        prog.add_task("MajorLogin...", total=None)
        payload = await build_major_login_request(open_id, access_token, version)
        resp = await perform_major_login(payload, login_url, headers)

    if not resp:
        console.log("[red]❌ MajorLogin failed[/]")
        return
    auth = await decode_major_login_response(resp)
    token = auth.token
    if not token:
        console.log("[red]❌ No token received[/]")
        return

    # Save token for debugging
    with open("token.json", "w") as f:
        json.dump({
            "token": token,
            "saved_at": time.time(),
            "bot_uid": str(auth.account_uid),
            "region": getattr(auth, 'region', 'IND')
        }, f, indent=2)

    url = auth.url
    region = getattr(auth, 'region', 'IND')
    bot_uid = auth.account_uid
    CURRENT_BOT_UID = str(bot_uid)
    key = auth.key
    iv = auth.iv
    timestamp = auth.timestamp

    # Get login data (ports)
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                  console=console, transient=True) as prog:
        prog.add_task("Fetching login data...", total=None)
        login_data_raw = await fetch_login_data(url, payload, token, headers.copy())

    if not login_data_raw:
        console.log("[red]❌ GetLoginData failed[/]")
        return
    ports = await decode_get_login_data_response(login_data_raw)
    online_ip, online_port = ports.Online_IP_Port.split(":")
    chat_ip, chat_port = ports.AccountIP_Port.split(":")

    auth_token_hex = await build_auth_token(int(bot_uid), token, int(timestamp), key, iv)

    console.log("[green]🤖 Bot online – ready for commands[/]")
    await asyncio.gather(
        tcp_chat(chat_ip, chat_port, auth_token_hex, key, iv, ports, region),
        tcp_online(online_ip, online_port, auth_token_hex)
    )

async def start():
    while True:
        try:
            await main()
        except Exception as e:
            console.print_exception(show_locals=False)
            console.log("[yellow]Restarting in 5 seconds...[/]")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(start())