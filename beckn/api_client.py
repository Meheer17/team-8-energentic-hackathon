import requests
import json
import logging
import os
import uuid
from datetime import datetime

from .utils import create_beckn_context
from datetime import datetime, date, timedelta  # Make sure timedelta is included

logger = logging.getLogger(__name__)

class BecknAPIClient:
    """Client for interacting with Beckn APIs for energy-related services."""

    def __init__(self, base_url=None, bap_id=None, bap_uri=None, bpp_id=None, bpp_uri=None):
        """Initialize the Beckn API client."""
        # Load from environment variables if not provided
        self.base_url = base_url or os.getenv("BECKN_BASE_URL", "https://bap-ps-client-deg-team8.becknprotocol.io")
        self.bap_id = bap_id or os.getenv("BECKN_BAP_ID", "bap-ps-network-deg-team8.becknprotocol.io")
        self.bap_uri = bap_uri or os.getenv("BECKN_BAP_URI", "https://bap-ps-network-deg-team8.becknprotocol.io")
        self.bpp_id = bpp_id or os.getenv("BECKN_BPP_ID", "bpp-ps-network-deg-team8.becknprotocol.io")
        self.bpp_uri = bpp_uri or os.getenv("BECKN_BPP_URI", "https://bpp-ps-network-deg-team8.becknprotocol.io")

    def _create_context(self, action, domain="deg:schemes", city_code="NANP:628", country_code="USA"):
        """Create a Beckn context object for API requests."""
        return create_beckn_context(
            action=action,
            domain=domain,
            city_code=city_code,
            country_code=country_code,
            bap_id=self.bap_id,
            bap_uri=self.bap_uri,
            bpp_id=self.bpp_id,
            bpp_uri=self.bpp_uri
        )

    def _make_api_call(self, endpoint, payload):
        """Make an API call to the Beckn API."""
        url = f"{self.base_url}/{endpoint}"
        try:
            # Make the API call
            headers = {
                "Content-Type": "application/json"
            }
            logger.info(f"Making API call to {url}")
            logger.debug(f"Request payload: {json.dumps(payload)}")

            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()

            logger.info(f"API call successful: {response.status_code}")
            logger.debug(f"Response: {response.text}")

            return response.json()
        except Exception as e:
            logger.error(f"API call failed: {e}")
            return {"error": str(e)}

    def search_subsidies(self, query="incentive", domain="deg:schemes"):
        """Search for available subsidies and incentives."""
        context = self._create_context("search", domain=domain)
        payload = {
            "context": context,
            "message": {
                "descriptor": {
                    "name": query
                }

            }
        }
        return self._make_api_call("search", payload)

    def search_energy_programs(self, query="Program", domain="deg:schemes"):
        """Search for available energy programs."""
        context = self._create_context("search", domain=domain)
        payload = {
            "context": context,
            "message": {
                "intent": {
                    "item": {
                        "descriptor": {
                            "name": query
                        }
                    }
                }
            }
        }
        return self._make_api_call("search", payload)

    def search_solar_products(self, query="solar", domain="deg:retail"):
        """Search for solar panels and related products."""
        context = self._create_context("search", domain=domain)
        payload = {
            "context": context,
            "message": {
                "intent": {
                    "item": {
                        "descriptor": {
                            "name": query
                        }
                    }
                }
            }
        }
        return self._make_api_call("search", payload)

    def search_solar_services(self, query="resi", domain="deg:service"):
        """Search for solar installation and related services."""
        context = self._create_context("search", domain=domain)
        payload = {
            "context": context,
            "message": {
                "intent": {
                    "descriptor": {
                        "name": query
                    }
                }
            }
        }
        return self._make_api_call("search", payload)

    def select_item(self, provider_id, item_id, domain="deg:service"):
        """Select a specific item from a provider."""
        context = self._create_context("select", domain=domain)
        payload = {
            "context": context,
            "message": {
                "order": {
                    "provider": {
                        "id": provider_id
                    },
                    "items": [
                        {
                            "id": item_id
                        }
                    ]
                }
            }
        }
        return self._make_api_call("select", payload)

    def init_order(self, provider_id, item_id, domain="deg:service"):
        """Initialize an order for a specific item."""
        context = self._create_context("init", domain=domain)
        payload = {
            "context": context,
            "message": {
                "order": {
                    "provider": {
                        "id": provider_id
                    },
                    "items": [
                        {
                            "id": item_id
                        }
                    ]
                }
            }
        }
        return self._make_api_call("init", payload)

    def confirm_order(self, provider_id, item_id, fulfillment_id, customer_info, domain="deg:service"):
        """Confirm an order with customer information."""
        context = self._create_context("confirm", domain=domain)
        payload = {
            "context": context,
            "message": {
                "order": {
                    "provider": {
                        "id": provider_id
                    },
                    "items": [
                        {
                            "id": item_id
                        }
                    ],
                    "fulfillments": [
                        {
                            "id": fulfillment_id,
                            "customer": customer_info
                        }
                    ]
                }
            }
        }
        return self._make_api_call("confirm", payload)

    def check_status(self, order_id, domain="deg:schemes"):
        """Check the status of an order."""
        context = self._create_context("status", domain=domain)
        payload = {
            "context": context,
            "message": {
                "order_id": order_id
            }
        }
        return self._make_api_call("status", payload)

    def search_energy_trading_opportunities(self, location=None):
        """Search for energy trading opportunities."""
        context = self._create_context("search", domain="uei:p2p_trading")
        payload = {
            "context": context,
            "message": {
                "intent": {
                    "item": {
                        "descriptor": {
                            "name": "Solar Surplus Energy"
                        }
                    },
                    "fulfillment": {
                        "agent": {
                            "organization": {
                                "descriptor": {
                                    "name": "Grid Services"
                                }
                            }
                        },
                    }
                }
            }
        }

        return self._make_api_call("search", payload)

    def execute_energy_trade(self, provider_id, amount, price, trade_type="SELL", domain="uei:p2p_trading"):
        """Execute an energy trade (buy/sell)."""
        context = self._create_context("init", domain=domain)

        # Format request data according to the expected structure
        payload = {
            "context": context,
            "message": {
                "order": {
                    "provider": {
                        "id": provider_id
                    },
                    "items": [
                        {
                            "id": f"energy-{trade_type.lower()}",
                            "descriptor": {
                                "name": f"Energy {trade_type.capitalize()}",
                                "code": trade_type
                            },
                            "price": {
                                "value": str(price),
                                "currency": "USD/kWH"
                            },
                            "quantity": {
                                "selected": {
                                    "measure": {
                                        "value": str(amount),
                                        "unit": "kWH"
                                    }
                                }
                            }
                        }
                    ],
                    "billing": {
                        "name": "User",
                        "email": "user@example.com",
                        "phone": "+15555555555"
                    },
                    "fulfillments": [
                        {
                            "agent": {
                                "organization": {
                                    "descriptor": {
                                        "name": "Grid Services"
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        }

        return self._make_api_call("init", payload)

    def search_demand_response_programs(self, domain="deg:programs"):
        """Search for demand response programs."""
        context = self._create_context("search", domain=domain)
        payload = {
            "context": context,
            "message": {
                "intent": {
                    "category": {
                        "descriptor": {
                            "code": "demand-response"
                        }
                    }
                }
            }
        }
        return self._make_api_call("search", payload)

    def create_energy_nft(self, provider_id, energy_amount, domain="deg:tokens"):
        """Create an NFT from energy production."""
        context = self._create_context("init", domain=domain)
        payload = {
            "context": context,
            "message": {
                "order": {
                    "provider": {
                        "id": provider_id
                    },
                    "items": [
                        {
                            "id": "energy-nft",
                            "descriptor": {
                                "name": "Energy NFT",
                                "code": "ENERGY_TOKEN"
                            },
                            "quantity": {
                                "measure": {
                                    "value": str(energy_amount),
                                    "unit": "kWh"
                                }
                            }
                        }
                    ]
                }
            }
        }
        return self._make_api_call("init", payload)

    def execute_grid_sale(self, user_id: str, amount_kwh: float) -> dict[str, any]:
            """Execute a sale of energy to the grid."""
            try:
                # Call Beckn API to execute the trade
                user_state = self.get_state(user_id)
                auto_trading_settings = user_state.get('auto_trading', {})

                # Calculate price
                price_per_kwh = max(0.18, auto_trading_settings.get('min_sell_price_kwh', 0.12))

                # Get user's meter address
                meter_address = user_state.get('meter_address', f"der://meter/{user_id}")

                # Execute the energy trade via API
                response = self.beckn_client.execute_energy_trade(
                    "grid-op-1",  # Grid operator ID
                    amount_kwh,
                    price_per_kwh,
                    "SELL"
                )

                # Process response
                order = extract_order_details(response)
                transaction_id = order.get("id", f"grid-{user_id[:4]}-{int(datetime.now().timestamp())}")

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

    def execute_p2p_sharing(self, user_id: str, amount_kwh: float):
            """Execute a peer-to-peer energy sharing transaction."""
            try:
                # Call Beckn API to execute the P2P trade
                user_state = self.get_state(user_id)
                auto_trading_settings = user_state.get('auto_trading', {})

                # P2P price is usually between grid purchase and sale prices
                price_per_kwh = max(0.15, auto_trading_settings.get('min_sell_price_kwh', 0.12) * 0.9)

                # Get trading opportunities, looking specifically for P2P ones
                trading_opportunities = self.get_energy_trading_opportunities(user_id)
                p2p_opportunities = [opp for opp in trading_opportunities if opp.get("type") == "p2p_sharing"]

                if p2p_opportunities:
                    provider_id = p2p_opportunities[0]["provider_id"]
                    recipient = p2p_opportunities[0]["provider_name"]
                else:
                    provider_id = "community-1"  # Default if no providers found
                    recipient = f"neighbor-{random.randint(1000, 9999)}"

                # Execute the energy trade via API with proper domain
                response = self.beckn_client.execute_energy_trade(
                    provider_id,
                    amount_kwh,
                    price_per_kwh,
                    "SELL"
                )

                # Process response
                order = extract_order_details(response)
                transaction_id = order.get("id", f"p2p-{user_id[:4]}-{int(datetime.now().timestamp())}")

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
def extract_energy_trading_opportunities(response_data):
    """
    Extract energy trading opportunities from a Beckn search response.
    """
    opportunities = []

    if not response_data or "responses" not in response_data:
        logger.warning("Invalid response format for energy trading extraction")
        return opportunities

    # Process each response in the responses array
    for response in response_data.get("responses", []):
        if not response or "message" not in response:
            continue

        message = response.get("message", {})
        catalog = message.get("catalog", {})

        # Extract providers from catalog
        providers = catalog.get("providers", [])
        for provider in providers:
            provider_id = provider.get("id")
            provider_name = provider.get("descriptor", {}).get("name", "Unknown Provider")

            # Get provider location
            locations = provider.get("locations", [])
            provider_location = None
            if locations and len(locations) > 0:
                provider_location = {
                    "gps": locations[0].get("gps"),
                    "address": locations[0].get("address")
                }

            # Extract items (energy offers) from this provider
            items = provider.get("items", [])
            for item in items:
                # Determine if this is a buying or selling opportunity
                item_type = "p2p_sharing"
                if "sell" in item.get("descriptor", {}).get("name", "").lower():
                    item_type = "sell_excess"
                elif "buy" in item.get("descriptor", {}).get("name", "").lower():
                    item_type = "buy_energy"

                # Get price - handle USD/kWH format
                price_value = item.get("price", {}).get("value", "0")
                try:
                    price_per_kwh = float(price_value.replace("USD/kWH", "").strip())
                except (ValueError, AttributeError):
                    price_per_kwh = float(price_value) if isinstance(price_value, (int, float)) else 0.0

                # Get available quantity
                available_kwh = "0"
                quantity = item.get("quantity", {})
                if "available" in quantity:
                    available_kwh = quantity.get("available", {}).get("measure", {}).get("value", "0")

                opportunity = {
                    "id": item.get("id"),
                    "provider_id": provider_id,
                    "provider_name": provider_name,
                    "type": item_type,
                    "name": item.get("descriptor", {}).get("name", "Unknown Opportunity"),
                    "description": item.get("descriptor", {}).get("short_desc", ""),
                    "price_per_kwh": price_per_kwh,
                    "currency": "USD",
                    "tags": {},
                    "location": provider_location
                }

                # Extract energy-specific details from tags
                for tag in item.get("tags", []):
                    tag_name = tag.get("descriptor", {}).get("name", "")

                    if tag_name:
                        tag_values = {}
                        for tag_item in tag.get("list", []):
                            item_name = tag_item.get("descriptor", {}).get("name", "")
                            value = tag_item.get("value")
                            if item_name and value:
                                tag_values[item_name] = value

                        if tag_values:
                            opportunity["tags"][tag_name] = tag_values

                # Add energy availability info
                opportunity["tags"]["energy_available"] = {"amount": available_kwh}

                # Extract source type if available
                energy_attributes = opportunity["tags"].get("Energy Attributes", {})
                source_type = energy_attributes.get("Source Type", "Solar")
                opportunity["tags"]["source_type"] = source_type

                opportunities.append(opportunity)

    return opportunities
