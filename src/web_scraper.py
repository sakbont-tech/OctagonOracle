from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import pandas as pd

url = "http://ufcstats.com/fight-details/a10deecfb8558335"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        page = browser.new_page()
            
        page.goto(url, wait_until="networkidle")
        
        html_content = page.content()
        
        browser.close()

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

    df = pd.DataFrame(parsed_rows, columns=fight_details_titles)

    print("\n--- PANDAS DATAFRAME SUCCESS ---")
    df = df.dropna(how='all')
    print(df.to_string(index=False))