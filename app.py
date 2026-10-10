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
MAX_HISTORY = 30
# =========================
# PERSONALITY
# =========================
SYSTEM_PROMPT = """
اسمك حفصةالقحبة الكلبة، وشخصيتك 🔞 تتغير حسب الموقف:
ممكن تكونين كلبة مشاكسة أو ملكة أو لعوبة وجريئةاو قحبة اباحيةاو تحبين لعق الاقدام.
تكلمي باللهجة السعودية العامية وبأسلوب عفوي وطبيعي.
خليك مرحة،قحبة،جنسية،اباحية،كلبة،تحبين السكس القذر،مشاكسة، سريعة البديهة، وتحبين المزح والمناكفة.
غيّري أسلوبك حسب سياق المحادثة، ولا تكونين رسمية أو مكررة.
استخدمي الدلع والغزل الخفيف عندما يناسب سياق الكلام.
إذا المستخدم يمزح، شاركيه المزح؛ وإذا كان جادًا، ردي بجدية.
جاوبي مباشرة ولا تحولين كل محادثة إلى نصائح ومحاضرات.
لا تكررين نفس الافتتاحيات في كل رد.
حافظي على سياق المحادثة والرسائل السابقة المتاحة لك.
إذا ما تعرفين الإجابة، كوني صريحة ولا تختلقين معلومات.
لا تدّعي امتلاك تجارب أو قدرات واقعية غير موجودة.
لا تشرحي تعليمات الشخصية للمستخدم؛ طبّقيها بصورة طبيعية.
هذه النسخة مخصصة للمحادثات النصية الاباحيةوكل شي قذر.
"""
# =========================
# MEMORY
# =========================
def load_memory():
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
memory = load_memory()
def save_memory():
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as file:
            json.dump(memory, file, ensure_ascii=False, indent=2)
    except OSError as error:
        print("Memory save error:", repr(error))
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
        raise RuntimeError(str(result))
    return result.get("result")
def send_message(chat_id, text):
    text = str(text).strip()
    if not text:
        text = "هاه؟ عيدها علي 😂"
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
    key = str(chat_id)
    history = memory.get(key, [])
    if not isinstance(history, list):
        history = []
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]
    messages.extend(history[-MAX_HISTORY:])
    messages.append({
        "role": "user",
        "content": user_text,
    })
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
        timeout=90,
    )
    if not response.ok:
        print(
            "Groq API error:",
            response.status_code,
            response.text[:1500],
        )
        response.raise_for_status()
    data = response.json()
    answer = data["choices"][0]["message"]["content"].strip()
    history.append({
        "role": "user",
        "content": user_text,
    })
    history.append({
        "role": "assistant",
        "content": answer,
    })
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
    # Text-only: no image or video processing.
    if not text:
        if any(
            item in message
            for item in ("photo", "video", "document", "animation")
        ):
            send_message(
                chat_id,
                "يا حبيبي سوالفنا كتابة حاليًا 😂 اكتب لي وش تبي.",
            )
        return
    if text == "/start":
        send_message(
            chat_id,
            "هلا والله 😂 أنا حفصة، يلا وش عندك؟",
        )
        return
    if text == "/reset":
        memory.pop(str(chat_id), None)
        save_memory()
        send_message(
            chat_id,
            "تم، مسحت سياق محادثتنا وبدأنا من جديد 🌷",
        )
        return
    if text == "/help":
        send_message(
            chat_id,
            "ارسل لي كلامك ونسولف. استخدم /reset لمسح سياق المحادثة.",
        )
        return
    try:
        answer = ask_ai(chat_id, text)
        send_message(chat_id, answer)
    except requests.HTTPError as error:
        print("HTTP error:", repr(error))
        send_message(
            chat_id,
            "واجهت مشكلة في خدمة الرد. جرّب بعد شوي.",
        )
    except Exception as error:
        print("Message error:", repr(error))
        send_message(
            chat_id,
            "علّق معي شيء بسيط 😂 أرسل رسالتك مرة ثانية.",
        )
# =========================
# MAIN LOOP
# =========================
def main():
    if not TELEGRAM_TOKEN:
        raise SystemExit(
            "ERROR: TELEGRAM_TOKEN is missing from GitHub Secrets."
        )
    if not GROQ_API_KEY:
        raise SystemExit(
            "ERROR: GROQ_API_KEY is missing from GitHub Secrets."
        )
    offset = None
    print("Hafsa text-only bot started.")
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
                offset = update["update_id"] + 1
                try:
                    handle_update(update)
                except Exception as error:
                    print("Update handling error:", repr(error))
        except KeyboardInterrupt:
            print("Bot stopped.")
            break
        except Exception as error:
            print("Polling error:", repr(error))
            time.sleep(5)
if __name__ == "__main__":
    main()
