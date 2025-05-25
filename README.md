# Novel Content Crawler

A Python script to crawl novel content from URLs in a CSV file and clean advertisement lines.

## Features

- Reads URLs from a CSV file
- Crawls novel content from each URL
- Cleans advertisement lines from the content
- Saves the cleaned content to text files
- Supports various command-line options for flexibility

## Requirements

- Python 3.6+
- Required packages: `requests`, `beautifulsoup4`

You can install the required packages using pip:

```bash
pip install requests beautifulsoup4
```

## Usage

Basic usage:

```bash
python3 novel_crawler.py
```

This will read URLs from `m.csv`, crawl the content, and save it to the `novel_content` directory.

### Command-line Options

- `--csv`: Path to the CSV file containing URLs (default: `m.csv`)
- `--output`: Directory to save the crawled content (default: `novel_content`)
- `--delay`: Delay between requests in seconds (default: 1.0)
- `--verbose`: Show verbose output
- `--start`: Start crawling from this index (default: 0)
- `--end`: End crawling at this index (default: None, crawl all)
- `--test`: Test mode: only crawl the first URL

### Examples

Crawl with m1.csv file:

```bash
python3 novel_crawler.py --csv m1.csv --output zashuwu_novel
```

Crawl with a custom CSV file and output directory:

```bash
python3 novel_crawler.py --csv my_urls.csv --output my_novel
```

Crawl with a longer delay between requests:

```bash
python3 novel_crawler.py --delay 2.5
```

Crawl only a subset of URLs:

```bash
python3 novel_crawler.py --start 10 --end 20
```

Test the script with just the first URL:

```bash
python3 novel_crawler.py --csv m1.csv --test --verbose
```

## CSV File Format

The script supports two CSV file formats:

### Format 1 (URLs in first column)

```
"item-text href","item-text"
"https://example.com/chapter1.html","Chapter 1"
"https://example.com/chapter2.html","Chapter 2"
...
```

### Format 2 (URLs in second column, as in m1.csv)

```
"tablescraper-selected-row","tablescraper-selected-row href"
"分章閱讀 1","https://m.zashuwu.com/wen/2vFm/1.html"
"分章閱讀 2","https://m.zashuwu.com/wen/2vFm/2.html"
...
```

## Limitations

### Content Protection

Some websites (like zashuwu.com) use encoding or encryption to protect their content from being scraped. The script will detect this and inform you when it encounters such content. In these cases, you'll need to visit the original website to read the content.

For example, if you see a message like:
```
Content is encoded/encrypted and cannot be decoded without the website's decryption algorithm
```

This means the website is using a custom encoding or encryption scheme that the script cannot decode.

## Advertisement Cleaning

The script removes advertisement lines containing patterns like:

### For dewoxs.com:
- "德窝小说网"
- "DEWOXS.COM"
- "记住网址"
- "收藏本站"

### For zashuwu.com:
- "雜書屋"
- "zashuwu.com"
- "雜書屋小說網"

### General patterns:
- Common advertisement text in both simplified and traditional Chinese
- URLs and website references
- "加入书签" (Add to bookmarks)
- "手机阅读" / "手機閱讀" (Mobile reading)
- And many other common advertisement patterns

## Output

The script creates a text file for each URL in the output directory. The file name is based on the chapter number extracted from the URL.

### Examples:

- For the URL `https://m.dewoxs.com/8mkN/123.html`, the output file will be `chapter_123.txt`.
- For the URL `https://m.zashuwu.com/wen/2vFm/45.html`, the output file will be `chapter_45.txt`.
