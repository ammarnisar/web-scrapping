# =======================
# Libraries and their usage
# =======================

import asyncio            # Built-in library for asynchronous programming (running tasks concurrently)
import aiohttp            # Async HTTP client for making non-blocking web requests
import pandas as pd       # Data handling and exporting results to Excel
from datetime import datetime  # To get the current date and time for timestamps
from bs4 import BeautifulSoup  # HTML parsing and extracting readable text
import logging            # Structured logging instead of print statements
from typing import List, Dict, Any  # Type hints for better code readability and maintainability


# =======================
# Logging configuration
# =======================
logging.basicConfig(
    level=logging.INFO,  # Show INFO, WARNING, ERROR messages
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


# =======================
# Constants / Configuration
# =======================
API_KEY = "please create your own account for the key access link: https://serpapi.com/ "      # SerpAPI key to access Google search results
CITY = "Lahore"                    # City to search coffee shops in
PLACE_TYPES = ["coffee shops"]     # Types of places to search
RESULTS_LIMIT = 5                  # Number of results per query
OUTPUT_FILE = "Coffee_Shops_Lahore.xlsx"  # Excel file to save results
DELAY_BETWEEN_QUERIES = 1          # Seconds to wait between queries (throttle API requests)


# =======================
# Function: Fetch HTML Page (Async)
# =======================
async def fetch_page(session: aiohttp.ClientSession, url: str) -> str:
    """
    Fetch the content of a page asynchronously.
    Library used: aiohttp
    """
    try:
        async with session.get(url, timeout=10) as response:
            response.raise_for_status()
            text = await response.text()  # Non-blocking page fetch
            return text
    except Exception as e:
        logging.warning(f"Failed to fetch URL {url}: {e}")
        return ""


# =======================
# Function: Extract Readable Text
# =======================
def extract_details_from_html(html: str, char_limit: int = 600) -> str:
    """
    Extract readable text from HTML using BeautifulSoup.
    Libraries used: bs4 (BeautifulSoup)
    """
    if not html:
        return "N/A"
    soup = BeautifulSoup(html, "html.parser")  # Parse HTML
    text = " ".join(soup.stripped_strings)     # Extract readable text
    return text[:char_limit]                   # Limit to first 600 characters


# =======================
# Function: Fetch + Extract Page Details (Async)
# =======================
async def extract_place_details(session: aiohttp.ClientSession, link: str) -> str:
    """
    Combines fetching and extracting details for a single link asynchronously.
    Libraries used: aiohttp + BeautifulSoup
    """
    html = await fetch_page(session, link)
    return extract_details_from_html(html)


# =======================
# Function: Fetch Places Data (Async)
# =======================
async def fetch_places_async(city: str, place_types: List[str], api_key: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Fetches search results from SerpAPI and extracts details concurrently.
    Libraries used: aiohttp, asyncio, BeautifulSoup
    """
    all_data: List[Dict[str, Any]] = []

    async with aiohttp.ClientSession() as session:  # Async HTTP session
        for place in place_types:
            query = f"{place} in {city}"
            logging.info(f"Searching: {query}")

            params = {
                "engine": "google",
                "q": query,
                "num": limit,
                "api_key": api_key
            }

            try:
                async with session.get("https://serpapi.com/search", params=params) as resp:
                    resp.raise_for_status()
                    results = await resp.json()  # Get JSON response asynchronously
                    tasks = []

                    for result in results.get("organic_results", []):
                        title = result.get("title", "N/A")
                        snippet = result.get("snippet", "N/A")
                        link = result.get("link", "")

                        tasks.append(extract_place_details(session, link))  # Schedule async detail extraction

                        all_data.append({
                            "City": city,
                            "Place Type": place,
                            "Name": title,
                            "Description": snippet,
                            "Details": None,  # Will be updated after async task
                            "Link": link,
                            "Fetched On": datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Library: datetime
                        })

                    # Run all detail extraction tasks concurrently
                    details_results = await asyncio.gather(*tasks)  # Library: asyncio

                    # Update extracted details in all_data
                    for i, details in enumerate(details_results):
                        all_data[-len(details_results) + i]["Details"] = details

                    # Delay between queries to avoid rate-limiting
                    await asyncio.sleep(DELAY_BETWEEN_QUERIES)

            except Exception as e:
                logging.error(f"Error fetching {place} in {city}: {e}")

    return all_data


# =======================
# Function: Save Data to Excel
# =======================
def save_to_excel(data: List[Dict[str, Any]], file_name: str) -> None:
    """
    Save data to Excel using Pandas.
    Libraries used: pandas
    """
    if data:
        df = pd.DataFrame(data)
        df.to_excel(file_name, index=False)  # Export to Excel
        logging.info(f"✅ Data saved successfully to '{file_name}'")
    else:
        logging.warning("⚠️ No data to save.")


# =======================
# Main Execution
# =======================
if __name__ == "__main__":
    place_data = asyncio.run(fetch_places_async(CITY, PLACE_TYPES, API_KEY, RESULTS_LIMIT))  # Library: asyncio
    save_to_excel(place_data, OUTPUT_FILE)  # Library: pandas
