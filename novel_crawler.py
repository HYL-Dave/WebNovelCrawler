import csv
import requests
from bs4 import BeautifulSoup
import time
import os
import re

def read_urls_from_csv(csv_file):
    """Read URLs from CSV file."""
    urls = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # Skip header
        for row in reader:
            # Check if the URL is in the first column (old format)
            if len(row) > 0 and (row[0].startswith('"https://') or row[0].startswith('https://')):
                url = row[0].strip('"')
                urls.append(url)
            # Check if the URL is in the second column (m1.csv format)
            elif len(row) > 1 and (row[1].startswith('"https://') or row[1].startswith('https://')):
                url = row[1].strip('"')
                urls.append(url)
    return urls

def clean_content(text):
    """Clean advertisement lines from the content."""
    # Define patterns to remove
    ad_patterns = [
        # Specific patterns mentioned in the requirements
        r'记住【德窝小说网】：DEWOXS\.COM',
        r'海量小说，在【德窝小说网】',
        r'【收藏德窝小说网，防止丢失阅读度】',
        r'记邮件找地址: dz@DEWOXS\.COM',

        # Patterns for zashuwu.com
        r'.*雜書屋.*',
        r'.*杂书屋.*',
        r'.*zashuwu\.com.*',
        r'.*ZASHUWU\.COM.*',
        r'.*雜書屋小說網.*',
        r'.*请记住.*',
        r'.*域名.*',
        r'.*章节内容加载中.*',
        r'.*若无法阅读关闭广告屏蔽即可.*',
        r'.*小说主人公是.*',
        r'.*更新于：.*',
        r'.*由.*所写.*',
        r'^--$',  # Lines with just dashes
        r'.*风流皇太子$',  # Title line
        r'.*】\+【.*',  # Lines with tags like 【架空】
        r'.*无系统.*',  # System-related lines
        r'.*开局大夏太子爷.*',  # Story introduction

        # More general patterns
        r'.*德窝小说网.*',
        r'.*DEWOXS\.COM.*',
        r'.*dewoxs\.com.*',
        r'.*收藏.*防止丢失.*',
        r'.*记住.*网址.*',
        r'.*請記住本站.*',
        r'.*本站網址.*',
        r'.*记住网址.*',
        r'.*dz@.*\.COM.*',
        r'.*請牢記.*',
        r'.*手机阅读.*',
        r'.*手機閱讀.*',

        # Common advertisement patterns
        r'.*广告.*',
        r'.*推荐.*',
        r'.*热门小说.*',
        r'.*最新章节.*',
        r'.*免费阅读.*',
        r'.*加入书签.*',
        r'.*收藏本站.*',
        r'.*手机访问.*',
        r'.*小说网.*',
        r'.*阅读网.*',
        r'.*小说阅读网.*',
        r'.*http.*\.com.*',
        r'.*https.*\.com.*',
        r'.*www\..*\.com.*'
    ]

    # Split text into lines
    lines = text.split('\n')

    # Filter out advertisement lines
    cleaned_lines = []
    for line in lines:
        # Skip empty lines or very short lines (likely not content)
        if not line.strip() or len(line.strip()) < 2:
            continue

        is_ad = False
        for pattern in ad_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                is_ad = True
                print(f"Removed ad line: {line[:50]}..." if len(line) > 50 else f"Removed ad line: {line}")
                break
        if not is_ad:
            cleaned_lines.append(line)

    # Join lines back into text
    cleaned_text = '\n'.join(cleaned_lines)
    return cleaned_text

def crawl_novel_content(url):
    """Crawl novel content from URL."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # Check if it's a zashuwu.com URL
        if 'zashuwu.com' in url:
            # Try to find the initTxt script that contains the content URL
            script_tags = soup.find_all('script')
            content_url = None

            for script in script_tags:
                if script.string and 'initTxt' in script.string:
                    # Extract the URL from the initTxt function call
                    import re
                    match = re.search(r'initTxt\("([^"]+)"', script.string)
                    if match:
                        content_url = match.group(1)
                        if not content_url.startswith('http'):
                            content_url = 'https:' + content_url
                        print(f"Found content URL: {content_url}")
                        break

            if content_url:
                try:
                    # Make a request to the content URL
                    content_response = requests.get(content_url, headers=headers, timeout=10)
                    content_response.raise_for_status()

                    # The content might be in JSON format or plain text
                    try:
                        import json

                        # Check if it's in the _txt_call format
                        if content_response.text.startswith('_txt_call('):
                            print("Content is encoded/encrypted and cannot be decoded without the website's decryption algorithm")
                            content = "This content is encoded/encrypted by the website and cannot be decoded. Please visit the original website to read the content."
                        else:
                            # Try to parse as JSON
                            try:
                                content_data = json.loads(content_response.text)
                                if isinstance(content_data, dict) and 'content' in content_data:
                                    content = content_data['content']
                                else:
                                    content = content_response.text
                            except json.JSONDecodeError:
                                content = content_response.text
                    except Exception as e:
                        print(f"Error parsing content: {e}")
                        content = content_response.text

                    print(f"Successfully loaded content from {content_url}")

                    # Save raw content for debugging
                    with open('raw_content.txt', 'w', encoding='utf-8') as f:
                        f.write(content_response.text)
                    print("Raw content saved to raw_content.txt")

                    # Clean content
                    cleaned_content = clean_content(content)
                    return cleaned_content
                except Exception as e:
                    print(f"Error loading content from {content_url}: {e}")
                    # Fall back to regular content extraction

        # Try various common content element selectors
        content_element = None
        selectors = [
            # Common selectors
            ('div', {'class': 'content'}),
            ('div', {'id': 'content'}),
            ('div', {'class': 'article-content'}),
            ('div', {'class': 'chapter-content'}),
            ('div', {'class': 'novel-content'}),
            ('div', {'class': 'text-content'}),
            ('article', {}),
            ('div', {'class': 'read-content'}),
            ('div', {'id': 'chapter-content'}),
            ('div', {'class': 'entry-content'}),

            # Selectors for zashuwu.com
            ('div', {'id': 'chaptercontent'}),
            ('div', {'class': 'readcontent'}),
            ('div', {'class': 'showtxt'}),
            ('div', {'class': 'read-content j_readContent'}),
            ('div', {'id': 'txtContent'}),
            ('div', {'id': 'BookText'}),
            ('div', {'id': 'acontent'})
        ]

        for tag, attrs in selectors:
            element = soup.find(tag, attrs)
            if element and len(element.get_text(strip=True)) > 100:  # Ensure it has substantial content
                content_element = element
                print(f"Found content using selector: {tag}, {attrs}")
                break

        # If still not found, try to find the largest text block
        if not content_element:
            text_blocks = []
            for div in soup.find_all('div'):
                text = div.get_text(strip=True)
                if len(text) > 200:  # Only consider substantial blocks
                    text_blocks.append((div, len(text)))

            if text_blocks:
                # Sort by text length (descending)
                text_blocks.sort(key=lambda x: x[1], reverse=True)
                content_element = text_blocks[0][0]
                print(f"Found content using largest text block method: {len(text_blocks[0][1])} characters")

        if content_element:
            # Extract text content
            content = content_element.get_text('\n', strip=True)

            # Save raw content for debugging
            with open('raw_content.txt', 'w', encoding='utf-8') as f:
                f.write(content)
            print("Raw content saved to raw_content.txt")

            # Clean content
            cleaned_content = clean_content(content)
            return cleaned_content
        else:
            print(f"Could not find content element for {url}")
            return None
    except Exception as e:
        print(f"Error crawling {url}: {e}")
        return None

def save_content(content, filename):
    """Save content to file."""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)

def parse_arguments():
    """Parse command line arguments."""
    import argparse

    parser = argparse.ArgumentParser(description='Crawl novel content from URLs in a CSV file.')
    parser.add_argument('--csv', type=str, default='m.csv',
                        help='Path to the CSV file containing URLs (default: m.csv)')
    parser.add_argument('--output', type=str, default='novel_content',
                        help='Directory to save the crawled content (default: novel_content)')
    parser.add_argument('--delay', type=float, default=1.0,
                        help='Delay between requests in seconds (default: 1.0)')
    parser.add_argument('--verbose', action='store_true',
                        help='Show verbose output')
    parser.add_argument('--start', type=int, default=0,
                        help='Start crawling from this index (default: 0)')
    parser.add_argument('--end', type=int, default=None,
                        help='End crawling at this index (default: None, crawl all)')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: only crawl the first URL')

    return parser.parse_args()

def main():
    # Parse command line arguments
    args = parse_arguments()

    # Create output directory if it doesn't exist
    output_dir = args.output
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")

    # Read URLs from CSV
    urls = read_urls_from_csv(args.csv)
    print(f"Found {len(urls)} URLs in {args.csv}")

    # Apply start/end limits
    if args.test:
        urls = urls[:1]
        print("Test mode: only crawling the first URL")
    else:
        end = args.end if args.end is not None else len(urls)
        urls = urls[args.start:end]
        print(f"Crawling URLs from index {args.start} to {end-1}")

    # Crawl content for each URL
    for i, url in enumerate(urls):
        current_index = i + args.start
        print(f"Crawling {current_index+1}/{len(urls) + args.start}: {url}")

        # Extract chapter number from URL
        chapter_match = re.search(r'/(\d+)\.html', url)
        chapter_num = chapter_match.group(1) if chapter_match else str(current_index+1)

        # Crawl content
        content = crawl_novel_content(url)

        if content:
            # Save content to file
            filename = os.path.join(output_dir, f'chapter_{chapter_num}.txt')
            save_content(content, filename)
            print(f"Saved to {filename}")

            # Print sample of content if verbose
            if args.verbose:
                sample = content[:200] + '...' if len(content) > 200 else content
                print(f"Sample content: {sample}")
        else:
            print(f"Failed to crawl content from {url}")

        # Add delay to avoid being blocked
        if i < len(urls) - 1:  # No need to delay after the last URL
            if args.verbose:
                print(f"Waiting {args.delay} seconds before next request...")
            time.sleep(args.delay)

    print("Crawling completed!")

if __name__ == "__main__":
    main()
