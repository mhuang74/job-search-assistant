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

    # Updated to v2 API (v1 endpoints deprecated as of late 2024)
    base_url = "https://api.coresignal.com/cdapi/v2"

    # Test company search endpoint
    print("Testing Company Search Endpoint (v2 API)...")
    print("-" * 50)

    company_name = "Stripe"
    url = f"{base_url}/company_base/search/filter"
    payload = {
        'name': company_name,
        'limit': 1
    }

    print(f"URL: {url}")
    print(f"Headers: Authorization: Bearer {api_key[:10]}...")
    print(f"Payload: {payload}")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                url,
                headers={'Authorization': f'Bearer {api_key}'},
                json=payload
            )

            print(f"Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            print(f"Response Body: {response.text}")
            print()

            if response.status_code == 200:
                print("✅ Company search endpoint working!")
                companies = response.json()
                if companies:
                    print(f"Found company: {companies[0].get('name')}")
                    company_id = companies[0].get('id')
                    print(f"Company ID: {company_id}")

                    # Test employee search
                    print()
                    print("Testing Employee Search Endpoint (v2 API)...")
                    print("-" * 50)

                    emp_url = f"{base_url}/employee_base/search/filter"
                    emp_payload = {
                        'company_id': company_id,
                        'country': 'Taiwan',  # v2 uses 'country' instead of 'location'
                        'limit': 10
                    }

                    print(f"URL: {emp_url}")
                    print(f"Payload: {emp_payload}")
                    print()

                    emp_response = await client.post(
                        emp_url,
                        headers={'Authorization': f'Bearer {api_key}'},
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
