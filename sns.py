import asyncio
from playwright.async_api import async_playwright

async def get_solscan_labels(address: str):
    url = f"https://solscan.io/account/{address}"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # or headless=False to watch it work
        page = await browser.new_page()
        await page.goto(url, wait_until='networkidle')

        # Wait for the main info section
        await page.wait_for_selector("div", timeout=10000)

        # Extract Public name
        public_name = None
        try:
            name_element = await page.query_selector("div:has-text('Public name')")
            if name_element:
                wrapper = await name_element.evaluate_handle("node => node.parentElement.parentElement.nextElementSibling")
                if wrapper:
                    name = await wrapper.query_selector("div.font-bold")
                    if name:
                        public_name = (await name.inner_text()).strip()
        except Exception:
            pass

        # Extract tags (e.g. #Coinbase Exchange, #Exchange Wallet)
        tags = []
        try:
            tag_elements = await page.query_selector_all("a[href^='/labelcloud']")
            for tag in tag_elements:
                txt = await tag.inner_text()
                if txt.startswith("#"):
                    tags.append(txt.strip("#"))
        except Exception:
            pass

        await browser.close()
        return tags


# Example usage
if __name__ == "__main__":
    address = "3yFwqXBfZY4jBVUafQ1YEXw189y2dN3V5KQq9uzBDy1E"  # Coinbase 4 wallet
    tags = asyncio.run(get_solscan_labels(address))
    print(tags)




