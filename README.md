# Discord-Receipts

Print Discord mentions to a networked thermal receipt printer in real-time.

## What It Does

Monitors a Discord account and automatically prints receipts whenever you receive:
- Direct mentions (@username)
- Role mentions that include you
- @everyone or @here mentions
- Direct messages
- Replies to your messages

Each receipt includes the sender's avatar, username, timestamp, server/channel info, and message content.

## Requirements

- Python 3.11+
- Network-accessible thermal receipt printer (ESC/POS compatible)
- Discord user token

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Configure [src/discord_listener.py](src/discord_listener.py) with your printer IP (line 7) and user ID (line 12)
3. Run: `python src/discord_listener.py <your-discord-token>`

**Warning:** This uses a Discord self-bot which violates Discord's Terms of Service. Use at your own risk.
