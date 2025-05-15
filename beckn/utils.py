import json
import os
import uuid
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def create_beckn_context(action, domain="deg:schemes", city_code="NANP:628", country_code="USA",
                        bap_id=None, bap_uri=None, bpp_id=None, bpp_uri=None):
    """
    Create a Beckn context object with default values if not provided.
    """
    # Load from environment if not provided
    bap_id = bap_id or os.getenv("BECKN_BAP_ID", "bap-ps-network-deg-team8.becknprotocol.io")
    bap_uri = bap_uri or os.getenv("BECKN_BAP_URI", "https://bap-ps-network-deg-team8.becknprotocol.io")
    bpp_id = bpp_id or os.getenv("BECKN_BPP_ID", "bpp-ps-network-deg-team8.becknprotocol.io")
    bpp_uri = bpp_uri or os.getenv("BECKN_BPP_URI", "https://bpp-ps-network-deg-team8.becknprotocol.io")
    
    return {
        "domain": domain,
        "action": action,
        "location": {
            "country": {
                "code": country_code
            },
            "city": {
                "code": city_code
            }
        },
        "version": "1.1.0",
        "bap_id": bap_id,
        "bap_uri": bap_uri,
        "bpp_id": bpp_id,
        "bpp_uri": bpp_uri,
        "transaction_id": str(uuid.uuid4()),
        "message_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    }

def extract_subsidies_from_response(response_data):
    """
    Extract subsidy information from a Beckn search response.
    """
    subsidies = []
    
    if not response_data or "responses" not in response_data:
        logger.warning("Invalid response format for subsidy extraction")
        return subsidies
    
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
            provider_desc = provider.get("descriptor", {}).get("short_desc", "")
            
            # Extract items (subsidies/incentives) from each provider
            items = provider.get("items", [])
            for item in items:
                subsidy = {
                    "id": item.get("id"),
                    "provider_id": provider_id,
                    "provider_name": provider_name,
                    "fulfillment_id": provider.get("fulfillments", [])[0].get("id"),
                    "provider_desc": provider_desc,
                    "name": item.get("descriptor", {}).get("name", "Unknown Subsidy"),
                    "description": item.get("descriptor", {}).get("short_desc", ""),
                    "long_description": item.get("descriptor", {}).get("long_desc", ""),
                    "image": item.get("descriptor", {}).get("images", [{}])[0].get("url", "") if item.get("descriptor", {}).get("images") else "",
                    "price": item.get("price", {}).get("value", "0"),
                    "currency": item.get("price", {}).get("currency", "USD"),
                    "tags": {}
                }
                
                # Extract details from tags
                for tag in item.get("tags", []):
                    tag_desc = tag.get("descriptor", {}).get("description")
                    if not tag_desc:
                        continue
                    
                    tag_values = {}
                    for tag_item in tag.get("list", []):
                        item_desc = tag_item.get("descriptor", {})
                        key = item_desc.get("description", "") or item_desc.get("code", "")
                        value = tag_item.get("value")
                        if key and value:
                            tag_values[key] = value
                    
                    if tag_values:
                        subsidy["tags"][tag_desc] = tag_values
                
                subsidies.append(subsidy)
    
    return subsidies

def extract_installers_from_response(response_data):
    """
    Extract installer information from a Beckn search response.
    """
    installers = []
    
    if not response_data or "responses" not in response_data:
        logger.warning("Invalid response format for installer extraction")
        return installers
    
    # Process each response in the responses array
    for response in response_data.get("responses", []):
        if not response or "message" not in response:
            continue
        
        message = response.get("message", {})
        catalog = message.get("catalog", {})
        
        # Extract providers from catalog
        providers = catalog.get("providers", [])
        for provider in providers:
            installer = {
                "id": provider.get("id"),
                "name": provider.get("descriptor", {}).get("name", "Unknown Provider"),
                "short_desc": provider.get("descriptor", {}).get("short_desc", ""),
                "long_desc": provider.get("descriptor", {}).get("long_desc", ""),
                "image": provider.get("descriptor", {}).get("images", [{}])[0].get("url", "") if provider.get("descriptor", {}).get("images") else "",
                "locations": provider.get("locations", []),
                "services": []
            }
            
            # Extract services (items) offered by this installer
            items = provider.get("items", [])
            for item in items:
                service = {
                    "id": item.get("id"),
                    "name": item.get("descriptor", {}).get("name", "Unknown Service"),
                    "description": item.get("descriptor", {}).get("short_desc", ""),
                    "long_description": item.get("descriptor", {}).get("long_desc", ""),
                    "image": item.get("descriptor", {}).get("images", [{}])[0].get("url", "") if item.get("descriptor", {}).get("images") else "",
                    "price": item.get("price", {}).get("value", "0"),
                    "currency": item.get("price", {}).get("currency", "USD"),
                    "tags": {}
                }
                
                # Extract details from tags
                for tag in item.get("tags", []):
                    tag_desc = tag.get("descriptor", {}).get("description")
                    if not tag_desc:
                        continue
                    
                    tag_values = {}
                    for tag_item in tag.get("list", []):
                        item_desc = tag_item.get("descriptor", {})
                        key = item_desc.get("description", "") or item_desc.get("code", "")
                        value = tag_item.get("value")
                        if key and value:
                            tag_values[key] = value
                    
                    if tag_values:
                        service["tags"][tag_desc] = tag_values
                
                installer["services"].append(service)
            
            installers.append(installer)
    
    return installers

def extract_energy_programs_from_response(response_data):
    """
    Extract energy program information from a Beckn search response.
    """
    programs = []
    
    if not response_data or "responses" not in response_data:
        logger.warning("Invalid response format for energy program extraction")
        return programs
    
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
            
            # Extract programs (items) offered by this provider
            items = provider.get("items", [])
            for item in items:
                program = {
                    "id": item.get("id"),
                    "provider_id": provider_id,
                    "provider_name": provider_name,
                    "name": item.get("descriptor", {}).get("name", "Unknown Program"),
                    "description": item.get("descriptor", {}).get("short_desc", ""),
                    "long_description": item.get("descriptor", {}).get("long_desc", ""),
                    "image": item.get("descriptor", {}).get("images", [{}])[0].get("url", "") if item.get("descriptor", {}).get("images") else "",
                    "tags": {}
                }
                
                # Extract details from tags
                for tag in item.get("tags", []):
                    tag_desc = tag.get("descriptor", {}).get("description")
                    if not tag_desc:
                        continue
                    
                    tag_values = {}
                    for tag_item in tag.get("list", []):
                        item_desc = tag_item.get("descriptor", {})
                        key = item_desc.get("description", "") or item_desc.get("code", "")
                        value = tag_item.get("value")
                        if key and value:
                            tag_values[key] = value
                    
                    if tag_values:
                        program["tags"][tag_desc] = tag_values
                
                programs.append(program)
    
    return programs

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
            
            # Extract opportunities (items) offered by this provider
            items = provider.get("items", [])
            for item in items:
                opportunity = {
                    "id": item.get("id"),
                    "provider_id": provider_id,
                    "provider_name": provider_name,
                    "type": item.get("descriptor", {}).get("code", "unknown"),
                    "name": item.get("descriptor", {}).get("name", "Unknown Opportunity"),
                    "description": item.get("descriptor", {}).get("short_desc", ""),
                    "price_per_kwh": float(item.get("price", {}).get("value", "0")),
                    "currency": item.get("price", {}).get("currency", "USD"),
                    "tags": {}
                }
                
                # Extract details from tags
                for tag in item.get("tags", []):
                    tag_desc = tag.get("descriptor", {}).get("description")
                    if not tag_desc:
                        continue
                    
                    tag_values = {}
                    for tag_item in tag.get("list", []):
                        item_desc = tag_item.get("descriptor", {})
                        key = item_desc.get("description", "") or item_desc.get("code", "")
                        value = tag_item.get("value")
                        if key and value:
                            tag_values[key] = value
                    
                    if tag_values:
                        opportunity["tags"][tag_desc] = tag_values
                
                opportunities.append(opportunity)
    
    return opportunities

def extract_order_details(response_data):
    """
    Extract order details from a Beckn API response.
    """
    if not response_data or "responses" not in response_data:
        logger.warning("Invalid response format for order extraction")
        return {}
    
    for response in response_data.get("responses", []):
        if "message" in response and "order" in response["message"]:
            return response["message"]["order"]
    
    return {}
