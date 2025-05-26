"""
OCR圖片文字識別工具
用於提取網頁中以圖片形式顯示的文字
"""

import os
import re
import time
import requests
from PIL import Image
from io import BytesIO
import base64
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    pytesseract = None
    TESSERACT_AVAILABLE = False

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    easyocr = None
    EASYOCR_AVAILABLE = False


class OCRImageExtractor:
    def __init__(self, use_easyocr=True):
        """
        初始化OCR工具
        use_easyocr: 優先使用EasyOCR（精度更高），否則使用Tesseract
        """
        self.use_easyocr = use_easyocr and EASYOCR_AVAILABLE
        self.ocr_reader = None
        
        if self.use_easyocr:
            try:
                print("初始化EasyOCR...")
                self.ocr_reader = easyocr.Reader(['ch_tra', 'ch_sim', 'en'])  # 繁體中文、簡體中文、英文
                print("✓ EasyOCR初始化成功")
            except Exception as e:
                print(f"✗ EasyOCR初始化失敗: {e}")
                self.use_easyocr = False
                
        if not self.use_easyocr and not TESSERACT_AVAILABLE:
            print("警告: 沒有可用的OCR引擎，請安裝 pytesseract 或 easyocr")

    def extract_images_from_page(self, driver):
        """從當前頁面提取所有圖片"""
        images_info = []
        
        try:
            # 獲取所有img標籤
            img_elements = driver.find_elements("tag name", "img")
            print(f"找到 {len(img_elements)} 個圖片元素")
            
            for i, img in enumerate(img_elements):
                try:
                    # 獲取圖片信息
                    src = img.get_attribute('src')
                    alt = img.get_attribute('alt') or ''
                    width = img.get_attribute('width') or img.size['width']
                    height = img.get_attribute('height') or img.size['height']
                    
                    # 過濾掉明顯不是文字的圖片
                    if self.is_likely_text_image(src, alt, width, height):
                        images_info.append({
                            'index': i,
                            'src': src,
                            'alt': alt,
                            'width': width,
                            'height': height,
                            'element': img
                        })
                        
                except Exception as e:
                    print(f"獲取圖片 {i} 信息失敗: {e}")
                    
            print(f"過濾後找到 {len(images_info)} 個可能包含文字的圖片")
            return images_info
            
        except Exception as e:
            print(f"提取圖片失敗: {e}")
            return []

    def is_likely_text_image(self, src, alt, width, height):
        """判斷圖片是否可能包含文字"""
        if not src:
            return False
            
        # 過濾廣告、LOGO等
        if any(keyword in src.lower() for keyword in ['logo', 'banner', 'ad', 'icon']):
            return False
            
        # 檢查圖片尺寸（文字圖片通常不會太小或太大）
        try:
            w, h = int(width or 0), int(height or 0)
            if w > 0 and h > 0:
                # 過濾太小的圖片（可能是圖標）
                if w < 50 or h < 20:
                    return False
                # 過濾寬高比異常的圖片
                ratio = w / h
                if ratio > 10 or ratio < 0.1:
                    return False
        except:
            pass
            
        return True

    def download_image(self, src, headers=None):
        """下載圖片"""
        try:
            if src.startswith('data:'):
                # Base64編碼的圖片
                header, data = src.split(',', 1)
                image_data = base64.b64decode(data)
                return Image.open(BytesIO(image_data))
            else:
                # URL圖片
                if headers is None:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    
                response = requests.get(src, headers=headers, timeout=10)
                response.raise_for_status()
                return Image.open(BytesIO(response.content))
                
        except Exception as e:
            print(f"下載圖片失敗 {src}: {e}")
            return None

    def extract_text_from_image(self, image):
        """從圖片中提取文字"""
        if not image:
            return ""
            
        try:
            if self.use_easyocr and self.ocr_reader:
                # 使用EasyOCR
                result = self.ocr_reader.readtext(image)
                text_parts = [item[1] for item in result if item[2] > 0.5]  # 置信度過濾
                return ' '.join(text_parts)
                
            elif TESSERACT_AVAILABLE:
                # 使用Tesseract
                # 預處理圖片以提高識別率
                processed_image = self.preprocess_image(image)
                text = pytesseract.image_to_string(processed_image, lang='chi_tra+chi_sim+eng')
                return text.strip()
                
            else:
                print("沒有可用的OCR引擎")
                return ""
                
        except Exception as e:
            print(f"OCR識別失敗: {e}")
            return ""

    def preprocess_image(self, image):
        """預處理圖片以提高OCR識別率"""
        try:
            # 轉換為灰度
            if image.mode != 'L':
                image = image.convert('L')
                
            # 調整尺寸（太小的圖片放大）
            width, height = image.size
            if width < 200 or height < 50:
                scale_factor = max(200/width, 50/height)
                new_size = (int(width * scale_factor), int(height * scale_factor))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                
            # 可以添加更多預處理步驟，如二值化、降噪等
            
            return image
            
        except Exception as e:
            print(f"圖片預處理失敗: {e}")
            return image

    def extract_text_from_page_images(self, driver, save_debug=False):
        """從當前頁面的所有圖片中提取文字"""
        all_text = []
        images_info = self.extract_images_from_page(driver)
        
        for img_info in images_info:
            print(f"處理圖片 {img_info['index']}: {img_info['src'][:100]}...")
            
            # 下載圖片
            image = self.download_image(img_info['src'])
            
            if image:
                # 保存調試圖片
                if save_debug:
                    debug_file = f"debug_image_{img_info['index']}.png"
                    image.save(debug_file)
                    print(f"調試圖片保存到: {debug_file}")
                    
                # 提取文字
                text = self.extract_text_from_image(image)
                
                if text and len(text.strip()) > 5:  # 過濾太短的文字
                    print(f"✓ 提取到文字: {text[:100]}...")
                    all_text.append(text.strip())
                else:
                    print("✗ 未提取到有效文字")
            else:
                print("✗ 圖片下載失敗")
                
        return '\n'.join(all_text)

    def extract_canvas_text(self, driver):
        """提取Canvas元素中的文字（如果有的話）"""
        try:
            # 查找Canvas元素
            canvas_elements = driver.find_elements("tag name", "canvas")
            print(f"找到 {len(canvas_elements)} 個Canvas元素")
            
            all_text = []
            
            for i, canvas in enumerate(canvas_elements):
                try:
                    # 獲取Canvas內容為圖片
                    canvas_data = driver.execute_script("""
                        var canvas = arguments[0];
                        return canvas.toDataURL('image/png');
                    """, canvas)
                    
                    if canvas_data:
                        # 解析Base64圖片
                        image = self.download_image(canvas_data)
                        if image:
                            text = self.extract_text_from_image(image)
                            if text and len(text.strip()) > 5:
                                print(f"✓ 從Canvas {i} 提取到文字: {text[:100]}...")
                                all_text.append(text.strip())
                                
                except Exception as e:
                    print(f"處理Canvas {i} 失敗: {e}")
                    
            return '\n'.join(all_text)
            
        except Exception as e:
            print(f"提取Canvas文字失敗: {e}")
            return ""


# 集成到現有爬蟲的示例函數
def enhanced_content_extraction(driver, use_ocr=True):
    """增強的內容提取，結合文字和OCR"""
    content_parts = []
    
    # 1. 提取常規文字內容
    try:
        text_content = driver.find_element("id", "txtContent").text
        if text_content:
            content_parts.append("=== 文字內容 ===")
            content_parts.append(text_content)
    except:
        print("未找到txtContent元素")
    
    # 2. 如果啟用OCR，提取圖片文字
    if use_ocr:
        try:
            ocr_extractor = OCRImageExtractor()
            
            # 提取圖片文字
            image_text = ocr_extractor.extract_text_from_page_images(driver, save_debug=True)
            if image_text:
                content_parts.append("=== 圖片文字 ===")
                content_parts.append(image_text)
                
            # 提取Canvas文字
            canvas_text = ocr_extractor.extract_canvas_text(driver)
            if canvas_text:
                content_parts.append("=== Canvas文字 ===")
                content_parts.append(canvas_text)
                
        except Exception as e:
            print(f"OCR提取失敗: {e}")
    
    return '\n\n'.join(content_parts)


def install_ocr_dependencies():
    """安裝OCR相關依賴的指南"""
    print("""
OCR依賴安裝指南：

1. EasyOCR (推薦):
   pip install easyocr

2. Tesseract:
   # Windows:
   下載安裝包: https://github.com/UB-Mannheim/tesseract/wiki
   pip install pytesseract
   
   # Ubuntu/Debian:
   sudo apt-get install tesseract-ocr
   sudo apt-get install tesseract-ocr-chi-sim tesseract-ocr-chi-tra
   pip install pytesseract
   
   # macOS:
   brew install tesseract
   pip install pytesseract

3. 其他依賴:
   pip install Pillow requests
""")


if __name__ == "__main__":
    if not EASYOCR_AVAILABLE and not TESSERACT_AVAILABLE:
        print("未安裝OCR引擎！")
        install_ocr_dependencies()
    else:
        print("OCR工具可用")
        extractor = OCRImageExtractor()
        print("OCR工具初始化完成")
