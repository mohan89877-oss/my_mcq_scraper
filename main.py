import os
import pandas as pd
from pydantic import BaseModel, Field
from scrapegraphai.graphs import SmartScraperGraph

# Define the exact output structure for MCQs
class MCQItem(BaseModel):
    question: str = Field(description="The question text")
    option_a: str = Field(description="Option A text")
    option_b: str = Field(description="Option B text")
    option_c: str = Field(description="Option C text")
    option_d: str = Field(description="Option D text")
    correct_answer: str = Field(description="Correct answer letter or text")

class MCQList(BaseModel):
    mcqs: list[MCQItem]

def process_urls():
    # Load target URLs
    with open("urls.txt", "r") as f:
        urls = [line.strip() for line in f if line.strip()]

    all_data = []

    graph_config = {
        "llm": {
            "api_key": os.getenv("GEMINI_API_KEY"),
            "model": "gemini/gemini-1.5-flash",
        },
        "verbose": True,
    }

    prompt = (
        "Extract all Multiple Choice Questions (MCQs) from the page. "
        "For each question, extract the question text, option A, option B, "
        "option C, option D, and the designated correct answer."
    )

    for url in urls:
        print(f"Scraping: {url}")
        smart_scraper = SmartScraperGraph(
            prompt=prompt,
            source=url,
            config=graph_config,
            schema=MCQList
        )
        
        result = smart_scraper.run()
        
        # Parse result into standard records
        if result and "mcqs" in result:
            for item in result["mcqs"]:
                all_data.append({
                    "Source_URL": url,
                    "Question": item.get("question", ""),
                    "Option A": item.get("option_a", ""),
                    "Option B": item.get("option_b", ""),
                    "Option C": item.get("option_c", ""),
                    "Option D": item.get("option_d", ""),
                    "Correct Answer": item.get("correct_answer", "")
                })

    # Save to CSV
    if all_data:
        df = pd.DataFrame(all_data)
        os.makedirs("data", exist_ok=True)
        df.to_csv("data/mcqs.csv", index=False)
        print("Scraping completed! Data saved to data/mcqs.csv")

if __name__ == "__main__":
    process_urls()
