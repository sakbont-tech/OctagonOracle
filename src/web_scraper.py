from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import pandas as pd

def get_fight_urls(page, event_url):

    fight_urls = []

    page.goto(event_url, wait_until="networkidle")
        
    html_content = page.content()

    event = BeautifulSoup(html_content, "html.parser")
    fights = event.find_all("tr", class_="b-fight-details__table-row b-fight-details__table-row__hover js-fight-details-click")
    for fight in fights:
        fight_link = fight.get('data-link')
        if fight_link:
            fight_urls.append(fight_link)
    return fight_urls

def scrape_fight_data(page, fight_url):

    page.goto(fight_url, wait_until="networkidle")
        
    html_content = page.content()

    soup = BeautifulSoup(html_content, "html.parser")

    table = soup.find_all("table")[1]

    first_row = table.find("tr")

    table_titles = first_row.find_all("th")

    fight_details_titles = [title.text.strip() for title in table_titles]

    df = pd.DataFrame(columns=fight_details_titles)

    parsed_rows = []

    for row in table.find_all('tr'):
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

    event_url = "http://ufcstats.com/event-details/495add4fbede0a44"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page()
                            
        fight_urls = get_fight_urls(page, event_url)

        for fight in fight_urls:
            fight_data, titles = scrape_fight_data(page, fight)

            master_parsed_rows.extend(fight_data)
            final_titles = titles

        browser.close()


    df = pd.DataFrame(master_parsed_rows, columns=final_titles)

    print("\n--- PANDAS DATAFRAME SUCCESS ---")
    df = df.dropna(how='all')
    print(df.to_string(index=False))

if __name__ == "__main__":
    main()