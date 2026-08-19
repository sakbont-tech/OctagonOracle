import json
import os
import random
import time

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

MIN_DELAY = 3.0          
MAX_DELAY = 6.0            
MAX_RETRIES = 4            
BACKOFF_BASE = 8.0         
RATE_LIMIT_BACKOFF = 60.0  
NAV_TIMEOUT_MS = 30_000

DATA_DIR = "data/raw"
OUTPUT_CSV = os.path.join(DATA_DIR, "historical_ufc_data.csv")
PROGRESS_FILE = os.path.join(DATA_DIR, "scrape_progress.json")


class NavigationFailed(Exception):
    """Raised when safe_goto exhausts all retries for a URL."""


def polite_delay():
    """Randomized delay so requests don't land at a robotic, fixed cadence."""
    time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))


def safe_goto(page, url):
    """
    Navigate to url with retries + exponential backoff.
    Returns True on success, False if every attempt failed.
    HTTP 429 gets a much longer, escalating pause since it's the site
    explicitly telling us to slow down.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = page.goto(url, wait_until="networkidle", timeout=NAV_TIMEOUT_MS)
        except Exception as e:
            wait = BACKOFF_BASE * (2 ** (attempt - 1)) + random.uniform(0, 3)
            print(f"    ! navigation error on {url} (attempt {attempt}/{MAX_RETRIES}): {type(e).__name__}")
            print(f"    ! backing off {wait:.1f}s...")
            time.sleep(wait)
            continue

        if response is None or response.status < 400:
            return True

        if response.status == 429:
            wait = RATE_LIMIT_BACKOFF * attempt + random.uniform(0, 10)
            print(f"    ! 429 Too Many Requests on {url} -- pausing {wait:.0f}s")
        else:
            wait = BACKOFF_BASE * (2 ** (attempt - 1)) + random.uniform(0, 3)
            print(f"    ! HTTP {response.status} on {url} (attempt {attempt}/{MAX_RETRIES}) -- backing off {wait:.1f}s")
        time.sleep(wait)

    print(f"    ! giving up on {url} after {MAX_RETRIES} attempts.")
    return False


def load_progress():
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_progress(done_events):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PROGRESS_FILE, "w") as f:
        json.dump(sorted(done_events), f, indent=2)


def append_rows_to_csv(rows, titles):
    """Append one event's worth of rows to the output CSV (header written once)."""
    os.makedirs(DATA_DIR, exist_ok=True)
    file_exists = os.path.exists(OUTPUT_CSV)
    df = pd.DataFrame(rows, columns=titles)
    df = df.dropna(how="all")
    df.to_csv(OUTPUT_CSV, mode="a", header=not file_exists, index=False)


def get_all_events(page, site_url):
    if not safe_goto(page, site_url):
        raise NavigationFailed(site_url)

    event_urls = []
    html_content = page.content()
    site = BeautifulSoup(html_content, "html.parser")
    events = site.find_all("a", class_="b-link b-link_style_black")

    for event in events:
        event_link = event.get("href")
        if event_link:
            event_urls.append(event_link)
    return event_urls


def get_fight_urls(page, event_url):
    if not safe_goto(page, event_url):
        raise NavigationFailed(event_url)

    fight_urls = []
    html_content = page.content()
    event = BeautifulSoup(html_content, "html.parser")
    fights = event.find_all(
        "tr",
        class_="b-fight-details__table-row b-fight-details__table-row__hover js-fight-details-click",
    )
    for fight in fights:
        fight_link = fight.get("data-link")
        if fight_link:
            fight_urls.append(fight_link)
    return fight_urls


def scrape_fight_data(page, fight_url):
    if not safe_goto(page, fight_url):
        raise NavigationFailed(fight_url)

    html_content = page.content()
    soup = BeautifulSoup(html_content, "html.parser")

    all_tables = soup.find_all("table")

    if len(all_tables) < 3:
        print("  -> Missing Significant Strikes table. Skipping incomplete fight!")
        return None, None

    table_0 = all_tables[0]
    table_1 = all_tables[2] 

    t0_titles = [title.text.strip() for title in table_0.find("tr").find_all("th")]
    t1_titles = [title.text.strip() for title in table_1.find("tr").find_all("th")]

    t1_titles_clean = [f"{t} (SS)" for t in t1_titles[3:]]    
    fight_details_titles = ["Result"] + t0_titles + t1_titles_clean

    status_badges = soup.find_all("i", class_="b-fight-details__person-status")
    status_a = status_badges[0].text.strip()
    status_b = status_badges[1].text.strip()

    parsed_rows = []
    t0_rows = table_0.find_all("tr")
    t1_rows = table_1.find_all("tr")

    for row_0, row_1 in zip(t0_rows, t1_rows):
        cells_0 = row_0.find_all(["th", "td"])
        cells_1 = row_1.find_all(["th", "td"])

        if not cells_0 or not cells_1:
            continue

        row_data_0 = [cell.get_text(separator=" | ", strip=True) for cell in cells_0]
        row_data_1 = [cell.get_text(separator=" | ", strip=True) for cell in cells_1]

        if len(row_data_0) != len(t0_titles) or len(row_data_1) != len(t1_titles):
            continue

        if row_data_0[0] == "Fighter":
            continue

        fighter_a_t0, fighter_b_t0 = [], []
        fighter_a_t1, fighter_b_t1 = [], []

        for cell_value in row_data_0:
            if " | " in cell_value:
                a, b = cell_value.split(" | ")
                fighter_a_t0.append(a)
                fighter_b_t0.append(b)
            else:
                fighter_a_t0.append(cell_value)
                fighter_b_t0.append(cell_value)

        for cell_value in row_data_1:
            if " | " in cell_value:
                a, b = cell_value.split(" | ")
                fighter_a_t1.append(a)
                fighter_b_t1.append(b)
            else:
                fighter_a_t1.append(cell_value)
                fighter_b_t1.append(cell_value)

        combined_fighter_a = [status_a] + fighter_a_t0 + fighter_a_t1[3:]
        combined_fighter_b = [status_b] + fighter_b_t0 + fighter_b_t1[3:]

        if len(combined_fighter_a) == len(fight_details_titles):
            parsed_rows.append(combined_fighter_a)
            parsed_rows.append(combined_fighter_b)

    return parsed_rows, fight_details_titles

def main():
    site_url = "http://ufcstats.com/statistics/events/completed?page=all"
    done_events = load_progress()

    if done_events:
        print(f"Resuming: {len(done_events)} events already scraped, will skip them.")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            print("Fetching all historical events...")
            try:
                event_urls = get_all_events(page, site_url)
            except NavigationFailed:
                print("Could not load the events list page after retries.")
                print("Check your connection, or the site may be blocking this IP right now.")
                return

            event_urls = event_urls[:250]            
            remaining = [e for e in event_urls if e not in done_events]
            print(f"{len(event_urls)} events total, {len(remaining)} left to scrape.")

            for i, event in enumerate(remaining, 1):
                print(f"\n--- Event {i}/{len(remaining)}: {event} ---")

                try:
                    fight_urls = get_fight_urls(page, event)
                except NavigationFailed:
                    print(f"    ! could not load event page, will retry next run: {event}")
                    polite_delay()
                    continue

                polite_delay()

                event_rows, event_titles = [], []
                any_fight_failed = False

                for fight in fight_urls:
                    try:
                        fight_data, titles = scrape_fight_data(page, fight)
                    except NavigationFailed:
                        print(f"    ! could not load fight page, will retry whole event next run: {fight}")
                        any_fight_failed = True
                        polite_delay()
                        continue

                    if fight_data and titles:
                        event_rows.extend(fight_data)
                        event_titles = titles

                    polite_delay()

                if any_fight_failed:
                    print("    ! skipping write for this event to avoid duplicate rows; will retry it fully next run.")
                    continue

                if event_rows:
                    append_rows_to_csv(event_rows, event_titles)

                done_events.add(event)
                save_progress(done_events)

        finally:
            browser.close()

    print(f"\nExport complete -- data written incrementally to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
