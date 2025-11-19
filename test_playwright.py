#!/usr/bin/env python3
"""
Simple test script to verify Playwright is working correctly.
This will open a visible browser window and navigate to example.com.
"""
import asyncio
from playwright.async_api import async_playwright


async def test_browser(browser_type='chromium', headless=False):
    """Test if Playwright can launch a browser and navigate"""
    print(f"\n{'='*60}")
    print(f"Testing Playwright with {browser_type} (headless={headless})")
    print(f"{'='*60}\n")

    async with async_playwright() as p:
        try:
            # Launch browser
            print(f"1. Launching {browser_type} browser...")
            if browser_type == 'firefox':
                browser = await p.firefox.launch(headless=headless)
            else:
                browser = await p.chromium.launch(headless=headless)
            print(f"   ✅ Browser launched successfully!")

            # Create context and page
            print(f"2. Creating browser context...")
            context = await browser.new_context()
            print(f"   ✅ Context created!")

            print(f"3. Opening new page...")
            page = await context.new_page()
            print(f"   ✅ Page created!")

            # Navigate to example.com
            print(f"4. Navigating to https://example.com...")
            await page.goto('https://example.com', wait_until='domcontentloaded')
            print(f"   ✅ Navigation successful!")

            # Get page title
            title = await page.title()
            print(f"5. Page title: '{title}'")

            # Take screenshot
            screenshot_path = f'test_{browser_type}_screenshot.png'
            await page.screenshot(path=screenshot_path)
            print(f"6. Screenshot saved to: {screenshot_path}")

            # Wait a bit if visible so you can see it
            if not headless:
                print(f"\n⏳ Browser window should be visible now!")
                print(f"   Waiting 5 seconds so you can see it...")
                await asyncio.sleep(5)

            # Close
            print(f"7. Closing browser...")
            await browser.close()
            print(f"   ✅ Browser closed!")

            print(f"\n{'='*60}")
            print(f"✅ SUCCESS! Playwright is working with {browser_type}!")
            print(f"{'='*60}\n")
            return True

        except Exception as e:
            print(f"\n{'='*60}")
            print(f"❌ ERROR! Playwright test failed!")
            print(f"{'='*60}")
            print(f"Error type: {type(e).__name__}")
            print(f"Error message: {str(e)}")
            print(f"\n")
            import traceback
            traceback.print_exc()
            return False


async def main():
    """Run tests for both browsers"""
    print("\n" + "="*60)
    print("PLAYWRIGHT FUNCTIONALITY TEST")
    print("="*60)

    # Test Chromium visible
    success_chromium_visible = await test_browser('chromium', headless=False)

    # Test Chromium headless
    success_chromium_headless = await test_browser('chromium', headless=True)

    # Test Firefox visible
    success_firefox_visible = await test_browser('firefox', headless=False)

    # Test Firefox headless
    success_firefox_headless = await test_browser('firefox', headless=True)

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    print(f"Chromium (visible):  {'✅ PASS' if success_chromium_visible else '❌ FAIL'}")
    print(f"Chromium (headless): {'✅ PASS' if success_chromium_headless else '❌ FAIL'}")
    print(f"Firefox (visible):   {'✅ PASS' if success_firefox_visible else '❌ FAIL'}")
    print(f"Firefox (headless):  {'✅ PASS' if success_firefox_headless else '❌ FAIL'}")
    print("="*60 + "\n")

    if all([success_chromium_visible, success_chromium_headless,
            success_firefox_visible, success_firefox_headless]):
        print("🎉 All tests passed! Playwright is working correctly!")
        print("\nYou can now try running the Indeed scraper:")
        print("  python main.py search 'software engineer' --no-headless --verbose")
    else:
        print("⚠️  Some tests failed. Check the errors above.")


if __name__ == "__main__":
    asyncio.run(main())
