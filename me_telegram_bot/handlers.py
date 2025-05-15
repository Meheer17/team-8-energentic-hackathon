import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from telegram.ext import ContextTypes
from datetime import datetime, date, timedelta  # Make sure timedelta is included
from me_telegram_bot.keyboards import (
    get_main_menu_keyboard,
    get_solar_onboarding_keyboard,
    get_subsidy_options_keyboard,
    get_installer_options_keyboard,
    get_financing_options_keyboard,
    get_back_to_main_keyboard,
    get_confirm_cancel_keyboard
)
from db.user_sessions import get_user_session, update_user_session
from agents.solar_onboarding_agent import solar_agent
from agents.prosumer_energy_agent import prosumer_agent
from langchain_modules.image_classifier import rooftop_analyzer

logger = logging.getLogger(__name__)

# Start command handler
async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the /start command is issued."""
    user = update.effective_user
    # Initialize user session if needed
    user_id = str(user.id)
    user_session = get_user_session(user_id)
    if not user_session:
        update_user_session(user_id, {"state": "new_user"})

    # Welcome message
    welcome_message = (
        f"👋 Hi {user.first_name}! Welcome to the DEG Energy Agent.\n\n"
        f"I can help you with:\n\n"
        f"1️⃣ *Onboard for Rooftop Solar*: Find subsidies, check eligibility, connect with installers\n\n"
        f"2️⃣ *Use My Installed System*: Sell excess energy, participate in demand response, earn with NFTs\n\n"
        "What would you like to do today?"
    )

    # Send message with main menu keyboard
    await update.message.reply_markdown(
        welcome_message,
        reply_markup=get_main_menu_keyboard()
    )

async def handle_unknown_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown callback queries."""
    query = update.callback_query
    await query.answer()  # Answer the callback query to remove the loading state
    
    # Check if the callback data is "solar_onboarding:back_to_main"
    if query.data == "solar_onboarding:back_to_main":
        # Forward to the start command handler
        user = update.effective_user
        if user:
            # Create a new context for the start command
            await handle_start(update, context)
            return
    
    # For all other unknown callbacks, provide a helpful message
    try:
        await query.edit_message_text(
            "Sorry, I couldn't process that request. Please try again or use the button below to return to the main menu.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Return to Main Menu", callback_data="solar_onboarding:back_to_main")]
            ])
        )
    except Exception as e:
        # Fallback if editing the message fails
        logger.error(f"Error handling unknown callback: {e}")
        if update.effective_chat:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="Sorry, I encountered an error. Please use /start to begin again.",
                reply_markup=get_main_menu_keyboard()
            )

# Help command handler
async def handle_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a helpful message when the /help command is issued."""
    help_text = (
        "*DEG Energy Agent Help*\n\n"
        "Here are the commands you can use:\n\n"
        "• /start - Start or restart the bot\n"
        "• /help - Show this help message\n\n"
        "You can also use the menu buttons to navigate and access different features."
    )

    await update.message.reply_markdown(help_text)

# Text message handler
async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process text messages based on the current user state."""
    user_id = str(update.effective_user.id)
    user_session = get_user_session(user_id)
    text = update.message.text

    # Default response if we can't determine the user's state
    if not user_session or "state" not in user_session:
        await update.message.reply_text(
            "I'm not sure what you're looking for. Please use the /start command to begin.",
            reply_markup=get_main_menu_keyboard()
        )
        return

    # Handle different user states
    state = user_session["state"]

    if state == "solar_onboarding_address":
        # User is providing their address for solar onboarding
        await update.message.reply_text("Processing your address...")

        # Save address and update state
        update_user_session(user_id, {"address": text, "state": "solar_onboarding_electricity_bill"})

        await update.message.reply_text(
            "Thanks for providing your address. Next, please send me your monthly electricity consumption in kWh "
            "or upload a photo of your electricity bill."
        )

    elif state == "solar_onboarding_electricity_bill":
        # User is providing electricity consumption information
        try:
            # Try to parse as a number
            consumption = float(text.replace("kWh", "").strip())
            update_user_session(user_id, {"electricity_consumption": consumption, "state": "solar_onboarding_confirm"})

            # Show confirmation keyboard
            confirm_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Continue", callback_data="solar_onboarding:confirm")],
                [InlineKeyboardButton("❌ Cancel", callback_data="solar_onboarding:cancel")]
            ])

            await update.message.reply_text(
                f"I've recorded your monthly consumption as {consumption} kWh. "
                f"Now I can check what solar options are available for you. "
                f"Shall we proceed?",
                reply_markup=confirm_keyboard
            )
        except ValueError:
            # Not a number, ask again
            await update.message.reply_text(
                "Please enter your monthly electricity consumption as a number in kWh. "
                "For example: 350 kWh"
            )

    elif state == "energy_services_auto_trading_config":
        # User is providing auto-trading configuration information
        lines = text.split('\n')
        config = {}

        for line in lines:
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower().replace(' ', '_')
                value = value.strip()

                if key == 'min_sell_price' or key == 'max_buy_price':
                    try:
                        config[f"{key}_kwh"] = float(value.replace('$', ''))
                    except ValueError:
                        pass
                elif key == 'optimization_target':
                    if 'financial' in value.lower():
                        config['ai_optimization_target'] = 'financial'
                    elif 'environment' in value.lower():
                        config['ai_optimization_target'] = 'environmental'
                    else:
                        config['ai_optimization_target'] = 'balanced'
                elif key == 'reserve_capacity':
                    try:
                        config['reserve_capacity_pct'] = float(value.replace('%', ''))
                    except ValueError:
                        pass
                elif key == 'neighbor_sharing' and ('yes' in value.lower() or 'enable' in value.lower()):
                    config['neighbor_sharing_enabled'] = True
                elif key == 'token_rewards' and ('yes' in value.lower() or 'enable' in value.lower()):
                    config['token_rewards'] = True

        # Enable auto-trading with the provided config
        result = prosumer_agent.enable_auto_trading(user_id, config)
        update_user_session(user_id, {"auto_trading": result, "state": "energy_services_auto_trading_enabled"})

        # Format the result for display
        settings = result.get('settings', {})

        response = (
            "✅ *Auto-Trading Enabled!*\n\n"
            f"*Settings:*\n"
            f"• Min. selling price: ${settings.get('min_sell_price_kwh', 0.12)}/kWh\n"
            f"• Max. buying price: ${settings.get('max_buy_price_kwh', 0.08)}/kWh\n"
            f"• Optimization target: {settings.get('ai_optimization_target', 'balanced').capitalize()}\n"
            f"• Reserve capacity: {settings.get('reserve_capacity_pct', 20)}%\n"
            f"• Neighbor sharing: {'Enabled' if settings.get('neighbor_sharing_enabled', True) else 'Disabled'}\n"
            f"• Token rewards: {'Enabled' if settings.get('token_rewards', True) else 'Disabled'}\n\n"
            f"*Estimated monthly benefit: ${result.get('estimated_monthly_benefit_usd', 0.0)}*\n\n"
            f"I'll now automatically trade energy for you based on these preferences! You can check your earnings anytime."
        )

        await update.message.reply_markdown(
            response,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📈 Run Trading Simulation", callback_data="energy_services:run_simulation")],
                [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
            ])
        )

    else:
        # Default response for other states
        await update.message.reply_text(
            "To navigate through the available options, please use the menu below.",
            reply_markup=get_main_menu_keyboard()
        )

# Callback handlers
async def handle_solar_onboarding_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callbacks related to solar onboarding process."""
    query = update.callback_query
    await query.answer()  # Answer the callback query to remove the loading state

    user_id = str(update.effective_user.id)
    callback_data = query.data.split(":")

    if len(callback_data) < 2:
        await handle_unknown_callback(update, context)
        return

    action = callback_data[1]

    if action == "start":
        # Start the solar onboarding flow
        update_user_session(user_id, {"state": "solar_onboarding_address"})

        await query.edit_message_text(
            "Great choice! Let's start your solar onboarding process. 🌞\n\n"
            "First, I'll need your address to check solar potential and available subsidies in your area. "
            "Please provide your complete address."
        )

    elif action == "confirm":
        # User confirmed their information, now we'll show them options
        user_session = get_user_session(user_id)
        address = user_session.get("address", "Unknown")
        consumption = user_session.get("electricity_consumption", "Unknown")

        # Update state to indicate we're moving to options
        update_user_session(user_id, {"state": "solar_onboarding_options"})

        # Start searching for subsidies and installers in the background
        #subsidies = solar_agent.search_subsidies(user_id)
        #installers = solar_agent.search_installers(user_id)
        
        # Show options to the user
        options_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search Subsidies", callback_data="solar_onboarding:search_subsidies")],
            [InlineKeyboardButton("🏪 Find Installers", callback_data="solar_onboarding:find_installers")],
            [InlineKeyboardButton("🛒 Buy Solar Panels", callback_data="solar_onboarding:find_products")],
            [InlineKeyboardButton("🧮 Calculate ROI", callback_data="solar_onboarding:calc_roi")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="solar_onboarding:back_to_main")]
        ])

        await query.edit_message_text(
            f"Thanks for the information! I've recorded:\n\n"
            f"📍 *Address*: {address}\n"
            f"⚡ *Monthly Consumption*: {consumption} kWh\n\n"
            f"Now, what would you like to do next?",
            parse_mode="Markdown",
            reply_markup=options_keyboard
        )

    elif action == "search_subsidies":
        # Show available subsidies
        user_session = get_user_session(user_id)
        subsidies = []#user_session.get("subsidies", [])        
        # If subsidies weren't loaded yet, load them now
        if not subsidies:
            subsidies = solar_agent.search_subsidies(user_id)

        if not subsidies:
            await query.edit_message_text(
                "I couldn't find any subsidies at the moment. Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")]
                ])
            )
            return

        # Format the subsidies for display
        subsidies_text = "Here are the available subsidies for your area:\n\n"
        subsidy_buttons = []
        for i, subsidy in enumerate(subsidies[:3]):  # Show top 3 subsidies
            provider_name = subsidy.get("provider_name", "Unknown Provider")
            name = subsidy.get("name", "Unknown Subsidy")
            description = subsidy.get("description", "")
            price = subsidy.get("price", "0")
            currency = subsidy.get("currency", "USD")
            fulfillment_id = subsidy.get("fulfillment_id", "615")
            subsidies_text += f"*{i+1}. {name}*\n"
            subsidies_text += f"Provider: {provider_name}\n"
            subsidies_text += f"Description: {description}\n"
            if price != "0":
                subsidies_text += f"Value: {price} {currency}\n"
            subsidies_text += "\n"
            # Add a button for each subsidy
            subsidy_buttons.append([
                InlineKeyboardButton(
                    f"Apply for {name}", 
                    callback_data=f"solar_onboarding:apply_subsidy:{subsidy.get('provider_id')}:{subsidy.get('id')}:{subsidy.get("fulfillment_id", "615")}"
                )
            ])

        # Add a back button
        subsidy_buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")])
        subsidies_keyboard = InlineKeyboardMarkup(subsidy_buttons)

        await query.edit_message_text(
            subsidies_text,
            parse_mode="Markdown",
            reply_markup=subsidies_keyboard
        )

    elif action == "find_installers":
        # Show available installers
        user_session = get_user_session(user_id)
        installers = user_session.get("installers", [])

        # If installers weren't loaded yet, load them now
        if not installers:
            installers = solar_agent.search_installers(user_id)

        if not installers:
            await query.edit_message_text(
                "I couldn't find any installers at the moment. Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")]
                ])
            )
            return

        # Format the installers for display
        installers_text = "Here are the recommended solar installers in your area:\n\n"

        installer_buttons = []
        for i, installer in enumerate(installers[:3]):  # Show top 3 installers
            name = installer.get("name", "Unknown Installer")
            short_desc = installer.get("short_desc", "")

            installers_text += f"*{i+1}. {name}*\n"
            installers_text += f"Description: {short_desc}\n"

            # Show services if available
            services = installer.get("services", [])
            if services:
                installers_text += "Services:\n"
                for service in services[:2]:  # Show only first 2 services
                    service_name = service.get("name", "Unknown Service")
                    service_price = service.get("price", "0")
                    service_currency = service.get("currency", "USD")
                    installers_text += f"- {service_name}: {service_price} {service_currency}\n"

            installers_text += "\n"

            # Add a button for each installer with their first service
            if services:
                installer_buttons.append([
                    InlineKeyboardButton(
                        f"Select {name}",
                        callback_data=f"solar_onboarding:select_installer:{installer.get('id')}:{services[0].get('id')}"
                    )
                ])

        # Add a back button
        installer_buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")])
        installers_keyboard = InlineKeyboardMarkup(installer_buttons)

        await query.edit_message_text(
            installers_text,
            parse_mode="Markdown",
            reply_markup=installers_keyboard
        )

    elif action == "calc_roi":
        # Calculate and show ROI
        roi_data = solar_agent.estimate_roi(user_id)

        roi_text = (
            "📊 *Solar Investment Analysis*\n\n"
            f"System Size: {roi_data['estimated_system_size_kw']} kW\n"
            f"System Cost: ${roi_data['estimated_cost_usd']:,.2f}\n\n"
            f"Annual Production: {roi_data['estimated_annual_production_kwh']:,} kWh\n"
            f"Annual Savings: ${roi_data['estimated_annual_savings_usd']:,.2f}\n\n"
            f"Payback Period: {roi_data['estimated_payback_years']} years\n"
            f"20-Year ROI: {roi_data['estimated_roi_20_year_percent']}%\n\n"
            "Ready to take the next step toward energy independence?"
        )

        roi_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏪 Find Installers", callback_data="solar_onboarding:find_installers")],
            [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")]
        ])

        await query.edit_message_text(
            roi_text,
            parse_mode="Markdown",
            reply_markup=roi_keyboard
        )

    elif action == "apply_subsidy" and len(callback_data) >= 4:
        # User is applying for a specific subsidy
        provider_id = callback_data[2]
        subsidy_id = callback_data[3]
        fulfillment_id = callback_data[4]
        # Update state
        update_user_session(user_id, {
            "state": "solar_onboarding_applying_subsidy",
            "selected_provider": provider_id,
            "selected_subsidy": subsidy_id
        })

        # Show confirmation to the user
        await query.edit_message_text(
            "Great! Let's apply for this subsidy. I'll need to collect some information.\n\n"
            "Would you like to confirm your application with the information you've already provided?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Confirm Application", callback_data=f"solar_onboarding:confirm_subsidy:{provider_id}:{subsidy_id}:{fulfillment_id}")],
                [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:search_subsidies")]
            ])
        )

    elif action == "confirm_subsidy" and len(callback_data) >= 4:
        # User confirmed subsidy application
        provider_id = callback_data[2]
        subsidy_id = callback_data[3]
        fulfillment_id = callback_data[4]
       
        # Get user info
        user_session = get_user_session(user_id)
        user_name = update.effective_user.first_name

        # Default contact info (in real app, would collect this)
        customer_info = {
            "person": {
                "name": user_name
            },
            "contact": {
                "phone": "876756454",  # Example phone
                "email": f"{user_name}@example.com"  # Example email
            }
        }

        # Submit the subsidy application using Beckn

        order_confirmation = solar_agent.confirm_order(user_id, provider_id, subsidy_id, fulfillment_id, customer_info)
        if order_confirmation and "id" in order_confirmation:
            # Store the order ID
            update_user_session(user_id, {
                "state": "solar_onboarding_subsidy_confirmed",
                "subsidy_order_id": order_confirmation["id"]
            })

            await query.edit_message_text(
                "✅ *Subsidy Application Submitted!*\n\n"
                f"Order ID: `{order_confirmation['id']}`\n\n"
                "Your application has been received and is being processed. "
                "You'll be notified once it's approved.\n\n"
                "Would you like to find solar panels and installers now?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔍 Find Solar Products", callback_data="solar_onboarding:find_products")],
                    [InlineKeyboardButton("🏪 Find Installers", callback_data="solar_onboarding:find_installers")],
                    [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="solar_onboarding:back_to_main")]
                ])
            )
        else:
            await query.edit_message_text(
                "❌ There was a problem submitting your subsidy application. Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:search_subsidies")]
                ])
            )

    elif action == "select_installer" and len(callback_data) >= 4:
        # User is selecting a specific installer and service
        provider_id = callback_data[2]
        service_id = callback_data[3]

        # Update state
        update_user_session(user_id, {
            "state": "solar_onboarding_selecting_installer",
            "selected_installer": provider_id,
            "selected_service": service_id
        })

        # Select the service using Beckn
        selection = solar_agent.select_service(user_id, provider_id, service_id)

        if selection:
            # Show service details and confirmation
            service_name = selection.get("item", {}).get("descriptor", {}).get("name", "Solar Installation Service")
            provider_name = selection.get("provider", {}).get("descriptor", {}).get("name", "Solar Installer")

            # Get price from quote
            price = "N/A"
            currency = "USD"
            if "quote" in selection and "price" in selection["quote"]:
                price = selection["quote"]["price"].get("value", "N/A")
                currency = selection["quote"]["price"].get("currency", "USD")

            await query.edit_message_text(
                f"You've selected *{service_name}* from *{provider_name}*.\n\n"
                f"Price: {price} {currency}\n\n"
                "Would you like to proceed with scheduling an installation consultation?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Schedule Consultation", callback_data=f"solar_onboarding:init_order:{provider_id}:{service_id}")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:find_installers")]
                ])
            )
        elif action == "select_product" and len(callback_data) >= 4:
            # Forward to the solar retail handler
            await handle_solar_retail_callback(update, context)
        
        elif action == "init_product" and len(callback_data) >= 4:
            # Initialize the order for the selected product
            provider_id = callback_data[2]
            product_id = callback_data[3]
            
            # Call the Beckn init API
            init_response = solar_agent.init_solar_product_order(user_id, provider_id, product_id)
            
            if init_response and "order" in init_response:
                # Update state
                update_user_session(user_id, {
                    "state": "solar_onboarding_init_product",
                    "product_init": {"provider_id": provider_id, "product_id": product_id}
                })
                
                # Show order summary and confirmation
                await query.edit_message_text(
                    "Your product order has been initialized!\n\n"
                    "To complete your purchase, I'll need to collect your contact and delivery information.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("📝 Provide Delivery Info", callback_data=f"solar_onboarding:provide_delivery_info:{provider_id}:{product_id}")],
                        [InlineKeyboardButton("⬅️ Back", callback_data=f"solar_onboarding:select_product:{provider_id}:{product_id}")]
                    ])
                )
            else:
                await query.edit_message_text(
                    "There was a problem initializing your order. Please try again later.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Back", callback_data=f"solar_onboarding:select_product:{provider_id}:{product_id}")]
                    ])
                )
        
        elif action == "provide_delivery_info" and len(callback_data) >= 4:
            # User is providing delivery info for product order
            provider_id = callback_data[2]
            product_id = callback_data[3]
            user_name = update.effective_user.first_name
            user_session = get_user_session(user_id)
            address = user_session.get("address", "Default Address")

            customer_info = {
                "person": {
                    "name": user_name
                },
                "contact": {
                    "phone": "876756454",  # Example phone
                    "email": f"{user_name}@example.com"  # Example email
                },
                "delivery": {
                    "address": address
                }
            }
            
            # Call the Beckn confirm API
            confirm_response = solar_agent.confirm_solar_product_order(user_id, provider_id, product_id, customer_info)
            
            if confirm_response and "order" in confirm_response:
                order_id = confirm_response["order"]["id"]
                
                # Store the order ID
                update_user_session(user_id, {
                    "state": "solar_onboarding_product_confirmed",
                    "product_order_id": order_id
                })
                
                await query.edit_message_text(
                    "✅ *Solar Panel System Purchase Confirmed!*\n\n"
                    f"Order ID: `{order_id}`\n\n"
                    "Your solar panel system has been ordered and will be delivered to your address. "
                    "Would you like to schedule an installation with one of our certified installers?",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏪 Find Installers", callback_data="solar_onboarding:find_installers")],
                        [InlineKeyboardButton("📊 View Solar Summary", callback_data="solar_onboarding:view_summary")],
                        [InlineKeyboardButton("🏠 Return to Main Menu", callback_data="solar_onboarding:back_to_main")]
                    ])
                )
            else:
                await query.edit_message_text(
                    "❌ There was a problem confirming your order. Please try again later.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("⬅️ Back", callback_data=f"solar_onboarding:init_product:{provider_id}:{product_id}")]
                    ])
                )
        
        else:
            await query.edit_message_text(
                "There was a problem selecting this service. Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:find_installers")]
                ])
            )

    elif action == "init_order" and len(callback_data) >= 4:
        # Initialize the order for the selected installer service
        provider_id = callback_data[2]
        service_id = callback_data[3]
        
        # Initialize the order using Beckn
        order_init = solar_agent.initialize_order(user_id, provider_id, service_id)

        if order_init:
            # Update state
            update_user_session(user_id, {
                "state": "solar_onboarding_init_order",
                "order_init": order_init
            })

            # Show order summary and confirmation
            await query.edit_message_text(
                "Your installation consultation has been initialized!\n\n"
                "To complete your order, I'll need to collect your contact information.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 Provide Contact Info", callback_data=f"solar_onboarding:provide_contact:{provider_id}:{service_id}")],
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"solar_onboarding:select_installer:{provider_id}:{service_id}")]
                ])
            )
        else:
            await query.edit_message_text(
                "There was a problem initializing your order. Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"solar_onboarding:select_installer:{provider_id}:{service_id}")]
                ])
            )

    elif action == "provide_contact" and len(callback_data) >= 4:
        # User is providing contact info for installation order
        provider_id = callback_data[2]
        service_id = callback_data[3]

        # In a real app, we would collect this info via form
        # Here we'll use example data for demonstration
        user_name = update.effective_user.first_name

        customer_info = {
            "person": {
                "name": user_name
            },
            "contact": {
                "phone": "876756454",  # Example phone
                "email": f"{user_name}@example.com"  # Example email
            }
        }

        # Update state with contact info
        update_user_session(user_id, {
            "state": "solar_onboarding_confirming_order",
            "contact_info": customer_info
        })

        # Confirm the order using Beckn
        order_confirmation = solar_agent.confirm_order(
            user_id, provider_id, service_id, "617", customer_info
        )

        if order_confirmation and "id" in order_confirmation:
            # Store the order ID
            update_user_session(user_id, {
                "state": "solar_onboarding_order_confirmed",
                "installation_order_id": order_confirmation["id"]
            })

            await query.edit_message_text(
                "✅ *Installation Consultation Confirmed!*\n\n"
                f"Order ID: `{order_confirmation['id']}`\n\n"
                "Your installation consultation has been scheduled. "
                "The installer will contact you soon to coordinate the details.\n\n"
                "Congratulations on taking this important step toward energy independence!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 View Solar Summary", callback_data="solar_onboarding:view_summary")],
                    [InlineKeyboardButton("🏠 Return to Main Menu", callback_data="solar_onboarding:back_to_main")]
                ])
            )
        else:
            await query.edit_message_text(
                "❌ There was a problem confirming your installation consultation. Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"solar_onboarding:init_order:{provider_id}:{service_id}")]
                ])
            )

    elif action == "find_products":
        # Forward to the solar retail handler
        # Instead of modifying the callback data, we'll directly call the handler with the search_products action
        user_id = str(update.effective_user.id)
        user_session = get_user_session(user_id)
        products = []
        
        # Search for solar panel products
        search_response = solar_agent.search_solar_products(user_id)
        print("--------------------------")
        print(search_response)
        print("--------------------------")
        # Process the search response
        if isinstance(search_response, list):
            products = search_response
        elif isinstance(search_response, dict) and "catalog" in search_response:
            for provider in search_response.get("catalog", {}).get("providers", []):
                for item in provider.get("items", []):
                    if "solar" in item.get("descriptor", {}).get("name", "").lower():
                        products.append({
                            "id": item.get("id", ""),
                            "provider_id": provider.get("id", ""),
                            "provider_name": provider.get("descriptor", {}).get("name", "Unknown Provider"),
                            "name": item.get("descriptor", {}).get("name", "Unknown Product"),
                            "description": item.get("descriptor", {}).get("short_desc", ""),
                            "price": item.get("price", {}).get("value", "0"),
                            "currency": item.get("price", {}).get("currency", "USD"),
                            "image": item.get("descriptor", {}).get("images", [{}])[0].get("url", "")
                        })
        
        # Store the processed products in the user session
        update_user_session(user_id, {"products": products})
        
        if not products:
            await query.edit_message_text(
                "I couldn't find any solar products at the moment. Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")]
                ])
            )
            return

        # Format the products for display
        products_text = "🌞 *Recommended Solar Panel Systems*\n\n"
        
        product_buttons = []
        for i, product in enumerate(products[:3]):  # Show top 3 products
            name = product.get("name", "Unknown Product")
            description = product.get("description", "")
            price = product.get("price", "0")
            currency = product.get("currency", "USD")
            provider_name = product.get("provider_name", "Unknown Provider")
            
            products_text += f"*{i+1}. {name}*\n"
            products_text += f"Provider: {provider_name}\n"
            products_text += f"Description: {description}\n"
            products_text += f"Price: {price} {currency}\n\n"

            # Add a button for each product
            product_buttons.append([
                InlineKeyboardButton(

                    f"Select {name}", 
                    callback_data=f"solar_retail:select_product:{product.get('provider_id')}:{product.get('id')}"
                )
            ])

        # Add a back button
        product_buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")])
        products_keyboard = InlineKeyboardMarkup(product_buttons)

        await query.edit_message_text(
            products_text,
            parse_mode="Markdown",
            reply_markup=products_keyboard
        )

    elif action == "view_summary":
        # Generate and show a summary of the user's solar journey
        summary = solar_agent.generate_summary(user_id)

        await query.edit_message_text(
            summary,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏠 Return to Main Menu", callback_data="solar_onboarding:back_to_main")]
            ])
        )

    elif action == "back_to_main":
            # Return to the main menu - don't use handle_start as it's designed for direct messages
            welcome_message = (
                f"👋 Hi {update.effective_user.first_name}! Welcome to the DEG Energy Agent.\n\n"
                f"I can help you with:\n\n"
                f"1️⃣ *Onboard for Rooftop Solar*: Find subsidies, check eligibility, connect with installers\n\n"
                f"2️⃣ *Use My Installed System*: Sell excess energy, participate in demand response, earn with NFTs\n\n"
                f"What would you like to do today?"
            )
        
            # Send message with main menu keyboard by editing the current message
            await query.edit_message_text(
                welcome_message,
                reply_markup=get_main_menu_keyboard(),
                parse_mode="Markdown"
            )

    else:
        # Handle unknown action
        await handle_unknown_callback(update, context)

async def handle_solar_retail_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callbacks related to solar retail (buying solar panels)."""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    callback_data = query.data.split(":")
    
    if len(callback_data) < 2:
        await handle_unknown_callback(update, context)
        return
    
    action = callback_data[1]
    
    if action == "search_products":
        # Search for solar panel products
        user_session = get_user_session(user_id)
        products = []
        print("searchingggg ")
        # Search for solar panel products
        search_response = solar_agent.search_solar_products(user_id)
        print(search_response)
        # Process the search response
        if isinstance(search_response, list):
            products = search_response
        elif isinstance(search_response, dict) and "catalog" in search_response:
            for provider in search_response.get("catalog", {}).get("providers", []):
                for item in provider.get("items", []):
                    if "solar" in item.get("descriptor", {}).get("name", "").lower():
                        products.append({
                            "id": item.get("id", ""),
                            "provider_id": provider.get("id", ""),
                            "provider_name": provider.get("descriptor", {}).get("name", "Unknown Provider"),
                            "name": item.get("descriptor", {}).get("name", "Unknown Product"),
                            "description": item.get("descriptor", {}).get("short_desc", ""),
                            "price": item.get("price", {}).get("value", "0"),
                            "currency": item.get("price", {}).get("currency", "USD"),
                            "image": item.get("descriptor", {}).get("images", [{}])[0].get("url", "")
                        })
        
        # Store the processed products in the user session
        update_user_session(user_id, {"products": products})
        
        if not products:
            await query.edit_message_text(
                "I couldn't find any solar products at the moment. Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")]
                ])
            )
            return
        
        # Format the products for display
        products_text = "🌞 *Recommended Solar Panel Systems*\n\n"
        
        product_buttons = []
        for i, product in enumerate(products[:3]):  # Show top 3 products
            name = product.get("name", "Unknown Product")
            description = product.get("description", "")
            price = product.get("price", "0")
            currency = product.get("currency", "USD")
            provider_name = product.get("provider_name", "Unknown Provider")
            
            products_text += f"*{i+1}. {name}*\n"
            products_text += f"Provider: {provider_name}\n"
            products_text += f"Description: {description}\n"
            products_text += f"Price: {price} {currency}\n\n"
            
            # Add a button for each product
            product_buttons.append([
                InlineKeyboardButton(
                    f"Select {name}", 
                    callback_data=f"solar_retail:select_product:{product.get('provider_id')}:{product.get('id')}"
                )
            ])
        
        # Add a back button
        product_buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")])
        products_keyboard = InlineKeyboardMarkup(product_buttons)
        
        await query.edit_message_text(
            products_text,
            parse_mode="Markdown",
            reply_markup=products_keyboard
        )
    
    elif action == "select_product" and len(callback_data) >= 4:
        # User is selecting a specific solar panel product
        provider_id = callback_data[2]
        product_id = callback_data[3]
        
        # Update state
        update_user_session(user_id, {
            "state": "solar_retail_selecting_product",
            "selected_product_provider": provider_id,
            "selected_product": product_id
        })
        
        # Call the Beckn select API
        select_response = solar_agent.select_solar_product(user_id, provider_id, product_id)
        if select_response:
            order = select_response
            item = order.get("item", {})
            provider = order.get("provider", {})
            
            # Extract product details
            name = item.get("descriptor", {}).get("name", "Unknown Product")
            description = item.get("descriptor", {}).get("short_desc", "")
            price = item.get("price", {}).get("value", "0")
            currency = item.get("price", {}).get("currency", "USD")
            provider_name = provider.get("descriptor", {}).get("name", "Unknown Provider")
            
            # Show product details and confirmation
            product_text = (
                f"*Selected Product Details*\n\n"
                f"Product: *{name}*\n"
                f"Provider: {provider_name}\n"
                f"Description: {description}\n"
                f"Price: {price} {currency}\n\n"
                "Would you like to proceed with the purchase?"
            )
            
            product_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Purchase Product", callback_data=f"solar_retail:init_product:{provider_id}:{product_id}")],
                [InlineKeyboardButton("⬅️ Back", callback_data="solar_retail:search_products")]
            ])
            
            await query.edit_message_text(
                product_text,
                parse_mode="Markdown",
                reply_markup=product_keyboard
            )
        else:
            await query.edit_message_text(
                "❌ There was a problem selecting this product. Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="solar_retail:search_products")]
                ])
            )
    
    elif action == "init_product" and len(callback_data) >= 4:
        # Initialize the order for the selected product
        provider_id = callback_data[2]
        product_id = callback_data[3]
        
        # Call the Beckn init API
        init_response = solar_agent.init_solar_product_order(user_id, provider_id, product_id)
        print(init_response)
        if init_response:
            # Update state
            update_user_session(user_id, {
                "state": "solar_retail_init_product",
                "product_init": {"provider_id": provider_id, "product_id": product_id}
            })
            
            # Show order summary and confirmation
            await query.edit_message_text(
                "🛒 *Order Initialized*\n\n"
                "To complete your purchase, I'll need to collect your delivery information.\n\n"
                "Please provide your delivery address in the following format:\n"
                "`Street Address, City, State, ZIP Code`\n\n"
                "Or click the button below to use your saved address.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📝 Use Saved Address", callback_data=f"solar_retail:use_saved_address:{provider_id}:{product_id}")],
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"solar_retail:select_product:{provider_id}:{product_id}")]
                ])
            )
        else:
            await query.edit_message_text(
                "❌ There was a problem initializing your order. Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"solar_retail:select_product:{provider_id}:{product_id}")]
                ])
            )
    
    elif action == "use_saved_address" and len(callback_data) >= 4:
        # User is using their saved address for delivery
        provider_id = callback_data[2]
        product_id = callback_data[3]
        
        # Get user info and saved address
        user_name = update.effective_user.first_name
        user_session = get_user_session(user_id)
        address = user_session.get("address")
        
        if not address:
            await query.edit_message_text(
                "❌ No saved address found. Please provide your delivery address in the following format:\n"
                "`Street Address, City, State, ZIP Code`",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"solar_retail:init_product:{provider_id}:{product_id}")]
                ])
            )
            return
        
        # Prepare customer info
        customer_info = {
            "person": {
                "name": user_name
            },
            "contact": {
                "phone": user_session.get("phone", ""),
                "email": user_session.get("email", f"{user_name}@example.com")
            },
            "delivery": {
                "address": address
            }
        }
        
        # Call the Beckn confirm API
        confirm_response = solar_agent.confirm_solar_product_order(user_id, provider_id, product_id, customer_info)
        print("------------------------------------------------------------")
        print(confirm_response)
        print("------------------------------------------------------------")
        if confirm_response:
            order_id = confirm_response["order"]["id"]
            
            # Store the order ID
            update_user_session(user_id, {
                "state": "solar_retail_product_confirmed",
                "product_order_id": order_id
            })
            
            await query.edit_message_text(
                "✅ *Solar Panel System Purchase Confirmed!*\n\n"
                f"Order ID: `{order_id}`\n\n"
                "Your solar panel system has been ordered and will be delivered to your address. "
                "Would you like to schedule an installation with one of our certified installers?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏪 Find Installers", callback_data="solar_onboarding:find_installers")],
                    [InlineKeyboardButton("📊 View Solar Summary", callback_data="solar_onboarding:view_summary")],
                    [InlineKeyboardButton("🏠 Return to Main Menu", callback_data="solar_onboarding:back_to_main")]
                ])
            )
        else:
            await query.edit_message_text(
                "❌ There was a problem confirming your order. Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data=f"solar_retail:init_product:{provider_id}:{product_id}")]
                ])
            )
    
    else:
        # Handle unknown solar retail actions
        await handle_unknown_callback(update, context)

async def handle_energy_services_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callbacks related to energy services."""
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    callback_data = query.data.split(":")

    if len(callback_data) < 2:
        await handle_unknown_callback(update, context)
        return

    action = callback_data[1]

    if action == "start":
        # Start the energy services flow
        update_user_session(user_id, {"state": "energy_services_menu"})

        energy_services_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 Sell Energy", callback_data="energy_services:sell_energy")],
            [InlineKeyboardButton("🛒 Buy Energy", callback_data="energy_services:buy_energy")],
            [InlineKeyboardButton("📊 Track My Production", callback_data="energy_services:track_production")],
            [InlineKeyboardButton("💹 View Energy Stats", callback_data="energy_services:view_stats")],
            [InlineKeyboardButton("🎟️ Tokenize as NFTs", callback_data="energy_services:tokenize_energy")],
            [InlineKeyboardButton("🤖 Auto-Trading Settings", callback_data="energy_services:auto_trading")],
            [InlineKeyboardButton("🔌 P2P Energy Sharing", callback_data="energy_services:p2p_sharing")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="solar_onboarding:back_to_main")]
        ])

        await query.edit_message_text(
            "Welcome to Energy Services! 🌟\n\n"
            "As a prosumer with installed solar panels, you can participate in the energy market. "
            "What would you like to do today?",
            reply_markup=energy_services_keyboard
        )

    elif action == "view_transactions":
        # Show transaction history
        update_user_session(user_id, {"state": "energy_services_transactions"})

        # Get transaction history from user state
        user_session = get_user_session(user_id)
        transactions = user_session.get('transactions', [])

        if not transactions:
            await query.edit_message_text(
                "You haven't made any energy transactions yet.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="energy_services:start")]])
            )
            return

        # Sort transactions by timestamp (newest first)
        transactions.sort(key=lambda x: x.get('timestamp', ''), reverse=True)

        # Format the transactions for display
        transactions_text = "📜 *Your Energy Transactions*\n\n"

        for i, tx in enumerate(transactions[:5]):  # Show only the 5 most recent transactions
            tx_type = tx.get('transaction_type', '').replace('_', ' ').title()
            amount = tx.get('amount_kwh', 0)
            price = tx.get('price_per_kwh', 0)
            total = tx.get('total_amount_usd', 0)
            timestamp = tx.get('timestamp', '').split('T')[0]  # Just show the date part

            transactions_text += (
                f"{i+1}. **{tx_type}**\n"
                f"   Amount: {amount} kWh\n"
                f"   Price: ${price}/kWh\n"
                f"   {'Total earning' if 'sell' in tx_type.lower() or 'shar' in tx_type.lower() else 'Total cost'}: ${total}\n"
                f"   Date: {timestamp}\n\n"
            )

        # Add pagination if there are more transactions
        if len(transactions) > 5:
            transactions_text += f"Showing 5 of {len(transactions)} transactions."

        await query.edit_message_text(
            transactions_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 View Stats", callback_data="energy_services:view_stats")],
                [InlineKeyboardButton("⬅️ Back", callback_data="energy_services:start")]
            ]),
            parse_mode="Markdown"
        )

    elif action == "auto_trading_set_schedule":
        # Interface for setting auto-trading schedule
        update_user_session(user_id, {"state": "energy_services_auto_trading_schedule"})

        # Get current schedule settings from user state
        user_session = get_user_session(user_id)
        auto_trading = user_session.get('auto_trading', {}).get('settings', {})
        trading_hours = auto_trading.get('trading_hours', '8:00-20:00')

        schedule_text = (
            "⏰ *Set Auto-Trading Schedule*\n\n"
            f"Current trading hours: {trading_hours}\n\n"
            "When should auto-trading be active? Select an option below, "
            "or type a custom schedule (e.g., '9:00-17:00,22:00-6:00')."
        )

        schedule_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("All day (24/7)", callback_data="energy_services:set_schedule:0:00-23:59")],
            [InlineKeyboardButton("Daytime only (8am-8pm)", callback_data="energy_services:set_schedule:8:00-20:00")],
            [InlineKeyboardButton("Peak hours only (12pm-8pm)", callback_data="energy_services:set_schedule:12:00-20:00")],
            [InlineKeyboardButton("Off-peak only (8pm-12pm)", callback_data="energy_services:set_schedule:20:00-12:00")],
            [InlineKeyboardButton("⬅️ Back", callback_data="energy_services:auto_trading")]
        ])

        await query.edit_message_text(
            schedule_text,
            reply_markup=schedule_keyboard,
            parse_mode="Markdown"
        )

    elif action == "set_schedule" and len(callback_data) >= 3:
        # Set auto-trading schedule
        schedule = callback_data[2]

        # Update user state with new schedule
        user_session = get_user_session(user_id)
        auto_trading = user_session.get('auto_trading', {})
        if 'settings' not in auto_trading:
            auto_trading['settings'] = {}

        auto_trading['settings']['trading_hours'] = schedule
        update_user_session(user_id, {"auto_trading": auto_trading})

        await query.edit_message_text(
            f"✅ Auto-trading schedule updated to: {schedule}\n\n"
            "Would you like to adjust any other auto-trading settings?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ More Settings", callback_data="energy_services:auto_trading")],
                [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
            ])
        )
    elif action == "sell_energy":
        # User wants to sell excess energy
        update_user_session(user_id, {"state": "energy_services_sell"})

        # Get energy production data
        production = prosumer_agent.get_energy_production(user_id)

        # Format the production data for display
        production_text = (
            "📊 *Your Energy Production*\n\n"
            f"Today's production: {production['daily'][-1]['kwh']} kWh\n"
            f"Weekly total: {production['total_kwh']} kWh\n"
            f"Peak production: {production['peak_kw']} kW\n\n"

            "🔋 *Available to Sell*\n\n"
            f"Estimated excess: {round(production['daily'][-1]['kwh'] * 0.6, 1)} kWh\n"
            f"Current grid price: $0.18/kWh\n"
            f"Potential earnings: ${round(production['daily'][-1]['kwh'] * 0.6 * 0.18, 2)}\n\n"

            "Would you like to sell your excess energy now?"
        )

        sell_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 Sell to Grid", callback_data="energy_services:sell_to_grid")],
            [InlineKeyboardButton("👥 Share with Neighbors", callback_data="energy_services:share_p2p")],
            [InlineKeyboardButton("⬅️ Back", callback_data="energy_services:start")]
        ])

        await query.edit_message_text(
            production_text,
            reply_markup=sell_keyboard,
            parse_mode="Markdown"
        )

    # Update the sell_to_grid handler:
    elif action == "sell_to_grid":
        # Execute a grid sale with proper error handling
        await query.edit_message_text("Processing your energy sale... Please wait.")
        
        # Get production data to determine realistic amount
        production = prosumer_agent.get_energy_production(user_id)
        excess_energy = round(production['daily'][-1]['kwh'] * 0.6, 1)  # Use 60% of daily production
        
        sale_result = prosumer_agent.execute_grid_sale(user_id, excess_energy)
        
        # Handle error case
        if sale_result.get("status") == "error":
            await query.edit_message_text(
                f"❌ *Error Selling Energy*\n\n"
                f"There was a problem selling energy to the grid: {sale_result.get('message', 'Unknown error')}\n\n"
                f"Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
                ]),
                parse_mode="Markdown"
            )
            return
        
        # Update user session
        user_session = get_user_session(user_id)
        transactions = user_session.get('transactions', [])
        transactions.append(sale_result)
        update_user_session(user_id, {"transactions": transactions, "state": "energy_services_sale_complete"})
        
        # Format the sale result for display using safe gets
        result_text = (
            "✅ *Energy Sale Complete!*\n\n"
            f"Amount sold: {sale_result.get('amount_kwh', 0)} kWh\n"
            f"Price: ${sale_result.get('price_per_kwh', 0)}/kWh\n"
            f"Total earnings: ${sale_result.get('total_amount_usd', 0)}\n"
            f"Transaction ID: {sale_result.get('transaction_id', 'Unknown')}\n\n"
        )
        
        if sale_result.get('nft_details'):
            nft_details = sale_result.get('nft_details', {})
            result_text += (
                "🎁 *NFT Reward*\n\n"
                f"Token ID: {nft_details.get('token_id', 'Unknown')}\n"
                f"Value: ${nft_details.get('value_usd', 0)}\n"
                f"Marketplace: {nft_details.get('marketplace_url', 'Unknown')}\n\n"
            )
        
        result_text += "Thank you for contributing to a greener grid!"
        
        await query.edit_message_text(
            result_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 View My Stats", callback_data="energy_services:view_stats")],
                [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
            ]),
            parse_mode="Markdown"
        )
    
    # Update the share_p2p handler:
    elif action == "share_p2p":
        # Execute a P2P sharing transaction with proper error handling
        await query.edit_message_text("Processing your P2P energy sharing... Please wait.")
        
        # Get production data to determine realistic amount
        production = prosumer_agent.get_energy_production(user_id)
        excess_energy = round(production['daily'][-1]['kwh'] * 0.5, 1)  # Use 50% of daily production for P2P
        
        sharing_result = prosumer_agent.execute_p2p_sharing(user_id, excess_energy)
        
        # Handle error case
        if sharing_result.get("status") == "error":
            await query.edit_message_text(
                f"❌ *Error Sharing Energy*\n\n"
                f"There was a problem sharing energy: {sharing_result.get('message', 'Unknown error')}\n\n"
                f"Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
                ]),
                parse_mode="Markdown"
            )
            return
        
        # Update user session
        user_session = get_user_session(user_id)
        transactions = user_session.get('transactions', [])
        transactions.append(sharing_result)
        update_user_session(user_id, {"transactions": transactions, "state": "energy_services_sharing_complete"})
        
        # Format the sharing result for display with safe gets
        result_text = (
            "✅ *P2P Energy Sharing Complete!*\n\n"
            f"Amount shared: {sharing_result.get('amount_kwh', 0)} kWh\n"
            f"Price: ${sharing_result.get('price_per_kwh', 0)}/kWh\n"
            f"Total earnings: ${sharing_result.get('total_amount_usd', 0)}\n"
            f"Recipient: {sharing_result.get('recipient', 'Unknown')}\n"
            f"Transaction ID: {sharing_result.get('transaction_id', 'Unknown')}\n\n"
            f"Community contribution: +{sharing_result.get('community_contribution', 0)} points\n"
            f"Total community score: {sharing_result.get('community_score', 0)} points\n\n"
        )
        
        if sharing_result.get('nft_details'):
            nft_details = sharing_result.get('nft_details', {})
            result_text += (
                "🎁 *NFT Reward*\n\n"
                f"Token ID: {nft_details.get('token_id', 'Unknown')}\n"
                f"Value: ${nft_details.get('value_usd', 0)}\n"
                f"Marketplace: {nft_details.get('marketplace_url', 'Unknown')}\n\n"
            )
        
        result_text += "Thank you for sharing with your community!"
        
        await query.edit_message_text(
            result_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 View My Stats", callback_data="energy_services:view_stats")],
                [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
            ]),
            parse_mode="Markdown"
        )
    
    # Update the buy_from_grid handler:
    elif action == "buy_from_grid":
        # Interface for buying energy from the grid
        update_user_session(user_id, {"state": "energy_services_buy_grid"})
        
        # Get current time to determine if it's peak or off-peak
        current_hour = datetime.now().hour
        is_peak_time = 12 <= current_hour <= 20  # Define peak time between 12pm-8pm
        
        # Set price based on peak/off-peak
        price_per_kwh = 0.22 if is_peak_time else 0.08
        
        grid_text = (
            "🏢 *Buy Energy from the Grid*\n\n"
            f"Current time: {datetime.now().strftime('%H:%M')}\n"
            f"Period: {'Peak hours' if is_peak_time else 'Off-peak hours'}\n"
            f"Price: ${price_per_kwh}/kWh\n\n"
            "How much energy would you like to purchase?"
        )
        
        # Create options for different amounts
        grid_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"1.0 kWh (${round(1.0 * price_per_kwh, 2)})", 
                                  callback_data=f"energy_services:confirm_grid_buy:1.0")],
            [InlineKeyboardButton(f"5.0 kWh (${round(5.0 * price_per_kwh, 2)})", 
                                  callback_data=f"energy_services:confirm_grid_buy:5.0")],
            [InlineKeyboardButton(f"10.0 kWh (${round(10.0 * price_per_kwh, 2)})", 
                                  callback_data=f"energy_services:confirm_grid_buy:10.0")],
            [InlineKeyboardButton("⬅️ Back", callback_data="energy_services:buy_energy")]
        ])
        
        await query.edit_message_text(
            grid_text,
            reply_markup=grid_keyboard,
            parse_mode="Markdown"
        )
    
    elif action == "confirm_grid_buy" and len(callback_data) >= 3:
        # Execute confirmed grid energy purchase with proper error handling
        await query.edit_message_text("Processing your energy purchase... Please wait.")
        
        amount_kwh = float(callback_data[2])
        
        # Execute the grid purchase
        purchase_result = prosumer_agent.execute_grid_purchase(user_id, amount_kwh)
        
        # Handle error case
        if purchase_result.get("status") == "error":
            await query.edit_message_text(
                f"❌ *Error Purchasing Energy*\n\n"
                f"There was a problem buying energy: {purchase_result.get('message', 'Unknown error')}\n\n"
                f"Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
                ]),
                parse_mode="Markdown"
            )
            return
        
        # Update user session
        user_session = get_user_session(user_id)
        transactions = user_session.get('transactions', [])
        transactions.append(purchase_result)
        update_user_session(user_id, {"transactions": transactions, "state": "energy_services_purchase_complete"})
        
        # Format the purchase result for display with safe gets
        result_text = (
            "✅ *Grid Energy Purchase Complete!*\n\n"
            f"Amount purchased: {purchase_result.get('amount_kwh', 0)} kWh\n"
            f"Price: ${purchase_result.get('price_per_kwh', 0)}/kWh\n"
            f"Total cost: ${purchase_result.get('total_amount_usd', 0)}\n"
            f"Transaction ID: {purchase_result.get('transaction_id', 'Unknown')}\n\n"
            "Your battery has been charged with the purchased energy!"
        )
        
        await query.edit_message_text(
            result_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 View My Stats", callback_data="energy_services:view_stats")],
                [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
            ]),
            parse_mode="Markdown"
        )

    elif action == "track_production":
        # Show energy production data
        update_user_session(user_id, {"state": "energy_services_viewing_production"})

        # Get energy production data
        production = prosumer_agent.get_energy_production(user_id)

        # Format daily production data
        daily_production = "\n".join([f"• {day['date']}: {day['kwh']} kWh" for day in production['daily']])

        production_text = (
            "📈 *Energy Production Data*\n\n"
            f"Total this week: {production['total_kwh']} kWh\n"
            f"Peak production: {production['peak_kw']} kW\n"
            f"Carbon offset: {production['carbon_offset_kg']} kg CO2\n\n"
            f"*Daily breakdown:*\n{daily_production}\n\n"
        )

        await query.edit_message_text(
            production_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💹 View Financial Stats", callback_data="energy_services:view_stats")],
                [InlineKeyboardButton("⬅️ Back", callback_data="energy_services:start")]
            ]),
            parse_mode="Markdown"
        )

    elif action == "view_stats":
        # Show comprehensive energy stats
        update_user_session(user_id, {"state": "energy_services_viewing_stats"})

        # Get energy stats
        stats = prosumer_agent.get_energy_stats(user_id)

        stats_text = (
            "📊 *Energy Dashboard*\n\n"
            "*Production*\n"
            f"• Today: {stats['production']['today_kwh']} kWh\n"
            f"• This week: {stats['production']['week_kwh']} kWh\n"
            f"• This month: {stats['production']['month_kwh']} kWh\n"
            f"• Lifetime: {stats['production']['lifetime_kwh']} kWh\n\n"

            "*Consumption*\n"
            f"• Today: {stats['consumption']['today_kwh']} kWh\n"
            f"• This week: {stats['consumption']['week_kwh']} kWh\n"
            f"• Self-consumption: {stats['grid_interaction']['self_consumption_pct']}%\n\n"

            "*Grid Interaction*\n"
            f"• Exported: {stats['grid_interaction']['exported_kwh']} kWh\n"
            f"• Imported: {stats['grid_interaction']['imported_kwh']} kWh\n\n"

            "*Financial Benefits*\n"
            f"• Monthly savings: ${stats['financial']['savings_current_month_usd']}\n"
            f"• Monthly earnings: ${stats['financial']['earnings_current_month_usd']}\n"
            f"• Projected annual: ${stats['financial']['projected_annual_savings_usd']}\n\n"

            "*Environmental Impact*\n"
            f"• Carbon offset: {stats['environmental']['carbon_offset_kg']} kg\n"
            f"• Trees equivalent: {stats['environmental']['trees_equivalent']}\n"
            f"• Miles not driven: {stats['environmental']['miles_not_driven_equivalent']}\n"
        )

        await query.edit_message_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🏆 View Community Rank", callback_data="energy_services:community_rank")],
                [InlineKeyboardButton("⬅️ Back", callback_data="energy_services:start")]
            ]),
            parse_mode="Markdown"
        )

    elif action == "tokenize_energy":
        # Show NFT tokenization options
        update_user_session(user_id, {"state": "energy_services_tokenize"})

        # Get NFT opportunities
        opportunities = prosumer_agent.get_nft_opportunities(user_id)

        nft_text = (
            "🎟️ *Energy NFT Tokenization*\n\n"
            "Turn your renewable energy production and grid contributions into valuable digital assets!\n\n"
            "*Available Tokenization Options:*\n\n"
        )

        for i, opp in enumerate(opportunities):
            nft_text += (
                f"{i+1}. *{opp['type'].replace('_', ' ').title()}*\n"
                f"   • {opp['description']}\n"
                f"   • Value: ${opp['value_per_mwh']}/MWh or ${opp['value_per_event']}/event\n"
                f"   • Marketplace: {opp['marketplace']}\n"
                f"   • Blockchain: {opp['blockchain']}\n\n"
            )

        nft_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Create Renewable Credit NFT", callback_data="energy_services:create_renewable_nft")],
            [InlineKeyboardButton("⚡ Create Flexibility NFT", callback_data="energy_services:create_flexibility_nft")],
            [InlineKeyboardButton("⬅️ Back", callback_data="energy_services:start")]
        ])

        await query.edit_message_text(
            nft_text,
            reply_markup=nft_keyboard,
            parse_mode="Markdown"
        )

    elif action == "create_renewable_nft" or action == "create_flexibility_nft":
        # Create an energy NFT
        nft_type = "renewable_credit" if action == "create_renewable_nft" else "grid_flexibility"
        amount = 100.0 if nft_type == "renewable_credit" else 5  # kWh or events

        nft_details = prosumer_agent.create_energy_nft(user_id, nft_type, amount)

        # Update user session
        user_session = get_user_session(user_id)
        nfts = user_session.get('nfts', [])
        nfts.append(nft_details)
        update_user_session(user_id, {"nfts": nfts, "state": "energy_services_nft_created"})

        # Format the NFT details for display
        nft_text = (
            "✅ *NFT Created Successfully!*\n\n"
            f"Token ID: `{nft_details['token_id']}`\n"
            f"Blockchain: {nft_details['blockchain']}\n"
            f"Value: ${nft_details['value_usd']}\n"
            f"Created: {nft_details['creation_time'].split('T')[0]}\n\n"
            f"*Contract Address:*\n`{nft_details['contract_address']}`\n\n"
            "Your energy contribution has been tokenized! You can now trade this NFT "
            "on supported marketplaces or hold it as proof of your green energy production."
        )

        await query.edit_message_text(
            nft_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 View on Marketplace", url=nft_details['marketplace_url'])],
                [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
            ]),
            parse_mode="Markdown"
        )

    elif action == "auto_trading":
        # Configure auto-trading
        update_user_session(user_id, {"state": "energy_services_auto_trading_config"})

        auto_trading_text = (
            "🤖 *AI-Powered Auto-Trading*\n\n"
            "Let our AI automatically sell your excess energy during peak hours and buy during off-peak to maximize your savings!\n\n"
            "*Please configure your preferences:*\n\n"
            "• Minimum selling price: $0.12/kWh\n"
            "• Maximum buying price: $0.08/kWh\n"
            "• Optimization target: Financial (Financial/Environmental/Balanced)\n"
            "• Reserve capacity: 20%\n"
            "• Neighbor sharing: Enabled (Yes/No)\n"
            "• Token rewards: Enabled (Yes/No)\n\n"
            "You can edit these settings by sending a message with your preferences (one per line).\n"
            "Example:\n"
            "Min sell price: $0.15\n"
            "Max buy price: $0.07\n"
            "Optimization target: Environmental\n"
        )

        await query.edit_message_text(
            auto_trading_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Use Default Settings", callback_data="energy_services:auto_trading_default")],
                [InlineKeyboardButton("⬅️ Back", callback_data="energy_services:start")]
            ]),
            parse_mode="Markdown"
        )

    elif action == "buy_energy":
        # User wants to buy energy
        update_user_session(user_id, {"state": "energy_services_buy"})

        # Get energy trading opportunities specifically for buying
        trading_opportunities = prosumer_agent.get_energy_trading_opportunities(user_id)
        buy_opportunities = [opp for opp in trading_opportunities if opp.get("type") == "sell_excess"]

        buy_text = (
            "🛒 *Buy Energy from the Market*\n\n"
            "Current grid price: $0.22/kWh (peak) / $0.08/kWh (off-peak)\n\n"
        )

        if buy_opportunities:
            buy_text += "*Available energy sources:*\n\n"
            for i, opp in enumerate(buy_opportunities[:5]):
                buy_text += (
                    f"{i+1}. **{opp.get('provider_name')}**\n"
                    f"   Available: {opp.get('tags', {}).get('energy_available', {}).get('amount', '5.0')} kWh\n"
                    f"   Price: ${opp.get('price_per_kwh', 0.18)}/kWh\n"
                    f"   Type: {opp.get('tags', {}).get('source_type', 'Solar')}\n\n"
                )
        else:
            buy_text += "No energy sellers found at the moment. You can buy from the grid instead.\n\n"

        # Create dynamic keyboard based on opportunities
        buttons = []
        for i, opp in enumerate(buy_opportunities[:5]):
            buttons.append([
                InlineKeyboardButton(
                    f"Buy from {opp.get('provider_name')}",
                    callback_data=f"energy_services:buy_from:{opp.get('provider_id')}"
                )
            ])

        buttons.append([InlineKeyboardButton("🏢 Buy from Grid", callback_data="energy_services:buy_from_grid")])
        buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="energy_services:start")])

        buy_keyboard = InlineKeyboardMarkup(buttons)

        await query.edit_message_text(
            buy_text,
            reply_markup=buy_keyboard,
            parse_mode="Markdown"
        )

    elif action == "buy_from" and len(callback_data) >= 3:
        # Handle buying from a specific provider
        provider_id = callback_data[2]

        # Get trading opportunities to find the selected one
        trading_opportunities = prosumer_agent.get_energy_trading_opportunities(user_id)
        selected_opportunity = None

        for opp in trading_opportunities:
            if opp.get("provider_id") == provider_id:
                selected_opportunity = opp
                break

        if not selected_opportunity:
            await query.edit_message_text(
                "Sorry, this buying opportunity is no longer available.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="energy_services:buy_energy")]])
            )
            return

        # Show buying confirmation with amount input options
        provider_name = selected_opportunity.get("provider_name", "Unknown")
        price_per_kwh = selected_opportunity.get("price_per_kwh", 0.18)
        max_available = float(selected_opportunity.get("tags", {}).get("energy_available", {}).get("amount", "5.0"))

        # Create option buttons for different amounts
        small_amount = 1.0  # 1 kWh
        medium_amount = min(3.0, max_available)  # 3 kWh or max available
        large_amount = min(5.0, max_available)  # 5 kWh or max available

        buying_text = (
            f"🛒 *Buy Energy from {provider_name}*\n\n"
            f"This provider has up to {max_available} kWh available.\n"
            f"Price: ${price_per_kwh}/kWh\n\n"
            "How much would you like to buy?"
        )

        buying_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"{small_amount} kWh (${round(small_amount * price_per_kwh, 2)})",
                                callback_data=f"energy_services:confirm_buy:{provider_id}:{small_amount}")],
            [InlineKeyboardButton(f"{medium_amount} kWh (${round(medium_amount * price_per_kwh, 2)})",
                                callback_data=f"energy_services:confirm_buy:{provider_id}:{medium_amount}")],
            [InlineKeyboardButton(f"{large_amount} kWh (${round(large_amount * price_per_kwh, 2)})",
                                callback_data=f"energy_services:confirm_buy:{provider_id}:{large_amount}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="energy_services:buy_energy")]
        ])

        await query.edit_message_text(
            buying_text,
            reply_markup=buying_keyboard,
            parse_mode="Markdown"
        )

    elif action == "confirm_buy" and len(callback_data) >= 4:
        # Execute confirmed energy purchase
        provider_id = callback_data[2]
        amount_kwh = float(callback_data[3])

        # Get trading opportunity to get price
        trading_opportunities = prosumer_agent.get_energy_trading_opportunities(user_id)
        selected_opportunity = None
        for opp in trading_opportunities:
            if opp.get("provider_id") == provider_id:
                selected_opportunity = opp
                break

        price_per_kwh = selected_opportunity.get("price_per_kwh", 0.18) if selected_opportunity else 0.18

        # Create a custom purchase transaction (this would call a Beckn API in production)
        purchase_result = {
            "status": "completed",
            "transaction_type": "p2p_purchase",
            "amount_kwh": amount_kwh,
            "price_per_kwh": price_per_kwh,
            "total_amount_usd": round(amount_kwh * price_per_kwh, 2),
            "transaction_id": f"p2p-buy-{int(datetime.now().timestamp())}",
            "timestamp": datetime.now().isoformat(),
            "provider": selected_opportunity.get("provider_name", "Unknown Provider") if selected_opportunity else "Unknown Provider",
            "source_type": selected_opportunity.get("tags", {}).get("source_type", "Solar") if selected_opportunity else "Solar"
        }

        # Update user session
        user_session = get_user_session(user_id)
        transactions = user_session.get('transactions', [])
        transactions.append(purchase_result)
        update_user_session(user_id, {"transactions": transactions, "state": "energy_services_purchase_complete"})

        # Format the purchase result for display
        result_text = (
            "✅ *Energy Purchase Complete!*\n\n"
            f"Amount purchased: {purchase_result['amount_kwh']} kWh\n"
            f"Price: ${purchase_result['price_per_kwh']}/kWh\n"
            f"Total cost: ${purchase_result['total_amount_usd']}\n"
            f"Provider: {purchase_result['provider']}\n"
            f"Source type: {purchase_result['source_type']}\n"
            f"Transaction ID: {purchase_result['transaction_id']}\n\n"
            "Your battery has been charged with the purchased energy!"
        )

        await query.edit_message_text(
            result_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 View My Stats", callback_data="energy_services:view_stats")],
                [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
            ]),
            parse_mode="Markdown"
        )

    elif action == "auto_trading_default":
        # Enable auto-trading with default settings
        result = prosumer_agent.enable_auto_trading(user_id, {})
        update_user_session(user_id, {"auto_trading": result, "state": "energy_services_auto_trading_enabled"})

        # Format the result for display
        settings = result.get('settings', {})

        response = (
            "✅ *Auto-Trading Enabled!*\n\n"
            f"*Settings:*\n"
            f"• Min. selling price: ${settings.get('min_sell_price_kwh', 0.12)}/kWh\n"
            f"• Max. buying price: ${settings.get('max_buy_price_kwh', 0.08)}/kWh\n"
            f"• Optimization target: {settings.get('ai_optimization_target', 'balanced').capitalize()}\n"
            f"• Reserve capacity: {settings.get('reserve_capacity_pct', 20)}%\n"
            f"• Neighbor sharing: {'Enabled' if settings.get('neighbor_sharing_enabled', True) else 'Disabled'}\n"
            f"• Token rewards: {'Enabled' if settings.get('token_rewards', True) else 'Disabled'}\n\n"
            f"*Estimated monthly benefit: ${result.get('estimated_monthly_benefit_usd', 0.0)}*\n\n"
            f"I'll now automatically trade energy for you based on these preferences! You can check your earnings anytime."
        )

        await query.edit_message_text(
            response,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📈 Run Trading Simulation", callback_data="energy_services:run_simulation")],
                [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
            ]),
            parse_mode="Markdown"
        )

    elif action == "run_simulation":
        # Run auto-trading simulation
        await query.edit_message_text("Running AI trading simulation...")

        # Execute auto-trading simulation
        trading_result = prosumer_agent.execute_auto_trading(user_id)

        # Format the result for display
        simulation_text = (
            "🤖 *AI Trading Simulation Results*\n\n"
            f"*Action:* {trading_result['action'].replace('_', ' ').title()}\n\n"
            f"*AI Explanation:*\n{trading_result['explanation']}\n\n"
            f"*Details:*\n"
            f"• Time: {'Peak hours' if trading_result['is_peak_time'] else 'Off-peak hours'}\n"
            f"• Price: ${trading_result['current_price']}/kWh\n"
            f"• Current production: {trading_result['current_production']} kWh\n\n"
        )

        result = trading_result.get('result', {})
        if trading_result['action'] != 'no_action' and trading_result['action'] != 'error':
            simulation_text += (
                "*Transaction:*\n"
                f"• Type: {result.get('transaction_type', '').replace('_', ' ').title()}\n"
                f"• Amount: {result.get('amount_kwh', 0)} kWh\n"
                f"• Price: ${result.get('price_per_kwh', 0)}/kWh\n"
                f"• Total: ${result.get('total_amount_usd', 0)}\n"
            )

            if 'community_score' in result:
                simulation_text += (
                    f"• Community contribution: +{result.get('community_contribution', 0)} points\n"
                    f"• Total community score: {result.get('community_score', 0)} points\n"
                )

        simulation_text += (
            "\nThis is what the AI would do based on current conditions. "
            "When auto-trading is enabled, these actions happen automatically!"
        )

        await query.edit_message_text(
            simulation_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 View Energy Stats", callback_data="energy_services:view_stats")],
                [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
            ]),
            parse_mode="Markdown"
        )

    elif action == "p2p_sharing":
            # P2P energy sharing interface with real data
            update_user_session(user_id, {"state": "energy_services_p2p_sharing"})

            # Get trading opportunities from Beckn Protocol using uei:p2p_trading domain
            trading_opportunities = prosumer_agent.get_energy_trading_opportunities(user_id)

            # Format the opportunities for display
            p2p_text = (
                "🔌 *Peer-to-Peer Energy Sharing*\n\n"
                "Share your excess solar energy directly with your community!\n\n"
            )

            # Get user's available energy to share
            production = prosumer_agent.get_energy_production(user_id)
            available_kwh = round(production['daily'][-1]['kwh'] * 0.6, 1)
            p2p_text += f"*Available to share:* {available_kwh} kWh\n\n"

            if trading_opportunities:
                # Filter for P2P opportunities
                p2p_opportunities = [opp for opp in trading_opportunities if opp.get("type") == "p2p_sharing"]

                if p2p_opportunities:
                    p2p_text += "*Nearby energy consumers:*\n\n"
                    for i, opp in enumerate(p2p_opportunities[:3]):
                        # Extract source type from tags if available
                        source_type = opp.get("tags", {}).get("source_type", "Solar")
                        energy_needs = opp.get("tags", {}).get("energy_available", {}).get("amount", "3.0")

                        p2p_text += (
                            f"{i+1}. **{opp.get('provider_name')}**\n"
                            f"   Needs: {energy_needs} kWh\n"
                            f"   Offers: ${opp.get('price_per_kwh', 0.14)}/kWh\n"
                            f"   Type: {source_type}\n\n"
                        )

                    # Create dynamic keyboard based on opportunities
                    buttons = []
                    for i, opp in enumerate(p2p_opportunities[:3]):
                        buttons.append([
                            InlineKeyboardButton(
                                f"Share with {opp.get('provider_name')}",
                                callback_data=f"energy_services:share_with:{opp.get('provider_id')}"
                            )
                        ])

                    buttons.append([InlineKeyboardButton("⚙️ Configure Sharing Settings", callback_data="energy_services:configure_sharing")])
                    buttons.append([InlineKeyboardButton("⬅️ Back", callback_data="energy_services:start")])

                    p2p_keyboard = InlineKeyboardMarkup(buttons)
                else:
                    p2p_text += "No nearby P2P energy consumers found at the moment.\n\n"
                    p2p_keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🏢 Share with Grid Instead", callback_data="energy_services:sell_to_grid")],
                        [InlineKeyboardButton("⚙️ Configure Sharing Settings", callback_data="energy_services:configure_sharing")],
                        [InlineKeyboardButton("⬅️ Back", callback_data="energy_services:start")]
                    ])
            else:
                p2p_text += "No nearby energy consumers found at the moment.\n\n"
                p2p_keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏢 Share with Grid Instead", callback_data="energy_services:sell_to_grid")],
                    [InlineKeyboardButton("⚙️ Configure Sharing Settings", callback_data="energy_services:configure_sharing")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="energy_services:start")]
                ])

            await query.edit_message_text(
                p2p_text,
                reply_markup=p2p_keyboard,
                parse_mode="Markdown"
            )

    elif action == "share_with" and len(callback_data) >= 3:
            # Handle sharing with a specific provider
            provider_id = callback_data[2]

            # Get trading opportunities to find the selected one
            trading_opportunities = prosumer_agent.get_energy_trading_opportunities(user_id)
            selected_opportunity = None

            for opp in trading_opportunities:
                if opp.get("provider_id") == provider_id:
                    selected_opportunity = opp
                    break

            if not selected_opportunity:
                await query.edit_message_text(
                    "Sorry, this sharing opportunity is no longer available.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="energy_services:p2p_sharing")]])
                )
                return

            # Show sharing confirmation with amount input options
            provider_name = selected_opportunity.get("provider_name", "Unknown")
            price_per_kwh = selected_opportunity.get("price_per_kwh", 0.14)

            # Get user's available energy
            production = prosumer_agent.get_energy_production(user_id)
            available_kwh = round(production['daily'][-1]['kwh'] * 0.6, 1)

            # Create option buttons for different amounts
            quarter_kwh = round(available_kwh * 0.25, 1)
            half_kwh = round(available_kwh * 0.5, 1)
            full_kwh = available_kwh

            sharing_text = (
                f"📊 *Share Energy with {provider_name}*\n\n"
                f"You have {available_kwh} kWh available to share.\n"
                f"This provider is offering ${price_per_kwh}/kWh.\n\n"
                "How much would you like to share?"
            )

            sharing_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"{quarter_kwh} kWh (${round(quarter_kwh * price_per_kwh, 2)})",
                                     callback_data=f"energy_services:confirm_share:{provider_id}:{quarter_kwh}")],
                [InlineKeyboardButton(f"{half_kwh} kWh (${round(half_kwh * price_per_kwh, 2)})",
                                     callback_data=f"energy_services:confirm_share:{provider_id}:{half_kwh}")],
                [InlineKeyboardButton(f"{full_kwh} kWh (${round(full_kwh * price_per_kwh, 2)})",
                                     callback_data=f"energy_services:confirm_share:{provider_id}:{full_kwh}")],
                [InlineKeyboardButton("⬅️ Back", callback_data="energy_services:p2p_sharing")]
            ])

            await query.edit_message_text(
                sharing_text,
                reply_markup=sharing_keyboard,
                parse_mode="Markdown"
            )

    elif action == "confirm_share" and len(callback_data) >= 4:
            # Execute confirmed P2P sharing transaction
            provider_id = callback_data[2]
            amount_kwh = float(callback_data[3])

            # Execute the P2P sharing
            sharing_result = prosumer_agent.execute_p2p_sharing(user_id, amount_kwh)

            # Update user session
            user_session = get_user_session(user_id)
            transactions = user_session.get('transactions', [])
            transactions.append(sharing_result)
            update_user_session(user_id, {"transactions": transactions, "state": "energy_services_sharing_complete"})

            # Format the sharing result for display
            result_text = (
                "✅ *P2P Energy Sharing Complete!*\n\n"
                f"Amount shared: {sharing_result['amount_kwh']} kWh\n"
                f"Price: ${sharing_result['price_per_kwh']}/kWh\n"
                f"Total earnings: ${sharing_result['total_amount_usd']}\n"
                f"Recipient: {sharing_result['recipient']}\n"
                f"Transaction ID: {sharing_result['transaction_id']}\n\n"
                f"Community contribution: +{sharing_result['community_contribution']} points\n"
                f"Total community score: {sharing_result['community_score']} points\n\n"
            )

            if sharing_result.get('nft_details'):
                result_text += (
                    "🎁 *NFT Reward*\n\n"
                    f"Token ID: {sharing_result['nft_details']['token_id']}\n"
                    f"Value: ${sharing_result['nft_details']['value_usd']}\n"
                    f"Marketplace: {sharing_result['nft_details']['marketplace_url']}\n\n"
                )

            result_text += "Thank you for sharing with your community!"

            await query.edit_message_text(
                result_text,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📊 View My Stats", callback_data="energy_services:view_stats")],
                    [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
                ]),
                parse_mode="Markdown"
            )

    elif action == "configure_sharing":
            # Interface for configuring P2P sharing preferences
            update_user_session(user_id, {"state": "energy_services_configure_sharing"})

            # Get current sharing settings from user state
            user_session = get_user_session(user_id)
            sharing_settings = user_session.get('sharing_settings', {
                'daily_limit_kwh': 10.0,
                'min_price_per_kwh': 0.12,
                'preferred_recipients': 'any',
                'auto_share': False,
                'share_percentage': 60
            })

            config_text = (
                "⚙️ *Configure P2P Sharing Settings*\n\n"
                f"Current settings:\n\n"
                f"• Daily sharing limit: {sharing_settings['daily_limit_kwh']} kWh\n"
                f"• Minimum price: ${sharing_settings['min_price_per_kwh']}/kWh\n"
                f"• Preferred recipients: {sharing_settings['preferred_recipients'].capitalize()}\n"
                f"• Auto-share excess: {'Enabled' if sharing_settings['auto_share'] else 'Disabled'}\n"
                f"• Share percentage: {sharing_settings['share_percentage']}% of excess\n\n"
                "Which setting would you like to change?"
            )

            config_keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📏 Set Daily Limit", callback_data="energy_services:set_daily_limit")],
                [InlineKeyboardButton("💰 Set Minimum Price", callback_data="energy_services:set_min_price")],
                [InlineKeyboardButton("👥 Set Preferred Recipients", callback_data="energy_services:set_recipients")],
                [InlineKeyboardButton(f"🔄 {'Disable' if sharing_settings['auto_share'] else 'Enable'} Auto-Share",
                                    callback_data="energy_services:toggle_auto_share")],
                [InlineKeyboardButton("📊 Set Share Percentage", callback_data="energy_services:set_share_percentage")],
                [InlineKeyboardButton("⬅️ Back", callback_data="energy_services:p2p_sharing")]
            ])

            await query.edit_message_text(
                config_text,
                reply_markup=config_keyboard,
                parse_mode="Markdown"
            )

    elif action == "community_rank":
        # Show community ranking
        update_user_session(user_id, {"state": "energy_services_community_rank"})

        # Get user state to check community score
        user_session = get_user_session(user_id)
        community_score = user_session.get('community_score', 0)

        # Create a simulated community leaderboard
        rank_text = (
            "🏆 *Community Energy Leaderboard*\n\n"
            "*Your Rank:* #3 in your neighborhood\n\n"
            "*Your Impact:*\n"
            f"• Community Score: {community_score} points\n"
            "• Energy Shared: 42.7 kWh this month\n"
            "• CO₂ Prevented: 21.4 kg\n\n"
            "*Top Contributors:*\n\n"
            "1. **GreenPioneer** - 156.3 points\n"
            "2. **SolarFamily** - 143.8 points\n"
            f"3. **You** - {community_score} points\n"
            "4. **EcoNeighbor** - 89.2 points\n"
            "5. **SunshineHome** - 76.5 points\n\n"
            "*Community Impact:*\n"
            "Together, your neighborhood has generated 1,256 kWh of clean energy this month!"
        )

        await query.edit_message_text(
            rank_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📊 View My Stats", callback_data="energy_services:view_stats")],
                [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
            ]),
            parse_mode="Markdown"
        )

    else:
        # Default response for other energy service actions
        await query.edit_message_text(
            "This energy service feature is coming soon! Check back for updates.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Back to Energy Services", callback_data="energy_services:start")]
            ])
        )


async def handle_photo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle photo messages, particularly for rooftop analysis."""
    user_id = str(update.effective_user.id)
    user_session = get_user_session(user_id)

    # Check if we're expecting a rooftop photo  
    if user_session.get("state") == "solar_onboarding_awaiting_photo": #change to !=
        await update.message.reply_text(
            "Thanks for the photo! If you're trying to analyze your roof for solar potential, "
            "please start the solar onboarding process first using the menu."
        )
        return

    # Get the photo with the best quality
    photo = update.message.photo[-1]
    file_id = photo.file_id

    await update.message.reply_text("🔍 Analyzing your rooftop image... Please wait.")

    # Get the file URL
    file = await context.bot.get_file(file_id)
    file_url = file.file_path

    # Analyze the image using the rooftop analyzer
    analysis = rooftop_analyzer.analyze_image(file_url)

    update_user_session(user_id, {"rooftop_analysis": analysis, "state": "solar_onboarding_roof_analyzed"})

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 Calculate ROI", callback_data="solar_onboarding:calculate_roi")],
        [InlineKeyboardButton("🔍 Find Installers", callback_data="solar_onboarding:find_installers")],
        [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")]
    ])

    await update.message.reply_markdown(analysis, reply_markup=keyboard)
