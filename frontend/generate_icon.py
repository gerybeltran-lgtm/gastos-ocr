import os
from PIL import Image, ImageDraw

def draw_lightning_icon(size, output_path):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Draw dark blue circle background
    margin = size // 16
    draw.ellipse((margin, margin, size - margin, size - margin), fill="#0f172a")
    
    # Scale points for lightning bolt
    w, h = size, size
    points = [
        (w * 0.55, h * 0.15),
        (w * 0.33, h * 0.53),
        (w * 0.51, h * 0.53),
        (w * 0.41, h * 0.86),
        (w * 0.68, h * 0.43),
        (w * 0.49, h * 0.43),
    ]
    
    draw.polygon(points, fill="#eab308")
    
    img.save(output_path)

if __name__ == '__main__':
    out_dir = 'c:/Users/geryb/Desktop/Gastos_OCR/frontend/public'
    draw_lightning_icon(192, os.path.join(out_dir, 'pwa-192x192.png'))
    draw_lightning_icon(512, os.path.join(out_dir, 'pwa-512x512.png'))
    print("Icons generated!")
