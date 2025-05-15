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

## 👥 Team Members

- [Your Name] - Project Lead & Developer
- [Team Member 2] - Backend Developer
- [Team Member 3] - Frontend Developer
- [Team Member 4] - UI/UX Designer

## 🧰 Tech Stack

### Backend
- Python 3.9+
- python-telegram-bot
- LangChain
- Beckn Protocol API
- PostgreSQL

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
git clone [repository-url]
cd [repository-name]
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Initialize the database:
```bash
python scripts/init_db.py
```

5. Run the bot:
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
   - Implementing real-time price calculations
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
- [Solar Panel Analysis API](https://api.example.com/solar)
- [Energy Trading API](https://api.example.com/trading)

### Community
- [Beckn Protocol Community](https://community.becknprotocol.io)
- [Telegram Bot Development](https://t.me/telegrambotdev)
- [Solar Energy Community](https://community.example.com/solar)
