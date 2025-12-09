"""Check PDF form fields"""
import sys
from pathlib import Path

pdf_path = Path(r"C:\Users\mthompson\Downloads\1939_072519_b_reopening_request_508.pdf")

print("=" * 80)
print("Checking PDF Form Fields")
print("=" * 80)
print(f"PDF: {pdf_path}")
print(f"Exists: {pdf_path.exists()}")
print("=" * 80)

if not pdf_path.exists():
    print("ERROR: PDF file not found!")
    sys.exit(1)

# Try pdfrw (best for form fields)
print("\n1. Trying pdfrw (best for form fields)...")
try:
    import pdfrw
    template_pdf = pdfrw.PdfReader(str(pdf_path))
    print(f"   Pages: {len(template_pdf.pages)}")
    
    # Check for form fields
    if template_pdf.Root and template_pdf.Root.AcroForm:
        print("   ✅ PDF has form fields (AcroForm)")
        annotations = []
        for page in template_pdf.pages:
            if page.Annots:
                for annot in page.Annots:
                    if annot and annot.get('/Subtype') == '/Widget':
                        field_name = annot.get('/T')
                        field_type = annot.get('/FT')
                        if field_name:
                            annotations.append((str(field_name), str(field_type)))
        
        if annotations:
            print(f"   Found {len(annotations)} form fields:")
            for name, ftype in annotations[:20]:  # Show first 20
                print(f"      - {name}: {ftype}")
            if len(annotations) > 20:
                print(f"      ... and {len(annotations) - 20} more")
        else:
            print("   ⚠️ No form fields found in annotations")
    else:
        print("   ⚠️ PDF does not have AcroForm (may not be a fillable form)")
        
except ImportError:
    print("   ❌ pdfrw not installed")
    print("   Install with: pip install pdfrw")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Try PyPDF2
print("\n2. Trying PyPDF2...")
try:
    import PyPDF2
    with open(pdf_path, 'rb') as f:
        pdf_reader = PyPDF2.PdfReader(f)
        print(f"   Pages: {len(pdf_reader.pages)}")
        if pdf_reader.get_form_text_fields():
            fields = pdf_reader.get_form_text_fields()
            print(f"   ✅ Found {len(fields)} form fields:")
            for field_name in list(fields.keys())[:20]:
                print(f"      - {field_name}")
            if len(fields) > 20:
                print(f"      ... and {len(fields) - 20} more")
        else:
            print("   ⚠️ No form fields found")
except ImportError:
    print("   ❌ PyPDF2 not installed")
    print("   Install with: pip install PyPDF2")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Try pdfplumber (for text extraction)
print("\n3. Trying pdfplumber (text extraction)...")
try:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        print(f"   Pages: {len(pdf.pages)}")
        # Extract text from first page
        first_page = pdf.pages[0]
        text = first_page.extract_text()
        if text:
            print(f"   ✅ First page has text ({len(text)} chars)")
            print("   First 500 characters:")
            print("   " + "-" * 76)
            for line in text[:500].split('\n')[:10]:
                print(f"   {line}")
            print("   " + "-" * 76)
        else:
            print("   ⚠️ No text found on first page")
except ImportError:
    print("   ❌ pdfplumber not installed")
except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 80)

