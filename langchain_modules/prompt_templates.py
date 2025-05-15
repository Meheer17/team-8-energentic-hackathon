from langchain.prompts import PromptTemplate

# Prompt for handling user messages and determining intent
USER_INTENT_PROMPT = PromptTemplate.from_template(
    """You are an Energy Agent assistant that helps users with solar onboarding and energy services.
    
    Analyze the following user message and determine their primary intent:
    User Message: {user_message}
    
    Possible intents:
    1. SOLAR_ONBOARDING - User wants to install solar panels or learn about the process
    2. ENERGY_SERVICES - User wants to use/manage their existing solar system (sell energy, participate in demand response)
    3. SUBSIDY_INFO - User wants information about subsidies, incentives, or financing
    4. INSTALLER_INFO - User wants to find solar installers
    5. ROI_CALCULATION - User wants to calculate return on investment for solar
    6. GENERAL_INFO - General questions about solar or the bot
    7. OTHER - Other requests not covered above
    
    Return the most likely intent category from the list above and a confidence score (0-1).
    
    Intent:
    """
)

# Prompt for extracting structured information from user messages
INFO_EXTRACTION_PROMPT = PromptTemplate.from_template(
    """Extract the following structured information from the user message if present:
    
    User Message: {user_message}
    
    Extract these fields if they are mentioned (use null for missing values):
    - address: Any address or location information
    - electricity_consumption: Electricity consumption in kWh (just the number)
    - energy_type: Type of energy mentioned (solar, wind, etc.)
    - budget: Any budget information (just the number in dollars)
    - timeframe: When they want to install or use the system
    - property_type: Type of property (residential, commercial, etc.)
    
    Format your response as a JSON object.
    """
)

# Prompt for generating subsidy recommendations
SUBSIDY_RECOMMENDATION_PROMPT = PromptTemplate.from_template(
    """Based on the user's information and available subsidies, recommend the most suitable subsidies.
    
    User Information:
    - Location: {location}
    - Electricity Consumption: {electricity_consumption} kWh
    - Property Type: {property_type}
    
    Available Subsidies:
    {subsidies_list}
    
    Provide the top 3 recommended subsidies with brief explanations for why each is a good fit.
    Format your recommendations in a friendly, helpful way with emoji.
    """
)

# Prompt for generating installer recommendations
INSTALLER_RECOMMENDATION_PROMPT = PromptTemplate.from_template(
    """Based on the user's information and available installers, recommend the most suitable installers.
    
    User Information:
    - Location: {location}
    - System Size: {system_size} kW
    - Budget: {budget}
    
    Available Installers:
    {installers_list}
    
    Provide the top 3 recommended installers with brief explanations for why each is a good fit.
    Include pricing, experience, and any special features in your explanation.
    Format your recommendations in a friendly, helpful way with emoji.
    """
)

# Prompt for generating ROI explanations
ROI_EXPLANATION_PROMPT = PromptTemplate.from_template(
    """Explain the following solar ROI calculation in simple terms that a non-technical user can understand:
    
    System Size: {system_size} kW
    System Cost: ${system_cost}
    Annual Production: {annual_production} kWh
    Annual Savings: ${annual_savings}
    Payback Period: {payback_years} years
    20-Year ROI: {roi_20_year}%
    
    Use simple language, analogies, and highlight the financial benefits. Format your explanation with 
    clear sections and emojis to make it visually engaging.
    """
)

# Prompt for analyzing rooftop images
ROOFTOP_IMAGE_PROMPT = PromptTemplate.from_template(
    """You are analyzing a satellite or user-uploaded image of a rooftop to assess solar potential.
    
    Image Description: {image_description}
    
    First, determine if the image shows a clear view of a rooftop. Then, analyze the following:
    1. Approximate usable roof area (rough estimate in sq meters)
    2. Roof orientation (north, south, east, west facing)
    3. Potential shading issues (trees, buildings, etc.)
    4. Roof type (flat, sloped, complex)
    5. Overall suitability for solar installation (high, medium, low)
    
    Format your analysis in a structured way that highlights the key findings.
    """
)

# Prompt for energy trading recommendations
ENERGY_TRADING_PROMPT = PromptTemplate.from_template(
    """Based on the user's energy production data and available trading opportunities, provide recommendations:
    
    User's Energy Production:
    {production_data}
    
    Available Trading Opportunities:
    {trading_opportunities}
    
    User's Goals: {user_goals}
    
    Recommend the best trading strategies for this user to maximize their {optimization_target} (financial returns, environmental impact, or balanced approach).
    Include specific actions they should take and expected outcomes.
    """
)

# Prompt for NFT tokenization recommendations
NFT_RECOMMENDATION_PROMPT = PromptTemplate.from_template(
    """The user wants to tokenize their energy production or credits as NFTs.
    
    User's Energy Data:
    {energy_data}
    
    Available NFT Opportunities:
    {nft_opportunities}
    
    User's Experience Level: {experience_level}
    
    Explain in simple terms:
    1. How energy tokenization works
    2. The benefits for this specific user
    3. Recommended NFT option based on their data
    4. Step-by-step process to create their first energy NFT
    5. Potential financial and environmental benefits
    
    Make your explanation accessible to someone with {experience_level} blockchain experience.
    """
)

# Prompt for auto-trading strategy configuration
AUTO_TRADING_PROMPT = PromptTemplate.from_template(
    """Help configure an AI-powered auto-trading strategy for the user's excess solar energy.
    
    User's Energy Profile:
    {energy_profile}
    
    User's Preferences:
    - Risk Tolerance: {risk_tolerance}
    - Optimization Goal: {optimization_goal}
    - Time Horizon: {time_horizon}
    
    Recommend optimal settings for:
    1. Minimum selling price ($/kWh)
    2. Maximum buying price ($/kWh)
    3. Best times to sell (time windows)
    4. Reserve capacity percentage
    5. AI optimization target
    
    Provide a clear explanation for each recommendation based on the user's specific situation.
    """
)

# Environmental impact calculation prompt
ENVIRONMENTAL_IMPACT_PROMPT = PromptTemplate.from_template(
    """Calculate and explain the environmental impact of the user's solar system in understandable terms.
    
    Solar System Details:
    - System Size: {system_size} kW
    - Annual Production: {annual_production} kWh
    - System Lifetime: 25 years
    
    Calculate:
    1. Annual carbon offset (in kg CO2)
    2. Lifetime carbon offset
    3. Equivalent in trees planted
    4. Equivalent in miles not driven
    5. Other meaningful environmental metrics
    
    Present the information in a way that makes the impact tangible and meaningful to the average person.
    Use comparisons and visualizations in your explanation.
    """
)