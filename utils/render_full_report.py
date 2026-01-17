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
import sqlite3

# === Configuration ===
WIDTH = 1200
HEIGHT = 1400
BACKGROUND_COLOR = (253, 251, 247)  # Moleskine Cream

# Colors
COLOR_NAVY = (26, 44, 66)    # Deep Navy
COLOR_TEAL = (0, 168, 150)   # Teal for highlights
COLOR_RED =  (220, 38, 38)   # Alert Red
COLOR_WHITE = (255, 255, 255)
COLOR_GRAY = (100, 116, 139) # Slate 500

# Paths
# Paths - macOS Compatible (with fallbacks if needed in future)
FONT_PATH_SANS_REG = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_PATH_SANS_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_PATH_SERIF = "/System/Library/Fonts/Supplemental/Times New Roman.ttf"

# Resolve absolute path to project root for assets
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_IMAGE_PATH = os.path.join(PROJECT_ROOT, "ludi_header_exact_v1.png")
DB_PATH = os.path.join(PROJECT_ROOT, "ludi.db")

# Font Sizes
FONT_SIZE_TITLE = 60
FONT_SIZE_HEADER = 34
FONT_SIZE_GAME_TITLE = 32
FONT_SIZE_BODY = 26
FONT_SIZE_BADGE = 22
FONT_SIZE_CONTEXT = 22
FONT_SIZE_FOOTER = 24

# Layout
PADDING_X = 40
PADDING_Y = 30
LINE_SPACING = 12
SECTION_SPACING = 30
BADGE_PADDING_X = 12
BADGE_PADDING_Y = 6
BADGE_RADIUS = 10

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

def get_notable_refs():
    """Fetch top strict and lenient referees for the footer."""
    if not os.path.exists(DB_PATH):
        return None
        
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        c.execute("SELECT referee_name, avg_fouls_per_game FROM referee_profiles WHERE style='STRICT' ORDER BY avg_fouls_per_game DESC LIMIT 3")
        strict = c.fetchall()
        
        c.execute("SELECT referee_name, avg_fouls_per_game FROM referee_profiles WHERE style='LENIENT' ORDER BY avg_fouls_per_game ASC LIMIT 3")
        lenient = c.fetchall()
        
        conn.close()
        return {"strict": strict, "lenient": lenient}
    except Exception as e:
        print(f"⚠️  Database error fetching refs: {e}")
        return None

def draw_badge(draw, xy, text, font, bg_color, text_color):
    """Draws a rounded rectangle badge with centered text."""
    x, y = xy
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_w = text_bbox[2] - text_bbox[0]
    text_h = text_bbox[3] - text_bbox[1]
    
    w = text_w + (BADGE_PADDING_X * 2)
    h = text_h + (BADGE_PADDING_Y * 2)
    
    # Draw rounded rect
    draw.rounded_rectangle([x, y, x + w, y + h], radius=BADGE_RADIUS, fill=bg_color)
    
    # Draw text centered
    text_x = x + BADGE_PADDING_X
    text_y = y + BADGE_PADDING_Y - 2 # slight adjustment for baseline
    draw.text((text_x, text_y), text, font=font, fill=text_color)
    
    return w

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
            # Format: "LeBron James | O 24.5 PTS"
            line1 = [
                {"text": f"{name}", "color": COLOR_NAVY, "is_bold": True},
                {"text": f" | {bet_on[0]} {line} {stat}", "color": COLOR_NAVY, "is_bold": False}
            ]
            
            # Line 2: Badges and Context
            line2_parts = []
            
            # Proj Badge
            line2_parts.append({
                "text": f"Proj: {proj}", 
                "color": COLOR_NAVY, 
                "bg_color": (226, 232, 240), # Slate 200
                "is_badge": True
            })
            
            # EV Badge (Teal if > 5%, else Navy)
            ev_color = COLOR_TEAL if ev >= 5 else COLOR_NAVY
            line2_parts.append({
                "text": f"EV: +{ev}%", 
                "color": COLOR_WHITE, 
                "bg_color": ev_color,
                "is_badge": True
            })
            
            # Parse Tags/Note
            context_text = ""
            if note:
                context_text = note[:40]
            elif tags and tags != "[]":
                # Clean up list string: "['TAG']" -> "TAG"
                cleaned = tags.replace("[", "").replace("]", "").replace('"', "").replace("'", "")
                # Take first 2 tags if multiple
                tag_list = [t.strip() for t in cleaned.split(',')]
                context_text = " • ".join(tag_list[:2])
            
            if context_text:
                line2_parts.append({
                    "text": context_text,
                    "color": COLOR_GRAY,
                    "is_badge": False,
                    "is_context": True
                })
            
            game_entry["lines"].append(line1)
            game_entry["lines"].append(line2_parts)
        
        briefing_data.append(game_entry)
    
    return briefing_data


def create_briefing_card(props_data: list = None, title: str = "LUDI GAME BRIEF") -> str:
    """
    Generate a visual briefing card from props data.
    """
    if props_data:
        briefing_data = transform_props_to_briefing_data(props_data)
    else:
        briefing_data = [{
            "game_title": "🏀 DEMO GAME",
            "lines": [
                [
                    {"text": "Demo Player", "color": COLOR_NAVY, "is_bold": True},
                    {"text": " | O 25.5 PTS", "color": COLOR_NAVY, "is_bold": False}
                ],
                [
                    {"text": "Proj: 28.0", "color": COLOR_NAVY, "bg_color": (226, 232, 240), "is_badge": True},
                    {"text": "EV: +15%", "color": COLOR_WHITE, "bg_color": COLOR_TEAL, "is_badge": True},
                    {"text": "VACUUM: Star Out", "color": COLOR_GRAY, "is_badge": False, "is_context": True}
                ]
            ]
        }]
    
    # Calculate dynamic height
    content_lines = sum(len(g["lines"]) for g in briefing_data) + len(briefing_data) * 2
    calculated_height = max(900, 350 + content_lines * 55 + 200) 
    
    img = Image.new('RGB', (WIDTH, calculated_height), color=BACKGROUND_COLOR)
    draw = ImageDraw.Draw(img)
    pm = Pilmoji(img)

    # Load Fonts
    try:
        font_header = ImageFont.truetype(FONT_PATH_SANS_REG, FONT_SIZE_HEADER)
        font_game_bold = ImageFont.truetype(FONT_PATH_SANS_BOLD, FONT_SIZE_GAME_TITLE)
        font_body = ImageFont.truetype(FONT_PATH_SANS_REG, FONT_SIZE_BODY)
        font_body_bold = ImageFont.truetype(FONT_PATH_SANS_BOLD, FONT_SIZE_BODY)
        font_badge = ImageFont.truetype(FONT_PATH_SANS_BOLD, FONT_SIZE_BADGE)
        font_context = ImageFont.truetype(FONT_PATH_SANS_REG, FONT_SIZE_CONTEXT)
        font_footer_bold = ImageFont.truetype(FONT_PATH_SANS_BOLD, FONT_SIZE_FOOTER)
        font_footer_reg = ImageFont.truetype(FONT_PATH_SANS_REG, FONT_SIZE_FOOTER)
    except IOError:
        print("Error: Font files not found. Using default.")
        # Fallback to default if needed (though macOS paths usually work)
        font_header = ImageFont.load_default()
        font_game_bold = ImageFont.load_default()
        font_body = ImageFont.load_default()
        font_body_bold = ImageFont.load_default()
        font_badge = ImageFont.load_default()
        font_context = ImageFont.load_default()
        font_footer_bold = ImageFont.load_default()
        font_footer_reg = ImageFont.load_default()

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
    # draw.textlength requires font object
    header_w = draw.textlength(header_text, font=font_header)
    draw.text((int((WIDTH - header_w) / 2), current_y), header_text, font=font_header, fill=COLOR_NAVY)
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
            max_h = 0
            
            for segment in line_segments:
                is_badge = segment.get("is_badge", False)
                text_content = segment["text"]
                text_color = segment["color"]
                
                if is_badge:
                    bg_color = segment.get("bg_color", COLOR_NAVY)
                    badge_w = draw_badge(draw, (current_x, current_y), text_content, font_badge, bg_color, text_color)
                    current_x += badge_w + 10
                    max_h = max(max_h, FONT_SIZE_BADGE + BADGE_PADDING_Y * 2)
                else:
                    # Regular text
                    is_bold = segment.get("is_bold", False)
                    is_context = segment.get("is_context", False)
                    
                    font_to_use = font_body_bold if is_bold else (font_context if is_context else font_body)
                    
                    # Vertical alignment adjustment for text next to badges
                    text_y = current_y + (BADGE_PADDING_Y if is_context else 0)
                    
                    pm.text((int(current_x), int(text_y)), text_content, font=font_to_use, fill=text_color)
                    segment_w = draw.textlength(text_content, font=font_to_use)
                    current_x += segment_w
                    max_h = max(max_h, FONT_SIZE_BODY)

            current_y += max_h + LINE_SPACING
        
        current_y += SECTION_SPACING // 2
        draw.line([(PADDING_X, current_y), (WIDTH - PADDING_X, current_y)], fill=(230,230,230), width=1)
        current_y += SECTION_SPACING
        
    # === WHISTLE WATCH FOOTER ===
    current_y += SECTION_SPACING
    draw.line([(PADDING_X, current_y), (WIDTH - PADDING_X, current_y)], fill=(0,0,0), width=3)
    current_y += SECTION_SPACING
    
    pm.text((PADDING_X, current_y), "📢 LUDI WHISTLE WATCH", font=font_footer_bold, fill=COLOR_NAVY)
    current_y += FONT_SIZE_FOOTER + LINE_SPACING
    
    refs = get_notable_refs()
    if refs:
        # Strict Column
        col1_x = PADDING_X
        pm.text((col1_x, current_y), "🔥 STRICT (High Fouls)", font=font_footer_bold, fill=COLOR_RED)
        y_temp = current_y + FONT_SIZE_FOOTER + 5
        for r in refs['strict']:
            pm.text((col1_x, y_temp), f"{r[0]} ({r[1]} PF/G)", font=font_footer_reg, fill=COLOR_NAVY)
            y_temp += FONT_SIZE_FOOTER + 5
            
        # Lenient Column
        col2_x = WIDTH // 2 + PADDING_X
        pm.text((col2_x, current_y), "❄️ LENIENT (Let 'em Play)", font=font_footer_bold, fill=COLOR_TEAL)
        y_temp = current_y + FONT_SIZE_FOOTER + 5
        for r in refs['lenient']:
            pm.text((col2_x, y_temp), f"{r[0]} ({r[1]} PF/G)", font=font_footer_reg, fill=COLOR_NAVY)
            y_temp += FONT_SIZE_FOOTER + 5
    else:
        pm.text((PADDING_X, current_y + 10), "No referee data available.", font=font_footer_reg, fill=COLOR_NAVY)

    # Ensure directory exists
    output_dir = os.path.join(PROJECT_ROOT, "assets", "generated")
    os.makedirs(output_dir, exist_ok=True)
    
    output_path = os.path.join(output_dir, "ludi_generated_briefing.png")
    img.save(output_path)
    print(f"✅ Visual briefing generated: {output_path}")
    return output_path


if __name__ == "__main__":
    # Demo with sample data to verify visuals
    demo_props = [
        {"matchup": "HOU @ BKN", "name": "Amen Thompson", "bet_on": "OVER", "line": 13.5, "stat": "PTS", "proj": 19.5, "ev": 44, "note": "🚀 VACUUM: Sengun OUT"},
        {"matchup": "HOU @ BKN", "name": "Jalen Green", "bet_on": "UNDER", "line": 24.5, "stat": "PTS", "proj": 20.1, "ev": 18, "tags": "[\"#PaceUp\"]"},
        {"matchup": "LAL @ GSW", "name": "LeBron James", "bet_on": "OVER", "line": 24.5, "stat": "PTS", "proj": 28.5, "ev": 22, "note": ""},
    ]
    create_briefing_card(demo_props)