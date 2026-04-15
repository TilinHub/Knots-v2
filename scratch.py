import PyPDF2

try:
    with open('Papers/2005.13168v1.pdf', 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        text = ""
        for i in range(min(3, len(reader.pages))):
            text += reader.pages[i].extract_text() + "\n"
        print(text[:1500])
except Exception as e:
    print(f"Error PyPDF2: {e}")
    try:
        import pymupdf
        doc = pymupdf.open('Papers/2005.13168v1.pdf')
        text = ""
        for i in range(min(3, len(doc))):
            text += doc[i].get_text() + "\n"
        print(text[:1500])
    except Exception as e2:
        print(f"Error PyMuPDF: {e2}")
