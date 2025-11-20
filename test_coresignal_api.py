#!/usr/bin/env python3
"""
Test script to diagnose Coresignal API issues
"""
import asyncio
import os
import httpx
from dotenv import load_dotenv

load_dotenv()


async def test_coresignal_api():
    """Test Coresignal API endpoints"""
    api_key = os.getenv('CORESIGNAL_API_KEY')

    if not api_key:
        print("❌ CORESIGNAL_API_KEY not found in .env file")
        return

    print(f"✅ API Key found: {api_key[:10]}...")
    print()

    # Updated to v2 API with clean endpoints
    base_url = "https://api.coresignal.com/cdapi/v2"

    # Test company enrich endpoint
    print("Testing Company Enrich Endpoint (Clean API)...")
    print("-" * 50)

    company_website = "stripe.com"
    url = f"{base_url}/company_clean/enrich"
    params = {'website': company_website}

    print(f"URL: {url}")
    print(f"Headers: apikey: {api_key[:10]}...")
    print(f"Params: {params}")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                url,
                headers={
                    'apikey': api_key,
                    'Content-Type': 'application/json'
                },
                params=params
            )

            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text}")
            print()

            if response.status_code == 200:
                print("✅ Company enrich endpoint working!")
                company_data = response.json()
                if company_data:
                    print(f"Found company: {company_data.get('name')}")
                    company_id = company_data.get('id')
                    print(f"Company ID: {company_id}")
                    print(f"Website: {company_data.get('website')}")
                    print(f"Industry: {company_data.get('industry')}")
                    print(f"Employees: {company_data.get('employee_count')}")

                    # Test employee search
                    print()
                    print("Testing Employee Search Endpoint (ES DSL API)...")
                    print("-" * 50)

                    emp_url = f"{base_url}/employee_clean/search/es_dsl"
                    emp_payload = {
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
                                        "match": {
                                            "country": "Taiwan"
                                        }
                                    }
                                ]
                            }
                        }
                    }
                    emp_params = {'limit': 10}

                    print(f"URL: {emp_url}")
                    print(f"Payload: {emp_payload}")
                    print(f"Params: {emp_params}")
                    print()

                    emp_response = await client.post(
                        emp_url,
                        headers={
                            'apikey': api_key,
                            'Content-Type': 'application/json'
                        },
                        params=emp_params,
                        json=emp_payload
                    )

                    print(f"Status Code: {emp_response.status_code}")
                    print(f"Response Body: {emp_response.text}")
                    print()

                    if emp_response.status_code == 200:
                        employees = emp_response.json()
                        print(f"✅ Employee search working! Found {len(employees)} Taiwan employees")
                    else:
                        print(f"❌ Employee search failed")
                else:
                    print("⚠️  Company not found in database")
            elif response.status_code == 401:
                print("❌ Authentication failed - API key is invalid")
            elif response.status_code == 404:
                print("❌ Endpoint not found - API may have changed")
                print()
                print("Possible issues:")
                print("1. Coresignal API endpoints have changed")
                print("2. API key doesn't have access to this endpoint")
                print("3. API version mismatch")
                print()
                print("Recommendation:")
                print("- Check Coresignal API documentation: https://docs.coresignal.com/")
                print("- Or try People Data Labs instead (has free tier)")
            else:
                print(f"❌ API call failed with status {response.status_code}")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()


if __name__ == '__main__':
    print("Coresignal API Diagnostic Tool")
    print("=" * 50)
    print()

    asyncio.run(test_coresignal_api())
