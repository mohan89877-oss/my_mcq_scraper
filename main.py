import argparse
import csv
import json
import os
from datetime import datetime, timezone

import pandas as pd
from pydantic import BaseModel, Field
from scrapegraphai.graphs import SmartScraperGraph


# ---------------------------------------------------------------------------
# MCQ mode (original behavior — bulk-extract MCQs from urls.txt)
# ---------------------------------------------------------------------------
class MCQItem(BaseModel):
    question: str = Field(description="The clear question text")
    option_a: str = Field(description="Option A text")
    option_b: str = Field(description="Option B text")
    option_c: str = Field(description="Option C text")
    option_d: str = Field(description="Option D text")
    correct_answer: str = Field(description="The designated correct answer (e.g. 'Option A', 'A', or answer text)")


class MCQList(BaseModel):
    mcqs: list[MCQItem]


MCQ_PROMPT = (
    "Extract all Multiple Choice Questions (MCQs) present on the page. "
    "For every question, accurately identify and extract: "
    "1. The question text "
    "2. Option A "
    "3. Option B "
    "4. Option C "
    "5. Option D "
    "6. The correct answer (reveal hidden answer elements if necessary)."
)


def get_graph_config(api_key: str) -> dict:
    return {
        "llm": {
            "api_key": api_key,
            "model": "gemini/gemini-1.5-flash",
        },
        "headless": True,
        "verbose": True,
    }


def run_mcq_mode(api_key: str) -> None:
    if not os.path.exists("urls.txt"):
        print("urls.txt file not found!")
        return

    with open("urls.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    if not urls:
        print("No URLs found in urls.txt")
        return

    all_mcqs = []
    graph_config = get_graph_config(api_key)

    for index, url in enumerate(urls, start=1):
        print(f"\n[{index}/{len(urls)}] Scraping URL: {url}")
        try:
            scraper = SmartScraperGraph(
                prompt=MCQ_PROMPT,
                source=url,
                config=graph_config,
                schema=MCQList,
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
                        "Correct Answer": item.get("correct_answer", ""),
                    })
                print(f"Successfully extracted {len(result['mcqs'])} MCQs from {url}")
            else:
                print(f"No MCQs found or returned for {url}")

        except Exception as e:
            print(f"Error scraping {url}: {e}")

    if all_mcqs:
        os.makedirs("data", exist_ok=True)
        csv_path = "data/mcqs.csv"
        file_exists = os.path.exists(csv_path)
        df_new = pd.DataFrame(all_mcqs)
        df_new.to_csv(csv_path, mode="a", header=not file_exists, index=False)
        print(f"\nScraping complete! Total {len(all_mcqs)} questions saved to '{csv_path}'.")
    else:
        print("\nNo data was extracted from any URL.")


# ---------------------------------------------------------------------------
# General mode (new) — any URL + any prompt, ScrapeGraphAI-style free-form use
# ---------------------------------------------------------------------------
def run_general_mode(api_key: str, url: str, prompt: str) -> None:
    if not url or not prompt:
        print("General mode requires both a URL and a prompt (--url / --prompt, "
              "or SCRAPE_URL / SCRAPE_PROMPT env vars).")
        return

    graph_config = get_graph_config(api_key)

    print(f"\nScraping URL: {url}")
    print(f"Prompt: {prompt}")

    try:
        scraper = SmartScraperGraph(
            prompt=prompt,
            source=url,
            config=graph_config,
        )
        result = scraper.run()
    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return

    os.makedirs("data/general", exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    json_path = f"data/general/scrape_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(f"Saved raw result to {json_path}")

    log_path = "data/general_scrapes_log.csv"
    file_exists = os.path.exists(log_path)
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["Timestamp", "URL", "Prompt", "Result_File"])
        writer.writerow([timestamp, url, prompt, json_path])

    print("\nExtracted result:")
    print(json.dumps(result, indent=2, default=str))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="AI-powered web scraper — mcq mode (bulk, urls.txt) or general mode (any URL + prompt)."
    )
    parser.add_argument(
        "--mode", choices=["mcq", "general"],
        default=os.getenv("SCRAPE_MODE", "mcq"),
        help="mcq: bulk-extract MCQs from urls.txt. general: extract anything from one URL+prompt.",
    )
    parser.add_argument("--url", default=os.getenv("SCRAPE_URL", ""), help="Target URL (general mode only)")
    parser.add_argument("--prompt", default=os.getenv("SCRAPE_PROMPT", ""), help="What to extract (general mode only)")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set. Please provide a valid key.")

    if args.mode == "general":
        run_general_mode(api_key, args.url, args.prompt)
    else:
        run_mcq_mode(api_key)


if __name__ == "__main__":
    main()
