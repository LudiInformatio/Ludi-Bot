# Ludi Lite UI Design & Output Format Prompt

**Copy this entire prompt and send to your local Claude Code agent.**

---

## PROMPT START

You are implementing a UI redesign and output format update for Ludi Lite. Apply the Lo-Fi Premium color palette, PropsMadness-inspired output cards, and a cleaner side-by-side comparison format.

**Repository:** https://github.com/LudiInformatio/Ludi-Lite.git

---

## DESIGN SYSTEM: Lo-Fi Premium Palette

Replace the current cold dark theme with a warmer, more sophisticated palette.

### Color Variables

**File:** `app.py` (CSS section, around line 60)

**Replace current CSS with:**
```python
st.markdown("""
<style>
    /* Lo-Fi Premium Color Palette */
    :root {
        --charcoal: #383531;
        --amber: #C6A34F;
        --stone: #8A867F;
        --paper: #f5f3ed;
        --cream: #FAF8F5;
        --dark-navy: #0F172A;
        --success: #4A7C59;
        --info: #5B7C99;
    }

    /* Dark theme with warm undertones */
    .stApp {
        background-color: var(--charcoal);
    }

    /* Game card styling - Lo-Fi Premium */
    .game-card {
        background: linear-gradient(135deg, #2D2A26 0%, #3D3935 100%);
        border-radius: 12px;
        padding: 15px;
        margin: 8px 0;
        border: 1px solid var(--stone);
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .game-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(198, 163, 79, 0.2);
        border-color: var(--amber);
    }
    .game-card h3 {
        color: var(--paper);
        margin: 0 0 8px 0;
        font-size: 18px;
    }
    .game-card .line {
        color: var(--amber);
        font-weight: bold;
        font-size: 14px;
    }
    .game-card .time {
        color: var(--stone);
        font-size: 12px;
    }

    /* Analysis panels - Warmer tones */
    .freestyle-panel {
        background: linear-gradient(135deg, #2A3441 0%, #344152 100%);
        border: 2px solid var(--info);
        border-radius: 12px;
        padding: 20px;
    }
    .method-panel {
        background: linear-gradient(135deg, #2A3D2E 0%, #344D3A 100%);
        border: 2px solid var(--success);
        border-radius: 12px;
        padding: 20px;
    }

    /* PropsMadness-style stat cards */
    .stat-card {
        background: #2D2A26;
        border: 1px solid var(--stone);
        border-radius: 8px;
        padding: 12px;
        text-align: center;
    }
    .stat-card .label {
        color: var(--stone);
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .stat-card .value {
        color: var(--paper);
        font-size: 24px;
        font-weight: bold;
    }
    .stat-card .subtext {
        color: var(--amber);
        font-size: 12px;
    }

    /* Hit rate indicator */
    .hit-rate {
        display: inline-flex;
        gap: 3px;
    }
    .hit-rate .dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: var(--stone);
    }
    .hit-rate .dot.active {
        background: var(--amber);
    }

    /* Time badge */
    .time-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        background: rgba(198, 163, 79, 0.15);
        color: var(--amber);
        border: 1px solid var(--amber);
    }

    /* Section headers */
    .section-header {
        color: var(--paper);
        font-size: 14px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 1px solid var(--stone);
    }

    /* Mobile responsive */
    @media (max-width: 768px) {
        .game-card {
            padding: 12px;
        }
        .game-card h3 {
            font-size: 16px;
        }
        .stat-card .value {
            font-size: 20px;
        }
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)
```

---

## OUTPUT FORMAT: PropsMadness "Check My Prop" Style

Create a new analysis output format inspired by PropsMadness with brief, scannable cards.

**File:** `ui_components.py`

**Add new rendering function:**
```python
def render_prop_analysis_card(player: str, stat: str, line: float, analysis: dict) -> None:
    """
    Render a PropsMadness-style prop analysis card.

    Args:
        player: Player name
        stat: Stat type (PTS, AST, REB, etc.)
        line: The betting line
        analysis: Dict with hit_rate, l15_avg, h2h_record, defense_rank, verdict
    """
    st.markdown(f"""
    <div style="background: #2D2A26; border-radius: 12px; padding: 20px; border: 1px solid #8A867F;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
            <div>
                <h3 style="color: #f5f3ed; margin: 0;">{player}</h3>
                <span style="color: #8A867F; font-size: 12px;">{stat} | Line: {line}</span>
            </div>
            <div class="time-badge">{analysis.get('verdict', 'LEAN OVER')}</div>
        </div>

        <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 16px;">
            <div class="stat-card">
                <div class="label">L15 Avg</div>
                <div class="value">{analysis.get('l15_avg', 'N/A')}</div>
                <div class="subtext">{analysis.get('l15_min', 'N/A')} min</div>
            </div>
            <div class="stat-card">
                <div class="label">Hit Rate</div>
                <div class="value">{analysis.get('hit_rate', 'N/A')}</div>
                <div class="subtext">{analysis.get('hit_games', '0')}/15 games</div>
            </div>
            <div class="stat-card">
                <div class="label">vs Opp</div>
                <div class="value">{analysis.get('h2h_rate', 'N/A')}</div>
                <div class="subtext">{analysis.get('h2h_games', '0')} games</div>
            </div>
            <div class="stat-card">
                <div class="label">Def Rank</div>
                <div class="value">#{analysis.get('defense_rank', 'N/A')}</div>
                <div class="subtext">vs {stat}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_hit_rate_dots(hits: int, total: int = 15) -> str:
    """Generate HTML for hit rate dot visualization."""
    dots = ""
    for i in range(total):
        if i < hits:
            dots += '<span class="dot active"></span>'
        else:
            dots += '<span class="dot"></span>'
    return f'<div class="hit-rate">{dots}</div>'
```

---

## SIDE-BY-SIDE COMPARISON: Freestyle vs S.A.V.A.G.E.

**File:** `ui_components.py`

**Update `render_analysis_output()` with cleaner comparison format:**
```python
def render_analysis_output(freestyle: str, methodology: str, show_both: bool = True, perplexity_used: bool = False):
    """
    Render analysis output with Lo-Fi Premium styling.
    Brief, scannable format inspired by PropsMadness.
    """
    # Clean leaked instructions
    freestyle = clean_ai_response(freestyle) if freestyle else ""
    methodology = clean_ai_response(methodology) if methodology else ""

    if show_both and freestyle and methodology:
        # Section header
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <span style="color: #8A867F; font-size: 12px; text-transform: uppercase; letter-spacing: 2px;">
                Analysis Comparison
            </span>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            # Freestyle Header
            st.markdown("""
            <div style="background: linear-gradient(135deg, #2A3441 0%, #344152 100%);
                        border: 2px solid #5B7C99; border-radius: 12px; padding: 16px; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                    <span style="font-size: 20px;">🔍</span>
                    <div>
                        <div style="color: #f5f3ed; font-weight: 600;">FREESTYLE</div>
                        <div style="color: #5B7C99; font-size: 11px;">Raw AI Research</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Perplexity badge if used
            if perplexity_used:
                st.markdown("""
                <div style="background: rgba(139, 92, 246, 0.1); border: 1px solid #8B5CF6;
                            border-radius: 6px; padding: 6px 10px; margin-bottom: 12px; display: inline-block;">
                    <span style="color: #A78BFA; font-size: 11px;">⚡ + Perplexity Real-Time</span>
                </div>
                """, unsafe_allow_html=True)

            st.markdown(freestyle)

        with col2:
            # S.A.V.A.G.E. Header
            st.markdown("""
            <div style="background: linear-gradient(135deg, #2A3D2E 0%, #344D3A 100%);
                        border: 2px solid #4A7C59; border-radius: 12px; padding: 16px; margin-bottom: 8px;">
                <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 12px;">
                    <span style="font-size: 20px;">🎯</span>
                    <div>
                        <div style="color: #f5f3ed; font-weight: 600;">S.A.V.A.G.E.</div>
                        <div style="color: #4A7C59; font-size: 11px;">Ludi Methodology</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Methodology badges
            st.markdown("""
            <div style="display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px;">
                <span style="background: rgba(198, 163, 79, 0.15); border: 1px solid #C6A34F;
                            border-radius: 4px; padding: 3px 8px; font-size: 10px; color: #C6A34F;">Usage Vacuum</span>
                <span style="background: rgba(198, 163, 79, 0.15); border: 1px solid #C6A34F;
                            border-radius: 4px; padding: 3px 8px; font-size: 10px; color: #C6A34F;">Archetype</span>
                <span style="background: rgba(198, 163, 79, 0.15); border: 1px solid #C6A34F;
                            border-radius: 4px; padding: 3px 8px; font-size: 10px; color: #C6A34F;">Pace</span>
            </div>
            """, unsafe_allow_html=True)

            st.markdown(methodology)

        # Comparison legend
        st.markdown("""
        <div style="background: #2D2A26; border-radius: 8px; padding: 12px; margin-top: 16px;">
            <div style="color: #8A867F; font-size: 11px; text-align: center;">
                <strong style="color: #5B7C99;">Freestyle</strong> = General AI research |
                <strong style="color: #4A7C59;">S.A.V.A.G.E.</strong> = Usage Vacuum • Archetype vs Scheme • Pace • Blowout Tax • B2B Fatigue
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif methodology:
        # Single panel (Ludi Method only)
        st.markdown("""
        <div style="background: linear-gradient(135deg, #2A3D2E 0%, #344D3A 100%);
                    border: 2px solid #4A7C59; border-radius: 12px; padding: 20px;">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
                <span style="font-size: 24px;">🎯</span>
                <div>
                    <div style="color: #f5f3ed; font-weight: 600; font-size: 18px;">S.A.V.A.G.E. Analysis</div>
                    <div style="color: #4A7C59; font-size: 12px;">Ludi Methodology Applied</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(methodology)
```

---

## HEADER UPDATE: Lo-Fi Premium Branding

**File:** `ui_components.py`

**Update `render_header()` function:**
```python
def render_header():
    """Render app header with Lo-Fi Premium styling."""
    st.markdown("""
    <div style="text-align: center; padding: 20px 0 30px 0;">
        <div style="display: inline-flex; align-items: center; gap: 12px;">
            <span style="font-size: 32px;">🏀</span>
            <div>
                <h1 style="color: #f5f3ed; margin: 0; font-size: 28px; font-weight: 700; letter-spacing: -1px;">
                    Ludi Lite
                </h1>
                <p style="color: #C6A34F; margin: 0; font-size: 12px; text-transform: uppercase; letter-spacing: 2px;">
                    AI Sports Research Lab
                </p>
            </div>
        </div>
        <p style="color: #8A867F; font-size: 13px; margin-top: 12px; font-style: italic;">
            "A Sanctuary from the Noise"
        </p>
    </div>
    """, unsafe_allow_html=True)
```

---

## FOOTER UPDATE: Data Source Badges

**File:** `app.py` (footer section, around line 380)

**Update footer with Lo-Fi Premium styling:**
```python
# Footer with data sources
st.markdown("---")

# Data source badges - Lo-Fi Premium style
st.markdown("""
<div style="text-align: center; margin-bottom: 12px;">
    <span style="background: rgba(91, 124, 153, 0.15); border: 1px solid #5B7C99; border-radius: 4px;
                padding: 4px 10px; margin: 3px; font-size: 10px; color: #5B7C99; display: inline-block;">Claude AI</span>
    <span style="background: rgba(74, 124, 89, 0.15); border: 1px solid #4A7C59; border-radius: 4px;
                padding: 4px 10px; margin: 3px; font-size: 10px; color: #4A7C59; display: inline-block;">Tank01 API</span>
    <span style="background: rgba(198, 163, 79, 0.15); border: 1px solid #C6A34F; border-radius: 4px;
                padding: 4px 10px; margin: 3px; font-size: 10px; color: #C6A34F; display: inline-block;">The-Odds-API</span>
</div>
""", unsafe_allow_html=True)

# Perplexity badge if enabled
if PERPLEXITY_ENABLED:
    st.markdown("""
    <div style="text-align: center; margin-bottom: 12px;">
        <span style="background: rgba(139, 92, 246, 0.15); border: 1px solid #8B5CF6; border-radius: 4px;
                    padding: 4px 10px; font-size: 10px; color: #A78BFA; display: inline-block;">+ Perplexity Search</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("""
<p style="color: #8A867F; font-size: 11px; text-align: center;">
    Ludi Lite | Research Assistant | Not betting advice<br/>
    <span style="font-size: 9px; color: #5A5752;">We reject "AI Slop" in favor of Human Verification</span>
</p>
""", unsafe_allow_html=True)
```

---

## VERIFICATION STEPS

1. **Color check:** Verify amber (#C6A34F) appears on accents, not bright gold
2. **Card styling:** Game cards should have warm charcoal background with stone borders
3. **Analysis panels:** Freestyle = blue-gray tones, S.A.V.A.G.E. = green tones
4. **Comparison format:** Side-by-side with clear headers and methodology badges
5. **Footer:** "A Sanctuary from the Noise" tagline visible

---

## COMMIT MESSAGE

```bash
git add -A
git commit -m "feat: Lo-Fi Premium UI redesign + PropsMadness-style output

UI Changes:
- Replace cold dark theme with warm Lo-Fi Premium palette
- Charcoal (#383531), Amber (#C6A34F), Stone (#8A867F), Paper (#f5f3ed)
- Warmer game cards with amber hover accents
- PropsMadness-inspired stat cards with hit rate dots

Output Format:
- Side-by-side Freestyle vs S.A.V.A.G.E. comparison
- Clear methodology badges (Usage Vacuum, Archetype, Pace)
- Brief, scannable card format
- 'A Sanctuary from the Noise' branding

Inspired by: LandYourBets, PropsMadness, Sharp Hunter

https://claude.ai/code"

git push origin main
```

---

## PROMPT END
