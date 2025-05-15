# DEG Energy Agentic Platform

A Telegram-based intelligent agent platform for solar onboarding and energy services, built for the DEG Hackathon 2025.

## Overview

This platform provides an AI-powered assistant that helps users with:

1. **Solar Onboarding (Use Case 1)**: Guides users through the process of getting solar panels installed on their rooftops, including subsidy discovery, installer matching, and ROI calculation.

2. **Energy Services (Use Case 2)**: Helps users with installed solar systems to participate in energy markets, sell excess energy, earn through demand response, and tokenize their energy as NFTs.

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

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/deg-hackathon-2025.git
cd deg-hackathon-2025/deg_agentic_platform
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Set up environment variables:
```
cp config/secrets.env.example config/secrets.env
# Edit the secrets.env file with your credentials
```

4. Run the application:
```
python main.py
```

## Usage

1. Start the Telegram bot by sending `/start`
2. Choose between "Onboard for Rooftop Solar" or "Use My Installed System"
3. Follow the interactive prompts and respond to the bot's questions
4. Upload images, provide location info, and receive personalized recommendations

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
