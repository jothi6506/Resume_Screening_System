import sys
import traceback

print("Testing EasyOCR...")
try:
    import easyocr
    print("EasyOCR imported successfully.")
except ImportError as e:
    print("EasyOCR not installed:", e)
except Exception as e:
    print("EasyOCR error:")
    traceback.print_exc()

print("\nTesting PyTesseract...")
try:
    from PIL import Image
    import pytesseract
    
    import os
    if os.path.exists(r'C:\Program Files\Tesseract-OCR\tesseract.exe'):
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    elif os.path.exists(r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'):
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
    elif os.path.exists(os.path.expandvars(r'%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe')):
        pytesseract.pytesseract.tesseract_cmd = os.path.expandvars(r'%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe')
        
    print("PyTesseract imported successfully. Path:", pytesseract.pytesseract.tesseract_cmd)
    
    # Try creating a dummy image and running pytesseract
    img = Image.new('RGB', (100, 30), color = (73, 109, 137))
    try:
        text = pytesseract.image_to_string(img)
        print("PyTesseract ran successfully. Output:", text)
    except Exception as e:
        print("PyTesseract execution failed:")
        traceback.print_exc()

except ImportError as e:
    print("PyTesseract/PIL not installed:", e)
except Exception as e:
    print("PyTesseract error:")
    traceback.print_exc()
