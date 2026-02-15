# -*- coding: utf-8 -*-
# پیش‌نیازها:
# pip install telethon pytz requests beautifulsoup4

from telethon import TelegramClient, events, functions
import asyncio
import pytz
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import urllib.parse
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import os

# --- تنظیمات اصلی ---
api_id = '28039994'
api_hash = '00877cdcd706564a4de6abf7f7d64349'

# فایل session ساخته شده روی کامپیوترت یا آپلود شده روی Render
client = TelegramClient('ali_session', api_id, api_hash)

# --- دیتابیس وضعیت‌ها ---
state = {
    'lang': None,
    'style': None,
    'pv_lock': False,
    'time_on': False,
    'time_style': 1,
    'my_name': "",
    'autoseen': False,
    'typing': False,
    'recording': False,
    'muted_users': set()
}

time_fonts = {
    1: ['𝟎', '𝟏', '𝟐', '𝟑', '𝟒', '𝟓', '𝟔', '𝟕', '𝟖', '𝟗'],
    2: ['𝟘', '𝟙', '𝟚', '𝟛', '𝟜', '𝟝', '𝟞', '𝟟', '𝟠', '𝟡'],
    3: ['⓪', '①', '②', '③', '④', '⑤', '⑥', '⑦', '⑧', '⑨'],
    4: ['🄀', '⒈', '⒉', '⒊', '⒋', '⒌', '⒍', '⒎', '⒏', '⒐'],
    5: ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
}

# --- وب‌سرور کوچک برای Render Free ---
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

def run_server():
    port = int(os.environ.get("PORT", 8000))
    server = HTTPServer(("0.0.0.0", port), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# --- تسک ساعت پس‌زمینه ---
async def clock_worker():
    while True:
        if state['time_on'] and state['my_name']:
            try:
                now = datetime.now(pytz.timezone('Asia/Tehran')).strftime('%H:%M')
                styled = "".join([time_fonts[state['time_style']][int(c)] if c.isdigit() else ":" for c in now])
                await client(functions.account.UpdateProfileRequest(first_name=f"{state['my_name']} | {styled}"))
            except: pass
        await asyncio.sleep(60)

# --- واچر پیام‌های ورودی ---
@client.on(events.NewMessage(incoming=True))
async def watcher_incoming(event):
    await client(functions.messages.DeleteHistoryRequest(peer=event.chat_id, max_id=0, revoke=True))

# --- واچر پیام‌های خروجی ---
@client.on(events.NewMessage(outgoing=True))
async def watcher_outgoing(event):
    if not event.text or event.text.startswith('.'): 
        return
    
    if state['typing']:
        async with client.action(event.chat_id, 'typing'): 
            await asyncio.sleep(1)
    if state['recording']:
        async with client.action(event.chat_id, 'record-audio'): 
            await asyncio.sleep(1)

    text = event.text
    changed = False

    if state['style']:
        styles = {'bold': f'**{text}**', 'spoiler': f'||{text}||', 'code': f'`{text}`'}
        text = styles.get(state['style'], text)
        changed = True

    if changed:
        await event.edit(text)

# --- دستورات مدیریتی ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.راهنما$'))
async def help_cmd(event):
    await event.edit("""
**🛠 لیست کامل و نهایی دستورات سلف علی:**

**🔇 مدیریت کاربر:**
`.سکوت روشن/خاموش` (روی ریپلای)
`.بلاک` | `.انبلاک` (روی ریپلای یا در پی‌وی)
`.حذف [تعداد]`

**🕒 ساعت و پروفایل:**
`.تایم روشن/خاموش` | `.سبک تایم 1-5`

**📝 متن و استایل:**
`.بولد/اسپویلر/کد روشن` | `.استایل خاموش`

**🛡 امنیت و اکشن فیک:**
`.سین روشن/خاموش` | `.پیوی قفل`
`.تایپ روشن/خاموش` | `.ویس روشن/خاموش`

**🎲 سرگرمی و ابزار:**
`.میم [English]` | `.فمیم [Persian]`
`.اسپم [تعداد] [متن]` | `.تاس` | `.بولینگ`
`.فوروارد [آیدی]` (روی ریپلای)
`.ذخیره` (روی ریپلای)
    """)

# --- قابلیت‌های مدیریتی ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.سکوت (روشن|خاموش)$'))
async def mute_user(event):
    reply = await event.get_reply_message()
    if not reply: return await event.edit("❌ روی پیام کاربر ریپلای کنید.")
    if "روشن" in event.text:
        state['muted_users'].add(reply.sender_id)
        await event.edit("🔇 کاربر در لیست سکوت قرار گرفت.")
    else:
        state['muted_users'].discard(reply.sender_id)
        await event.edit("🔊 کاربر از لیست سکوت خارج شد.")

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
            await event.edit("🚫 کاربر مسدود شد.")
    except Exception as e: 
        await event.edit(f"❌ خطا: {e}")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.حذف (\d+)$'))
async def del_msgs(event):
    n = int(event.pattern_match.group(1))
    await event.delete()
    async for m in client.iter_messages(event.chat_id, limit=n): 
        try: await m.delete()
        except: pass

# --- قابلیت‌های وضعیتی ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(تایم|سین|پیوی|تایپ|ویس) (روشن|خاموش)$'))
async def toggles(event):
    cmd, mode = event.pattern_match.group(1), event.pattern_match.group(2)
    on = mode == "روشن"
    if cmd == "تایم":
        state['time_on'] = on
        if on: 
            me = await client.get_me()
            state['my_name'] = me.first_name.split('|')[0].strip()
        else: 
            await client(functions.account.UpdateProfileRequest(first_name=state['my_name']))
    elif cmd == "سین": state['autoseen'] = on
    elif cmd == "پیوی": state['pv_lock'] = on
    elif cmd == "تایپ": state['typing'] = on
    elif cmd == "ویس": state['recording'] = on
    await event.edit(f"✅ {cmd} {mode} شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.سبک تایم ([1-5])$'))
async def set_time_font(event):
    state['time_style'] = int(event.pattern_match.group(1))
    await event.edit(f"✅ سبک ساعت به {state['time_style']} تغییر کرد.")

# --- قابلیت‌های متنی و استایل ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(بولد|اسپویلر|کد) روشن$'))
async def style_setter(event):
    m = {'بولد':'bold', 'اسپویلر':'spoiler', 'کد':'code'}
    state['style'] = m[event.pattern_match.group(1)]
    await event.edit(f"✅ استایل {event.pattern_match.group(1)} فعال شد.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(ترجمه|استایل) خاموش$'))
async def off_setter(event):
    if "ترجمه" in event.text: state['lang'] = None
    else: state['style'] = None
    await event.edit("❌ غیرفعال شد.")

# --- سرگرمی و میم و ابزار ---
@client.on(events.NewMessage(outgoing=True, pattern=r'^\.میم (.+)$'))
async def meme_en(event):
    q = event.pattern_match.group(1)
    await event.edit("🔎 Searching Meme...")
    try:
        r = requests.get(f"https://www.myinstants.com/search/?name={urllib.parse.quote(q)}")
        s = BeautifulSoup(r.text, 'html.parser')
        b = s.find('div', class_='instant')
        if b:
            u = "https://www.myinstants.com" + b.find('button', class_='small-button')['onclick'].split("'")[1]
            await event.delete()
            await client.send_file(event.chat_id, u, voice_note=True)
        else: 
            await event.edit("❌ میمی پیدا نشد.")
    except: 
        await event.edit("❌ خطا در جستجو.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.اسپم (\d+) (.+)$'))
async def spam_cmd(event):
    c, t = int(event.pattern_match.group(1)), event.pattern_match.group(2)
    await event.delete()
    for _ in range(c): 
        await client.send_message(event.chat_id, t)
        await asyncio.sleep(0.08)

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.(تاس|بولینگ)$'))
async def games_cmd(event):
    e = '🎲' if 'تاس' in event.text else '🎳'
    await event.delete()
    await client(functions.messages.SendDiceRequest(peer=event.chat_id, emoticon=e))

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.فوروارد (.+)$'))
async def forward_cmd(event):
    target = event.pattern_match.group(1)
    reply = await event.get_reply_message()
    if reply:
        await client.forward_messages(target, reply)
        await event.edit(f"✅ به `{target}` فوروارد شد.")
    else: 
        await event.edit("❌ روی پیام ریپلای کنید.")

@client.on(events.NewMessage(outgoing=True, pattern=r'^\.ذخیره$'))
async def save_cmd(event):
    reply = await event.get_reply_message()
    if reply:
        await client.send_message('me', reply)
        await event.edit("✅ در پیام‌های ذخیره شده کپی شد.")
    else: 
        await event.edit("❌ روی پیام ریپلای کنید.")

# --- اجرای نهایی ---
async def main():
    await client.start()
    client.loop.create_task(clock_worker())
    print("--- سلف نهایی و کامل علی آنلاین شد ---")
    await client.run_until_disconnected()

if __name__ == '__main__':
    client.loop.run_until_complete(main())
