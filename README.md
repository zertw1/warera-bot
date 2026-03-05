# WarEra Mercenary Tool Bot

This is a Telegram and Discord bot that notifies users about profitable battles in the game WarEra.

## Deploying to Render

This bot is designed to be deployed on [Render](https://render.com/).

### 1. Fork the Repository

Fork this repository to your own GitHub account.

### 2. Create a New Blueprint Instance on Render

1.  Go to the [Render Dashboard](https://dashboard.render.com/) and click "New" -> "Blueprint".
2.  Connect your GitHub account and select the forked repository.
3.  Render will automatically detect the `render.yaml` file and create the following services:
    - A **web service** for the bot.
    - A **PostgreSQL database**.

### 3. Set Environment Variables

After the services are created, go to the "Environment" tab for the `merc-tool-bot` service and add the following environment variables:

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token.
- `DISCORD_BOT_TOKEN`: Your Discord bot token.

Render will automatically inject the `DATABASE_URL` environment variable for the PostgreSQL database.

### 4. Automatic Deploys

Render is configured to automatically deploy new changes pushed to the `main` branch of your repository.
