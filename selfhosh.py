# pip install telethon pytz requests beautifulsoup4

from telethon import TelegramClient, events, functions
import asyncio
import pytz
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib.parse

# ---------------- تنظیمات اصلی ----------------
api_id = 28039994
api_hash = "00877cdcd706564a4de6abf7f7d64349"

client = TelegramClient("ali_session", api_id, api_hash)

# ---------------- دیتابیس وضعیت ----------------
state = {
    "style": None,
    "pv_lock": False,
    "time_on": False,
    "time_style": 1,
    "my_name": "",
    "autoseen": False,
    "typing": False,
    "recording": False,
    "muted_users": set()
}

time_fonts = {
    1: ['𝟎','𝟏','𝟐','𝟑','𝟒','𝟓','𝟔','𝟕','𝟖','𝟗'],
    2: ['𝟘','𝟙','𝟚','𝟛','𝟜','𝟝','𝟞','𝟟','𝟠','𝟡'],
    3: ['⓪','①','②','③','④','⑤','⑥','⑦','⑧','⑨'],
    4: ['0','1','2','3','4','5','6','7','8','9'],
    5: ['0','1','2','3','4','5','6','7','8','9']
}

# ---------------- ساعت اتومات ----------------
async def clock_worker():
    while True:
        if state["time_on"] and state["my_name"]:
            try:
                now = datetime.now(
                    pytz.timezone("Asia/Tehran")
                ).strftime("%H:%M")

                styled = "".join(
                    time_fonts[state["time_style"]][int(c)]
                    if c.isdigit() else ":"
                    for c in now
                )

                await client(functions.account.UpdateProfileRequest(
                    first_name=f"{state['my_name']} | {styled}"
                ))
            except:
                pass

        await asyncio.sleep(60)

# ---------------- پیام‌های ورودی ----------------
@client.on(events.NewMessage(incoming=True))
async def watcher_incoming(event):

    # سکوت کاربر
    if event.sender_id in state["muted_users"]:
        try:
            await event.delete()
        except:
            pass
        return

    # قفل پیوی
    if state["pv_lock"] and event.is_private:
        try:
            await event.delete()
        except:
            pass
        return

    # سین خودکار
    if state["autoseen"]:
        try:
            await client.send_read_acknowledge(event.chat_id)
        except:
            pass

# ---------------- پیام‌های خروجی ----------------
@client.on(events.NewMessage(outgoing=True))
async def watcher_outgoing(event):

    if not event.text:
        return

    if event.text.startswith("."):
        return

    # اکشن فیک تایپ
    if state["typing"]:
        try:
            async with client.action(event.chat_id, "typing"):
                await asyncio.sleep(1)
        except:
            pass

    # اکشن فیک ویس
    if state["recording"]:
        try:
            async with client.action(event.chat_id, "record-audio"):
                await asyncio.sleep(1)
        except:
            pass

    text = event.text
    changed = False

    # استایل متن
    if state["style"]:
        styles = {
            "bold": f"**{text}**",
            "spoiler": f"||{text}||",
            "code": f"`{text}`"
        }
        text = styles.get(state["style"], text)
        changed = True

    if changed:
        try:
            await event.edit(text)
        except:
            pass

# ---------------- سکوت ----------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.سکوت (روشن|خاموش)$'))
async def mute_user(event):
    reply = await event.get_reply_message()

    if not reply:
        await event.edit("❌ روی پیام کاربر ریپلای کن.")
        return

    if "روشن" in event.text:
        state["muted_users"].add(reply.sender_id)
        await event.edit("🔇 کاربر ساکت شد.")
    else:
        state["muted_users"].discard(reply.sender_id)
        await event.edit("🔊 کاربر از سکوت خارج شد.")

# ---------------- بلاک ----------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(بلاک|انبلاک)$'))
async def block_handler(event):

    reply = await event.get_reply_message()
    target = reply.sender_id if reply else event.chat_id

    try:
        if "انبلاک" in event.text:
            await client(functions.contacts.UnblockRequest(id=target))
            await event.edit("✅ کاربر آزاد شد.")
        else:
            await client(functions.contacts.BlockRequest(id=target))
            await event.edit("🚫 کاربر بلاک شد.")
    except Exception as e:
        await event.edit(f"❌ خطا: {e}")

# ---------------- حذف پیام ----------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.حذف (\d+)$'))
async def delete_msgs(event):

    count = int(event.pattern_match.group(1))
    await event.delete()

    async for msg in client.iter_messages(event.chat_id, limit=count):
        try:
            await msg.delete()
        except:
            pass

# ---------------- تنظیمات عمومی ----------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(تایم|سین|پیوی|تایپ|ویس) (روشن|خاموش)$'))
async def toggles(event):

    cmd, mode = event.pattern_match.groups()
    on = mode == "روشن"

    if cmd == "تایم":
        state["time_on"] = on

        if on:
            me = await client.get_me()
            state["my_name"] = me.first_name.split("|")[0].strip()
        else:
            try:
                await client(functions.account.UpdateProfileRequest(
                    first_name=state["my_name"]
                ))
            except:
                pass

    elif cmd == "سین":
        state["autoseen"] = on

    elif cmd == "پیوی":
        state["pv_lock"] = on

    elif cmd == "تایپ":
        state["typing"] = on

    elif cmd == "ویس":
        state["recording"] = on

    await event.edit(f"✅ {cmd} {mode} شد.")

# ---------------- تغییر فونت تایم ----------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.سبک تایم ([1-5])$'))
async def set_time_style(event):
    state["time_style"] = int(event.pattern_match.group(1))
    await event.edit("✅ سبک تایم تغییر کرد.")

# ---------------- استایل متن ----------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(بولد|اسپویلر|کد) روشن$'))
async def set_style(event):
    mapping = {
        "بولد": "bold",
        "اسپویلر": "spoiler",
        "کد": "code"
    }
    state["style"] = mapping[event.pattern_match.group(1)]
    await event.edit("✅ استایل فعال شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.استایل خاموش$'))
async def style_off(event):
    state["style"] = None
    await event.edit("❌ استایل خاموش شد.")

# ---------------- میم ----------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.میم (.+)$'))
async def meme_en(event):

    query = event.pattern_match.group(1)
    await event.edit("🔎 Searching Meme...")

    try:
        r = requests.get(
            f"https://www.myinstants.com/search/?name={urllib.parse.quote(query)}"
        )

        soup = BeautifulSoup(r.text, "html.parser")
        block = soup.find("div", class_="instant")

        if block:
            url = "https://www.myinstants.com" + \
                  block.find("button", class_="small-button")["onclick"].split("'")[1]

            await event.delete()
            await client.send_file(event.chat_id, url, voice_note=True)
        else:
            await event.edit("❌ میمی پیدا نشد.")

    except:
        await event.edit("❌ خطا در جستجو.")

# ---------------- اسپم ----------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.اسپم (\d+) (.+)$'))
async def spam_cmd(event):

    count = int(event.pattern_match.group(1))
    text = event.pattern_match.group(2)

    await event.delete()

    for _ in range(count):
        try:
            await client.send_message(event.chat_id, text)
            await asyncio.sleep(0.08)
        except:
            pass

# ---------------- بازی تاس و بولینگ ----------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(تاس|بولینگ)$'))
async def games_cmd(event):

    emoji = "🎲" if "تاس" in event.text else "🎳"

    await event.delete()
    await client(functions.messages.SendDiceRequest(
        peer=event.chat_id,
        emoticon=emoji
    ))

# ---------------- فوروارد ----------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.فوروارد (.+)$'))
async def forward_cmd(event):

    target = event.pattern_match.group(1)
    reply = await event.get_reply_message()

    if reply:
        await client.forward_messages(target, reply)
        await event.edit(f"✅ به {target} فوروارد شد.")
    else:
        await event.edit("❌ روی پیام ریپلای کن.")

# ---------------- ذخیره ----------------
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.ذخیره$'))
async def save_cmd(event):

    reply = await event.get_reply_message()

    if reply:
        await client.send_message("me", reply)
        await event.edit("✅ در Saved Messages ذخیره شد.")
    else:
        await event.edit("❌ روی پیام ریپلای کن.")

# ---------------- اجرای اصلی ----------------
async def main():
    await client.start()
    client.loop.create_task(clock_worker())
    print("Self Bot Online ✅")
    await client.run_until_disconnected()

if __name__ == "__main__":
    asyncio.run(main())
    import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_server).start()
