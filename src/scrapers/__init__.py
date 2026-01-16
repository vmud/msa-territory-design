"""Retailer scrapers registry"""

from typing import Dict, Type, List

# Registry of available scrapers
SCRAPER_REGISTRY: Dict[str, str] = {
    'verizon': 'src.scrapers.verizon',
    'att': 'src.scrapers.att',
    'target': 'src.scrapers.target',
    'tmobile': 'src.scrapers.tmobile',
    'walmart': 'src.scrapers.walmart',
    'bestbuy': 'src.scrapers.bestbuy',
}

def get_available_retailers() -> List[str]:
    """Get list of available retailer names"""
    return list(SCRAPER_REGISTRY.keys())

def get_scraper_module(retailer: str):
    """Dynamically import and return a scraper module"""
    import importlib
    if retailer not in SCRAPER_REGISTRY:
        raise ValueError(f"Unknown retailer: {retailer}. Available: {get_available_retailers()}")
    return importlib.import_module(SCRAPER_REGISTRY[retailer])

__all__ = ['SCRAPER_REGISTRY', 'get_available_retailers', 'get_scraper_module']
