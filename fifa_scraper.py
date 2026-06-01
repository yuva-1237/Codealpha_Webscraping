from playwright.sync_api import sync_playwright
import pandas as pd
import re

def scrape_fifa_world_cup_stats():
    url = "https://en.wikipedia.org/wiki/FIFA_World_Cup"

    with sync_playwright() as p:
        # Launch browser in headless mode
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Navigating to {url}...")
        page.goto(url, wait_until="networkidle")

        # Locate all tables of class wikitable
        tables = page.locator("table.wikitable")
        total_tables = tables.count()
        print(f"Total wikitables found: {total_tables}")

        # Robustly locate the correct table by checking for specific headers
        target_table = None
        for i in range(total_tables):
            table = tables.nth(i)
            inner_text = table.inner_text().lower()
            if "champion" in inner_text and "runner-up" in inner_text and "third place" in inner_text:
                target_table = table
                print(f"Found the tournament summary table at index: {i}")
                break

        if target_table is None:
            print("Error: Could not locate the World Cup tournament summary table.")
            browser.close()
            return []

        rows = target_table.locator("tr")
        row_count = rows.count()
        print(f"Processing {row_count} rows from the table...")

        data = []

        # Helper regex to clean Wikipedia citation footnotes like [n 1] or [1]
        footnote_regex = re.compile(r"\[[^\]]+\]")

        for i in range(2, row_count):  # Skip the first two header rows
            row = rows.nth(i)
            cells = row.locator("th, td")
            cell_count = cells.count()

            # Inspect the row content
            row_texts = [cells.nth(j).inner_text().strip() for j in range(cell_count)]

            # Skip rows representing years where the tournament was not held
            # (e.g. 1942, 1946 which contain "Not held due to World War II")
            if any("not held" in text.lower() or "world war" in text.lower() for text in row_texts):
                continue

            # Standard tournament rows have 10 columns:
            # [Ed., Year, Host, Champion, Score, Runner-up, Third place, Score, Fourth place, Teams]
            if cell_count == 10:
                cleaned_row = []
                for j in range(cell_count):
                    text = row_texts[j]
                    # Replace various unicode dashes with standard hyphens
                    text = text.replace("\u2013", "-").replace("\u2014", "-").replace("–", "-")
                    # Remove Wikipedia footnotes
                    text = footnote_regex.sub("", text)
                    # Normalize whitespace
                    text = " ".join(text.split())
                    cleaned_row.append(text)
                
                data.append(cleaned_row)
            else:
                # Handle unexpected rows or edge cases with rowspans gracefully
                continue

        browser.close()
        return data


if __name__ == "__main__":
    fifa_data = scrape_fifa_world_cup_stats()

    if not fifa_data:
        print("No data extracted. Please check the website layout or network connectivity.")
    else:
        # Define clean and rich columns matching the extracted table structure
        columns = [
            "Edition",
            "Year",
            "Host",
            "Champion",
            "Score",
            "Runner-up",
            "Third Place",
            "Third Place Score",
            "Fourth Place",
            "Teams"
        ]

        df = pd.DataFrame(fifa_data, columns=columns)

        print("\n--- Scraped FIFA World Cup Tournaments Data (First 5 Rows) ---")
        print(df.head())

        # Save to CSV using utf-8-sig to ensure Excel handles special characters correctly
        output_file = "fifa_world_cup_stats.csv"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"\nSuccessfully saved {len(df)} records to '{output_file}'.")