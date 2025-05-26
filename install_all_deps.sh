#!/bin/bash
# 一鍵安裝所有爬蟲依賴

echo "==================================="
echo "小說爬蟲依賴安裝腳本"
echo "==================================="

# 檢查是否使用 uv
if command -v uv &> /dev/null; then
    PIP_CMD="uv pip"
    echo "使用 uv pip 安裝"
else
    PIP_CMD="pip"
    echo "使用 pip 安裝"
fi

# 1. 安裝 Firefox（如果需要）
echo -e "\n[1/4] 檢查 Firefox..."
if ! command -v firefox &> /dev/null; then
    echo "Firefox 未安裝，嘗試安裝..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y firefox
        elif command -v yum &> /dev/null; then
            sudo yum install -y firefox
        else
            echo "請手動安裝 Firefox"
        fi
    else
        echo "請手動安裝 Firefox"
    fi
else
    echo "✓ Firefox 已安裝"
fi

# 2. 安裝 Python 依賴
echo -e "\n[2/4] 安裝 Python 依賴..."

# 基礎依賴
echo "安裝基礎依賴..."
$PIP_CMD install -U \
    selenium \
    webdriver-manager \
    requests \
    beautifulsoup4 \
    lxml \
    pandas

# Playwright 依賴
echo -e "\n安裝 Playwright..."
$PIP_CMD install -U \
    playwright \
    playwright-stealth

# 安裝 Playwright 瀏覽器
echo "安裝 Playwright 瀏覽器..."
playwright install chromium firefox

# OCR 依賴
echo -e "\n[3/4] 安裝 OCR 依賴..."
echo "注意：這可能需要較長時間..."

# 檢查是否有 CUDA
if command -v nvidia-smi &> /dev/null; then
    echo "檢測到 NVIDIA GPU，安裝 CUDA 版本..."
    # 訪問 https://pytorch.org/ 獲取正確的安裝命令
    $PIP_CMD install torch torchvision --index-url https://download.pytorch.org/whl/cu121
else
    echo "未檢測到 GPU，安裝 CPU 版本..."
    $PIP_CMD install torch torchvision --index-url https://download.pytorch.org/whl/cpu
fi

# 其他 OCR 依賴
$PIP_CMD install -U \
    easyocr \
    opencv-python \
    Pillow \
    scikit-image \
    scipy \
    numpy

# 3. 下載進階解碼器
echo -e "\n[4/4] 設置進階解碼器..."
if [ ! -f "advanced_decoder.py" ]; then
    echo "請將 advanced_decoder.py 複製到當前目錄"
else
    echo "✓ advanced_decoder.py 已存在"
fi

# 4. 驗證安裝
echo -e "\n==================================="
echo "驗證安裝..."
echo "==================================="

python3 << EOF
import sys

def check_module(name, display_name=None):
    if display_name is None:
        display_name = name
    try:
        __import__(name)
        print(f"✓ {display_name}")
        return True
    except ImportError:
        print(f"✗ {display_name}")
        return False

print("Python 模組:")
modules = [
    ('selenium', 'Selenium'),
    ('webdriver_manager', 'Webdriver Manager'),
    ('playwright', 'Playwright'),
    ('easyocr', 'EasyOCR'),
    ('cv2', 'OpenCV'),
    ('PIL', 'Pillow'),
    ('torch', 'PyTorch'),
    ('bs4', 'BeautifulSoup4'),
]

all_ok = True
for module, name in modules:
    if not check_module(module, name):
        all_ok = False

if all_ok:
    print("\n✓ 所有 Python 依賴已安裝！")
else:
    print("\n✗ 部分依賴未安裝成功")
EOF

# 檢查系統工具
echo -e "\n系統工具:"
tools=("firefox" "geckodriver")
for tool in "${tools[@]}"; do
    if command -v $tool &> /dev/null; then
        echo "✓ $tool"
    else
        echo "✗ $tool"
    fi
done

echo -e "\n==================================="
echo "安裝完成！"
echo "==================================="
echo "使用方法:"
echo "1. 基本爬取: python fixed_comprehensive_crawler.py --csv urls.csv"
echo "2. 啟用 OCR: python fixed_comprehensive_crawler.py --csv urls.csv --use-ocr"
echo "3. 測試模式: python fixed_comprehensive_crawler.py --csv urls.csv --test"
echo ""
echo "如果 Firefox 仍有問題，請嘗試："
echo "1. 手動下載 geckodriver: https://github.com/mozilla/geckodriver/releases"
echo "2. 或使用 Playwright: python novel_crawler_playwright.py"
