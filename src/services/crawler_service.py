import os
import sys
import time
import json
import random
import argparse
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

class RandomWalkCrawler:
    def __init__(self, seed_url, max_pages=10, delay=1.0):
        self.seed_url = seed_url
        self.max_pages = max_pages
        self.delay = delay
        self.visited = set()
        self.output_dir = "data/raw"
        os.makedirs(self.output_dir, exist_ok=True)

    def _is_valid_url(self, url, base_netloc):
        parsed = urlparse(url)
        # Ensure it stays within the same domain and uses http/https
        return parsed.netloc == base_netloc and parsed.scheme in ["http", "https"]

    def scrape_page(self, url):
        try:
            headers = {"User-Agent": "Mozilla/5.0 (RAGEvaluatorBot/1.0)"}
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Skipping {url}: Received status code {response.status_code}")
                return None, []

            soup = BeautifulSoup(response.text, "html.parser")
            
            # Clean unwanted structural elements
            for element in soup(["script", "style", "nav", "footer", "header"]):
                element.decompose()

            # Extract main textual content
            text_content = soup.get_text(separator="\n", strip=True)
            
            # Gather valid navigation links for random walking
            base_netloc = urlparse(url).netloc
            links = []
            for a_tag in soup.find_all("a", href=True):
                absolute_url = urljoin(url, a_tag["href"])
                # Strip out fragments/anchors
                absolute_url = absolute_url.split("#")[0]
                if self._is_valid_url(absolute_url, base_netloc) and absolute_url not in self.visited:
                    links.append(absolute_url)

            return {
                "url": url,
                "content": text_content,
                "timestamp": time.time()
            }, list(set(links))

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None, []

    def start_crawl(self):
        queue = [self.seed_url]
        pages_collected = 0
        base_netloc = urlparse(self.seed_url).netloc

        print(f"Starting random-walk crawl from seed: {self.seed_url}")
        print(f"Target max pages to collect: {self.max_pages}\n")

        while queue and pages_collected < self.max_pages:
            current_url = queue.pop(0)
            if current_url in self.visited:
                continue

            self.visited.add(current_url)
            print(f"[{pages_collected + 1}/{self.max_pages}] Crawling: {current_url}")

            page_data, discovered_links = self.scrape_page(current_url)
            if page_data and len(page_data["content"]) > 100:  # Skip virtually empty pages
                pages_collected += 1
                # Save raw output locally
                filename = f"page_{pages_collected}_{int(time.time())}.json"
                file_path = os.path.join(self.output_dir, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(page_data, f, ensure_ascii=False, indent=2)

            # Randomize discovered links to drive the random walk exploration
            random.shuffle(discovered_links)
            for link in discovered_links:
                if link not in self.visited and link not in queue and self._is_valid_url(link, base_netloc):
                    queue.append(link)

            time.sleep(self.delay)

        print(f"\nCrawl complete! Successfully saved {pages_collected} pages to '{self.output_dir}/'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run a random-walk web crawler for the RAG evaluation framework.")
    parser.add_argument(
        "--url", 
        type=str, 
        required=True, 
        help="The initial seed URL to start crawling from (e.g., https://example.com/docs)"
    )
    parser.add_argument(
        "--max-pages", 
        type=int, 
        default=5, 
        help="The maximum number of random pages to extract (default: 5)"
    )
    parser.add_argument(
        "--delay", 
        type=float, 
        default=1.0, 
        help="Delay in seconds between requests (default: 1.0)"
    )

    args = parser.parse_args()

    crawler = RandomWalkCrawler(
        seed_url=args.url,
        max_pages=args.max_pages,
        delay=args.delay
    )
    crawler.start_crawl()