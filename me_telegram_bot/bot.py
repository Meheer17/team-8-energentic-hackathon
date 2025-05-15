import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
import google.generativeai as genai
import os
from dotenv import load_dotenv

from .handlers import (
    handle_start,
    handle_help,
    handle_text_message,
    handle_solar_onboarding_callback,
    handle_photo_message,
    handle_energy_services_callback,
    handle_unknown_callback
)

logger = logging.getLogger(__name__)
# Load environment variables from .env file
load_dotenv("config/secrets.env")

genai.configure(api_key=os.environ["GOOGLE_API_KEY"])


def setup_telegram_bot(token):
    """Create and configure the Telegram bot application."""
    
    # Create the application instance
    application = Application.builder().token(token).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", handle_start))
    application.add_handler(CommandHandler("help", handle_help))
    
    # Register message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo_message))

    # Register callback query handlers
    application.add_handler(CallbackQueryHandler(handle_solar_onboarding_callback, pattern="^solar_onboarding:"))
    application.add_handler(CallbackQueryHandler(handle_energy_services_callback, pattern="^energy_services:"))
    application.add_handler(CallbackQueryHandler(handle_unknown_callback))
    
    # Log errors
    application.add_error_handler(error_handler)
    
    return application

async def error_handler(update, context):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error: {context.error}")
    # Notify user about the error
    if update:
        if update.message:
            await update.message.reply_text("Sorry, something went wrong. Please try again later.")
        elif update.callback_query:
            await update.callback_query.message.reply_text("Sorry, something went wrong. Please try again later.")
