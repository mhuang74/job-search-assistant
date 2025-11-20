"""Coresignal API integration"""
import hashlib
import re
from typing import Optional, List, Dict
from datetime import datetime
import httpx
from loguru import logger

from ..models import CompanyProfile


class CoresignalEnricher:
    """Coresignal API for LinkedIn enrichment"""

    def __init__(self, api_key: str):
        """
        Initialize Coresignal client

        Args:
            api_key: Coresignal API key
        """
        self.api_key = api_key
        # Updated to v2 API with multi-source endpoint
        self.base_url = "https://api.coresignal.com/cdapi/v2"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    def _infer_website(self, company_name: str) -> str:
        """
        Infer company website from company name

        Args:
            company_name: Company name

        Returns:
            Inferred website domain
        """
        # Clean company name
        name = company_name.lower()

        # Remove common suffixes
        name = re.sub(r'\s+(inc\.?|llc\.?|ltd\.?|corp\.?|corporation|company|co\.?)$', '', name)

        # Remove special characters and spaces
        name = re.sub(r'[^\w\s-]', '', name)
        name = re.sub(r'[-\s]+', '', name)

        # Common patterns
        domain = f"{name}.com"

        logger.debug(f"Inferred website for '{company_name}': {domain}")
        return domain

    async def get_company_profile(self, company_name: str, company_website: Optional[str] = None) -> Optional[CompanyProfile]:
        """
        Get company data from Coresignal using clean enrich endpoint

        Args:
            company_name: Company name to search
            company_website: Company website/domain (if known)

        Returns:
            CompanyProfile if found, None otherwise
        """
        try:
            # Use provided website or infer from company name
            website = company_website or self._infer_website(company_name)

            # Use company_clean enrich endpoint (requires website parameter)
            url = f"{self.base_url}/company_clean/enrich"
            params = {'website': website}

            logger.debug(f"Coresignal company enrich - URL: {url}")
            logger.debug(f"Coresignal company enrich - Params: {params}")

            response = await self.client.get(
                url,
                headers={
                    'apikey': self.api_key,
                    'Content-Type': 'application/json'
                },
                params=params
            )

            if response.status_code == 200:
                company_data = response.json()

                if company_data:
                    return CompanyProfile(
                        id=str(company_data.get('id', '')),
                        name=company_data.get('name', company_name),
                        linkedin_url=company_data.get('url'),
                        website=company_data.get('website') or website,
                        industry=company_data.get('industry'),
                        company_size=company_data.get('company_size'),
                        headquarters_location=company_data.get('location'),
                        description=company_data.get('description'),
                        total_employees=company_data.get('employee_count'),
                        enriched_at=datetime.now(),
                        source='coresignal'
                    )
                else:
                    logger.warning(f"Company not found: {company_name} (website: {website})")
                    return None

            else:
                logger.error(f"Coresignal API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error fetching company profile for {company_name}: {e}")
            return None

    async def get_employees_in_asia(
        self,
        company_website: str,
        max_results: int = 100,
        countries: List[str] = None
    ) -> List[Dict]:
        """
        Get employees in Asia from Coresignal using ES DSL query

        Args:
            company_website: Company website domain
            max_results: Maximum number of employees to return
            countries: List of countries to search (defaults to Taiwan, China, Singapore, Hong Kong)

        Returns:
            List of employee dictionaries
        """
        if countries is None:
            countries = ["Taiwan", "China", "Singapore", "Hong Kong"]

        try:
            # Use employee_clean ES DSL endpoint
            url = f"{self.base_url}/employee_clean/search/es_dsl"

            # Elasticsearch DSL query to find employees by company website in target countries
            payload = {
                "query": {
                    "bool": {
                        "must": [
                            {
                                "nested": {
                                    "path": "experience",
                                    "query": {
                                        "match": {
                                            "experience.company_website.domain_only": company_website
                                        }
                                    }
                                }
                            },
                            {
                                "terms": {
                                    "country": countries
                                }
                            }
                        ]
                    }
                }
            }

            logger.debug(f"Coresignal employee search - URL: {url}")
            logger.debug(f"Coresignal employee search - Payload: {payload}")

            # Add limit as query parameter instead of in body
            params = {'limit': max_results}

            response = await self.client.post(
                url,
                headers={
                    'apikey': self.api_key,
                    'Content-Type': 'application/json'
                },
                params=params,
                json=payload
            )

            if response.status_code == 200:
                employees_data = response.json()

                employees = []
                for emp in employees_data:
                    employees.append({
                        'name': emp.get('name'),
                        'title': emp.get('title'),
                        'location': emp.get('location'),
                        'city': self._extract_city(emp.get('location'), emp.get('country')),
                        'country': emp.get('country'),
                        'linkedin_url': emp.get('url')
                    })

                logger.info(f"Found {len(employees)} Asia employees for company {company_website}")

                return employees

            else:
                logger.error(f"Coresignal API error: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error searching employees: {e}")
            return []

    def _extract_city(self, location: Optional[str], country: Optional[str] = None) -> Optional[str]:
        """Extract city from location string"""
        if not location:
            return None

        # Common cities in target countries
        cities = {
            'Taiwan': ['Taipei', 'Hsinchu', 'Taichung', 'Tainan', 'Kaohsiung'],
            'China': ['Beijing', 'Shanghai', 'Shenzhen', 'Guangzhou', 'Hangzhou', 'Chengdu'],
            'Singapore': ['Singapore'],
            'Hong Kong': ['Hong Kong']
        }

        # If country is specified, only check cities in that country
        if country and country in cities:
            for city in cities[country]:
                if city.lower() in location.lower():
                    return city
        else:
            # Check all cities
            for city_list in cities.values():
                for city in city_list:
                    if city.lower() in location.lower():
                        return city

        return None
