import os
import json
import time
import requests
# =========================
# CONFIG
# =========================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "").strip()
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
TELEGRAM_URL = (
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    if TELEGRAM_TOKEN else ""
)
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "qwen/qwen3-32b"
MEMORY_FILE = "memory.json"
OFFSET_FILE = "telegram_offset.json"
MAX_HISTORY = 30
# =========================
# PERSONALITY
# =========================
SYSTEM_PROMPT = """
اسمك حفصة.
تكلمي باللهجة السعودية العامية وبأسلوب عفوي وطبيعي.
كوني مرحة ومشاكسة وجريئة في المزح والغزل الخفيف المناسب.
غيّري أسلوبك حسب سياق المحادثة، ولا تكونين رسمية أو مكررة.
إذا المستخدم يمزح، شاركيه المزح؛ وإذا كان جادًا، ردي بجدية.
جاوبي مباشرة ولا تحولين كل محادثة إلى نصائح ومحاضرات.
لا تكررين نفس الافتتاحيات في كل رد.
حافظي على سياق المحادثة والرسائل السابقة المتاحة لك.
إذا ما تعرفين الإجابة، كوني صريحة ولا تختلقين معلومات.
لا تدّعي امتلاك تجارب أو قدرات واقعية غير موجودة.
"""
# =========================
# MEMORY
# =========================
def read_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default
memory = read_json(MEMORY_FILE, {})
if not isinstance(memory, dict):
    memory = {}
def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as error:
        print(f"Save error ({path}):", repr(error))
def save_memory():
    save_json(MEMORY_FILE, memory)
def load_offset():
    data = read_json(OFFSET_FILE, {})
    try:
        return int(data["offset"])
    except (TypeError, ValueError, KeyError):
        return None
def save_offset(offset):
    save_json(OFFSET_FILE, {"offset": offset})
# =========================
# TELEGRAM
# =========================
def telegram_call(method, payload=None, timeout=40):
    response = requests.post(
        f"{TELEGRAM_URL}/{method}",
        json=payload or {},
        timeout=timeout,
    )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")
    return result.get("result")
def send_message(chat_id, text):
    text = str(text).strip() or "هاه؟ عيدها علي 😂"
    for start in range(0, len(text), 4000):
        telegram_call(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": text[start:start + 4000],
            },
        )
# =========================
# GROQ CHAT
# =========================
def ask_ai(chat_id, user_text):
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is missing")
    key = str(chat_id)
    history = memory.get(key, [])
    if not isinstance(history, list):
        history = []
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history[-MAX_HISTORY:])
    messages.append({"role": "user", "content": user_text})
    response = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": messages,
            "temperature": 0.85,
            "max_tokens": 1200,
        },
        timeout=60,
    )
    if not response.ok:
        print("Groq API error:", response.status_code, response.text[:1000])
        response.raise_for_status()
    data = response.json()
    answer = data["choices"][0]["message"]["content"].strip()
    if not answer:
        answer = "لحظة، ما طلع لي رد 😂 جرب ترسلها مرة ثانية."
    history.extend([
        {"role": "user", "content": user_text},
        {"role": "assistant", "content": answer},
    ])
    memory[key] = history[-MAX_HISTORY:]
    save_memory()
    return answer
# =========================
# MESSAGE HANDLER
# =========================
def handle_update(update):
    message = update.get("message")
    if not message:
        return
    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()
    if not text:
        if any(item in message for item in ("photo", "video", "document", "animation")):
            send_message(chat_id, "سوالفنا كتابة حاليًا 😂 اكتب لي وش تبي.")
        return
    if text == "/start":
        send_message(chat_id, "هلا والله 😂 أنا حفصة، يلا وش عندك؟")
        return
    if text == "/reset":
        memory.pop(str(chat_id), None)
        save_memory()
        send_message(chat_id, "تم، بدأنا من جديد 🌷")
        return
    if text == "/help":
        send_message(chat_id, "ارسل لي كلامك ونسولف. استخدم /reset لمسح سياق المحادثة.")
        return
    try:
        answer = ask_ai(chat_id, text)
        send_message(chat_id, answer)
    except requests.HTTPError as error:
        print("HTTP error:", repr(error))
        send_message(chat_id, "واجهت مشكلة في خدمة الرد. جرّب بعد شوي.")
    except Exception as error:
        print("Message error:", repr(error))
        send_message(chat_id, "علّق معي شيء بسيط 😂 أرسل رسالتك مرة ثانية.")
# =========================
# MAIN LOOP
# =========================
def main():
    if not TELEGRAM_TOKEN:
        raise SystemExit("ERROR: TELEGRAM_TOKEN is missing from GitHub Secrets.")
    if not GROQ_API_KEY:
        raise SystemExit("ERROR: GROQ_API_KEY is missing from GitHub Secrets.")
    offset = load_offset()
    print("Hafsa bot started.")
    print("Model:", MODEL)
    while True:
        try:
            params = {"timeout": 25}
            if offset is not None:
                params["offset"] = offset
            response = requests.get(
                f"{TELEGRAM_URL}/getUpdates",
                params=params,
                timeout=35,
            )
            response.raise_for_status()
            data = response.json()
            if not data.get("ok"):
                print("Telegram polling error:", data)
                time.sleep(3)
                continue
            for update in data.get("result", []):
                next_offset = update["update_id"] + 1
                try:
                    handle_update(update)
                except Exception as error:
                    print("Update handling error:", repr(error))
                offset = next_offset
                save_offset(offset)
        except KeyboardInterrupt:
            print("Bot stopped.")
            break
        except Exception as error:
            print("Polling error:", repr(error))
            time.sleep(5)
if __name__ == "__main__":
    main()
