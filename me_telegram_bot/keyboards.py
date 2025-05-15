from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu_keyboard():
    """Create the main menu keyboard with onboarding and energy services options."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Onboard for Rooftop Solar", callback_data="solar_onboarding:start"),
        ],
        [
            InlineKeyboardButton("⚡ Use My Installed System", callback_data="energy_services:start"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_solar_onboarding_keyboard():
    """Create keyboard for solar onboarding options."""
    keyboard = [
        [InlineKeyboardButton("🔍 Search Subsidies", callback_data="solar_onboarding:search_subsidies")],
        [InlineKeyboardButton("🏪 Find Installers", callback_data="solar_onboarding:find_installers")],
        [InlineKeyboardButton("💰 Explore Financing", callback_data="solar_onboarding:explore_financing")],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="solar_onboarding:back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_energy_services_keyboard():
    """Create keyboard for energy services options."""
    keyboard = [
        [InlineKeyboardButton("☀️⚡ Sell My Excess Solar", callback_data="energy_services:sell_energy")],
        [InlineKeyboardButton("📊 Track My Production", callback_data="energy_services:track_production")],
        [InlineKeyboardButton("💰 Earn by Shifting Usage", callback_data="energy_services:shift_usage")],
        [InlineKeyboardButton("🎟️ Tokenize as NFTs", callback_data="energy_services:tokenize_energy")],
        [InlineKeyboardButton("💹 View Savings & Earnings", callback_data="energy_services:view_savings")],
        [InlineKeyboardButton("🔍 Find Local Buyers", callback_data="energy_services:find_buyers")],
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="solar_onboarding:back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_subsidy_options_keyboard(arr):
    """Create keyboard for subsidy options."""
    keyboard = [[InlineKeyboardButton(f"{i+1}", callback_data="solar_onboarding:apply_tou_plan")] for i in range(0,len(arr))]
    keyboard.append(
       [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")]
    )
    return InlineKeyboardMarkup(keyboard)

def get_installer_options_keyboard():
    """Create keyboard for installer options."""
    keyboard = [
        [InlineKeyboardButton("Contact Luminalt", callback_data="solar_onboarding:contact_luminalt")],
        [InlineKeyboardButton("Contact Sunrun", callback_data="solar_onboarding:contact_sunrun")],
        [InlineKeyboardButton("Contact SolarUnion", callback_data="solar_onboarding:contact_solarunion")],
        [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_financing_options_keyboard():
    """Create keyboard for financing options."""
    keyboard = [
        [InlineKeyboardButton("Apply for Solar Loan", callback_data="solar_onboarding:apply_loan")],
        [InlineKeyboardButton("Apply for Solar Lease", callback_data="solar_onboarding:apply_lease")],
        [InlineKeyboardButton("Apply for PPA", callback_data="solar_onboarding:apply_ppa")],
        [InlineKeyboardButton("⬅️ Back", callback_data="solar_onboarding:confirm")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_back_to_main_keyboard():
    """Create keyboard with just a back to main menu button."""
    keyboard = [
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="solar_onboarding:back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_confirm_cancel_keyboard(confirm_data, cancel_data):
    """Create a confirmation keyboard with confirm and cancel options."""
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=confirm_data)],
        [InlineKeyboardButton("❌ Cancel", callback_data=cancel_data)]
    ]
    return InlineKeyboardMarkup(keyboard)
