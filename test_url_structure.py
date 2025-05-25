import requests
from bs4 import BeautifulSoup
import re

def check_url_structure(url):
    """Check the HTML structure of a URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Save the raw HTML for inspection
        with open('raw_html.txt', 'w', encoding='utf-8') as f:
            f.write(response.text)
        print(f"Raw HTML saved to raw_html.txt")

        soup = BeautifulSoup(response.text, 'html.parser')

        # Print all div elements with their class or id
        print("Div elements with class or id:")
        for div in soup.find_all('div'):
            if div.get('class') or div.get('id'):
                print(f"Div: class={div.get('class')}, id={div.get('id')}")

        # Check for common content containers
        content_candidates = [
            soup.find('div', class_='content'),
            soup.find('div', id='content'),
            soup.find('div', id='chaptercontent'),
            soup.find('div', class_='readcontent'),
            soup.find('div', class_='showtxt'),
            soup.find('div', id='txtContent'),
            soup.find('div', id='BookText'),
            soup.find('div', id='acontent'),
            soup.find('div', id='chapter-content'),
            soup.find('div', class_='read-content'),
            soup.find('div', class_='read-content j_readContent'),
            soup.find('article'),
            soup.find('div', class_='article'),
            soup.find('div', class_='chapter'),
            soup.find('div', class_='novel-content'),
            soup.find('div', class_='text-content')
        ]

        print("\nPotential content containers:")
        for i, candidate in enumerate(content_candidates):
            if candidate:
                print(f"Candidate {i+1}: {candidate.name}, class={candidate.get('class')}, id={candidate.get('id')}")
                # Print first 100 characters of text to verify
                text = candidate.get_text(strip=True)
                print(f"Sample text: {text[:100]}...")

                # Save the content to a file
                with open(f'candidate_{i+1}.txt', 'w', encoding='utf-8') as f:
                    f.write(candidate.get_text('\n', strip=True))
                print(f"Content saved to candidate_{i+1}.txt")

        # Try to find content using JavaScript patterns
        script_tags = soup.find_all('script')
        for i, script in enumerate(script_tags):
            if script.string:
                # Look for content in JavaScript variables
                content_match = re.search(r'var\s+content\s*=\s*[\'"](.+?)[\'"]', script.string, re.DOTALL)
                if content_match:
                    content = content_match.group(1)
                    print(f"\nFound content in script tag {i+1}:")
                    print(content[:100] + "..." if len(content) > 100 else content)

                    # Save the content to a file
                    with open(f'script_content_{i+1}.txt', 'w', encoding='utf-8') as f:
                        f.write(content)
                    print(f"Content saved to script_content_{i+1}.txt")

        return soup
    except Exception as e:
        print(f"Error checking URL structure: {e}")
        return None

if __name__ == "__main__":
    # Test with a URL from m1.csv
    test_url = "https://m.zashuwu.com/wen/2vFm/10.html"
    soup = check_url_structure(test_url)

    if soup:
        # Additional checks if needed
        print("\nPage title:", soup.title.string if soup.title else "No title found")
