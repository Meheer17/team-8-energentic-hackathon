import requests
import json
import logging
import os
import uuid
from datetime import datetime

from .utils import create_beckn_context

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
    
    def check_status(self, order_id, domain="deg:service"):
        """Check the status of an order."""
        context = self._create_context("status", domain=domain)
        payload = {
            "context": context,
            "message": {
                "order_id": order_id
            }
        }
        return self._make_api_call("status", payload)
    
    def search_energy_trading_opportunities(self, location=None, domain="deg:energy"):
        """Search for energy trading opportunities."""
        context = self._create_context("search", domain=domain)
        payload = {
            "context": context,
            "message": {
                "intent": {
                    "fulfillment": {
                        "type": "ENERGY_TRADE"
                    }
                }
            }
        }
        
        if location:
            payload["message"]["intent"]["fulfillment"]["location"] = location
            
        return self._make_api_call("search", payload)
    
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
    
    def execute_energy_trade(self, provider_id, amount, price, trade_type="SELL", domain="deg:energy"):
        """Execute an energy trade (buy/sell)."""
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
                            "id": f"energy-{trade_type.lower()}",
                            "descriptor": {
                                "name": f"Energy {trade_type.capitalize()}",
                                "code": trade_type
                            },
                            "price": {
                                "value": str(price),
                                "currency": "USD"
                            },
                            "quantity": {
                                "measure": {
                                    "value": str(amount),
                                    "unit": "kWh"
                                }
                            }
                        }
                    ]
                }
            }
        }
        return self._make_api_call("init", payload)
    
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
