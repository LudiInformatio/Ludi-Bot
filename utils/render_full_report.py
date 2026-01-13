from PIL import Image, ImageDraw, ImageFont
try:
    from pilmoji import Pilmoji
except ImportError:
    print("⚠️  Pilmoji not found. Emojis will be rendered as text.")
    class Pilmoji:
        def __init__(self, img, source=None):
            self.draw = ImageDraw.Draw(img)
        def text(self, xy, text, fill=None, font=None, *args, **kwargs):
            self.draw.text(xy, text, fill=fill, font=font, *args, **kwargs)

import os
from datetime import datetime

# === Configuration ===
WIDTH = 1200
HEIGHT = 1400
BACKGROUND_COLOR = (253, 251, 247)  # Moleskine Cream

# Colors
COLOR_NAVY = (26, 44, 66)    # Deep Navy
COLOR_TEAL = (0, 168, 150)   # Teal for highlights
COLOR_RED =  (220, 38, 38)   # Alert Red

# Paths
FONT_PATH_SANS_REG = "/usr/share/fonts/chromeos/croscore/Arimo-Regular.ttf"
FONT_PATH_SANS_BOLD = "/usr/share/fonts/chromeos/croscore/Arimo-Bold.ttf"
FONT_PATH_SERIF = "/usr/share/fonts/chromeos/croscore/Tinos-Regular.ttf"
LOGO_IMAGE_PATH = "/home/mnprice86/.gemini/antigravity/brain/b25297a4-052f-47a9-abcb-a2bfc821945c/uploaded_image_1_1768264766933.jpg"

# Font Sizes
FONT_SIZE_TITLE = 60
FONT_SIZE_HEADER = 34
FONT_SIZE_GAME_TITLE = 32
FONT_SIZE_BODY = 26
FONT_SIZE_CONTEXT = 22

# Layout
PADDING_X = 40
PADDING_Y = 30
LINE_SPACING = 8
SECTION_SPACING = 25

def make_bg_transparent(img, tolerance=30):
    """Remove background from logo by sampling corner color."""
    img = img.convert("RGBA")
    datas = img.getdata()
    bg_sample = img.getpixel((0, 0))
    bg_r, bg_g, bg_b = bg_sample[0], bg_sample[1], bg_sample[2]
    
    newData = []
    for item in datas:
        r, g, b = item[0], item[1], item[2]
        if abs(r - bg_r) < tolerance and abs(g - bg_g) < tolerance and abs(b - bg_b) < tolerance:
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
    img.putdata(newData)
    return img

def transform_props_to_briefing_data(props_list: list) -> list:
    """
    Transform Module F props list into the visual template format.
    Groups plays by matchup.
    """
    grouped = {}
    for p in props_list:
        matchup = p.get('matchup', 'Unknown')
        if matchup not in grouped:
            grouped[matchup] = []
        grouped[matchup].append(p)
    
    briefing_data = []
    for matchup in sorted(grouped.keys()):
        plays = grouped[matchup]
        plays.sort(key=lambda x: x.get('ev', 0), reverse=True)
        
        game_entry = {
            "game_title": f"🏀 {matchup}",
            "lines": []
        }
        
        for play in plays[:5]:  # Top 5 per game
            name = play.get('name', 'Unknown')
            bet_on = play.get('bet_on', 'O')
            line = play.get('line', 0)
            stat = play.get('stat', 'PTS')
            proj = play.get('proj', 0)
            ev = play.get('ev', 0)
            tags = play.get('tags', '')
            note = play.get('note', '')
            
            # Line 1: Player | Side Line Stat
            line1 = [
                {"text": f"{name} | {bet_on[0]} {line} {stat}", "color": COLOR_NAVY}
            ]
            
            # Line 2: Proj | EV | Context
            line2_parts = [
                {"text": f"Proj: {proj}", "color": COLOR_NAVY},
                {"text": f" | EV: +{ev}%", "color": COLOR_TEAL}
            ]
            
            # Add tags/note if present
            context = ""
            if note:
                context = note[:40]  # Truncate
            elif tags and tags != "[]":
                context = tags.replace("[", "").replace("]", "").replace('"', '')[:40]
            
            if context:
                line2_parts.append({"text": f" | {context}", "color": COLOR_NAVY})
            
            game_entry["lines"].append(line1)
            game_entry["lines"].append(line2_parts)
        
        briefing_data.append(game_entry)
    
    return briefing_data


def create_briefing_card(props_data: list = None, title: str = "LUDI GAME BRIEF") -> str:
    """
    Generate a visual briefing card from props data.
    
    Args:
        props_data: List of dicts with keys: matchup, name, bet_on, line, stat, proj, ev, tags, note
        title: The title text to display at the top (e.g., "LUDI MORNING BRIEF", "LUDI EVENING LOCK")
    
    Returns:
        Path to generated PNG file
    """
    # Transform props to visual format
    if props_data:
        briefing_data = transform_props_to_briefing_data(props_data)
    else:
        # Fallback demo data
        briefing_data = [{
            "game_title": "🏀 DEMO GAME",
            "lines": [[{"text": "Demo Player | O 25.5 PTS", "color": COLOR_NAVY}],
                      [{"text": "Proj: 28.0 | EV: +15%", "color": COLOR_TEAL}]]
        }]
    
    # Calculate dynamic height
    total_lines = sum(len(g["lines"]) for g in briefing_data) + len(briefing_data) * 2
    calculated_height = max(800, 300 + total_lines * 40)
    
    img = Image.new('RGB', (WIDTH, calculated_height), color=BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)
    pm = Pilmoji(img)

    # Load Fonts
    try:
        font_header = ImageFont.truetype(FONT_PATH_SANS_REG, FONT_SIZE_HEADER)
        font_game_bold = ImageFont.truetype(FONT_PATH_SANS_BOLD, FONT_SIZE_GAME_TITLE)
        font_body = ImageFont.truetype(FONT_PATH_SANS_REG, FONT_SIZE_BODY)
    except IOError:
        print("Error: Font files not found.")
        return None

    current_y = PADDING_Y

    # Draw Logo
    if os.path.exists(LOGO_IMAGE_PATH):
        logo_img = Image.open(LOGO_IMAGE_PATH).convert("RGBA")
        logo_img = make_bg_transparent(logo_img)
        navy_layer = Image.new("RGBA", logo_img.size, COLOR_NAVY)
        navy_layer.putalpha(logo_img.split()[3])
        logo_img = navy_layer
        
        logo_width = int(WIDTH * 0.20)
        logo_height = int(logo_width * logo_img.height / logo_img.width)
        logo_img = logo_img.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
        
        logo_x = (WIDTH - logo_width) // 2
        img.paste(logo_img, (logo_x, current_y), logo_img)
        current_y += logo_height + 10

    # Date Header
    date_str = datetime.now().strftime('%b %d, %Y').upper()
    header_text = f"{title} | {date_str}"
    header_w = draw.textlength(header_text, font=font_header)
    draw.text(((WIDTH - header_w) / 2, current_y), header_text, font=font_header, fill=COLOR_NAVY)
    current_y += FONT_SIZE_HEADER + SECTION_SPACING
    
    # Divider
    draw.line([(PADDING_X, current_y), (WIDTH - PADDING_X, current_y)], fill=(200,200,200), width=1)
    current_y += SECTION_SPACING

    # Draw Content
    for game in briefing_data:
        pm.text((PADDING_X, current_y), game["game_title"], font=font_game_bold, fill=COLOR_NAVY)
        current_y += FONT_SIZE_GAME_TITLE + LINE_SPACING

        for line_segments in game["lines"]:
            current_x = PADDING_X
            for segment in line_segments:
                text_content = segment["text"]
                text_color = segment["color"]
                pm.text((current_x, current_y), text_content, font=font_body, fill=text_color)
                segment_w = draw.textlength(text_content, font=font_body)
                current_x += segment_w
            current_y += FONT_SIZE_BODY + LINE_SPACING
        
        current_y += SECTION_SPACING // 2
        draw.line([(PADDING_X, current_y), (WIDTH - PADDING_X, current_y)], fill=(230,230,230), width=1)
        current_y += SECTION_SPACING

    output_path = "/home/mnprice86/ludi_bot/ludi_generated_briefing.png"
    img.save(output_path)
    print(f"✅ Visual briefing generated: {output_path}")
    return output_path


if __name__ == "__main__":
    # Demo with sample data
    demo_props = [
        {"matchup": "HOU @ BKN", "name": "Amen Thompson", "bet_on": "OVER", "line": 13.5, "stat": "PTS", "proj": 19.5, "ev": 44, "note": "🚀 VACUUM: Sengun OUT"},
        {"matchup": "HOU @ BKN", "name": "Jalen Green", "bet_on": "UNDER", "line": 24.5, "stat": "PTS", "proj": 20.1, "ev": 18, "tags": "[\"#PaceUp\"]"},
        {"matchup": "LAL @ GSW", "name": "LeBron James", "bet_on": "OVER", "line": 24.5, "stat": "PTS", "proj": 28.5, "ev": 22, "note": ""},
    ]
    create_briefing_card(demo_props)
