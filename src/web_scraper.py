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

    table_0 = all_tables[0]
    table_1 = all_tables[1]

    t0_titles = [title.text.strip() for title in table_0.find("tr").find_all("th")]
    t1_titles = [title.text.strip() for title in table_1.find("tr").find_all("th")]

    t1_titles_clean = [f"{t} (SS)" for t in t1_titles[1:]]

    fight_details_titles = t0_titles + t1_titles_clean

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

        if len(row_data_0) != len(t0_titles) or row_data_0[0] == "Fighter":
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

        combined_fighter_a = fighter_a_t0 + fighter_a_t1[1:]
        combined_fighter_b = fighter_b_t0 + fighter_b_t1[1:]

        parsed_rows.append(combined_fighter_a)
        parsed_rows.append(combined_fighter_b)

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
