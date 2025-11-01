#!/usr/bin/env python3
"""
Playwright test for agent execution on the Streamlit dashboard.

This test:
1. Navigates to the Agent Execution page
2. Fills in the company list with three test companies
3. Executes the agent
4. Waits for all three companies to be processed
5. Verifies successful completion
"""

import asyncio
import os
import subprocess
from pathlib import Path

from playwright.async_api import async_playwright, expect  # type: ignore

# Test configuration
BASE_URL = "http://172.234.181.156:8501"
AGENT_PAGE_URL = f"{BASE_URL}/Agent"
REMOTE_HOST = "172.234.181.156"
REMOTE_USER = "langchain"
REMOTE_DB_PATH = "~/langchain-demo/data/research_agent.db"
SSH_KEY_PATH = os.getenv("LANGCHAIN_SSH_KEY", os.path.expanduser("~/.ssh/id_ed25519_langchain"))

# Three test companies
TEST_COMPANIES = [
    "BitMovin",
    "Hydrolix",
    "Queue-it"
]

def _ensure_ssh_key_available() -> None:
    key_path = Path(SSH_KEY_PATH)
    if not key_path.exists():
        raise FileNotFoundError(
            f"SSH key not found at {SSH_KEY_PATH}. Set LANGCHAIN_SSH_KEY to override."
        )


def _run_remote_python(script: str) -> str:
    result = subprocess.run(
        [
            "ssh",
            "-i",
            SSH_KEY_PATH,
            f"{REMOTE_USER}@{REMOTE_HOST}",
            "python3",
            "-c",
            script,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _clear_remote_companies() -> None:
    script = (
        "import sqlite3\n"
        "from pathlib import Path\n"
        "path = Path(\"{REMOTE_DB_PATH}\").expanduser()\n"  # placeholder
        "path.parent.mkdir(parents=True, exist_ok=True)\n"
        "conn = sqlite3.connect(path)\n"
        "conn.execute('CREATE TABLE IF NOT EXISTS companies (id INTEGER PRIMARY KEY AUTOINCREMENT, company_name TEXT UNIQUE, industry TEXT, company_size TEXT, headquarters TEXT, founded INTEGER, revenue TEXT, funding_stage TEXT, products TEXT, competitors TEXT, description TEXT, website TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP)')\n"
        "conn.execute('DELETE FROM companies')\n"
        "conn.commit()\n"
    ).replace("{REMOTE_DB_PATH}", REMOTE_DB_PATH)
    _run_remote_python(script)


def _fetch_remote_company_rows() -> dict[str, dict[str, str]]:
    script = (
        "import sqlite3\n"
        "from pathlib import Path\n"
        "path = Path(\"{REMOTE_DB_PATH}\").expanduser()\n"
        "conn = sqlite3.connect(path)\n"
        "rows = conn.execute('SELECT company_name, industry, company_size, headquarters FROM companies').fetchall()\n"
        "for row in rows:\n"
        "    print('|'.join(str(item or '') for item in row))\n"
    ).replace("{REMOTE_DB_PATH}", REMOTE_DB_PATH)
    output = _run_remote_python(script)

    results: dict[str, dict[str, str]] = {}
    if not output:
        return results
    for line in output.splitlines():
        parts = line.split("|")
        if len(parts) != 4:
            continue
        name, industry, company_size, headquarters = parts
        results[name.strip()] = {
            "industry": industry.strip(),
            "company_size": company_size.strip(),
            "headquarters": headquarters.strip(),
        }
    return results


async def test_agent_execution():
    """Test agent execution with three test companies."""
    print(f"Starting Playwright test for agent execution...")
    print(f"Target URL: {AGENT_PAGE_URL}")
    print(f"Test companies: {', '.join(TEST_COMPANIES)}")

    _ensure_ssh_key_available()
    print("\n0. Clearing remote database companies table...")
    await asyncio.to_thread(_clear_remote_companies)

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()

        try:
            # Navigate to the Agent Execution page
            print("\n1. Navigating to Agent Execution page...")
            await page.goto(AGENT_PAGE_URL, wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)  # Wait for Streamlit to fully load

            # Wait for page to be ready
            print("2. Waiting for page to load...")
            await page.wait_for_selector("text=Agent Execution", timeout=30000)
            print("✓ Page loaded successfully")

            # Find the company text area
            print("\n3. Looking for company text area...")
            # In Streamlit, text areas are typically in a div with data-testid
            textarea = page.locator('textarea').first
            await expect(textarea).to_be_visible(timeout=10000)
            print("✓ Found company text area")

            # Clear existing text and enter test companies
            print("\n4. Entering test companies...")
            await textarea.click()
            await textarea.press("Control+A")  # Select all
            await textarea.press("Backspace")  # Clear

            # Type each company on a new line
            companies_text = "\n".join(TEST_COMPANIES)
            await textarea.fill(companies_text)
            print(f"✓ Entered {len(TEST_COMPANIES)} companies")

            # Verify the companies were entered correctly
            await page.wait_for_timeout(1000)

            # Find and click the Execute Agent button
            print("\n5. Looking for Execute Agent button...")
            execute_button = page.locator('button:has-text("Execute Agent")')
            await expect(execute_button).to_be_visible(timeout=10000)
            print("✓ Found Execute Agent button")

            print("\n6. Clicking Execute Agent button...")
            await execute_button.click()
            print("✓ Clicked Execute Agent button")

            # Wait for execution to start
            await page.wait_for_timeout(3000)
            await page.wait_for_timeout(3000)

            # Monitor execution progress
            print("\n7. Monitoring execution progress...")
            print("   This may take several minutes...")

            # Wait for all companies to be processed
            # Look for success indicators for each company
            for i, company in enumerate(TEST_COMPANIES, 1):
                print(f"\n   Processing {i}/{len(TEST_COMPANIES)}: {company}")
                company_label = page.locator(f"text={company}").first
                await expect(company_label).to_be_visible(timeout=180000)
                print(f"   ✓ Found {company} in results")

            stored_badges = page.locator("text=Stored to database")
            await expect(stored_badges).to_have_count(len(TEST_COMPANIES), timeout=180000)
            print("   ✓ All results stored to database")

            reasoning_sections = page.locator("text=🧠 Agent Reasoning & Tool Calls")
            await expect(reasoning_sections).to_have_count(len(TEST_COMPANIES), timeout=60000)
            print("   ✓ Agent reasoning sections present")

            for i, company in enumerate(TEST_COMPANIES):
                section = reasoning_sections.nth(i)
                await section.click()
                details_container = section.locator("xpath=ancestor::details[1]")
                query_code = details_container.locator("code").first
                await expect(query_code).to_be_visible(timeout=10000)
                query_text = (await query_code.text_content()) or ""
                assert query_text.strip(), f"Tool query missing for {company}"

                raw_caption = details_container.locator("text=Raw provider response:")
                await expect(raw_caption).to_be_visible(timeout=10000)
                print(f"   ✓ {company} reasoning trace captured")

            # Wait for final completion message
            print("\n8. Waiting for final completion...")
            await page.wait_for_timeout(5000)

            # Look for the "All companies processed" message or similar
            await expect(page.locator('text=All companies processed')).to_be_visible(timeout=60000)
            print("✓ All companies processed successfully!")

            # Check for Results Summary section
            print("\n9. Verifying results summary...")
            try:
                results_header = page.locator('text=Results Summary')
                await expect(results_header).to_be_visible(timeout=10000)
                print("✓ Results summary displayed")

                # Try to read metrics
                total_processed = page.locator('text=Total Processed').locator('..')
                if await total_processed.count() > 0:
                    print("✓ Found total processed metric")

                successful = page.locator('text=Successful').locator('..')
                if await successful.count() > 0:
                    print("✓ Found successful metric")

            except Exception as e:
                print(f"⚠ Warning: Could not verify results summary: {e}")

            # Take a screenshot of the final results
            print("\n10. Taking screenshot of results...")
            screenshot_path = "/Users/jabrown/Documents/GitHub/Linode/langchain-demo/tests/agent_execution_results.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"✓ Screenshot saved to: {screenshot_path}")

            print("\n11. Validating remote database entries...")
            remote_companies = await asyncio.to_thread(_fetch_remote_company_rows)
            missing = [c for c in TEST_COMPANIES if c not in remote_companies]
            assert not missing, f"Missing companies in database: {missing}"

            for name, details in remote_companies.items():
                assert details["industry"], f"Industry missing for {name}"
                assert details["company_size"], f"Company size missing for {name}"
                assert details["headquarters"], f"Headquarters missing for {name}"
            print("✓ Database contains entries for all companies")

            print("\n" + "="*60)
            print("✅ TEST PASSED - Agent execution completed successfully!")
            print("="*60)

        except Exception as e:
            print("\n" + "="*60)
            print(f"❌ TEST FAILED - Error occurred: {e}")
            print("="*60)

            # Take error screenshot
            try:
                error_screenshot = "/Users/jabrown/Documents/GitHub/Linode/langchain-demo/tests/agent_execution_error.png"
                await page.screenshot(path=error_screenshot, full_page=True)
                print(f"Error screenshot saved to: {error_screenshot}")
            except:
                pass

            raise

        finally:
            # Close browser
            await browser.close()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_agent_execution())
