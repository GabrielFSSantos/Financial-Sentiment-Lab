#!/usr/bin/env python3
"""QA visual de PDF de apresentações; gera PNGs, contatos e alertas heurísticos.
Uso: python scripts/qa_slides_ppgcc.py output/apresentacao_ppgcc.pdf --out build/qa
Dependências: pymupdf, pillow. As advertências precisam de revisão visual.
"""
import argparse
import csv
import math
from pathlib import Path
import fitz
from PIL import Image, ImageDraw, ImageOps


def inspect(page, number):
    rect = page.rect
    w, h = rect.width, rect.height
    warns = []
    spans = []
    for bi, block in enumerate(page.get_text('dict')['blocks']):
        if block.get('type') != 0:
            continue
        for line in block.get('lines', []):
            for span in line.get('spans', []):
                txt = span.get('text', '').strip()
                if not txt:
                    continue
                box = fitz.Rect(span['bbox'])
                spans.append((bi, box, txt, span['size']))
                if box.x0 < -1 or box.y0 < -1 or box.x1 > w+1 or box.y1 > h+1:
                    warns.append(('FORA_DA_PAGINA', txt[:80]))
                if box.y0 > 45 and box.y1 < h-20 and span['size'] < 7.5:
                    warns.append(('FONTE_PEQUENA', f'{span["size"]:.1f}pt: {txt[:70]}'))
    seen = set()
    for i, (bid, a, at, fs) in enumerate(spans):
        for bid2, b, bt, fs2 in spans[i+1:]:
            if bid == bid2:
                continue
            if a.y0 > h-16 or b.y0 > h-16:
                continue
            overlap = a & b
            if not overlap or overlap.is_empty or a.get_area() <= 0 or b.get_area() <= 0:
                continue
            frac = overlap.get_area() / min(a.get_area(), b.get_area())
            if frac > 0.35:
                key = (at[:30], bt[:30])
                if key not in seen:
                    warns.append(('POSSIVEL_SOBREPOSICAO', f'{at[:38]!r} / {bt[:38]!r}'))
                    seen.add(key)
    if len(spans) > 110:
        warns.append(('SLIDE_DENSO', f'{len(spans)} trechos de texto'))
    return warns


def contact_sheet(files, target, cols=3, tile_width=600):
    tw, th = tile_width, round(tile_width*9/16)
    gap=12; label_h=24
    rows=math.ceil(len(files)/cols)
    sheet=Image.new('RGB', (cols*(tw+gap)+gap, rows*(th+label_h+gap)+gap), (230,233,238))
    draw=ImageDraw.Draw(sheet)
    for i, f in enumerate(files):
        with Image.open(f) as raw:
            img=ImageOps.contain(raw.convert('RGB'), (tw,th))
        x=gap+(i%cols)*(tw+gap)
        y=gap+(i//cols)*(th+label_h+gap)
        sheet.paste(img, (x,y+label_h))
        draw.text((x+3,y+4), f.stem, fill=(28,30,32))
    sheet.save(target, quality=86)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('pdf')
    ap.add_argument('--out', default='build/qa')
    ap.add_argument('--dpi', type=int, default=150)
    args=ap.parse_args()
    out=Path(args.out)
    pages_dir=out/'pages'; pages_dir.mkdir(parents=True,exist_ok=True)
    doc=fitz.open(args.pdf)
    rows=[]; images=[]
    for ix, page in enumerate(doc):
        filename=pages_dir/f'slide_{ix+1:02d}.png'
        page.get_pixmap(matrix=fitz.Matrix(args.dpi/72,args.dpi/72),alpha=False).save(filename)
        images.append(filename)
        for code,detail in inspect(page,ix+1):
            rows.append((ix+1,code,detail))
    with (out/'alertas.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['slide','alerta','detalhe']);writer.writerows(rows)
    for chunk in range(0,len(images),12):
        contact_sheet(images[chunk:chunk+12],out/f'contato_{chunk//12+1:02d}.jpg')
    print(f'OK: {len(doc)} slides, {len(rows)} alertas heurísticos.')
    print(f'Abra os arquivos contato_*.jpg em {out}/ e confira todos os slides.')
    print('Observação: alertas não substituem inspeção visual; elementos gráficos e imagens podem se sobrepor sem alerta.')

if __name__=='__main__':
    main()
