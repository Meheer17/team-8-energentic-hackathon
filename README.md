# 🌟 SUNSHARE - Solar Energy Management Platform

A comprehensive Telegram bot that helps users manage their solar energy systems, find subsidies, connect with installers, and participate in the energy marketplace.

## 📌 Project Description

SUNSHARE is an intelligent platform that simplifies the journey of solar energy adoption and management. It helps users:
- Find and apply for solar subsidies
- Connect with certified solar installers
- Purchase solar panels and equipment
- Calculate ROI and energy savings
- Participate in energy trading
- Earn rewards through NFTs
- Share excess energy with neighbors

## 🧰 Tech Stack

### Backend
- Python 3.9+
- python-telegram-bot
- LangChain
- Beckn Protocol API

### Frontend
- Telegram Bot Interface
- Markdown Formatting
- Inline Keyboards

### APIs & Services
- Beckn Protocol for Solar Retail
- Solar Panel Analysis API
- Energy Trading API
- NFT Marketplace Integration

## 🚀 Setup Instructions

1. Clone the repository:
```bash
git clone [[repository-url]](https://github.com/Meheer17/team-8-energentic-hackathon)
cd team-8-energentic-hackathon
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
touch config/secrets.env
# Add the Following to the env
TELEGRAM_BOT_TOKEN=

# Beckn API Configuration - Using the real sandbox API
BECKN_BASE_URL=https://sandbox-api.beckn-energy.com
BECKN_BAP_ID=bap-ps-network-deg-team8.becknprotocol.io
BECKN_BAP_URI=https://bap-ps-network-deg-team8.becknprotocol.io
BECKN_BPP_ID=bpp-ps-network-deg-team8.becknprotocol.io
BECKN_BPP_URI=https://bpp-ps-network-deg-team8.becknprotocol.io
BECKN_MOCK_MODE=false

# Google Cloud / Vertex AI Configuration
GOOGLE_APPLICATION_CREDENTIALS={}

VERTEX_PROJECT_ID= 
VERTEX_LOCATION=
VERTEX_MODEL_ID=

# Application Settings
DEBUG=true
LOG_LEVEL=INFO

```

4. Run the bot:
```bash
python main.py
```

## 🎥 Demo Video Link

[Add your demo video link here]

## 📸 Screenshots / Visuals

### Main Menu
![Main Menu](screenshots/main_menu.png)

### Solar Onboarding
![Solar Onboarding](screenshots/solar_onboarding.png)

### Energy Services
![Energy Services](screenshots/energy_services.png)

## 📚 Challenges & Learnings

### Technical Challenges
1. **Beckn Protocol Integration**
   - Complex API integration with multiple endpoints
   - Handling asynchronous responses
   - Managing state across different flows

2. **Energy Trading Logic**
   - Implementing price calculations
   - Managing grid interactions
   - Handling P2P energy sharing

3. **User Experience**
   - Creating intuitive flows in a text-based interface
   - Managing complex state transitions
   - Providing clear feedback and error handling

### Key Learnings
1. **Beckn Protocol**
   - Understanding the protocol's architecture
   - Implementing standardized flows
   - Handling different response formats

2. **Energy Management**
   - Solar system sizing and optimization
   - Grid interaction patterns
   - Energy trading strategies

3. **Bot Development**
   - State management in Telegram bots
   - User session handling
   - Error recovery and graceful degradation

## 🔗 Useful Resources

### Documentation
- [Beckn Protocol Documentation](https://docs.becknprotocol.io)
- [python-telegram-bot Documentation](https://python-telegram-bot.readthedocs.io)
- [LangChain Documentation](https://python.langchain.com)

### APIs & Services
- [Beckn Network](https://becknprotocol.io)

### Community
- [Beckn Protocol Community](https://community.becknprotocol.io)
- [Telegram Bot Development](https://t.me/telegrambotdev)
- [Solar Energy Community](https://community.example.com/solar)
