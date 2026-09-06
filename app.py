import os
import requests
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

client = Groq(api_key=GROQ_API_KEY)

def is_greeting(text):
    greetings = ["hi", "hello", "hey", "hii", "helloo", "vanakam", "hi sir", "hello sir"]
    return text.lower().strip() in greetings

def is_image_request(text):
    keywords = ["image", "photo", "picture", "generate image", "create image", "draw", "போட்டோ", "படம்", "இமேஜ்"]
    return any(k in text.lower() for k in keywords)

def ask_llama(prompt):
    system_prompt = """
    You are Karthick Sir Bot. Created by Karthick Sir.
    RULES:
    1. Detect user's language and answer in SAME language.
    2. If maths, solve step by step correctly.
    3. Be helpful, friendly, accurate.
    """
    try:
        chat = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        return chat.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def analyze_image(image_url, question="Solve this image"):
    try:
        chat = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{question}. Detect language and answer in same language. If maths, solve step by step."},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
        )
        return chat.choices[0].message.content
    except Exception as e:
        return f"Photo analyze error: {str(e)}"

def send_whatsapp(to, text):
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}}
    requests.post(url, headers=headers, json=data)

def send_whatsapp_image(to, image_url, caption=""):
    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {"link": image_url, "caption": caption}
    }
    requests.post(url, headers=headers, json=data)

@app.route("/webhook", methods=["GET"])
def verify():
    if request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge")
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    try:
        if data and "entry" in data:
            for entry in data["entry"]:
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    messages = value.get("messages", [])
                    for msg in messages:
                        phone = msg["from"]

                        if msg.get("type") == "text":
                            text = msg["text"]["body"]

                            if is_greeting(text):
                                send_whatsapp(phone, "Hello உங்களுக்கு என்ன உதவி வேண்டும்?")

                            elif is_image_request(text):
                                prompt_encoded = requests.utils.quote(text)
                                image_gen_url = f"https://image.pollinations.ai/prompt/{prompt_encoded}"
                                send_whatsapp_image(phone, image_gen_url, f"Here is your image for: {text}")
                                send_whatsapp(phone, ask_llama(text))

                            else:
                                reply = ask_llama(text)
                                send_whatsapp(phone, reply)

                        elif msg.get("type") == "image":
                            image_id = msg["image"]["id"]
                            media_url = f"https://graph.facebook.com/v20.0/{image_id}"
                            headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
                            r = requests.get(media_url, headers=headers).json()
                            img_url = r.get("url")
                            img_data = requests.get(img_url, headers=headers).url
                            result = analyze_image(img_data, "Solve this problem accurately step by step")
                            send_whatsapp(phone, result)

    except Exception as e:
        print(f"Error: {e}")

    return jsonify({"status": "ok"}), 200

@app.route("/")
def home():
    return "Karthick Sir Bot Running"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
