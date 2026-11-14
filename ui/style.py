"""Page styling: the wallpaper loader, the page stylesheet and the audit-table colours."""
import base64
from pathlib import Path


from ui.paths import ASSETS

CSS_FILE = Path(__file__).with_name("page.css")


def get_base64_image(image_path):
    """Base64 payload of an image file (the wallpaper is inlined into the CSS)."""
    with open(image_path, "rb") as handle:
        return base64.b64encode(handle.read()).decode()


def page_css() -> str:
    """The page stylesheet with the wallpaper substituted in.

    Read on every run (a few KB) so CSS edits show up without restarting Streamlit;
    the base64 wallpaper stays out of the file behind the __WALLPAPER__ placeholder.
    """
    wallpaper = get_base64_image(ASSETS / "wallpaper.jpg")
    return CSS_FILE.read_text(encoding="utf-8").replace("__WALLPAPER__", wallpaper)


AUDIT_BLOCKS = {
    "time": {"Time (s)"},
    "desc": {"Active", "Owner", "Action"},
    "reaction": {"Elemental App", "Aura", "Reaction"},
    "stats": {"HP", "ATK", "DEF", "EM", "CR%", "CD%", "CV"},
    "mult": {"Base DMG", "Quills", "Bonus Mult", "Elev Mult", "Crit Mult", "DEF Mult", "Res Mult"},
    "output": {"Average DMG", "Non-Crit DMG", "Crit DMG", "Effective Avg DMG"},
}

# One dark tint per party member: consecutive characters get different row colours.
OWNER_BG = ("#0b3d2e", "#1e3a8a", "#4c1d95", "#7c2d12", "#0f766e", "#831843", "#3f6212", "#1e40af")

def column_block(column):
    """Map an audit-table column to its block (buff = everything not core)."""
    for block, columns in AUDIT_BLOCKS.items():
        if column in columns:
            return block
    return "buff"


def blend_chart(fig):
    """Make a Plotly figure sit on the dark glass panels instead of a white rectangle.

    px.pie / px.bar draw Plotly's plain white canvas by default, which looked like a
    bright block on the wallpaper UI (and its dark tick/label colours were unreadable
    once the card behind it is translucent). Transparent paper/plot + light text keeps
    the series colours untouched.
    """
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e6e8ef"),
        title_font=dict(color="#e6e8ef"),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#e6e8ef")),
        margin=dict(l=12, r=12, t=52, b=12),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.12)",
                     zerolinecolor="rgba(255,255,255,0.20)",
                     linecolor="rgba(255,255,255,0.25)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.12)",
                     zerolinecolor="rgba(255,255,255,0.20)",
                     linecolor="rgba(255,255,255,0.25)")
    return fig


def style_timeline_dataframe(df):
    """Colour-code the audit table for st.dataframe.

    Each party member gets its own dark row tint, so consecutive characters are
    visually separated. Buff cells are muted grey when OFF/0 and highlighted
    green when the effect is active.
    """
    owners = list(dict.fromkeys(df["Owner"].tolist())) if "Owner" in df.columns else []
    owner_bg = {owner: OWNER_BG[i % len(OWNER_BG)] for i, owner in enumerate(owners)}
    columns = list(df.columns)

    def _paint(row):
        background = owner_bg.get(row.get("Owner"), "#111827")
        cells = []
        for column in columns:
            css = [f"background-color: {background}", "color: #f8fafc"]
            if column_block(column) == "buff":
                value = str(row.get(column, "")).strip()
                if value in ("OFF", "0", "", "-", "None", "nan"):
                    css.append("color: #64748b")
                else:
                    css.append("color: #86efac; font-weight: 600")
            cells.append("; ".join(css))
        return cells

    return df.style.apply(_paint, axis=1)
