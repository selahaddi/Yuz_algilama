import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://yuz-tanima-frontend.vercel.app/?event_id=8615eca4-ddb0-43c9-a866-d25479c0e9bb', wait_until='networkidle')
        await page.screenshot(path='screenshot.png')
        print(await page.content())
        await browser.close()

asyncio.run(main())
