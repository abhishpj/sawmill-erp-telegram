# Sawmill ERP Telegram Bot

This is a production-ready micro-ERP bot for sawmills using Telegram as the UI.
- Natural text input (no slash commands required)
- Automatic parsing via OpenAI
- SQLite/PostgreSQL storage
- Deployable on Render free tier

## Quick Start
1. Create a bot with @BotFather on Telegram and get the token.
2. Deploy this repo on Render or locally with Docker.
3. Set environment variables as per `.env.example`.
4. Set Telegram webhook:
   ```bash
   curl -X POST "https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url":"<PUBLIC_BASE_URL>/tg/webhook","secret_token":"<TELEGRAM_WEBHOOK_SECRET>"}'
   ```
5. Start chatting with your bot!

Example messages:
- "Got 50 logs from Kumar today, about 500 cft"
- "We cut 200 planks size 2x4 from batch 12"
- "Ravi ordered 100 planks of 2x4"