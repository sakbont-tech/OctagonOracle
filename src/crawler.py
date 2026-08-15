from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

url = "http://ufcstats.com/event-details/495add4fbede0a44"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    page = browser.new_page()
        
    page.goto(url, wait_until="networkidle")
    
    html_content = page.content()
    
    browser.close()

event = BeautifulSoup(html_content, "html.parser")
fights = event.find_all("tr", class_="b-fight-details__table-row b-fight-details__table-row__hover js-fight-details-click")
for fight in fights:
    fight_link = fight.get('data-link')
    if fight_link:
        print(fight_link)
