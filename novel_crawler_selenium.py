import csv
import time
import os
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import argparse


def setup_driver(headless=False):
    """設置Chrome驅動程序"""
    chrome_options = Options()

    if headless:
        chrome_options.add_argument('--headless')

    # 其他優化選項
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    # 設置User-Agent
    chrome_options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')

    driver = webdriver.Chrome(options=chrome_options)
    return driver


def read_urls_from_csv(csv_file):
    """從CSV文件讀取URL"""
    urls = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader)  # 跳過表頭
        for row in reader:
            # 檢查URL是否在第一列（舊格式）
            if len(row) > 0 and row[0].startswith(('https://', '"https://')):
                url = row[0].strip('"')
                urls.append(url)
            # 檢查URL是否在第二列（m1.csv格式）
            elif len(row) > 1 and row[1].startswith(('https://', '"https://')):
                url = row[1].strip('"')
                urls.append(url)
    return urls


def clean_content(text):
    """清理內容中的廣告"""
    # 定義要移除的模式
    ad_patterns = [
        # zashuwu.com的廣告模式
        r'.*雜書屋.*',
        r'.*杂书屋.*',
        r'.*zashuwu\.com.*',
        r'.*ZASHUWU\.COM.*',
        r'.*記郵件找地址.*',
        r'.*记邮件找地址.*',
        r'.*dz@.*',
        r'.*請記住.*',
        r'.*请记住.*',
        r'.*域名.*',
        r'.*章節內容加載中.*',
        r'.*章节内容加载中.*',
        r'.*若無法閱讀關閉廣告屏蔽即可.*',
        r'.*若无法阅读关闭广告屏蔽即可.*',
        r'.*手機閱讀.*',
        r'.*手机阅读.*',
        r'.*加入書簽.*',
        r'.*加入书签.*',
        r'.*收藏本站.*',
        r'.*最新章節.*',
        r'.*最新章节.*',
        r'.*熱門小說.*',
        r'.*热门小说.*',
        r'.*免費閱讀.*',
        r'.*免费阅读.*',

        # 通用廣告模式
        r'.*http[s]?://.*\.com.*',
        r'.*www\..*\.com.*',
        r'^--$',
        r'^\s*$'  # 空行
    ]

    # 分割文本為行
    lines = text.split('\n')

    # 過濾廣告行
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

    # 重新組合文本
    cleaned_text = '\n'.join(cleaned_lines)
    return cleaned_text


def crawl_novel_content_selenium(driver, url, wait_time=20):
    """使用Selenium爬取小說內容"""
    try:
        # 訪問URL
        driver.get(url)

        # 等待頁面基本加載
        wait = WebDriverWait(driver, wait_time)

        # 增加等待時間，讓JavaScript有充足時間解密內容
        print("等待JavaScript解密內容...")
        time.sleep(8)  # 增加到8秒

        # 嘗試滾動頁面觸發懶加載
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(2)

        # 首先嘗試直接獲取txtContent div
        try:
            # 等待txtContent元素出現並包含實際內容
            txt_content = wait.until(
                EC.presence_of_element_located((By.ID, "txtContent"))
            )
            # 再等待一下確保內容完全加載
            time.sleep(3)

            # 獲取內容
            content_text = txt_content.text.strip()

            # 檢查是否是真實的小說內容（應該包含"葉洵"或"第1章"等關鍵詞）
            if content_text and len(content_text) > 100 and not content_text.startswith('[都市小说]'):
                print("找到txtContent中的內容")
                return clean_content(content_text)
        except:
            pass

        # 嘗試多種選擇器來找到內容
        content_selectors = [
            # zashuwu.com的特定選擇器
            (By.ID, 'txtContent'),
            (By.ID, 'content'),
            (By.ID, 'chaptercontent'),
            (By.ID, 'BookText'),
            (By.ID, 'acontent'),
            (By.CLASS_NAME, 'readcontent'),
            (By.CLASS_NAME, 'showtxt'),
            (By.CLASS_NAME, 'read-content'),
            (By.CLASS_NAME, 'chapter-content'),
            (By.CLASS_NAME, 'novel-content'),
            (By.CLASS_NAME, 'content'),
            # 更精確的XPath選擇器
            (By.XPATH, "//div[@id='txtContent']"),
            (By.XPATH, "//div[@id='content' and not(contains(@class, 'recommend'))]"),
            (By.XPATH, "//div[contains(@class, 'read') and contains(@class, 'content')]"),
            (By.XPATH, "//div[@class='showtxt' or @class='readcontent']")
        ]

        content_element = None
        content_text = ""

        # 等待一下讓JavaScript完全執行
        time.sleep(3)

        # 嘗試每個選擇器
        for selector_type, selector_value in content_selectors:
            try:
                elements = driver.find_elements(selector_type, selector_value)
                for element in elements:
                    text = element.text.strip()
                    # 檢查是否有實質內容（至少100個字符）
                    if len(text) > 100:
                        # 排除推薦列表內容
                        if not any(
                                exclude in text for exclude in ['[都市小说]', '[言情小说]', '[武侠小说]', '最新章节']):
                            # 檢查是否包含小說內容的特徵
                            if any(keyword in text for keyword in
                                   ['第', '章', '葉洵', '秦王', '殿下', '陛下', '貞武', '夏國']) or len(text) > 1000:
                                content_element = element
                                content_text = text
                                print(f"找到內容使用選擇器: {selector_type}, {selector_value}")
                                break

                if content_element:
                    break

            except (TimeoutException, NoSuchElementException):
                continue

        # 如果還是沒找到，嘗試執行JavaScript來獲取內容
        if not content_text:
            try:
                print("嘗試使用JavaScript獲取動態內容...")

                # 首先檢查是否有_txt_call函數
                has_txt_call = driver.execute_script("return typeof _txt_call === 'function';")
                print(f"檢測到_txt_call函數: {has_txt_call}")

                # 等待更長時間讓解密完成
                time.sleep(5)

                # 嘗試多種JavaScript方法獲取內容
                content_text = driver.execute_script("""
                    // 方法1：直接獲取txtContent
                    var txtContent = document.getElementById('txtContent');
                    if (txtContent && txtContent.innerText && txtContent.innerText.length > 100) {
                        console.log('Found content in txtContent');
                        return txtContent.innerText;
                    }

                    // 方法2：查找包含小說內容的div
                    var divs = document.getElementsByTagName('div');
                    for (var i = 0; i < divs.length; i++) {
                        var text = divs[i].innerText || divs[i].textContent || '';
                        // 檢查是否包含小說特徵詞
                        if (text.length > 500 && 
                            (text.includes('葉洵') || text.includes('第1章') || 
                             text.includes('貞武') || text.includes('秦王') ||
                             text.includes('風流皇太子'))) {
                            console.log('Found content in div');
                            return text;
                        }
                    }

                    // 方法3：獲取最大的文本塊（排除推薦內容）
                    var maxLength = 0;
                    var maxDiv = null;
                    for (var i = 0; i < divs.length; i++) {
                        var text = divs[i].innerText || divs[i].textContent || '';
                        if (text.length > maxLength && 
                            !text.includes('[都市小说]') && 
                            !text.includes('[言情小说]') &&
                            !text.includes('最新章节')) {
                            maxLength = text.length;
                            maxDiv = divs[i];
                        }
                    }

                    if (maxDiv && maxLength > 300) {
                        console.log('Found max content block');
                        return maxDiv.innerText || maxDiv.textContent;
                    }

                    // 方法4：等待一下再試
                    setTimeout(function() {
                        var content = document.getElementById('txtContent');
                        if (content) {
                            console.log('Found content after timeout');
                        }
                    }, 3000);

                    return '';
                """)

                if content_text:
                    print("通過JavaScript獲取到內容")
                else:
                    # 再等待一下，讓setTimeout執行
                    time.sleep(4)
                    # 再次嘗試獲取
                    content_text = driver.execute_script("""
                        var txtContent = document.getElementById('txtContent');
                        if (txtContent) {
                            return txtContent.innerText || txtContent.textContent || '';
                        }
                        return '';
                    """)

                    if content_text:
                        print("通過延遲JavaScript獲取到內容")

            except Exception as e:
                print(f"JavaScript執行失敗: {e}")

        if content_text:
            # 檢查內容是否仍然是加密的
            if "This content is encoded/encrypted" in content_text:
                print("內容仍然是加密的，嘗試其他方法...")

                # 嘗試重新加載頁面
                driver.refresh()
                time.sleep(8)

                # 再次嘗試獲取
                content_text = driver.execute_script("""
                    var txtContent = document.getElementById('txtContent');
                    if (txtContent) {
                        return txtContent.innerText || txtContent.textContent || '';
                    }
                    return '';
                """)

            # 清理內容
            if content_text and len(content_text) > 100:
                cleaned_content = clean_content(content_text)
                return cleaned_content

        # 如果所有方法都失敗了，保存調試信息
        print(f"未能找到內容元素: {url}")

        # 保存頁面截圖
        screenshot_path = f'debug_screenshot_{int(time.time())}.png'
        driver.save_screenshot(screenshot_path)
        print(f"頁面截圖已保存到 {screenshot_path}")

        # 保存頁面源碼
        with open(f'debug_page_source_{int(time.time())}.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("頁面源碼已保存")

        # 嘗試列出所有可能的內容元素
        print("\n調試信息 - 頁面上的所有div元素:")
        debug_info = driver.execute_script("""
            var divs = document.getElementsByTagName('div');
            var info = [];
            for (var i = 0; i < divs.length; i++) {
                var div = divs[i];
                var text = (div.innerText || div.textContent || '').trim();
                if (text.length > 50 && text.length < 300) {
                    info.push({
                        id: div.id || 'no-id',
                        className: div.className || 'no-class',
                        textLength: text.length,
                        textPreview: text.substring(0, 100)
                    });
                }
            }
            return info;
        """)

        for item in debug_info[:10]:  # 只顯示前10個
            print(f"  ID: {item['id']}, Class: {item['className']}, Length: {item['textLength']}")
            print(f"  Preview: {item['textPreview']}...")

        return None

    except Exception as e:
        print(f"爬取 {url} 時出錯: {e}")
        return None


def save_content(content, filename):
    """保存內容到文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(content)


def parse_arguments():
    """解析命令行參數"""
    parser = argparse.ArgumentParser(description='使用Selenium爬取小說內容')
    parser.add_argument('--csv', type=str, default='m1.csv',
                        help='包含URL的CSV文件路徑 (默認: m1.csv)')
    parser.add_argument('--output', type=str, default='wen_novel',
                        help='保存內容的目錄 (默認: wen_novel)')
    parser.add_argument('--delay', type=float, default=2.5,
                        help='請求之間的延遲（秒） (默認: 2.5)')
    parser.add_argument('--headless', action='store_true',
                        help='使用無頭模式（不顯示瀏覽器）')
    parser.add_argument('--start', type=int, default=0,
                        help='從這個索引開始爬取 (默認: 0)')
    parser.add_argument('--end', type=int, default=None,
                        help='在這個索引結束爬取 (默認: None，爬取所有)')
    parser.add_argument('--test', action='store_true',
                        help='測試模式：只爬取第一個URL')
    parser.add_argument('--verbose', action='store_true',
                        help='顯示詳細輸出')

    return parser.parse_args()


def main():
    # 解析命令行參數
    args = parse_arguments()

    # 創建輸出目錄
    output_dir = args.output
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"創建輸出目錄: {output_dir}")

    # 讀取URL
    urls = read_urls_from_csv(args.csv)
    print(f"從 {args.csv} 找到 {len(urls)} 個URL")

    # 應用開始/結束限制
    if args.test:
        urls = urls[:1]
        print("測試模式：只爬取第一個URL")
    else:
        end = args.end if args.end is not None else len(urls)
        urls = urls[args.start:end]
        print(f"爬取URL從索引 {args.start} 到 {end - 1}")

    # 設置驅動程序
    print("初始化瀏覽器驅動...")
    driver = setup_driver(headless=args.headless)

    try:
        # 爬取每個URL的內容
        for i, url in enumerate(urls):
            current_index = i + args.start
            print(f"\n爬取 {current_index + 1}/{len(urls) + args.start}: {url}")

            # 從URL提取章節號
            chapter_match = re.search(r'/(\d+)\.html', url)
            chapter_num = chapter_match.group(1) if chapter_match else str(current_index + 1)

            # 爬取內容
            content = crawl_novel_content_selenium(driver, url)

            if content:
                # 保存內容到文件
                filename = os.path.join(output_dir, f'chapter_{chapter_num}.txt')
                save_content(content, filename)
                print(f"保存到 {filename}")

                # 如果verbose模式，打印內容樣本
                if args.verbose:
                    sample = content[:200] + '...' if len(content) > 200 else content
                    print(f"內容樣本: {sample}")
            else:
                print(f"無法從 {url} 爬取內容")
                # 可以選擇保存一個錯誤日誌
                error_filename = os.path.join(output_dir, f'error_chapter_{chapter_num}.txt')
                with open(error_filename, 'w', encoding='utf-8') as f:
                    f.write(f"無法爬取此URL的內容: {url}\n")
                    f.write("請手動訪問網站查看內容。")

            # 添加延遲
            if i < len(urls) - 1:
                if args.verbose:
                    print(f"等待 {args.delay} 秒...")
                time.sleep(args.delay)

    finally:
        # 關閉瀏覽器
        driver.quit()
        print("\n爬取完成！")


if __name__ == "__main__":
    main()