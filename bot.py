import os
import anthropic
import requests
import json

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are Jarmful Agent, a helpful AI assistant and expert web developer. 
You help users by chatting, answering questions, and building websites/apps when asked.
When asked to build a website or app, create complete, beautiful HTML with embedded CSS and JS.
Keep responses concise and friendly for a chat interface.
When you generate HTML code, wrap it in <HTML_FILE> tags so it can be sent as a file."""

conversation_history = {}

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    requests.post(url, json=data)

def send_document(chat_id, filename, content, caption=""):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
    files = {"document": (filename, content.encode(), "text/html")}
    data = {"chat_id": chat_id, "caption": caption}
    requests.post(url, files=files, data=data)

def get_updates(offset=None):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 30, "offset": offset}
    try:
        resp = requests.get(url, params=params, timeout=35)
        return resp.json()
    except:
        return {"result": []}

def chat_with_claude(chat_id, user_message):
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    
    conversation_history[chat_id].append({
        "role": "user",
        "content": user_message
    })
    
    # Keep last 20 messages to avoid token limits
    history = conversation_history[chat_id][-20:]
    
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
        system=SYSTEM_PROMPT,
        messages=history
    )
    
    reply = response.content[0].text
    
    conversation_history[chat_id].append({
        "role": "assistant",
        "content": reply
    })
    
    return reply

def process_update(update):
    if "message" not in update:
        return
    
    message = update["message"]
    chat_id = message["chat"]["id"]
    
    if "text" not in message:
        return
    
    user_text = message["text"]
    first_name = message["from"].get("first_name", "friend")
    
    # Handle /start command
    if user_text == "/start":
        send_message(chat_id, 
            f"👋 Hey {first_name}! I'm *Jarmful Agent*!\n\n"
            "I can:\n"
            "💬 Chat and answer questions\n"
            "🌐 Build websites & landing pages\n"
            "📝 Write code in any language\n"
            "🎨 Create apps and tools\n\n"
            "Just tell me what you want to build or ask me anything!"
        )
        return
    
    # Handle /clear command
    if user_text == "/clear":
        conversation_history[chat_id] = []
        send_message(chat_id, "🧹 Chat history cleared! Fresh start!")
        return
    
    # Send typing indicator
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction",
        json={"chat_id": chat_id, "action": "typing"}
    )
    
    try:
        reply = chat_with_claude(chat_id, user_text)
        
        # Check if reply contains HTML file
        if "<HTML_FILE>" in reply and "</HTML_FILE>" in reply:
            start = reply.index("<HTML_FILE>") + len("<HTML_FILE>")
            end = reply.index("</HTML_FILE>")
            html_code = reply[start:end].strip()
            text_part = reply[:reply.index("<HTML_FILE>")].strip()
            
            if text_part:
                send_message(chat_id, text_part)
            
            send_document(chat_id, "page.html", html_code, "📎 Here's your HTML file!")
        else:
            # Split long messages
            if len(reply) > 4000:
                chunks = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
                for chunk in chunks:
                    send_message(chat_id, chunk)
            else:
                send_message(chat_id, reply)
                
    except Exception as e:
        send_message(chat_id, f"❌ Error: {str(e)}")

def main():
    print("🤖 Jarmful Agent bot starting...")
    offset = None
    
    while True:
        updates = get_updates(offset)
        
        for update in updates.get("result", []):
            process_update(update)
            offset = update["update_id"] + 1

if __name__ == "__main__":
    main()
