import logging
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, date, timedelta
import random  # For simulating time-based energy data

from beckn.api_client import BecknAPIClient
from beckn.utils import extract_energy_programs_from_response, extract_energy_trading_opportunities, extract_order_details

logger = logging.getLogger(__name__)

class ProsumerEnergyAgent:
    """Agent responsible for managing energy services for prosumers with installed solar."""
    
    def __init__(self):
        """Initialize the prosumer energy agent."""
        self.beckn_client = BecknAPIClient()
        self.state = {}
        
        # Initialize AI if available
        try:
            # Using Google Vertex AI if configured
            from google.cloud import aiplatform
            from langchain_community.llms import VertexAI
            from langchain.chains import LLMChain
            from langchain.prompts import PromptTemplate
            
            project_id = os.getenv("VERTEX_PROJECT_ID")
            location = os.getenv("VERTEX_LOCATION", "us-central1")
            model_id = os.getenv("VERTEX_MODEL_ID", "text-bison")
            
            if project_id:
                aiplatform.init(project=project_id, location=location)
                self.llm = VertexAI(model_name=model_id)
                
                # Define auto-trading prompt
                self.auto_trade_prompt = PromptTemplate(
                    input_variables=["time_of_day", "current_price", "forecast", "user_preferences"],
                    template="""
                    As an AI energy trading assistant, please determine the optimal action based on:
                    
                    Time of day: {time_of_day}
                    Current energy price: ${current_price}/kWh
                    Weather forecast: {forecast}
                    User preferences: {user_preferences}
                    
                    Should we:
                    1. Sell excess energy to the grid
                    2. Store energy in batteries
                    3. Share energy with neighbors (P2P)
                    4. Buy energy from the grid
                    
                    Return only the action number (1-4) and a brief explanation.
                    """
                )
                self.auto_trade_chain = LLMChain(llm=self.llm, prompt=self.auto_trade_prompt)
                self.ai_available = True
                logger.info("AI trading assistant initialized successfully")
            else:
                self.ai_available = False
                logger.warning("Vertex AI not configured - using rule-based trading only")
        except Exception as e:
            logger.error(f"Failed to initialize AI trading assistant: {e}")
            self.ai_available = False
    
    def load_state(self, user_id: str, state_data: Dict[str, Any]) -> None:
        """Load agent state for a specific user."""
        self.state[user_id] = state_data
    
    def get_state(self, user_id: str) -> Dict[str, Any]:
        """Get the current state for a user."""
        return self.state.get(user_id, {})
    
    def search_energy_programs(self, user_id: str) -> List[Dict[str, Any]]:
        """Search for energy flexibility programs."""
        try:
            # Call Beckn API to search for energy programs
            response = self.beckn_client.search_energy_programs("Program")
            
            # Process the response
            programs = extract_energy_programs_from_response(response)
            
            # Store in state
            if user_id in self.state:
                self.state[user_id]['programs'] = programs
            else:
                self.state[user_id] = {'programs': programs}
                
            return programs
            
        except Exception as e:
            logger.error(f"Error searching energy programs for user {user_id}: {str(e)}")
            return []
    
    def enroll_in_program(self, user_id: str, provider_id: str, program_id: str, fulfillment_id: str, customer_info: Dict[str, Any]) -> Dict[str, Any]:
        """Enroll a user in an energy flexibility program."""
        try:
            # Call Beckn API to confirm enrollment
            response = self.beckn_client.confirm_order(
                provider_id, 
                program_id, 
                fulfillment_id, 
                customer_info, 
                domain="deg:schemes"
            )
            
            # Extract order details
            enrollment = extract_order_details(response)
            
            # Store in state
            if user_id in self.state:
                self.state[user_id]['enrollment'] = enrollment
            else:
                self.state[user_id] = {'enrollment': enrollment}
                
            return enrollment
            
        except Exception as e:
            logger.error(f"Error enrolling user {user_id} in program: {str(e)}")
            return {}
    
    def get_energy_production(self, user_id: str, date_from: str = None, date_to: str = None) -> Dict[str, Any]:
        """Get energy production data for a user's solar system."""
        # In a production system, this would call real monitoring APIs
        # For now, generating realistic data
        
        if not date_from:
            # Default to last 7 days
            from_date = date.today() - timedelta(days=7)
        else:
            from_date = datetime.strptime(date_from, "%Y-%m-%d").date()
            
        if not date_to:
            to_date = date.today()
        else:
            to_date = datetime.strptime(date_to, "%Y-%m-%d").date()
        
        # Create daily data with realistic variance
        daily_data = []
        total_kwh = 0
        
        # Get base production from user state or use default
        user_state = self.get_state(user_id)
        system_size_kw = user_state.get('system_size_kw', 5.0)
        base_daily_production = system_size_kw * 4.5  # Avg 4.5 kWh per kW of system
        
        current_date = from_date
        while current_date <= to_date:
            # Add some daily randomness (weather effects)
            if current_date.weekday() >= 5:  # Weekends slightly sunnier
                weather_factor = random.uniform(0.95, 1.1)
            else:
                weather_factor = random.uniform(0.8, 1.05)
                
            daily_kwh = round(base_daily_production * weather_factor, 1)
            total_kwh += daily_kwh
            
            daily_data.append({
                "date": current_date.strftime("%Y-%m-%d"),
                "kwh": daily_kwh
            })
            
            current_date += timedelta(days=1)
        
        # Calculate other metrics
        peak_kw = round(system_size_kw * random.uniform(0.85, 0.95), 1)
        carbon_offset_kg = round(total_kwh * 0.5, 1)  # 0.5 kg CO2 per kWh
        
        return {
            "total_kwh": round(total_kwh, 1),
            "daily": daily_data,
            "peak_kw": peak_kw,
            "carbon_offset_kg": carbon_offset_kg
        }
    
    def get_energy_trading_opportunities(self, user_id: str) -> List[Dict[str, Any]]:
        """Get available energy trading opportunities in the user's area."""
        try:
            # Call Beckn API to search for trading opportunities
            response = self.beckn_client.search_energy_trading_opportunities()
            
            # Process the response
            opportunities = extract_energy_trading_opportunities(response)
            
            # If API returned no results, generate placeholder data
            if not opportunities:
                opportunities = [
                    {
                        "id": "opp-1",
                        "provider_id": "grid-op-1",
                        "provider_name": "Local Grid Operator",
                        "type": "sell_excess",
                        "name": "Peak Hour Selling",
                        "description": "Sell excess solar production during peak hours",
                        "price_per_kwh": 0.15,
                        "currency": "USD"
                    },
                    {
                        "id": "opp-2",
                        "provider_id": "community-1",
                        "provider_name": "Community Energy Group",
                        "type": "p2p_sharing",
                        "name": "Community Sharing",
                        "description": "Share excess with local community energy group",
                        "price_per_kwh": 0.12,
                        "currency": "USD"
                    }
                ]
            
            # Store in state
            if user_id in self.state:
                self.state[user_id]['trading_opportunities'] = opportunities
            else:
                self.state[user_id] = {'trading_opportunities': opportunities}
                
            return opportunities
            
        except Exception as e:
            logger.error(f"Error getting trading opportunities for user {user_id}: {str(e)}")
            return []
    
    def get_nft_opportunities(self, user_id: str) -> List[Dict[str, Any]]:
        """Get available NFT tokenization opportunities for energy credits."""
        # This would integrate with blockchain services in production
        # For now, return standard options
        
        opportunities = [
            {
                "id": "nft-1",
                "type": "renewable_credit",
                "description": "Tokenize your renewable energy production as carbon credits",
                "value_per_mwh": 25.00,
                "value_per_event": 0,
                "minimum_amount_kwh": 100,
                "marketplace": "GreenToken Exchange",
                "blockchain": "Ethereum"
            },
            {
                "id": "nft-2",
                "type": "grid_flexibility",
                "description": "Tokenize your grid flexibility contributions",
                "value_per_mwh": 0,
                "value_per_event": 15.00,
                "minimum_events": 5,
                "marketplace": "FlexChain",
                "blockchain": "Polygon"
            }
        ]
        
        return opportunities
    
    def get_energy_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive energy stats for the user."""
        user_state = self.get_state(user_id)
        system_size_kw = user_state.get('system_size_kw', 5.0)
        
        # Monthly estimate = system size * 120 kWh per kW
        monthly_production = system_size_kw * 120
        
        # Get today's production (simulated)
        today_hour = datetime.now().hour
        if today_hour <= 6 or today_hour >= 19:  # No production early/late
            today_production = 0
        else:
            # Simulate bell curve production during daylight
            daylight_hour = today_hour - 6  # 0-12 scale
            if daylight_hour > 6:
                daylight_factor = 12 - daylight_hour
            else:
                daylight_factor = daylight_hour
            today_production = round(system_size_kw * 0.9 * (daylight_factor / 6), 1)
        
        # Create stats object
        stats = {
            "production": {
                "today_kwh": today_production,
                "week_kwh": round(monthly_production / 4, 1),
                "month_kwh": round(monthly_production, 1),
                "lifetime_kwh": round(monthly_production * user_state.get('months_active', 12), 1)
            },
            "consumption": {
                "today_kwh": round(today_production * 0.7, 1),
                "week_kwh": round(monthly_production / 4 * 0.8, 1),
                "month_kwh": round(monthly_production * 0.8, 1),
                "lifetime_kwh": round(monthly_production * user_state.get('months_active', 12) * 0.8, 1)
            },
            "grid_interaction": {
                "exported_kwh": round(monthly_production * 0.3, 1),
                "imported_kwh": round(monthly_production * 0.1, 1),
                "self_consumption_pct": 70
            },
            "financial": {
                "savings_current_month_usd": round(monthly_production * 0.8 * 0.15, 2),
                "earnings_current_month_usd": round(monthly_production * 0.3 * 0.12, 2),
                "lifetime_savings_usd": round(monthly_production * user_state.get('months_active', 12) * 0.8 * 0.15, 2),
                "projected_annual_savings_usd": round(monthly_production * 12 * 0.8 * 0.15, 2)
            },
            "environmental": {
                "carbon_offset_kg": round(monthly_production * user_state.get('months_active', 12) * 0.5, 1),
                "trees_equivalent": round(monthly_production * user_state.get('months_active', 12) * 0.5 / 60, 1),
                "miles_not_driven_equivalent": round(monthly_production * user_state.get('months_active', 12) * 2.5, 1)
            }
        }
        
        return stats
    
    def create_energy_nft(self, user_id: str, nft_type: str, amount: float) -> Dict[str, Any]:
        """Create an NFT token for energy credits."""
        try:
            # Call Beckn API to create NFT
            # For now, simulating response
            
            if nft_type == "renewable_credit":
                value_usd = amount * 0.025  # $25 per MWh
                marketplace = "GreenToken Exchange"
                blockchain = "Ethereum"
            else:
                value_usd = 15.0  # $15 per flexibility event
                marketplace = "FlexChain"
                blockchain = "Polygon"
            
            token_id = f"nft-{user_id[:4]}-{nft_type[:4]}-{int(datetime.now().timestamp())}"
            marketplace_url = f"https://{marketplace.lower().replace(' ', '')}.io/token/{token_id}"
            
            nft_details = {
                "token_id": token_id,
                "status": "created",
                "value_usd": round(value_usd, 2),
                "blockchain": blockchain,
                "contract_address": f"0x{token_id}abcdef1234567890abcdef12345678",
                "creation_time": datetime.now().isoformat(),
                "marketplace": marketplace,
                "marketplace_url": marketplace_url,
                "type": nft_type
            }
            
            # Store in state
            if user_id in self.state:
                if 'nfts' not in self.state[user_id]:
                    self.state[user_id]['nfts'] = []
                self.state[user_id]['nfts'].append(nft_details)
            else:
                self.state[user_id] = {'nfts': [nft_details]}
                
            return nft_details
            
        except Exception as e:
            logger.error(f"Error creating energy NFT for user {user_id}: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "type": nft_type
            }
    
    def enable_auto_trading(self, user_id: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Enable automated energy trading using AI."""
        default_settings = {
            "min_sell_price_kwh": 0.12,
            "max_buy_price_kwh": 0.08,
            "trading_hours": "8:00-20:00",
            "reserve_capacity_pct": 20,
            "ai_optimization_target": "financial",  # financial, environmental, or balanced
            "auto_participation": True,
            "neighbor_sharing_enabled": True,
            "token_rewards": True,
            "peak_time_selling": True,
            "off_peak_buying": True
        }
        
        # Merge user settings with defaults
        final_settings = {**default_settings, **settings}
        
        # Store in state
        if user_id in self.state:
            self.state[user_id]['auto_trading'] = final_settings
        else:
            self.state[user_id] = {'auto_trading': final_settings}
            
        # Estimate monthly benefit based on system size and settings
        user_state = self.get_state(user_id)
        system_size_kw = user_state.get('system_size_kw', 5.0)
        
        if final_settings["ai_optimization_target"] == "financial":
            benefit_factor = 0.9
        elif final_settings["ai_optimization_target"] == "environmental":
            benefit_factor = 0.7
        else:
            benefit_factor = 0.8
            
        estimated_benefit = round(system_size_kw * 15 * benefit_factor, 2)
            
        return {
            "status": "enabled",
            "configured_at": datetime.now().isoformat(),
            "settings": final_settings,
            "estimated_monthly_benefit_usd": estimated_benefit
        }
    
    def execute_auto_trading(self, user_id: str) -> Dict[str, Any]:
        """Execute auto-trading based on current conditions and user preferences."""
        user_state = self.get_state(user_id)
        auto_trading_settings = user_state.get('auto_trading', {})
        
        if not auto_trading_settings.get('auto_participation', False):
            return {"status": "disabled", "message": "Auto-trading is disabled"}
        
        # Get current time, energy price, and weather forecast
        current_hour = datetime.now().hour
        is_peak_time = 12 <= current_hour <= 20  # Example peak time definition
        
        # For demonstration, using price based on peak/off-peak
        current_price = 0.22 if is_peak_time else 0.08  # Higher during peak hours
        
        # Weather forecast (would come from weather API in production)
        forecast = "sunny" if random.random() > 0.3 else "cloudy"
        
        # Get energy production data
        production = self.get_energy_production(user_id)
        current_production = production["daily"][-1]["kwh"] / 24  # Approximate hourly production
        
        # Determine if we have excess energy to sell/share
        has_excess = current_production > 2.0  # Example threshold
        
        # Make trading decision
        if hasattr(self, 'ai_available') and self.ai_available:
            # Use AI to make a decision
            user_preferences = f"""
            Optimization target: {auto_trading_settings.get('ai_optimization_target', 'financial')}
            Min selling price: ${auto_trading_settings.get('min_sell_price_kwh', 0.12)}/kWh
            Max buying price: ${auto_trading_settings.get('max_buy_price_kwh', 0.08)}/kWh
            Neighbor sharing enabled: {auto_trading_settings.get('neighbor_sharing_enabled', True)}
            Reserve capacity: {auto_trading_settings.get('reserve_capacity_pct', 20)}%
            """
            
            time_of_day = "peak hours" if is_peak_time else "off-peak hours"
            
            try:
                ai_decision = self.auto_trade_chain.run({
                    "time_of_day": time_of_day,
                    "current_price": current_price,
                    "forecast": forecast,
                    "user_preferences": user_preferences
                })
                
                # Parse the AI decision
                action_num = None
                explanation = ai_decision
                
                for i in range(1, 5):
                    if str(i) in ai_decision[:10]:  # Check beginning of response
                        action_num = i
                        break
                
                if action_num == 1 and has_excess:
                    # Sell excess energy to grid
                    trade_result = self.execute_grid_sale(user_id, current_production * 0.7)  # Sell 70% of production
                    action = "sell_to_grid"
                elif action_num == 2 and has_excess:
                    # Store energy in batteries
                    trade_result = {"status": "stored", "amount_kwh": current_production * 0.8, "message": "Energy stored in batteries"}
                    action = "store_in_battery"
                elif action_num == 3 and has_excess and auto_trading_settings.get('neighbor_sharing_enabled', True):
                    # Share with neighbors (P2P)
                    trade_result = self.execute_p2p_sharing(user_id, current_production * 0.6)  # Share 60% of production
                    action = "share_with_neighbors"
                elif action_num == 4 and not is_peak_time and auto_trading_settings.get('off_peak_buying', True):
                    # Buy from grid during off-peak
                    trade_result = self.execute_grid_purchase(user_id, 5.0)  # Buy 5 kWh
                    action = "buy_from_grid"
                else:
                    # No action taken
                    trade_result = {"status": "no_action", "message": "Conditions not optimal for trading"}
                    action = "no_action"
            except Exception as e:
                logger.error(f"Error in AI trading decision: {e}")
                trade_result = {"status": "error", "message": f"AI trading error: {str(e)}"}
                action = "error"
                explanation = str(e)
        else:
            # Fallback to rule-based trading if AI is not available
            if has_excess and is_peak_time and auto_trading_settings.get('peak_time_selling', True):
                # Sell during peak hours if we have excess
                trade_result = self.execute_grid_sale(user_id, current_production * 0.7)
                action = "sell_to_grid"
                explanation = "Selling excess energy during peak hours for maximum profit"
            elif not is_peak_time and not has_excess and auto_trading_settings.get('off_peak_buying', True):
                # Buy during off-peak hours if we need energy
                trade_result = self.execute_grid_purchase(user_id, 5.0)
                action = "buy_from_grid"
                explanation = "Buying energy during off-peak hours at lower prices"
            else:
                # No action
                trade_result = {"status": "no_action", "message": "Conditions not optimal for trading"}
                action = "no_action"
                explanation = "Current conditions do not warrant trading actions"
        
        # Log the trading activity
        trading_record = {
            "timestamp": datetime.now().isoformat(),
            "user_id": user_id,
            "action": action,
            "explanation": explanation,
            "is_peak_time": is_peak_time,
            "current_price": current_price,
            "current_production": current_production,
            "result": trade_result
        }
        
        # Store in state
        if user_id in self.state:
            if 'trading_history' not in self.state[user_id]:
                self.state[user_id]['trading_history'] = []
            self.state[user_id]['trading_history'].append(trading_record)
        
        return trading_record
    
    def execute_grid_sale(self, user_id: str, amount_kwh: float) -> Dict[str, Any]:
        """Execute a sale of energy to the grid."""
        try:
            # Call Beckn API to execute the trade
            user_state = self.get_state(user_id)
            auto_trading_settings = user_state.get('auto_trading', {})
            
            # Calculate price
            price_per_kwh = max(0.18, auto_trading_settings.get('min_sell_price_kwh', 0.12))
            
            # Get trading opportunities
            opportunities = self.get_energy_trading_opportunities(user_id)
            
            if opportunities:
                provider_id = opportunities[0]["provider_id"]
            else:
                provider_id = "grid-op-1"  # Default if no providers found
            
            # Execute the energy trade via API
            response = self.beckn_client.execute_energy_trade(
                provider_id, 
                amount_kwh, 
                price_per_kwh, 
                "SELL"
            )
            
            # Process response
            transaction_id = f"grid-{user_id[:4]}-{int(datetime.now().timestamp())}"
            
            order = extract_order_details(response)
            if order and order.get("id"):
                transaction_id = order["id"]
            
            # Generate NFT token if enabled
            nft_details = None
            if auto_trading_settings.get('token_rewards', False):
                nft_details = self.create_energy_nft(user_id, "renewable_credit", amount_kwh)
            
            sale_result = {
                "status": "completed",
                "transaction_type": "grid_sale",
                "amount_kwh": amount_kwh,
                "price_per_kwh": price_per_kwh,
                "total_amount_usd": round(amount_kwh * price_per_kwh, 2),
                "transaction_id": transaction_id,
                "timestamp": datetime.now().isoformat(),
                "nft_details": nft_details
            }
            
            # Update user stats
            if user_id in self.state:
                if 'transactions' not in self.state[user_id]:
                    self.state[user_id]['transactions'] = []
                self.state[user_id]['transactions'].append(sale_result)
                
                # Update total earnings
                self.state[user_id]['total_earnings'] = self.state[user_id].get('total_earnings', 0) + sale_result["total_amount_usd"]
            
            return sale_result
            
        except Exception as e:
            logger.error(f"Error executing grid sale for user {user_id}: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "transaction_type": "grid_sale",
                "amount_kwh": amount_kwh
            }
    
    def execute_grid_purchase(self, user_id: str, amount_kwh: float) -> Dict[str, Any]:
        """Execute a purchase of energy from the grid."""
        try:
            # Call Beckn API to execute the trade
            user_state = self.get_state(user_id)
            auto_trading_settings = user_state.get('auto_trading', {})
            
            # Calculate price
            price_per_kwh = min(0.10, auto_trading_settings.get('max_buy_price_kwh', 0.08))
            
            # Get trading opportunities
            opportunities = self.get_energy_trading_opportunities(user_id)
            
            if opportunities:
                provider_id = opportunities[0]["provider_id"]
            else:
                provider_id = "grid-op-1"  # Default if no providers found
            
            # Execute the energy trade via API
            response = self.beckn_client.execute_energy_trade(
                provider_id, 
                amount_kwh, 
                price_per_kwh, 
                "BUY"
            )
            
            # Process response
            transaction_id = f"buy-{user_id[:4]}-{int(datetime.now().timestamp())}"
            
            order = extract_order_details(response)
            if order and order.get("id"):
                transaction_id = order["id"]
            
            purchase_result = {
                "status": "completed",
                "transaction_type": "grid_purchase",
                "amount_kwh": amount_kwh,
                "price_per_kwh": price_per_kwh,
                "total_amount_usd": round(amount_kwh * price_per_kwh, 2),
                "transaction_id": transaction_id,
                "timestamp": datetime.now().isoformat()
            }
            
            # Update user stats
            if user_id in self.state:
                if 'transactions' not in self.state[user_id]:
                    self.state[user_id]['transactions'] = []
                self.state[user_id]['transactions'].append(purchase_result)
                
                # Update total costs
                self.state[user_id]['total_costs'] = self.state[user_id].get('total_costs', 0) + purchase_result["total_amount_usd"]
            
            return purchase_result
            
        except Exception as e:
            logger.error(f"Error executing grid purchase for user {user_id}: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "transaction_type": "grid_purchase",
                "amount_kwh": amount_kwh
            }
    
    def execute_p2p_sharing(self, user_id: str, amount_kwh: float) -> Dict[str, Any]:
        """Execute a peer-to-peer energy sharing transaction."""
        try:
            # Call Beckn API to execute the P2P trade
            user_state = self.get_state(user_id)
            auto_trading_settings = user_state.get('auto_trading', {})
            
            # P2P price is usually between grid purchase and sale prices
            price_per_kwh = max(0.15, auto_trading_settings.get('min_sell_price_kwh', 0.12) * 0.9)
            
            # Get trading opportunities, looking specifically for P2P ones
            opportunities = self.get_energy_trading_opportunities(user_id)
            p2p_opportunities = [opp for opp in opportunities if opp.get("type") == "p2p_sharing"]
            
            if p2p_opportunities:
                provider_id = p2p_opportunities[0]["provider_id"]
                recipient = p2p_opportunities[0]["provider_name"]
            else:
                provider_id = "community-1"  # Default if no providers found
                recipient = f"neighbor-{random.randint(1000, 9999)}"
            
            # Execute the energy trade via API
            response = self.beckn_client.execute_energy_trade(
                provider_id, 
                amount_kwh, 
                price_per_kwh, 
                "SELL"
            )
            
            # Process response
            transaction_id = f"p2p-{user_id[:4]}-{int(datetime.now().timestamp())}"
            
            order = extract_order_details(response)
            if order and order.get("id"):
                transaction_id = order["id"]
            
            # Generate NFT token for community sharing
            nft_details = None
            if auto_trading_settings.get('token_rewards', False):
                nft_details = self.create_energy_nft(user_id, "community_share", amount_kwh)
            
            # Update community contribution score
            community_contribution = amount_kwh / 10
            community_score = user_state.get('community_score', 0) + community_contribution
            
            if user_id in self.state:
                self.state[user_id]['community_score'] = community_score
            else:
                self.state[user_id] = {'community_score': community_score}
            
            sharing_result = {
                "status": "completed",
                "transaction_type": "p2p_sharing",
                "amount_kwh": amount_kwh,
                "price_per_kwh": price_per_kwh,
                "total_amount_usd": round(amount_kwh * price_per_kwh, 2),
                "community_contribution": round(community_contribution, 1),
                "community_score": round(community_score, 1),
                "transaction_id": transaction_id,
                "timestamp": datetime.now().isoformat(),
                "nft_details": nft_details,
                "recipient": recipient
            }
            
            # Update user stats
            if user_id in self.state:
                if 'transactions' not in self.state[user_id]:
                    self.state[user_id]['transactions'] = []
                self.state[user_id]['transactions'].append(sharing_result)
                
                # Update total earnings
                self.state[user_id]['total_earnings'] = self.state[user_id].get('total_earnings', 0) + sharing_result["total_amount_usd"]
            
            return sharing_result
            
        except Exception as e:
            logger.error(f"Error executing P2P sharing for user {user_id}: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "transaction_type": "p2p_sharing",
                "amount_kwh": amount_kwh
            }

# Create a singleton instance
prosumer_agent = ProsumerEnergyAgent()
