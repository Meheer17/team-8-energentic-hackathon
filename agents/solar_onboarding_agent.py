import logging
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from beckn.api_client import BecknAPIClient
from beckn.utils import extract_subsidies_from_response, extract_installers_from_response

logger = logging.getLogger(__name__)

class SolarOnboardingAgent:
    """Agent responsible for guiding users through the solar onboarding process."""
    
    def __init__(self):
        """Initialize the solar onboarding agent."""
        self.beckn_client = BecknAPIClient()
        self.state = {}
    
    def load_state(self, user_id: str, state_data: Dict[str, Any]) -> None:
        """Load agent state for a specific user."""
        self.state[user_id] = state_data
    
    def get_state(self, user_id: str) -> Dict[str, Any]:
        """Get the current state for a user."""
        return self.state.get(user_id, {})
    
    def search_subsidies(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Search for solar subsidies available to the user.
        
        Args:
            user_id: The user identifier
            
        Returns:
            A list of subsidies with their details
        """
        try:
            # Get location from user state if available
            user_state = self.get_state(user_id)
            location = user_state.get('address', None)
            
            # Call Beckn API to search for subsidies
            response = self.beckn_client.search_subsidies("incentive")
            
            # Process the response
            subsidies = extract_subsidies_from_response(response)
            
            # Store in state
            if user_id in self.state:
                self.state[user_id]['subsidies'] = subsidies
            else:
                self.state[user_id] = {'subsidies': subsidies}
                
            return subsidies
            
        except Exception as e:
            logger.error(f"Error searching subsidies for user {user_id}: {str(e)}")
            return []
    
    def search_installers(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Search for solar installation service providers.
        
        Args:
            user_id: The user identifier
            
        Returns:
            A list of installers with their services
        """
        try:
            # Get location from user state if available
            user_state = self.get_state(user_id)
            location = user_state.get('address', None)
            
            # Call Beckn API to search for solar services
            response = self.beckn_client.search_solar_services("resi")
            
            # Process the response
            installers = extract_installers_from_response(response)
            
            # Store in state
            if user_id in self.state:
                self.state[user_id]['installers'] = installers
            else:
                self.state[user_id] = {'installers': installers}
                
            return installers
            
        except Exception as e:
            logger.error(f"Error searching installers for user {user_id}: {str(e)}")
            return []
    
    def search_solar_products(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Search for solar panel products.
        
        Args:
            user_id: The user identifier
            
        Returns:
            A list of solar products
        """
        try:
            # Call Beckn API to search for solar products
            response = self.beckn_client.search_solar_products()
            # Extract products from response
            products = []
            print(response)
            if "responses" in response:
                for resp in response.get("responses", []):
                    if "message" in resp and "catalog" in resp["message"]:
                        catalog = resp["message"]["catalog"]
                        providers = catalog.get("providers", [])
                        for provider in providers:
                            provider_id = provider.get("id")
                            provider_name = provider.get("descriptor", {}).get("name", "Unknown")
                            print(provider)
                            for item in provider.get("items", []):
                                product = {
                                    "id": item.get("id"),
                                    "provider_id": provider_id,
                                    "provider_name": provider_name,
                                    "name": item.get("descriptor", {}).get("name", "Unknown Product"),
                                    "description": item.get("descriptor", {}).get("short_desc", ""),
                                    "price": item.get("price", {}).get("value", "0"),
                                    "currency": item.get("price", {}).get("currency", "USD"),
                                    "image": item.get("descriptor", {}).get("images", [{}])[0].get("url", "")
                                }
                                products.append(product)
            
            # Store in state
            if user_id in self.state:
                self.state[user_id]['products'] = products
            else:
                self.state[user_id] = {'products': products}
                
            return products
            
        except Exception as e:
            logger.error(f"Error searching solar products for user {user_id}: {str(e)}")
            return []
    
    def select_solar_product(self, user_id: str, provider_id: str, product_id: str) -> Dict[str, Any]:
        """
        Select a specific solar panel product.
        
        Args:
            user_id: The user identifier
            provider_id: The provider ID
            product_id: The product ID
            
        Returns:
            Selected product details
        """
        try:
            # Call Beckn API to select the product
            response = self.beckn_client.select_item(provider_id, product_id, domain="deg:retail")
            
            # Extract selection details
            selection = {}
            if "responses" in response:
                for resp in response.get("responses", []):
                    if "message" in resp and "order" in resp["message"]:
                        order = resp["message"]["order"]
                        selection = {
                            "provider": order.get("provider", {}),
                            "item": order.get("items", [{}])[0] if order.get("items") else {},
                            "quote": order.get("quote", {})
                        }
            
            # Store in state
            if user_id in self.state:
                self.state[user_id]['product_selection'] = selection
            else:
                self.state[user_id] = {'product_selection': selection}
                
            return selection
            
        except Exception as e:
            logger.error(f"Error selecting solar product for user {user_id}: {str(e)}")
            return {}
    
    def init_solar_product_order(self, user_id: str, provider_id: str, product_id: str) -> Dict[str, Any]:
        """
        Initialize an order for a solar panel product.
        
        Args:
            user_id: The user identifier
            provider_id: The provider ID
            product_id: The product ID
            
        Returns:
            Order initialization details
        """
        try:
            # Call Beckn API to initialize the order
            response = self.beckn_client.init_order(provider_id, product_id, domain="deg:retail")
            
            # Extract order details
            order_init = {}
            
            if "responses" in response:
                for resp in response.get("responses", []):
                    if "message" in resp and "order" in resp["message"]:
                        order_init = resp["message"]["order"]
            
            # Store in state
            if user_id in self.state:
                self.state[user_id]['product_order_init'] = order_init
            else:
                self.state[user_id] = {'product_order_init': order_init}
                
            return order_init
            
        except Exception as e:
            logger.error(f"Error initializing solar product order for user {user_id}: {str(e)}")
            return {}
    
    def confirm_solar_product_order(self, user_id: str, provider_id: str, product_id: str, customer_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Confirm an order for a solar panel product.
        
        Args:
            user_id: The user identifier
            provider_id: The provider ID
            product_id: The product ID
            customer_info: Customer information including name, contact details, and delivery address
            
        Returns:
            Order confirmation details
        """
        try:
            # Call Beckn API to confirm the order
            response = self.beckn_client.confirm_order(
                provider_id, 
                product_id, 
                "618",  # Default fulfillment ID for retail products
                customer_info, 
                domain="deg:retail"
            )
            
            # Extract order details
            order_confirmation = {}
            
            if "responses" in response:
                for resp in response.get("responses", []):
                    if "message" in resp and "order" in resp["message"]:
                        order_confirmation = resp["message"]["order"]
            
            # Store in state
            if user_id in self.state:
                self.state[user_id]['product_order_confirmation'] = order_confirmation
            else:
                self.state[user_id] = {'product_order_confirmation': order_confirmation}
                
            return order_confirmation
            
        except Exception as e:
            logger.error(f"Error confirming solar product order for user {user_id}: {str(e)}")
            return {}
    
    def select_service(self, user_id: str, provider_id: str, service_id: str) -> Dict[str, Any]:
        """
        Select a specific solar installation service.
        
        Args:
            user_id: The user identifier
            provider_id: The provider ID
            service_id: The service ID
            
        Returns:
            Selected service details
        """
        try:
            # Call Beckn API to select the service
            response = self.beckn_client.select_item(provider_id, service_id, domain="deg:service")
            
            # Extract selection details
            selection = {}
            
            if "responses" in response:
                for resp in response.get("responses", []):
                    if "message" in resp and "order" in resp["message"]:
                        order = resp["message"]["order"]
                        selection = {
                            "provider": order.get("provider", {}),
                            "item": order.get("items", [{}])[0] if order.get("items") else {},
                            "quote": order.get("quote", {})
                        }
            
            # Store in state
            if user_id in self.state:
                self.state[user_id]['selection'] = selection
            else:
                self.state[user_id] = {'selection': selection}
                
            return selection
            
        except Exception as e:
            logger.error(f"Error selecting service for user {user_id}: {str(e)}")
            return {}
    
    def initialize_order(self, user_id: str, provider_id: str, service_id: str) -> Dict[str, Any]:
        """
        Initialize an order for a solar installation service.
        
        Args:
            user_id: The user identifier
            provider_id: The provider ID
            service_id: The service ID
            
        Returns:
            Order initialization details
        """
        try:
            # Call Beckn API to initialize the order
            response = self.beckn_client.init_order(provider_id, service_id, domain="deg:service")
            
            # Extract order details
            order_init = {}
            
            if "responses" in response:
                for resp in response.get("responses", []):
                    if "message" in resp and "order" in resp["message"]:
                        order_init = resp["message"]["order"]
            
            # Store in state
            if user_id in self.state:
                self.state[user_id]['order_init'] = order_init
            else:
                self.state[user_id] = {'order_init': order_init}
                
            return order_init
            
        except Exception as e:
            logger.error(f"Error initializing order for user {user_id}: {str(e)}")
            return {}
    
    def confirm_order(self, user_id: str, provider_id: str, service_id: str, fulfillment_id: str, customer_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Confirm an order for a solar installation service.
        
        Args:
            user_id: The user identifier
            provider_id: The provider ID
            service_id: The service ID
            fulfillment_id: The fulfillment ID
            customer_info: Customer information including name, contact details, etc.
            
        Returns:
            Order confirmation details
        """
        try:
            # Call Beckn API to confirm the order
            response = self.beckn_client.confirm_order(
                provider_id, 
                service_id, 
                fulfillment_id, 
                customer_info, 
                domain="deg:schemes"
            )
            
            # Extract order details
            order_confirmation = {}
            
            if "responses" in response:
                for resp in response.get("responses", []):
                    if "message" in resp and "order" in resp["message"]:
                        order_confirmation = resp["message"]["order"]
            
            # Store in state
            if user_id in self.state:
                self.state[user_id]['order_confirmation'] = order_confirmation
            else:
                self.state[user_id] = {'order_confirmation': order_confirmation}
                
            return order_confirmation
            
        except Exception as e:
            logger.error(f"Error confirming order for user {user_id}: {str(e)}")
            return {}
    
    def check_order_status(self, user_id: str, order_id: str) -> Dict[str, Any]:
        """
        Check the status of an order.
        
        Args:
            user_id: The user identifier
            order_id: The order ID
            
        Returns:
            Order status details
        """
        try:
            # Call Beckn API to check order status
            response = self.beckn_client.check_status(order_id, domain="deg:service")
            
            # Extract status details
            order_status = {}
            
            if "responses" in response:
                for resp in response.get("responses", []):
                    if "message" in resp and "order" in resp["message"]:
                        order_status = resp["message"]["order"]
            
            # Store in state
            if user_id in self.state:
                self.state[user_id]['order_status'] = order_status
            else:
                self.state[user_id] = {'order_status': order_status}
                
            return order_status
            
        except Exception as e:
            logger.error(f"Error checking order status for user {user_id}: {str(e)}")
            return {}
    
    def process_rooftop_image(self, user_id: str, image_url: str) -> Dict[str, Any]:
        """
        Process a rooftop image to estimate solar potential.
        
        Args:
            user_id: The user identifier
            image_url: URL of the rooftop image
            
        Returns:
            Analysis results
        """
        # This would integrate with Google Vertex AI or similar service
        # For now, returning mock results
        
        results = {
            "suitable_area_sqm": 25.5,
            "estimated_capacity_kw": 3.8,
            "annual_generation_kwh": 5700,
            "suitable": True,
            "confidence": 0.85,
            "roof_orientation": "south",
            "shading_factor": 0.12
        }
        
        # Store in state
        if user_id in self.state:
            self.state[user_id]['rooftop_analysis'] = results
        else:
            self.state[user_id] = {'rooftop_analysis': results}
            
        return results
    
    def estimate_roi(self, user_id: str) -> Dict[str, Any]:
        """
        Calculate estimated ROI for solar installation.
        
        Args:
            user_id: The user identifier
            
        Returns:
            ROI calculations
        """
        # Get relevant data from state
        user_state = self.get_state(user_id)
        
        # Default values if not available
        electricity_consumption = user_state.get('electricity_consumption', 350)  # kWh per month
        electricity_rate = user_state.get('electricity_rate', 0.20)  # $ per kWh
        
        # Estimate system size in kW (based on consumption)
        system_size = electricity_consumption * 12 / 1500  # rough estimate: 1500 kWh/year per kW
        
        # Estimate cost ($3000 per kW is a rough average)
        system_cost = system_size * 3000
        
        # Estimate annual savings
        annual_production = system_size * 1500  # kWh per year
        annual_savings = annual_production * electricity_rate
        
        # Calculate simple payback
        payback_years = system_cost / annual_savings
        
        # Calculate 20-year ROI
        lifetime_savings = annual_savings * 20
        roi_20_year = (lifetime_savings - system_cost) / system_cost * 100
        
        # Result
        roi_data = {
            "estimated_system_size_kw": round(system_size, 1),
            "estimated_cost_usd": round(system_cost, 2),
            "estimated_annual_production_kwh": round(annual_production),
            "estimated_annual_savings_usd": round(annual_savings, 2),
            "estimated_payback_years": round(payback_years, 1),
            "estimated_roi_20_year_percent": round(roi_20_year, 1)
        }
        
        # Store in state
        if user_id in self.state:
            self.state[user_id]['roi_estimate'] = roi_data
        else:
            self.state[user_id] = {'roi_estimate': roi_data}
            
        return roi_data
    
    def generate_summary(self, user_id: str) -> str:
        """
        Generate a summary of the user's solar onboarding progress.
        
        Args:
            user_id: The user identifier
            
        Returns:
            A formatted summary text
        """
        user_state = self.get_state(user_id)
        
        address = user_state.get('address', 'Not provided')
        consumption = user_state.get('electricity_consumption', 'Not provided')
        
        # Get ROI data if available
        roi_data = user_state.get('roi_estimate', {})
        system_size = roi_data.get('estimated_system_size_kw', 'Not calculated')
        system_cost = roi_data.get('estimated_cost_usd', 'Not calculated')
        annual_savings = roi_data.get('estimated_annual_savings_usd', 'Not calculated')
        payback_years = roi_data.get('estimated_payback_years', 'Not calculated')
        
        # Get selected installer if available
        selection = user_state.get('selection', {})
        provider = selection.get('provider', {})
        provider_name = provider.get('descriptor', {}).get('name', 'Not selected')
        
        # Format the summary
        summary = f"""
        🌞 *Solar Onboarding Summary* 🌞
        
        📍 *Address*: {address}
        ⚡ *Monthly Consumption*: {consumption} kWh
        
        📊 *System Estimates*:
        • Recommended Size: {system_size} kW
        • Estimated Cost: ${system_cost}
        • Annual Savings: ${annual_savings}
        • Payback Period: {payback_years} years
        
        🏪 *Selected Installer*: {provider_name}
        
        Your solar journey has begun! The next steps will involve scheduling an installation consultation and finalizing your system design.
        """
        
        return summary

# Create a singleton instance
solar_agent = SolarOnboardingAgent()