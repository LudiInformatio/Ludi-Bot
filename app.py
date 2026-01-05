from flask import Flask, render_template_string
import json
import os

app = Flask(__name__)

# --- THE FRONT END (HTML + CSS) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LUDI INFORMATIO | ORIGINATOR DASHBOARD</title>
    <style>
        :root {
            --neon-green: #00ff00;
            --dark-green: #004400;
            --alert-red: #ff3333;
            --bg-color: #0d0d0d;
            --card-bg: #1a1a1a;
            --text-color: #e0e0e0;
        }
        body {
            font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 20px;
        }
        h1, h2, h3 { text-transform: uppercase; letter-spacing: 1px; margin-top: 0;}
        h1 { color: var(--neon-green); border-bottom: 2px solid var(--neon-green); padding-bottom: 10px; }
        h2 { margin-top: 30px; font-size: 1.2rem; color: #888; }
        
        .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        
        .card {
            background: var(--card-bg);
            border: 1px solid #333;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            transition: transform 0.2s;
        }
        .card:hover { transform: translateY(-2px); border-color: #555; }
        
        /* DIAMOND PLAYS (Green Glow) */
        .diamond-card {
            border: 1px solid var(--neon-green);
            box-shadow: 0 0 10px rgba(0, 255, 0, 0.1);
        }
        .diamond-header {
            color: var(--neon-green);
            font-weight: bold;
            font-size: 0.9rem;
            margin-bottom: 10px;
            display: block;
        }

        .bet-row { display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px; }
        .bet-name { font-size: 1.1rem; font-weight: bold; color: #fff; }
        .bet-line { color: #aaa; }
        
        .badge {
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 0.85rem;
        }
        .badge-ev { background: var(--dark-green); color: var(--neon-green); }
        .badge-streak { background: #442200; color: #ffaa00; }
        
        .stat-line { font-family: 'Courier New', monospace; font-size: 0.9rem; margin-top: 8px; color: #bbb;}
        
        .footer { margin-top: 50px; text-align: center; color: #444; font-size: 0.8rem; }
    </style>
</head>
<body>

    <div style="display: flex; justify-content: space-between; align-items: center;">
        <h1>LUDI INFORMATIO</h1>
        <div style="text-align: right; font-size: 0.8rem; color: #666;">
            STATUS: <span style="color: var(--neon-green)">ONLINE</span><br>
            UPDATED: {{ data.generated_at }}
        </div>
    </div>

    <h2>🏆 CHAMPIONSHIP PLAYS (Top 3)</h2>
    <div class="grid">
        {% for bet in data.diamond_plays %}
        <div class="card diamond-card">
            <span class="diamond-header">💎 DIAMOND LOCK</span>
            <div class="bet-row">
                <span class="bet-name">{{ bet.name }}</span>
                <span class="badge badge-ev">+{{ bet.ev }}% EV</span>
            </div>
            <div class="bet-line">
                🎯 {{ bet.bet_on }} @ {{ bet.line }}
            </div>
            <div class="stat-line">
                Model: {{ bet.model_val }} | Stake: {{ bet.units }}u
            </div>
        </div>
        {% endfor %}
    </div>

    <h2>🏎️ HIGH OCTANE PROPS</h2>
    <div class="grid">
        {% for prop in data.prop_bets[:6] %}
        <div class="card">
            <div class="bet-row">
                <span class="bet-name">{{ prop.name }}</span>
                <span class="badge badge-ev">+{{ prop.ev }}% EV</span>
            </div>
            <div class="bet-line">
                👉 {{ prop.bet_on }} ({{ prop.line }})
            </div>
            <div class="stat-line">
                Proj: {{ prop.model_val }} | Stake: {{ prop.units }}u
            </div>
        </div>
        {% endfor %}
    </div>

    <h2>🔥 HEAT CHECK (L10 Streaks)</h2>
    <div class="grid">
        {% for s in data.streaks %}
        <div class="card" style="border-left: 3px solid #ffaa00;">
            <div class="bet-row">
                <span class="bet-name">{{ s.player }}</span>
                <span class="badge badge-streak">HOT</span>
            </div>
            <div class="stat-line">
                {{ s.stat }} L10 Avg: <b>{{ s.l5 }}</b>
            </div>
            <div class="stat-line">
                vs Today's Line: {{ s.line }}
            </div>
        </div>
        {% endfor %}
    </div>

    <div class="footer">
        ORIGINATOR MODEL v1.0 | RUNNING ON LOCAL SERVER
    </div>

</body>
</html>
"""

@app.route('/')
def home():
    # 1. READ THE JSON FILE GENERATED BY MAIN.PY
    if not os.path.exists('daily_report.json'):
        return """
        <body style="background:#111; color:#fff; font-family:sans-serif; text-align:center; padding-top:50px;">
            <h1>⚠️ NO DATA FOUND</h1>
            <p>Please run <code>python3 main.py</code> first to generate the report.</p>
        </body>
        """
    
    with open('daily_report.json', 'r') as f:
        data = json.load(f)
    
    return render_template_string(HTML_TEMPLATE, data=data)

if __name__ == '__main__':
    print("\n" + "="*40)
    print("🚀 LUDI DASHBOARD LAUNCHING...")
    print("👉 OPEN THIS LINK: http://127.0.0.1:5000")
    print("="*40 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=True)