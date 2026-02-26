#!/usr/bin/env python3
"""Ask Ludi - Telegram bot for Ludi Lens v2.0 analytics."""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path so imports like 'from config import ...' work
# when running as standalone script (e.g., python bots/ask_ludi.py or via launchd)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import TELEGRAM_TOKEN
from bots import ask_ludi_handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

ALLOWED_CHAT_IDS = os.getenv("ASK_LUDI_ALLOWED_CHAT_IDS", "").split(",")


def _auth_filter(update: Update) -> bool:
    """Check if user is authorized to use the bot."""
    if not ALLOWED_CHAT_IDS or "" in ALLOWED_CHAT_IDS:
        return True
    chat_id = str(update.effective_chat.id)
    return chat_id in ALLOWED_CHAT_IDS


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if not _auth_filter(update):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    await update.message.reply_text(
        "Welcome to Ask Ludi! 🏀\n\n"
        "I can answer questions about NBA injuries, betting edges, trends, "
        "schedule, standings, and more.\n\n"
        "Try asking: \"Who is out tonight?\" or \"Show me today's edges\""
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    if not _auth_filter(update):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    await update.message.reply_text(
        "**Ask Ludi Commands:**\n\n"
        "/start - Welcome message\n"
        "/help - Show this help message\n\n"
        "**Example Questions:**\n"
        "• Who is out tonight?\n"
        "• Show me today's edges\n"
        "• What's the schedule?\n"
        "• Top of the standings?\n"
        "• Recent trends for Jokic"
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors."""
    logger.error(f"Error handling update: {context.error}")
    if update and update.message:
        await update.message.reply_text("Something went wrong. Please try again.")


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming messages."""
    if not _auth_filter(update):
        await update.message.reply_text("You are not authorized to use this bot.")
        return
    await ask_ludi_handlers.handle_message(update, context)


def main() -> None:
    """Main entry point for the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN not configured in .env")
        print("Error: TELEGRAM_TOKEN not configured in .env")
        return
    
    logger.info("Starting Ask Ludi bot...")

    # Python 3.14 removed implicit event loop creation in asyncio.get_event_loop().
    # python-telegram-bot v21.x relies on it internally, so we create one explicitly.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_error_handler(error_handler)

    logger.info("Bot initialized. Starting polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
