import asyncio
import os
import re

import phonenumbers
import requests
from phonenumbers import geocoder
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    def load_dotenv():
        return False

try:
    from telegram import CopyTextButton
except ImportError:  # pragma: no cover
    CopyTextButton = None

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_ID = int(os.getenv("GROUP_ID", "0"))
API_URL = os.getenv("API_URL", "https://www.ksiiprn.com/api/v1/iprn/messages")
API_BEARER_TOKEN = os.getenv("API_BEARER_TOKEN", "")
START_DATE = os.getenv("START_DATE", "2025-01-15")
PER_PAGE = int(os.getenv("PER_PAGE", "50"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "10"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing. Set it in your environment or .env file.")
if GROUP_ID == 0:
    raise RuntimeError("GROUP_ID is missing or invalid. Set it in your environment or .env file.")
if not API_BEARER_TOKEN:
    raise RuntimeError("API_BEARER_TOKEN is missing. Set it in your environment or .env file.")

APP_EMOJIS = {
    "whatsapp": "💬",
    "telegram": "✈️",
    "facebook": "📘",
    "instagram": "📸",
    "tiktok": "🎵",
    "google": "🌐",
    "twitter": "🐦",
}


def get_app_emoji(service_name):
    service_name = str(service_name).lower()
    for key, emoji in APP_EMOJIS.items():
        if key in service_name:
            return emoji
    return "📱"


def get_country_info(phone_number):
    if not str(phone_number).startswith("+"):
        phone_number = "+" + str(phone_number)
    try:
        parsed = phonenumbers.parse(phone_number)
        country_name = geocoder.country_name_for_number(parsed, "en") or "Unknown"
        region = phonenumbers.region_code_for_number(parsed)
        if region:
            flag = chr(ord(region[0]) + 127397) + chr(ord(region[1]) + 127397)
        else:
            flag = "🏳️"
        iso = region or "UN"
        return country_name, flag, iso
    except Exception:
        return "Unknown", "🏳️", "UN"


def extract_otp(msg):
    otp_match = re.search(r"\d{3}[-\s]?\d{3,4}|\d{4,8}", str(msg) or "")
    return otp_match.group(0) if otp_match else "Unknown"


def mask_number(num):
    num = str(num).replace("+", "")
    if len(num) <= 6:
        return num
    return num[:3] + "x" * (len(num) - 6) + num[-3:]


def get_item_data(item):
    if isinstance(item, dict):
        service = item.get("service") or item.get("app") or item.get("provider") or "unknown"
        num = item.get("number") or item.get("phone") or item.get("phone_number") or ""
        msg = item.get("message") or item.get("text") or item.get("content") or ""
        uid = item.get("id") or f"{service}_{num}_{msg}"
        return service, num, msg, uid

    if isinstance(item, (list, tuple)):
        if len(item) >= 4:
            service, num, msg, *_ = item
            return service, num, msg, f"{service}_{num}_{item[3]}"
        if len(item) >= 3:
            service, num, msg = item[:3]
            return service, num, msg, f"{service}_{num}_{msg}"

    return "unknown", "", "", "unknown"


def fetch_messages():
    headers = {
        "Authorization": f"Bearer {API_BEARER_TOKEN}",
        "Accept": "application/json",
    }
    params = {
        "start_date": START_DATE,
        "type": "a2p",
        "per_page": PER_PAGE,
    }
    response = requests.get(API_URL, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    if isinstance(data, dict):
        for key in ("data", "items", "results"):
            if key in data:
                data = data[key]
                break

    if not isinstance(data, list):
        return []
    return data


async def send_to_group(bot, entry):
    service, num, msg, _ = get_item_data(entry)
    if not num:
        return

    _, flag, iso = get_country_info(num)
    app_emoji = get_app_emoji(service)
    masked = mask_number(num)
    otp = extract_otp(msg)

    text = (
        f"{flag} <b>#{iso} {app_emoji}{service} {masked}</b> "
        "<tg-emoji emoji-id=\"5264919878082509254\">▶️</tg-emoji>"
    )

    if CopyTextButton:
        try:
            row1 = [
                InlineKeyboardButton(
                    text=f"{otp}",
                    copy_text=CopyTextButton(text=otp),
                    icon_custom_emoji_id="6176966310920983412",
                )
            ]
        except Exception:
            row1 = [InlineKeyboardButton(text=f"🔑 {otp}", callback_data="noop")]
    else:
        row1 = [InlineKeyboardButton(text=f"🔑 {otp}", callback_data="noop")]

    row2 = [
        InlineKeyboardButton(
            text="Methods",
            url="https://t.me/Axonnumber_bot",
            icon_custom_emoji_id="5807797645443340724",
        ),
        InlineKeyboardButton(
            text="Channel",
            url="https://t.me/+Pzz-0SEu-2s3NmZl",
            icon_custom_emoji_id="5429571366384842791",
        ),
    ]
    row3 = [
        InlineKeyboardButton(
            text="OTP Panel",
            url="https://t.me/Axonnumber_bot",
            icon_custom_emoji_id="5372917041193828849",
        )
    ]

    markup = InlineKeyboardMarkup([row1, row2, row3])

    try:
        await bot.send_message(
            chat_id=GROUP_ID,
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
            disable_web_page_preview=True,
        )
        print(f"✅ Sent OTP for {num} - {service}")
    except Exception as exc:
        print(f"❌ Failed to send to group: {exc}")


async def main():
    bot = Bot(token=BOT_TOKEN)
    seen_otps = set()
    print("🚀 Starting Forwarder Bot...")

    try:
        for item in fetch_messages():
            _, _, _, uid = get_item_data(item)
            if uid:
                seen_otps.add(uid)
        print(f"📦 Initialized with {len(seen_otps)} existing OTPs.")
    except Exception as exc:
        print(f"⚠️ Initial API fetch failed: {exc}")

    while True:
        try:
            for item in reversed(fetch_messages()):
                _, _, _, uid = get_item_data(item)
                if uid and uid not in seen_otps:
                    seen_otps.add(uid)
                    await send_to_group(bot, item)
                    await asyncio.sleep(0.5)

            if len(seen_otps) > 10000:
                seen_otps = set(list(seen_otps)[-5000:])
        except Exception as exc:
            print(f"⚠️ Error fetching API: {exc}")

        await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
