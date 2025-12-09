#!/usr/bin/env python3
"""
Create an ultra-sharp red pillar 'I' icon - maximum clarity
"""

from PIL import Image, ImageDraw
from pathlib import Path

def create_ultra_sharp_icon():
    """Create the sharpest possible icon - simple geometric shapes"""
    
    # Create each size individually for pixel-perfect rendering
    sizes_to_create = [
        (256, 256),
        (128, 128),
        (64, 64),
        (48, 48),
        (32, 32),
        (24, 24),
        (16, 16)
    ]
    
    images = []
    
    # Professional red - bold and clear
    red = (220, 20, 60, 255)
    
    for width, height in sizes_to_create:
        # Transparent background
        img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        if width >= 64:
            # Large icons - detailed pillar with classic proportions
            # Top bar (20% width for margins)
            margin = width // 5
            bar_height = max(width // 10, 2)
            
            # Top horizontal bar
            draw.rectangle([margin, margin, width - margin, margin + bar_height], fill=red)
            
            # Vertical shaft (30% width)
            shaft_width = width // 3
            shaft_left = (width - shaft_width) // 2
            shaft_top = margin + bar_height
            shaft_bottom = height - margin - bar_height
            draw.rectangle([shaft_left, shaft_top, shaft_left + shaft_width, shaft_bottom], fill=red)
            
            # Bottom horizontal bar
            draw.rectangle([margin, shaft_bottom, width - margin, shaft_bottom + bar_height], fill=red)
            
        elif width >= 32:
            # Medium icons - simplified but clear
            if width == 48:
                # 48x48 optimized
                draw.rectangle([10, 8, 38, 12], fill=red)  # Top bar
                draw.rectangle([18, 12, 30, 36], fill=red)  # Shaft
                draw.rectangle([10, 36, 38, 40], fill=red)  # Bottom bar
            else:  # 32x32
                draw.rectangle([6, 5, 26, 8], fill=red)   # Top bar
                draw.rectangle([12, 8, 20, 24], fill=red)  # Shaft
                draw.rectangle([6, 24, 26, 27], fill=red)  # Bottom bar
                
        elif width == 24:
            # 24x24 - simple but visible
            draw.rectangle([5, 4, 19, 6], fill=red)   # Top bar
            draw.rectangle([9, 6, 15, 18], fill=red)  # Shaft
            draw.rectangle([5, 18, 19, 20], fill=red)  # Bottom bar
            
        else:  # 16x16
            # 16x16 - ultra minimal, maximum clarity
            draw.rectangle([3, 2, 13, 4], fill=red)   # Top bar
            draw.rectangle([6, 4, 10, 12], fill=red)  # Shaft
            draw.rectangle([3, 12, 13, 14], fill=red)  # Bottom bar
        
        images.append(img)
    
    # Save with all sizes
    icon_path = Path(__file__).parent / "ccmd_bot_icon.ico"
    images[0].save(
        str(icon_path),
        format='ICO',
        sizes=sizes_to_create,
        append_images=images[1:]
    )
    
    print(f"✅ Created ULTRA-SHARP icon: {icon_path}")
    print(f"   Icon size: {icon_path.stat().st_size} bytes")
    print(f"   Includes 7 optimized sizes: 256, 128, 64, 48, 32, 24, 16")
    print(f"   Each size pixel-perfect optimized")
    print("\n🎯 Maximum sharpness achieved!")
    
    return str(icon_path)

if __name__ == "__main__":
    create_ultra_sharp_icon()

