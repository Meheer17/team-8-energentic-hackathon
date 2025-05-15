import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

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
        f"What would you like to do today?"
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

    # Provide a helpful message and a way to get back to the main menu
    await query.edit_message_text(
        "Sorry, I couldn't process that request. Please try again or use the button below to return to the main menu.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Return to Main Menu", callback_data="solar_onboarding:back_to_main")]
        ])
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
        subsidies = solar_agent.search_subsidies(user_id)
        installers = solar_agent.search_installers(user_id)
        
        # Show options to the user
        options_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔍 Search Subsidies", callback_data="solar_onboarding:search_subsidies")],
            [InlineKeyboardButton("🏪 Find Installers", callback_data="solar_onboarding:find_installers")],
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
        subsidies = user_session.get("subsidies", [])
        
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
        print(subsidies_text)
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
                    callback_data=f"solar_onboarding:apply_subsidy:{subsidy.get('provider_id')}:{subsidy.get('id'):{fulfillment_id}}"
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
        fullfillment_id = callback_data[4]
        print(provider_id, subsidy_id, fullfillment_id)
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
                [InlineKeyboardButton("✅ Confirm Application", callback_data=f"solar_onboarding:confirm_subsidy:{provider_id}:{subsidy_id}:{fullfillment_id}")],
                [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:search_subsidies")]
            ])
        )
    
    elif action == "confirm_subsidy" and len(callback_data) >= 4:
        # User confirmed subsidy application
        provider_id = callback_data[2]
        subsidy_id = callback_data[3]
        fullfillment_id = callback_data[4]
        
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
        order_confirmation = solar_agent.confirm_order(user_id, provider_id, subsidy_id, fullfillment_id, customer_info)
        
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
            # User is selecting a specific solar panel product
            provider_id = callback_data[2]
            product_id = callback_data[3]
            
            # Update state
            update_user_session(user_id, {
                "state": "solar_onboarding_selecting_product",
                "selected_product_provider": provider_id,
                "selected_product": product_id
            })
            
            # This would normally call the Beckn API to select the product
            # For now, simulate the selection
            
            # Show product details and confirmation
            await query.edit_message_text(
                "You've selected this solar panel system. Would you like to purchase it?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Purchase Product", callback_data=f"solar_onboarding:init_product:{provider_id}:{product_id}")],
                    [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:find_products")]
                ])
            )
        
        elif action == "init_product" and len(callback_data) >= 4:
            # Initialize the order for the selected product
            provider_id = callback_data[2]
            product_id = callback_data[3]
            
            # This would normally call the Beckn API to initialize the product order
            # For now, simulate the initialization
            
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
        
        elif action == "provide_delivery_info" and len(callback_data) >= 4:
            # User is providing delivery info for product order
            provider_id = callback_data[2]
            product_id = callback_data[3]
            
            # In a real app, we would collect this info via form
            # Here we'll use example data for demonstration
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
            
            # Update state with delivery info
            update_user_session(user_id, {
                "state": "solar_onboarding_confirming_product",
                "delivery_info": customer_info
            })
            
            # This would normally call the Beckn API to confirm the product order
            # For now, simulate the confirmation
            
            # Generate a mock order ID
            import uuid
            mock_order_id = f"PROD-{str(uuid.uuid4())[:8]}"
            
            # Store the order ID
            update_user_session(user_id, {
                "state": "solar_onboarding_product_confirmed",
                "product_order_id": mock_order_id
            })
            
            await query.edit_message_text(
                "✅ *Solar Panel System Purchase Confirmed!*\n\n"
                f"Order ID: `{mock_order_id}`\n\n"
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
        # Search for solar panel products
        user_session = get_user_session(user_id)
        products = user_session.get("products", [])
        
        # If products weren't loaded yet, load them now
        if not products:
            products = solar_agent.search_solar_products(user_id)
        
        if not products:
            await query.edit_message_text(
                "I couldn't find any solar products at the moment. Please try again later.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")]
                ])
            )
            return
        
        # Format the products for display
        products_text = "Here are recommended solar panel systems for your needs:\n\n"
        
        product_buttons = []
        for i, product in enumerate(products[:3]):  # Show top 3 products
            name = product.get("name", "Unknown Product")
            description = product.get("description", "")
            price = product.get("price", "0")
            currency = product.get("currency", "USD")
            
            products_text += f"*{i+1}. {name}*\n"
            products_text += f"Description: {description}\n"
            products_text += f"Price: {price} {currency}\n\n"
            
            # Add a button for each product
            product_buttons.append([
                InlineKeyboardButton(
                    f"Select {name}", 
                    callback_data=f"solar_onboarding:select_product:{product.get('provider_id')}:{product.get('id')}"
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
        # Return to the main menu
        await handle_start(update, context)
    
    else:
        # Handle unknown action
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
            [InlineKeyboardButton("☀️⚡ Sell My Excess Solar", callback_data="energy_services:sell_energy")],
            [InlineKeyboardButton("📊 Track My Production", callback_data="energy_services:track_production")],
            [InlineKeyboardButton("💹 View Energy Stats", callback_data="energy_services:view_stats")],
            [InlineKeyboardButton("🎟️ Tokenize as NFTs", callback_data="energy_services:tokenize_energy")],
            [InlineKeyboardButton("🤖 Enable Auto-Trading", callback_data="energy_services:auto_trading")],
            [InlineKeyboardButton("🔌 P2P Energy Sharing", callback_data="energy_services:p2p_sharing")],
            [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="solar_onboarding:back_to_main")]
        ])

        await query.edit_message_text(
            "Welcome to Energy Services! 🌟\n\n"
            "As a prosumer with installed solar panels, you can now participate in the energy market. "
            "What would you like to do today?",
            reply_markup=energy_services_keyboard
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

    elif action == "sell_to_grid":
        # Execute a grid sale
        excess_energy = 5.0  # Example amount
        sale_result = prosumer_agent.execute_grid_sale(user_id, excess_energy)

        # Update user session
        user_session = get_user_session(user_id)
        transactions = user_session.get('transactions', [])
        transactions.append(sale_result)
        update_user_session(user_id, {"transactions": transactions, "state": "energy_services_sale_complete"})

        # Format the sale result for display
        result_text = (
            "✅ *Energy Sale Complete!*\n\n"
            f"Amount sold: {sale_result['amount_kwh']} kWh\n"
            f"Price: ${sale_result['price_per_kwh']}/kWh\n"
            f"Total earnings: ${sale_result['total_amount_usd']}\n"
            f"Transaction ID: {sale_result['transaction_id']}\n\n"
        )

        if sale_result.get('nft_details'):
            result_text += (
                "🎁 *NFT Reward*\n\n"
                f"Token ID: {sale_result['nft_details']['token_id']}\n"
                f"Value: ${sale_result['nft_details']['value_usd']}\n"
                f"Marketplace: {sale_result['nft_details']['marketplace_url']}\n\n"
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

    elif action == "share_p2p":
        # Execute a P2P sharing transaction
        excess_energy = 3.5  # Example amount
        sharing_result = prosumer_agent.execute_p2p_sharing(user_id, excess_energy)

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
        # P2P energy sharing interface
        update_user_session(user_id, {"state": "energy_services_p2p_sharing"})

        # Get energy production data
        production = prosumer_agent.get_energy_production(user_id)

        p2p_text = (
            "🔌 *Peer-to-Peer Energy Sharing*\n\n"
            "Share your excess solar energy directly with your neighbors and earn community points!\n\n"
            f"*Available to share:* {round(production['daily'][-1]['kwh'] * 0.6, 1)} kWh\n\n"
            "*Nearby energy consumers:*\n\n"
            "1. **Neighbor #4521** - 1.2 miles away\n   Needs: 2.5 kWh, Offers: $0.14/kWh\n\n"
            "2. **Community Center** - 0.8 miles away\n   Needs: 4.0 kWh, Offers: $0.13/kWh\n\n"
            "3. **Small Business #782** - 1.5 miles away\n   Needs: 3.0 kWh, Offers: $0.15/kWh\n\n"
            "Select a recipient to share your excess energy:"
        )

        p2p_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Share with Neighbor #4521", callback_data="energy_services:share_p2p:neighbor")],
            [InlineKeyboardButton("🏫 Share with Community Center", callback_data="energy_services:share_p2p:community")],
            [InlineKeyboardButton("🏪 Share with Small Business", callback_data="energy_services:share_p2p:business")],
            [InlineKeyboardButton("⬅️ Back", callback_data="energy_services:start")]
        ])

        await query.edit_message_text(
            p2p_text,
            reply_markup=p2p_keyboard,
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
    if user_session.get("state") != "solar_onboarding_awaiting_photo":
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
    analysis = rooftop_analyzer.analyze_image_url(file_url)

    # Store analysis in user state
    update_user_session(user_id, {"rooftop_analysis": analysis, "state": "solar_onboarding_roof_analyzed"})

    # Format the response based on suitability
    if analysis.get("suitable", False):
        response = (
            "✅ *Good News!* Your roof looks suitable for solar panels.\n\n"
            f"*Analysis Results:*\n"
            f"• Usable area: {analysis.get('suitable_area_sqm', 'N/A')} sq.m\n"
            f"• Potential capacity: {analysis.get('estimated_capacity_kw', 'N/A')} kW\n"
            f"• Estimated annual generation: {analysis.get('annual_generation_kwh', 'N/A')} kWh\n"
            f"• Roof orientation: {analysis.get('roof_orientation', 'N/A')}\n"
            f"• Shading factor: {analysis.get('shading_factor', 'N/A')}\n\n"
            "Would you like to calculate your potential savings with this system?"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("💰 Calculate ROI", callback_data="solar_onboarding:calculate_roi")],
            [InlineKeyboardButton("🔍 Find Installers", callback_data="solar_onboarding:find_installers")],
            [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")]
        ])
    else:
        response = (
            "⚠️ *Solar Potential Analysis*\n\n"
            "Based on the image provided, your roof may not be ideal for solar installation.\n\n"
            f"*Reason:* {analysis.get('reason', 'Unable to determine')}\n\n"
            "However, there might still be options! You could consider:\n"
            "• Having an installer perform an in-person assessment\n"
            "• Ground-mounted solar panels if you have available land\n"
            "• Community solar projects in your area\n\n"
            "Would you like to explore these alternatives?"
        )

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏪 Find Installers Anyway", callback_data="solar_onboarding:find_installers")],
            [InlineKeyboardButton("🌞 Explore Alternatives", callback_data="solar_onboarding:explore_alternatives")],
            [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")]
        ])

    await update.message.reply_markdown(response, reply_markup=keyboard)
