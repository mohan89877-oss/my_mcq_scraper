import os
import pandas as pd
from pydantic import BaseModel, Field
from scrapegraphai.graphs import SmartScraperGraph

# Define structured schema for MCQ data
class MCQItem(BaseModel):
    question: str = Field(description="The clear question text")
    option_a: str = Field(description="Option A text")
    option_b: str = Field(description="Option B text")
    option_c: str = Field(description="Option C text")
    option_d: str = Field(description="Option D text")
    correct_answer: str = Field(description="The designated correct answer (e.g. 'Option A', 'A', or answer text)")

class MCQList(BaseModel):
    mcqs: list[MCQItem]

def run_scraper():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please provide a valid key.")

    # Read target links
    if not os.path.exists("urls.txt"):
        print("urls.txt file not found!")
        return

    with open("urls.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not urls:
        print("No URLs found in urls.txt")
        return

    all_mcqs = []

    # ScrapeGraphAI config using Gemini 1.5 Flash (Free tier model)
    graph_config = {
        "llm": {
            "api_key": api_key,
            "model": "gemini/gemini-1.5-flash",
        },
        "headless": True,
        "verbose": True,
    }

    prompt = (
        "Extract all Multiple Choice Questions (MCQs) present on the page. "
        "For every question, accurately identify and extract: "
        "1. The question text "
        "2. Option A "
        "3. Option B "
        "4. Option C "
        "5. Option D "
        "6. The correct answer (reveal hidden answer elements if necessary)."
    )

    for index, url in enumerate(urls, start=1):
        print(f"\n[{index}/{len(urls)}] Scraping URL: {url}")
        try:
            scraper = SmartScraperGraph(
                prompt=prompt,
                source=url,
                config=graph_config,
                schema=MCQList
            )
            result = scraper.run()

            if result and "mcqs" in result:
                for item in result["mcqs"]:
                    all_mcqs.append({
                        "Source_URL": url,
                        "Question": item.get("question", ""),
                        "Option A": item.get("option_a", ""),
                        "Option B": item.get("option_b", ""),
                        "Option C": item.get("option_c", ""),
                        "Option D": item.get("option_d", ""),
                        "Correct Answer": item.get("correct_answer", "")
                    })
                print(f"Successfully extracted {len(result['mcqs'])} MCQs from {url}")
            else:
                print(f"No MCQs found or returned for {url}")

        except Exception as e:
            print(f"Error scraping {url}: {e}")

    # Export scraped data to CSV
    if all_mcqs:
        os.makedirs("data", exist_ok=True)
        csv_path = "data/mcqs.csv"
        df = pd.DataFrame(all_mcqs)
        df.to_csv(csv_path, index=False)
        print(f"\nScraping complete! Total {len(all_mcqs)} questions saved to '{csv_path}'.")
    else:
        print("\nNo data was extracted from any URL.")

if __name__ == "__main__":
    run_scraper()
