#!/bin/bash

echo "=== 檢查 Firefox 安裝 ==="
# 檢查 Firefox 是否安裝
if command -v firefox &> /dev/null; then
    echo "✓ Firefox 已安裝"
    firefox --version
else
    echo "✗ Firefox 未安裝"
    echo "請安裝 Firefox："
    echo "  Ubuntu/Debian: sudo apt-get install firefox"
    echo "  CentOS/RHEL: sudo yum install firefox"
    echo "  Arch: sudo pacman -S firefox"
fi

echo -e "\n=== 檢查 geckodriver ==="
# 檢查 geckodriver 是否在 PATH 中
if command -v geckodriver &> /dev/null; then
    echo "✓ geckodriver 已安裝"
    geckodriver --version
else
    echo "✗ geckodriver 未找到"
    echo "請下載並安裝 geckodriver："
    echo "1. 從 https://github.com/mozilla/geckodriver/releases 下載最新版本"
    echo "2. 解壓並移動到 PATH 中："
    echo "   sudo tar -xvzf geckodriver-*.tar.gz"
    echo "   sudo mv geckodriver /usr/local/bin/"
    echo "   sudo chmod +x /usr/local/bin/geckodriver"
fi

echo -e "\n=== 檢查 Python selenium 和 webdriver-manager ==="
python -c "
try:
    import selenium
    print('✓ selenium 已安裝:', selenium.__version__)
except ImportError:
    print('✗ selenium 未安裝')
    print('  請安裝: uv pip install selenium')

try:
    import webdriver_manager
    print('✓ webdriver-manager 已安裝:', webdriver_manager.__version__)
except ImportError:
    print('✗ webdriver-manager 未安裝')
    print('  請安裝: uv pip install webdriver-manager')
"

echo -e "\n=== 安裝 geckodriver 的替代方法 ==="
echo "如果手動安裝有問題，可以使用 Python 自動管理："
cat << 'EOF'
# 在 Python 程式中使用 webdriver-manager 自動下載：
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager

# 自動下載並使用 geckodriver
service = Service(GeckoDriverManager().install())
driver = webdriver.Firefox(service=service)
EOF
