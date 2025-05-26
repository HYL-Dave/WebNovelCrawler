#!/usr/bin/env python3
"""檢查 OCR 相關依賴的安裝情況"""

import sys
import subprocess

def check_dependency(module_name, import_name=None):
    """檢查單個依賴"""
    if import_name is None:
        import_name = module_name
    
    try:
        __import__(import_name)
        module = sys.modules[import_name]
        version = getattr(module, '__version__', 'unknown')
        print(f"✓ {module_name} 已安裝 (版本: {version})")
        return True
    except ImportError:
        print(f"✗ {module_name} 未安裝")
        return False

def check_torch_cuda():
    """檢查 PyTorch CUDA 支援"""
    try:
        import torch
        if torch.cuda.is_available():
            print(f"  - CUDA 可用: {torch.cuda.get_device_name(0)}")
            print(f"  - CUDA 版本: {torch.version.cuda}")
        else:
            print("  - CUDA 不可用（將使用 CPU）")
    except:
        pass

print("=== 檢查 EasyOCR 相關依賴 ===\n")

# 核心依賴
dependencies = [
    ('torch', 'torch'),
    ('torchvision', 'torchvision'),
    ('opencv-python', 'cv2'),
    ('Pillow', 'PIL'),
    ('scikit-image', 'skimage'),
    ('scipy', 'scipy'),
    ('numpy', 'numpy'),
    ('easyocr', 'easyocr')
]

all_installed = True
for pip_name, import_name in dependencies:
    if not check_dependency(pip_name, import_name):
        all_installed = False

# 檢查 PyTorch CUDA
if 'torch' in sys.modules:
    check_torch_cuda()

print("\n=== 安裝建議 ===")
if not all_installed:
    print("\n使用以下命令安裝所有 OCR 依賴：")
    print("uv pip install easyocr torch torchvision opencv-python Pillow scikit-image scipy numpy")
    print("\n注意：如果有 NVIDIA GPU，建議安裝 CUDA 版本的 PyTorch：")
    print("訪問 https://pytorch.org/ 獲取適合您系統的安裝命令")
else:
    print("\n所有 OCR 依賴都已安裝！")

# 測試 EasyOCR
print("\n=== 測試 EasyOCR 初始化 ===")
try:
    import easyocr
    print("初始化中文 OCR 讀取器...")
    reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)  # 使用 CPU 測試
    print("✓ EasyOCR 初始化成功！")
    
    # 測試簡單圖片
    import numpy as np
    from PIL import Image
    
    # 創建一個簡單的測試圖片
    img = Image.new('RGB', (200, 50), color='white')
    img_array = np.array(img)
    
    result = reader.readtext(img_array)
    print("✓ OCR 功能測試通過！")
    
except Exception as e:
    print(f"✗ EasyOCR 測試失敗: {e}")
    print("\n可能的原因：")
    print("1. 首次運行需要下載模型文件（約 1GB）")
    print("2. 網絡連接問題")
    print("3. 依賴版本不兼容")
