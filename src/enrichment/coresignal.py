"""Coresignal API integration"""
import hashlib
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
        # Updated to v2 API (v1 endpoints deprecated)
        self.base_url = "https://api.coresignal.com/cdapi/v2"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def get_company_profile(self, company_name: str) -> Optional[CompanyProfile]:
        """
        Get company data from Coresignal

        Args:
            company_name: Company name to search

        Returns:
            CompanyProfile if found, None otherwise
        """
        try:
            # Updated to v2 endpoint (professional_network -> company_base)
            url = f"{self.base_url}/company_base/search/filter"
            payload = {'name': company_name, 'limit': 1}

            logger.debug(f"Coresignal company search - URL: {url}")
            logger.debug(f"Coresignal company search - Payload: {payload}")

            response = await self.client.post(
                url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                json=payload
            )

            if response.status_code == 200:
                companies = response.json()

                if companies and len(companies) > 0:
                    company_data = companies[0]

                    return CompanyProfile(
                        id=str(company_data.get('id')),
                        name=company_data.get('name', company_name),
                        linkedin_url=company_data.get('url'),
                        website=company_data.get('website'),
                        industry=company_data.get('industry'),
                        company_size=company_data.get('company_size'),
                        headquarters_location=company_data.get('location'),
                        description=company_data.get('description'),
                        total_employees=company_data.get('employee_count'),
                        enriched_at=datetime.now(),
                        source='coresignal'
                    )
                else:
                    logger.warning(f"Company not found: {company_name}")
                    return None

            else:
                logger.error(f"Coresignal API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error fetching company profile: {e}")
            return None

    async def get_employees_in_taiwan(
        self,
        company_id: str,
        max_results: int = 100
    ) -> List[Dict]:
        """
        Get employees in Taiwan from Coresignal

        Args:
            company_id: Coresignal company ID
            max_results: Maximum number of employees to return

        Returns:
            List of employee dictionaries
        """
        try:
            # Updated to v2 endpoint (professional_network -> employee_base)
            url = f"{self.base_url}/employee_base/search/filter"
            # Note: v2 API uses 'country' instead of 'location' for Taiwan filtering
            payload = {
                'company_id': company_id,
                'country': 'Taiwan',
                'limit': max_results
            }

            logger.debug(f"Coresignal employee search - URL: {url}")
            logger.debug(f"Coresignal employee search - Payload: {payload}")

            response = await self.client.post(
                url,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
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
                        'city': self._extract_city(emp.get('location')),
                        'country': 'Taiwan',
                        'linkedin_url': emp.get('url')
                    })

                logger.info(f"Found {len(employees)} Taiwan employees for company {company_id}")
                return employees

            else:
                logger.error(f"Coresignal API error: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error searching employees: {e}")
            return []

    def _extract_city(self, location: Optional[str]) -> Optional[str]:
        """Extract city from location string"""
        if not location:
            return None

        # Common Taiwan cities
        cities = ['Taipei', 'Hsinchu', 'Taichung', 'Tainan', 'Kaohsiung']

        for city in cities:
            if city.lower() in location.lower():
                return city

        return None
