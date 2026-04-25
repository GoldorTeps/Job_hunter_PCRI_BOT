"""
Ejecuta esto UNA VEZ en local para extraer el texto de tus PDFs:

    pip install pdfplumber
    python extract_cvs.py ruta/cv_mozo.pdf ruta/cv_admin.pdf ruta/cv_telemarketing.pdf

Genera los archivos cvs/mozo.txt, cvs/admin.txt, cvs/telemarketing.txt
que se suben a Railway con el resto del repo.
"""
import sys
import os

try:
    import pdfplumber
except ImportError:
    print('Instala pdfplumber: pip install pdfplumber')
    sys.exit(1)

NAMES = ['mozo', 'admin', 'telemarketing']

def extract(pdf_path: str, name: str):
    os.makedirs('cvs', exist_ok=True)
    out = f'cvs/{name}.txt'
    with pdfplumber.open(pdf_path) as pdf:
        text = '\n'.join(
            page.extract_text() or ''
            for page in pdf.pages
        ).strip()
    with open(out, 'w', encoding='utf-8') as f:
        f.write(text)
    print(f'✅  {pdf_path} → {out}  ({len(text)} caracteres)')

if __name__ == '__main__':
    pdfs = sys.argv[1:]
    if len(pdfs) != 3:
        print('Uso: python extract_cvs.py cv_mozo.pdf cv_admin.pdf cv_telemarketing.pdf')
        sys.exit(1)
    for pdf, name in zip(pdfs, NAMES):
        extract(pdf, name)
    print('\nListo. Haz commit de la carpeta cvs/ y despliega en Railway.')
