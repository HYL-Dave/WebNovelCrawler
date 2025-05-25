"""
使用Playwright的小說爬蟲
安裝: pip install playwright
初始化: playwright install chromium
"""

import asyncio
from playwright.async_api import async_playwright
try:
    from playwright_stealth import stealth_sync
except ImportError:
    stealth_sync = None
import csv
import os
import re
import time
import argparse


async def read_urls_from_csv(csv_file):
    """從CSV文件讀取URL"""
    urls = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # 跳過表頭
        for row in reader:
            if len(row) > 1 and row[1].startswith(('https://', '"https://')):
                url = row[1].strip('"')
                urls.append(url)
    return urls


def clean_content(text):
    """清理內容中的廣告"""
    ad_patterns = [
        r'.*雜書屋.*',
        r'.*杂书屋.*',
        r'.*zashuwu\.com.*',
        r'.*ZASHUWU\.COM.*',
        r'.*記郵件找地址.*',
        r'.*记邮件找地址.*',
        r'.*dz@.*',
        r'.*請記住.*',
        r'.*请记住.*',
        r'.*手機閱讀.*',
        r'.*手机阅读.*',
        r'.*加入書簽.*',
        r'.*加入书签.*',
        r'.*最新章節.*',
        r'.*最新章节.*',
        r'.*http[s]?://.*\.com.*',
        r'^--$',
        r'^\s*$'
    ]

    lines = text.split('\n')
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        is_ad = False
        for pattern in ad_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                is_ad = True
                break

        if not is_ad:
            cleaned_lines.append(line)

    return '\n'.join(cleaned_lines)


async def crawl_novel_content(page, url):
    """使用Playwright爬取小說內容"""
    try:
        print(f"訪問: {url}")

        # 設置額外的請求頭
        await page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'zh-TW,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        })

        # 訪問頁面
        await page.goto(url, wait_until='networkidle', timeout=30000)

        # 等待一段時間讓JavaScript執行
        print("等待JavaScript解密內容...")
        await page.wait_for_timeout(10000)  # 等待10秒

        # 嘗試等待txtContent元素出現並有內容
        try:
            await page.wait_for_function("""
                () => {
                    const el = document.getElementById('txtContent');
                    return el && el.innerText && el.innerText.length > 500;
                }
            """, timeout=15000)
            print("檢測到txtContent已加載")
        except:
            print("txtContent加載超時，繼續嘗試其他方法")

        # 滾動頁面觸發懶加載
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
        await page.wait_for_timeout(2000)

        # 嘗試獲取內容
        content = await page.evaluate("""
            () => {
                // 優先嘗試txtContent
                const txtContent = document.getElementById('txtContent');
                if (txtContent && txtContent.innerText && txtContent.innerText.length > 100) {
                    console.log('Found novel content in txtContent');
                    return txtContent.innerText;
                }

                // 嘗試其他選擇器
                const selectors = [
                    '#content', '#chaptercontent', '#chapter-content', '#BookText',
                    '.readcontent', '.read-content', '.novel-content'
                ];

                for (const selector of selectors) {
                    const el = document.querySelector(selector);
                    if (el && el.innerText && el.innerText.length > 100) {
                        const text = el.innerText;
                        if (!text.includes('[都市小说]') && !text.includes('最新章节')) {
                            console.log(`Found content in ${selector}`);
                            return text;
                        }
                    }
                }

                // 查找最大的文本塊
                const divs = document.getElementsByTagName('div');
                let maxLength = 0;
                let maxText = '';

                for (const div of divs) {
                    const text = div.innerText || '';
                    if (text.length > maxLength && 
                        !text.includes('[都市小说]') && 
                        !text.includes('最新章节') &&
                        text.length > 500) {
                        maxLength = text.length;
                        maxText = text;
                    }
                }

                if (maxLength > 500) {
                    console.log('Using largest text block');
                    return maxText;
                }

                return '';
            }
        """)

        if content:
            print(f"成功獲取內容，長度: {len(content)}")
            return clean_content(content)

        # 如果還是沒有內容，嘗試等待更長時間
        print("第一次嘗試失敗，等待更長時間...")
        await page.wait_for_timeout(5000)

        # 再次嘗試
        content = await page.evaluate("""
            () => {
                const txtContent = document.getElementById('txtContent');
                if (txtContent) {
                    return txtContent.innerText || txtContent.textContent || '';
                }
                return '';
            }
        """)

        if content and len(content) > 100:
            print(f"第二次嘗試成功，長度: {len(content)}")
            return clean_content(content)

        # 調試信息
        print("無法獲取內容，保存調試信息...")
        await page.screenshot(path=f'debug_playwright_{int(time.time())}.png')

        # 列出頁面上的元素信息
        debug_info = await page.evaluate("""
            () => {
                const info = [];
                const divs = document.getElementsByTagName('div');
                for (const div of divs) {
                    if (div.id || div.className) {
                        const text = (div.innerText || '').trim();
                        if (text.length > 50 && text.length < 300) {
                            info.push({
                                id: div.id,
                                class: div.className,
                                textLength: text.length,
                                preview: text.substring(0, 80)
                            });
                        }
                    }
                }
                return info.slice(0, 10);
            }
        """)

        print("頁面元素信息:")
        for item in debug_info:
            print(f"  {item}")

        return None

    except Exception as e:
        print(f"爬取失敗: {e}")
        return None


async def main():
    parser = argparse.ArgumentParser(description='使用Playwright爬取小說內容')
    parser.add_argument('--csv', type=str, default='m1.csv', help='CSV文件路徑')
    parser.add_argument('--output', type=str, default='wen_novel', help='輸出目錄')
    parser.add_argument('--delay', type=float, default=3.0, help='請求間延遲')
    parser.add_argument('--test', action='store_true', help='測試模式')
    parser.add_argument('--headless', action='store_true', help='無頭模式')
    parser.add_argument('--start', type=int, default=0, help='開始索引')
    parser.add_argument('--end', type=int, default=None, help='結束索引')

    args = parser.parse_args()

    # 創建輸出目錄
    if not os.path.exists(args.output):
        os.makedirs(args.output)
        print(f"創建輸出目錄: {args.output}")

    # 讀取URL
    urls = await read_urls_from_csv(args.csv)
    print(f"找到 {len(urls)} 個URL")

    # 應用範圍限制
    if args.test:
        urls = urls[:1]
        print("測試模式：只爬取第一個URL")
    else:
        end = args.end if args.end is not None else len(urls)
        urls = urls[args.start:end]

    async with async_playwright() as p:
        # 啟動瀏覽器
        browser = await p.chromium.launch(
            headless=args.headless,
            args=['--disable-blink-features=AutomationControlled']
        )

        # 創建上下文
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        # 創建頁面
        page = await context.new_page()
        if stealth_sync:
            stealth_sync(page)
        else:
            print('playwright-stealth plugin not installed, skipping stealth injection')

        # 添加控制台日誌監聽
        page.on('console', lambda msg: print(f'[Console] {msg.text}'))

        # 爬取每個URL
        for i, url in enumerate(urls):
            current_index = i + args.start
            print(f"\n爬取 {current_index + 1}/{len(urls) + args.start}: {url}")

            # 提取章節號
            chapter_match = re.search(r'/(\d+)\.html', url)
            chapter_num = chapter_match.group(1) if chapter_match else str(current_index + 1)

            # 爬取內容
            content = await crawl_novel_content(page, url)

            if content:
                # 保存內容
                filename = os.path.join(args.output, f'chapter_{chapter_num}.txt')
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"保存到 {filename}")

                # 顯示預覽
                preview = content[:200] + '...' if len(content) > 200 else content
                print(f"預覽: {preview}")
            else:
                print(f"無法獲取內容")
                # 保存錯誤信息
                error_file = os.path.join(args.output, f'error_chapter_{chapter_num}.txt')
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(f"無法爬取內容: {url}\n")

            # 延遲
            if i < len(urls) - 1:
                print(f"等待 {args.delay} 秒...")
                await asyncio.sleep(args.delay)

        await browser.close()
        print("\n爬取完成！")


if __name__ == "__main__":
    asyncio.run(main())