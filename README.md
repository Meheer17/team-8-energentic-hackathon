# SUNSHARE 

A Telegram-based intelligent agent platform for solar onboarding and energy services, built for the DEG Hackathon 2025. This platform provides an AI-powered assistant that helps users with solar panel installation and energy services management.

## 👥 Team Members

1) NANDAKISHORE P
2) MEHEER J
3) VISHNU S
4) SALAHUDHEEN THAJUDHEEN

## 🧰 Tech Stack

- **Frontend**: Telegram Bot Interface
- **Backend**: Python
- **AI/ML**: 
  - LangChain for NLP and reasoning
  - Google Vertex AI for image analysis
  - OpenAI's GPT models
- **APIs & Protocols**:
  - Beckn Protocol for energy services
  - Google Cloud Vision API
  - Blockchain for energy NFTs

## 🚀 Setup Instructions

1. Clone the repository:
```bash
git clone https://github.com/Meheer17/team-8-energentic-hackathon/
cd team-8-energentic-hackathon
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp config/secrets.env.example config/secrets.env
# Edit the secrets.env file with your credentials
```

4. Run the application:
```bash
python main.py
```

## 🎥 Demo Video Link

[Add your demo video link here]

## 📸 Screenshots / Visuals

<div align="center">
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/1f.jpeg" width="400" alt="SunShare Screenshot 1" />
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/2f.jpeg" width="400" alt="SunShare Screenshot 2" />
</div>

<div align="center">
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/3f.jpeg" width="400" alt="SunShare Screenshot 3" />
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/4f.jpeg" width="400" alt="SunShare Screenshot 4" />
</div>

<div align="center">
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/5f.jpeg" width="400" alt="SunShare Screenshot 5" />
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/6f.jpeg" width="400" alt="SunShare Screenshot 6" />
</div>

<div align="center">
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/7f.jpeg" width="400" alt="SunShare Screenshot 7" />
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/8f.jpeg" width="400" alt="SunShare Screenshot 8" />
</div>

<div align="center">
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/9f.jpeg" width="400" alt="SunShare Screenshot 9" />
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/10f.jpeg" width="400" alt="SunShare Screenshot 10" />
</div>

<div align="center">
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/11f.jpeg" width="400" alt="SunShare Screenshot 11" />
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/12f.jpeg" width="400" alt="SunShare Screenshot 12" />
</div>

<div align="center">
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/13f.jpeg" width="400" alt="SunShare Screenshot 13" />
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/14f.jpeg" width="400" alt="SunShare Screenshot 14" />
</div>

<div align="center">
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/15f.jpeg" width="400" alt="SunShare Screenshot 15" />
    <img src="https://github.com/Meheer17/team-8-energentic-hackathon/blob/6452217dafdae90aaf7d75ec69b9a363660abed5/screenshots/16f.jpeg" width="400" alt="SunShare Screenshot 16" />
</div>

## 📚 Challenges & Learnings

Throughout this hackathon, we encountered several challenges:

- Integrating multiple AI services (GPT, Vertex AI, LangChain) into a cohesive workflow
- Building a responsive Telegram bot interface that handles various media types
- Implementing the Beckn Protocol for energy services discovery
- Managing authentication and security across multiple APIs
- Optimizing performance for real-time image analysis

Key learnings:

- The importance of modular architecture in complex AI systems
- Effective prompt engineering for specialized energy domain knowledge
- Leveraging blockchain for transparent energy trading mechanisms
- Because documentation was awesome, it took us no time to just focus our minds on solving the real challenges
- The value of user-centric design even in technical B2B applications

## 🔗 Useful Resources

- [Beckn Protocol Documentation](https://docs.becknprotocol.io)
- [Google Cloud Vision API](https://cloud.google.com/vision)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [LangChain Documentation](https://python.langchain.com/docs/get_started/introduction)

## Features

### Solar Onboarding Agent
- Rooftop image analysis for solar potential
- Address-based subsidy and incentive discovery
- Solar installer matching and recommendations
- ROI calculation and financial projections
- Simplified paperwork and documentation assistance

### Prosumer Energy Agent
- Energy production monitoring and visualization
- Energy trading opportunities discovery
- Demand response program participation
- NFT tokenization of energy credits
- AI-powered automatic energy trading

## Architecture

The platform uses a modular architecture:
- Telegram Bot: User interface and interaction
- LangChain: Natural language processing and reasoning
- Beckn Protocol: Integration with energy ecosystem
- Google Vertex AI: Image analysis and large language models

## API Integrations

- Beckn Protocol for energy services discovery and transaction
- Google Cloud Vision API for rooftop image analysis
- OpenAI's GPT models for natural language understanding
- Blockchain integration for energy NFTs

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- DEG for organizing the hackathon
- Beckn Protocol for the energy services framework
- OpenAI and Google for their powerful AI models# Energentic_hackathon
