import os
import logging
from dotenv import load_dotenv
from me_telegram_bot.bot import setup_telegram_bot

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    # Load environment variables
    load_dotenv("config/secrets.env")
    
    # Get Telegram token from environment
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set")
        return
    
    # Setup and run the Telegram bot
    bot = setup_telegram_bot(telegram_token)
    logger.info("DEG Energy Agent started successfully!")
    
    # Start the bot (will run until interrupted)
    bot.run_polling()

if __name__ == "__main__":
    main()