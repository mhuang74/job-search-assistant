"""People Data Labs API integration"""
import hashlib
from typing import Optional, List, Dict
import httpx
from loguru import logger

from ..models import CompanyProfile


class PeopleDataLabsEnricher:
    """People Data Labs API for LinkedIn enrichment"""

    def __init__(self, api_key: str, proxy: Optional[str] = None):
        """
        Initialize People Data Labs client

        Args:
            api_key: PDL API key
            proxy: Optional HTTP/HTTPS proxy URL (e.g., http://user:pass@host:port)
        """
        self.api_key = api_key
        self.base_url = "https://api.peopledatalabs.com/v5"

        # Configure httpx client with optional proxy
        client_kwargs = {"timeout": 30.0}
        if proxy:
            client_kwargs["proxies"] = proxy
            logger.info(f"PeopleDataLabs client configured with proxy")

        self.client = httpx.AsyncClient(**client_kwargs)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def get_company_profile(
        self,
        company_name: str,
        website: Optional[str] = None
    ) -> Optional[CompanyProfile]:
        """
        Get company profile from People Data Labs

        Args:
            company_name: Company name to search
            website: Company website (optional, improves matching)

        Returns:
            CompanyProfile if found, None otherwise

        Cost: $0.10 per successful match
        """
        try:
            params = {
                'name': company_name,
                'api_key': self.api_key
            }

            if website:
                params['website'] = website

            response = await self.client.get(
                f"{self.base_url}/company/enrich",
                params=params
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('status') == 200:
                    company_data = data.get('data', {})

                    # Generate company ID
                    company_id = hashlib.md5(company_name.lower().encode()).hexdigest()[:16]

                    return CompanyProfile(
                        id=company_id,
                        name=company_data.get('name', company_name),
                        linkedin_url=company_data.get('linkedin_url'),
                        website=company_data.get('website'),
                        industry=company_data.get('industry'),
                        company_size=self._format_company_size(company_data.get('employee_count')),
                        headquarters_location=self._format_location(company_data.get('location')),
                        description=company_data.get('summary'),
                        total_employees=company_data.get('employee_count'),
                        source='peopledatalabs'
                    )
                else:
                    logger.warning(f"Company not found: {company_name}")
                    return None

            elif response.status_code == 404:
                logger.warning(f"Company not found: {company_name}")
                return None
            else:
                logger.error(f"PDL API error: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Error fetching company profile: {e}")
            return None

    async def search_employees_in_asia(
        self,
        company_name: str,
        max_results: int = 100,
        countries: List[str] = None
    ) -> List[Dict]:
        """
        Search for employees in Asia for a company

        Args:
            company_name: Company name
            max_results: Maximum number of employees to return
            countries: List of countries to search (defaults to Taiwan, China, Singapore, Hong Kong)

        Returns:
            List of employee dictionaries

        Cost: $0.28 per successful match
        """
        if countries is None:
            countries = ['taiwan', 'china', 'singapore', 'hong kong']

        try:
            # Build search query with multiple countries
            query = {
                'query': {
                    'bool': {
                        'must': [
                            {'terms': {'location_country': countries}},
                            {'term': {'job_company_name': company_name}}
                        ]
                    }
                },
                'size': max_results,
                'dataset': 'phone'  # Use basic dataset to save costs
            }

            response = await self.client.post(
                f"{self.base_url}/person/search",
                json=query,
                headers={'X-Api-Key': self.api_key}
            )

            if response.status_code == 200:
                data = response.json()

                if data.get('status') == 200:
                    employees = []
                    for person in data.get('data', []):
                        employees.append({
                            'name': person.get('full_name'),
                            'title': person.get('job_title'),
                            'location': person.get('location_name'),
                            'city': person.get('location_locality'),
                            'country': person.get('location_country', '').title(),
                            'linkedin_url': person.get('linkedin_url')
                        })

                    logger.info(f"Found {len(employees)} Asia employees for {company_name}")
                    return employees
                else:
                    logger.warning(f"No employees found for {company_name} in target countries")
                    return []

            else:
                logger.error(f"PDL API error: {response.status_code} - {response.text}")
                return []

        except Exception as e:
            logger.error(f"Error searching employees: {e}")
            return []

    def _format_company_size(self, employee_count: Optional[int]) -> Optional[str]:
        """Format employee count to size range"""
        if employee_count is None:
            return None

        if employee_count <= 10:
            return "1-10"
        elif employee_count <= 50:
            return "11-50"
        elif employee_count <= 200:
            return "51-200"
        elif employee_count <= 500:
            return "201-500"
        elif employee_count <= 1000:
            return "501-1000"
        elif employee_count <= 5000:
            return "1001-5000"
        else:
            return "5000+"

    def _format_location(self, location: Optional[Dict]) -> Optional[str]:
        """Format location dictionary to string"""
        if not location:
            return None

        parts = []
        if location.get('locality'):
            parts.append(location['locality'])
        if location.get('region'):
            parts.append(location['region'])
        if location.get('country'):
            parts.append(location['country'])

        return ', '.join(parts) if parts else None
