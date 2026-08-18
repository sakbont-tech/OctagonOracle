from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import pandas as pd
import time


def get_all_events(page, site_url):

    event_urls = []

    page.goto(site_url, wait_until="networkidle")

    html_content = page.content()

    site = BeautifulSoup(html_content, "html.parser")

    events = site.find_all("a", class_="b-link b-link_style_black")

    for event in events:
        event_link = event.get("href")
        if event_link:
            event_urls.append(event_link)
    return event_urls


def get_fight_urls(page, event_url):

    fight_urls = []

    page.goto(event_url, wait_until="networkidle")

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

    page.goto(fight_url, wait_until="networkidle")

    html_content = page.content()

    soup = BeautifulSoup(html_content, "html.parser")

    all_tables = soup.find_all("table")

    if len(all_tables) < 2:
        print("  -> No stats table found. Skipping upcoming/empty fight!")
        return None, None

    table = all_tables[1]

    first_row = table.find("tr")

    table_titles = first_row.find_all("th")

    fight_details_titles = [title.text.strip() for title in table_titles]

    df = pd.DataFrame(columns=fight_details_titles)

    parsed_rows = []

    for row in table.find_all("tr"):
        cells = row.find_all(["th", "td"])
        if not cells:
            continue

        row_data = [cell.get_text(separator=" | ", strip=True) for cell in cells]

        if len(row_data) != len(fight_details_titles) or row_data[0] == "Fighter":
            continue

        fighter_a_stats = []
        fighter_b_stats = []
        for cell_value in row_data:
            if " | " in cell_value:
                a, b = cell_value.split(" | ")
                fighter_a_stats.append(a)
                fighter_b_stats.append(b)
            else:
                fighter_a_stats.append(cell_value)
                fighter_b_stats.append(cell_value)

        parsed_rows.append(fighter_a_stats)
        parsed_rows.append(fighter_b_stats)

    return parsed_rows, fight_details_titles


def main():

    master_parsed_rows = []
    final_titles = []

    site_url = "http://ufcstats.com/statistics/events/completed?page=all"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page()

        print("Fetching all historical events...")
        event_urls = get_all_events(page, site_url)

        for event in event_urls:
            print(f"\n--- Entering Event: {event} ---")
            fight_urls = get_fight_urls(page, event)

            for fight in fight_urls:
                fight_data, titles = scrape_fight_data(page, fight)

                if fight_data and titles:
                    master_parsed_rows.extend(fight_data)
                    final_titles = titles

                print("Pausing for 2 seconds to avoid ban...")
                time.sleep(2)

        browser.close()

    print("\n--- BUILDING MASTER DATAFRAME ---")
    df = pd.DataFrame(master_parsed_rows, columns=final_titles)
    df = df.dropna(how="all")

    df.to_csv("data/raw/historical_ufc_data.csv", index=False)
    print("Export Complete! Database secured.")


if __name__ == "__main__":
    main()
