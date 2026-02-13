"""
Quick script to get your Telegram chat ID
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    print("❌ TELEGRAM_BOT_TOKEN not found in .env")
    exit(1)

print("🔍 Fetching your chat ID...")
print("\n📱 First, send a message to @Hrvestbot on Telegram")
print("   (Just send /start or any message)\n")

input("Press Enter after you've sent a message to the bot...")

# Get updates
url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
response = requests.get(url)
data = response.json()

if not data.get("ok"):
    print(f"❌ Error: {data}")
    exit(1)

if not data.get("result"):
    print("❌ No messages found!")
    print("   Make sure you sent a message to @Hrvestbot first")
    exit(1)

# Get the latest message
latest_message = data["result"][-1]
chat_id = latest_message["message"]["chat"]["id"]
username = latest_message["message"]["chat"].get("username", "Unknown")
first_name = latest_message["message"]["chat"].get("first_name", "Unknown")

print("\n✅ Found your chat!")
print(f"   Name: {first_name}")
print(f"   Username: @{username}")
print(f"   Chat ID: {chat_id}")
print(f"\n📝 Add this to your .env file:")
print(f"   TELEGRAM_CHAT_ID={chat_id}")
print()
