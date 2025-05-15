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
        
        # Notify user about the error based on update type
        if update:
            if update.message:
                # If error occurred in a regular message
                await update.message.reply_text("Sorry, something went wrong. Please try again later.")
            elif update.callback_query:
                # If error occurred in a callback query
                await update.callback_query.answer("Sorry, something went wrong.")
                try:
                    await update.callback_query.edit_message_text(
                        "Sorry, something went wrong. Please use /start to restart.",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("Start Over", callback_data="start_over")
                        ]])
                    )
                except Exception:
                    pass  # If editing fails, we already showed an alert