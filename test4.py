import base64
import re
import subprocess
import sys
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from lxml import etree as et
from streamlit_sortables import sort_items


# ============================================================
# STREAMLIT PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="NWC Clash Test XML Generator",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Granger brand orange — rgb(237, 116, 60) / shading rgb(216, 84, 20)
BRAND_ORANGE = "#ed743c"
BRAND_ORANGE_SHADE = "#d85414"
BRAND_ORANGE_LIGHT = "#fff0e8"
BRAND_ORANGE_MUTED = "#fde8dc"
BRAND_ORANGE_BORDER = "#f5c4a8"
BRAND_ORANGE_TEXT = "#7c2d12"
BRAND_ORANGE_GRADIENT = (
    f"linear-gradient(135deg, {BRAND_ORANGE_SHADE} 0%, {BRAND_ORANGE} 55%, #f09062 100%)"
)
BRAND_ORANGE_GRADIENT_HOVER = (
    f"linear-gradient(135deg, {BRAND_ORANGE} 0%, #f09062 100%)"
)
# Drag-and-drop trade columns — light chrome only (items stay brand orange)
SORTABLE_BOX_BG = "#fff8f4"
SORTABLE_BOX_BORDER = "#fad4bc"
SORTABLE_HEADER_BG = "#fff0e8"
SORTABLE_HEADER_TEXT = "#9a4a2a"

# Injected into streamlit-sortables iframe (global page CSS cannot reach it)
SORTABLE_BRAND_STYLE = f"""
.sortable-component.vertical .sortable-container {{
    padding: 0.65rem !important;
    margin: 0.4rem 0.35rem !important;
}}
.sortable-container {{
    background-color: {SORTABLE_BOX_BG} !important;
    border: 1px solid {SORTABLE_BOX_BORDER} !important;
    border-radius: 14px !important;
    overflow: visible !important;
    padding: 0.55rem !important;
    box-sizing: border-box !important;
}}
.sortable-container-header {{
    background: linear-gradient(180deg, #ffffff 0%, {SORTABLE_HEADER_BG} 100%) !important;
    color: {SORTABLE_HEADER_TEXT} !important;
    font-weight: 600 !important;
    padding: 0.55rem 0.85rem !important;
    margin: 0 0 0.45rem 0 !important;
    border-radius: 10px !important;
    border: 1px solid {SORTABLE_BOX_BORDER} !important;
    cursor: help !important;
}}
.sortable-container-body {{
    background-color: {SORTABLE_BOX_BG} !important;
    border: 1px solid {SORTABLE_BOX_BORDER} !important;
    border-radius: 10px !important;
    padding: 0.5rem 0.45rem !important;
    margin: 0 !important;
    min-height: 52px !important;
    box-sizing: border-box !important;
}}
.sortable-item, .sortable-item:hover {{
    background-color: {BRAND_ORANGE} !important;
    color: #ffffff !important;
    border: 1px solid {BRAND_ORANGE_SHADE} !important;
    border-radius: 8px !important;
    margin: 0.35rem 0.2rem !important;
    padding: 0.45rem 0.55rem !important;
    box-sizing: border-box !important;
}}
.sortable-item:active {{
    background-color: {BRAND_ORANGE_SHADE} !important;
}}
"""


def inject_app_styles():
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&display=swap');

        html, body, [class*="css"] {
            font-family: 'DM Sans', system-ui, -apple-system, sans-serif;
        }

        .block-container {
            padding-top: 4.5rem;
            padding-bottom: 2.5rem;
            max-width: 1180px;
        }

        /* Clear Streamlit top header so first widgets are not covered */
        [data-testid="stAppViewContainer"] section.main > div {
            padding-top: 0.5rem;
        }
        header[data-testid="stHeader"] {
            z-index: 999;
        }

        /* Hero */
        .nw-hero {
            background: linear-gradient(135deg, #d85414 0%, #ed743c 55%, #f09062 100%);
            border-radius: 14px;
            padding: 1.1rem 1.35rem 1.05rem;
            margin-bottom: 1.25rem;
            color: #f8fafc;
            box-shadow: 0 8px 24px rgba(216, 84, 20, 0.22);
            overflow: hidden;
        }
        .nw-hero-layout {
            display: flex;
            align-items: center;
            gap: 1.15rem;
        }
        .nw-hero-brand {
            flex: 0 0 auto;
        }
        .nw-hero-brand img {
            display: block;
            max-height: 72px;
            max-width: min(280px, 42vw);
            width: auto;
            height: auto;
            object-fit: contain;
            /* Render transparent/dark logo as white on orange hero */
            filter: brightness(0) invert(1)
                drop-shadow(0 2px 8px rgba(0, 0, 0, 0.25));
        }
        .nw-hero-body {
            flex: 1 1 240px;
            min-width: 0;
        }
        .nw-hero-body h1 {
            font-size: 1.65rem;
            font-weight: 700;
            margin: 0 0 0.35rem 0;
            letter-spacing: -0.02em;
            color: #ffffff;
            line-height: 1.2;
        }
        .nw-hero-body p {
            margin: 0;
            font-size: 0.95rem;
            opacity: 0.92;
            line-height: 1.45;
            color: #e2e8f0;
        }
        @media (max-width: 720px) {
            .nw-hero-layout {
                flex-wrap: wrap;
            }
            .nw-hero-brand {
                width: 100%;
            }
            .nw-hero-brand img {
                max-height: 56px;
            }
        }

        /* Workflow strip */
        .nw-flow {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin: 0 0 1.35rem 0;
        }
        .nw-flow-step {
            flex: 1 1 140px;
            background: #f1f5f9;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 0.55rem 0.75rem;
            font-size: 0.78rem;
            color: #475569;
            line-height: 1.3;
        }
        .nw-flow-step strong {
            display: block;
            color: #d85414;
            font-size: 0.82rem;
            margin-bottom: 0.15rem;
        }

        /* Step section cards */
        .nw-step-head {
            display: flex;
            align-items: flex-start;
            gap: 0.85rem;
            margin: 0.25rem 0 0.85rem 0;
        }
        .nw-step-badge {
            flex-shrink: 0;
            width: 2.1rem;
            height: 2.1rem;
            border-radius: 10px;
            background: linear-gradient(145deg, #d85414, #ed743c);
            color: #fff;
            font-weight: 700;
            font-size: 1rem;
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 2px 8px rgba(216, 84, 20, 0.35);
        }
        .nw-step-title {
            font-size: 1.2rem;
            font-weight: 700;
            color: #0f172a;
            margin: 0;
            line-height: 1.25;
        }
        .nw-step-desc {
            font-size: 0.88rem;
            color: #64748b;
            margin: 0.2rem 0 0 0;
            line-height: 1.45;
        }

        .nw-tip {
            background: #fff0e8;
            border-left: 4px solid #ed743c;
            border-radius: 0 8px 8px 0;
            padding: 0.65rem 0.9rem;
            font-size: 0.86rem;
            color: #334155;
            margin-bottom: 0.85rem;
        }

        /* Matrix */
        .nw-matrix-wrap {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 0.75rem 0.5rem 0.5rem;
            margin: 0.5rem 0 1rem;
        }
        .nw-matrix-corner {
            font-size: 0.75rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }
        .nw-matrix-col {
            font-size: 0.72rem;
            font-weight: 600;
            color: #7c2d12;
            text-align: center;
            padding: 0.35rem 0.15rem;
            background: #fde8dc;
            border-radius: 6px;
            line-height: 1.2;
            min-height: 2.2rem;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        /* Matrix column toggle buttons (Step 3 headers) */
        .nw-matrix-wrap + div [data-testid="stHorizontalBlock"] [data-testid="stButton"] button {
            font-size: 0.72rem !important;
            font-weight: 600 !important;
            min-height: 2.2rem !important;
            border-radius: 8px !important;
            padding: 0.35rem 0.5rem !important;
        }
        .nw-matrix-row-label {
            font-size: 0.78rem;
            font-weight: 600;
            color: #334155;
            padding: 0.25rem 0;
        }

        /* Sortables layout only — item/header colors use SORTABLE_BRAND_STYLE on sort_items() */
        div[data-testid="stVerticalBlock"] div[class*="sortable"] {
            width: 100%;
        }
        div[class*="sortable-container"],
        div[class*="sortableContainer"],
        div[class*="SortableContainer"] {
            min-width: 260px !important;
            max-width: 260px !important;
            width: 260px !important;
            box-shadow: 0 2px 8px rgba(216, 84, 20, 0.14) !important;
        }
        div[class*="sortable-item"],
        div[class*="sortableItem"],
        div[class*="SortableItem"] {
            width: 100% !important;
            box-sizing: border-box !important;
            overflow-wrap: anywhere !important;
            border-radius: 6px !important;
        }
        div[class*="sortable"] {
            gap: 1rem !important;
            align-items: flex-start !important;
            padding: 0.20rem 0 !important;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%);
        }
        section[data-testid="stSidebar"] .block-container {
            padding-top: 1rem;
        }
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3 {{
            color: {BRAND_ORANGE_SHADE};
        }}

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 0.5rem 0.65rem;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
        }

        hr {
            margin: 1.75rem 0 !important;
            border-color: #e2e8f0 !important;
        }

        /* Space above tab bar (keeps tabs below Streamlit header) */
        .nw-tab-bar-anchor {
            display: block;
            min-height: 1.5rem;
            margin-top: 0.5rem;
            margin-bottom: 0.25rem;
            padding-top: 0.5rem;
        }
        .nw-app-mode-label {
            font-size: 0.8rem;
            font-weight: 600;
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin: 0 0 0.5rem 0;
        }

        /* Main app tabs (Generate / Modify) */
        div[data-testid="stTabs"] {
            position: relative;
            z-index: 50;
            margin-top: 0.25rem !important;
            margin-bottom: 1.75rem !important;
            padding: 0.85rem 0.65rem 0.65rem !important;
            background-color: #ffffff !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 14px rgba(15, 39, 68, 0.1) !important;
            min-height: 3.25rem !important;
        }
        div[data-testid="stTabs"] > div {
            overflow: visible !important;
        }
        div[data-testid="stTabs"] [role="tablist"],
        div[data-testid="stTabs"] [data-baseweb="tab-list"] {
            gap: 0.5rem !important;
            border-bottom: none !important;
            min-height: 2.5rem !important;
            overflow: visible !important;
        }
        div[data-testid="stTabs"] button[role="tab"],
        div[data-testid="stTabs"] button[data-baseweb="tab"] {
            color: #d85414 !important;
            background-color: #f1f5f9 !important;
            border: 1px solid #94a3b8 !important;
            border-radius: 8px !important;
            font-weight: 700 !important;
            font-size: 1rem !important;
            padding: 0.55rem 1.5rem !important;
            min-height: 2.25rem !important;
            opacity: 1 !important;
            visibility: visible !important;
            z-index: 51 !important;
        }
        div[data-testid="stTabs"] button[role="tab"]:hover,
        div[data-testid="stTabs"] button[data-baseweb="tab"]:hover {
            color: #d85414 !important;
            background-color: #fff0e8 !important;
        }
        div[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
        div[data-testid="stTabs"] button[aria-selected="true"],
        div[data-testid="stTabs"] button[data-baseweb="tab"][aria-selected="true"] {
            color: #ffffff !important;
            background: linear-gradient(135deg, #d85414 0%, #ed743c 55%, #f09062 100%) !important;
            border-color: #d85414 !important;
        }
        div[data-testid="stTabs"] button p,
        div[data-testid="stTabs"] button span,
        div[data-testid="stTabs"] button div,
        div[data-testid="stTabs"] [data-testid="stMarkdownContainer"],
        div[data-testid="stTabs"] [data-testid="stMarkdownContainer"] p {
            color: inherit !important;
            opacity: 1 !important;
            visibility: visible !important;
            font-weight: inherit !important;
        }

        /* Tab panel content sits below the tab bar */
        div[data-testid="stTabs"] ~ div[data-testid="stVerticalBlock"],
        div[data-testid="stTabs"] + div {
            padding-top: 0.75rem !important;
        }

        /* Brand-orange actions: Generate XML + download buttons (markers in markup below each widget) */
        div[data-testid="stVerticalBlock"]:has(.nw-gen-xml-marker) [data-testid="stButton"] > button,
        div[data-testid="stVerticalBlock"]:has(.nw-download-csv-marker) [data-testid="stDownloadButton"] > button,
        div[data-testid="stVerticalBlock"]:has(.nw-download-xml-marker) [data-testid="stDownloadButton"] > button,
        div[data-testid="column"]:has(.nw-download-xml-marker) [data-testid="stDownloadButton"] > button {
            background: linear-gradient(135deg, #d85414 0%, #ed743c 55%, #f09062 100%) !important;
            border-color: #d85414 !important;
            color: #ffffff !important;
        }
        div[data-testid="stVerticalBlock"]:has(.nw-gen-xml-marker) [data-testid="stButton"] > button:hover,
        div[data-testid="stVerticalBlock"]:has(.nw-download-csv-marker) [data-testid="stDownloadButton"] > button:hover,
        div[data-testid="stVerticalBlock"]:has(.nw-download-xml-marker) [data-testid="stDownloadButton"] > button:hover,
        div[data-testid="column"]:has(.nw-download-xml-marker) [data-testid="stDownloadButton"] > button:hover {
            background: linear-gradient(135deg, #ed743c 0%, #f09062 100%) !important;
            border-color: #ed743c !important;
            color: #ffffff !important;
        }
        div[data-testid="stVerticalBlock"]:has(.nw-gen-xml-marker) [data-testid="stButton"] > button:active,
        div[data-testid="stVerticalBlock"]:has(.nw-download-csv-marker) [data-testid="stDownloadButton"] > button:active,
        div[data-testid="stVerticalBlock"]:has(.nw-download-xml-marker) [data-testid="stDownloadButton"] > button:active,
        div[data-testid="column"]:has(.nw-download-xml-marker) [data-testid="stDownloadButton"] > button:active {
            background: #d85414 !important;
            border-color: #d85414 !important;
        }

        /* Targets the actual checkbox input */
            input[type="checkbox"] {
                accent-color: #ed743c;
            }
            
            /* Optional: Targets the span element for specific Streamlit versions */
            span:has(+input[type="checkbox"]) {
                background-color: #ed743c !important;
            }


        



        </style>
        """,
        unsafe_allow_html=True,
    )


APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = APP_DIR / "assets"
HEADER_LOGO_NAME = "Granger Construction - VDC - Transparent"
_HEADER_IMAGE_EXTS = (".png", ".svg", ".jpg", ".jpeg", ".webp", ".gif")


def resolve_header_logo() -> Path | None:
    """Granger VDC logo in assets/ (any common image extension)."""
    for ext in _HEADER_IMAGE_EXTS:
        candidate = ASSETS_DIR / f"{HEADER_LOGO_NAME}{ext}"
        if candidate.is_file():
            return candidate
    return None


def _header_image_data_uri(path: Path) -> str | None:
    """Embed a local image for use in the HTML hero (png, jpg, svg, webp)."""
    if not path.is_file():
        return None
    suffix = path.suffix.lower()
    mime_by_suffix = {
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }
    mime = mime_by_suffix.get(suffix)
    if not mime:
        return None
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _hero_img_html(path: Path, *, css_class: str, alt: str) -> str:
    uri = _header_image_data_uri(path)
    if not uri:
        return ""
    return f'<img class="{css_class}" src="{uri}" alt="{alt}" />'


def render_app_header(
    title: str = "NWC Clash Test XML Generator",
    subtitle: str | None = None,
):
    if subtitle is None:
        subtitle = (
            "Load Navisworks cache file names, correct trades and levels, pick which disciplines clash, "
            "then export a ready-to-import clash XML — or upload existing XML in the Modify tab."
        )

    logo_path = resolve_header_logo()
    logo_html = (
        _hero_img_html(
            logo_path,
            css_class="nw-hero-logo",
            alt="Granger Construction VDC",
        )
        if logo_path
        else ""
    )

    st.markdown(
        f"""
        <div class="nw-hero">
            <div class="nw-hero-layout">
                <div class="nw-hero-brand">{logo_html}</div>
                <div class="nw-hero-body">
                    <h1>{title}</h1>
                    <p>{subtitle}</p>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_workflow_strip():
    st.markdown(
        """
        <div class="nw-flow">
            <div class="nw-flow-step"><strong>1 · Input</strong>Add .nwc names in the sidebar</div>
            <div class="nw-flow-step"><strong>2 · Trades</strong>Drag files between trade groups</div>
            <div class="nw-flow-step"><strong>3 · Levels</strong>Fix floor assignments</div>
            <div class="nw-flow-step"><strong>4 · Matrix</strong>Choose discipline pairs</div>
            <div class="nw-flow-step"><strong>5 · Export</strong>Preview, CSV, and XML</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_step_header(step_number: int, title: str, description: str):
    st.markdown(
        f"""
        <div class="nw-step-head">
            <div class="nw-step-badge">{step_number}</div>
            <div>
                <p class="nw-step-title">{title}</p>
                <p class="nw-step-desc">{description}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tip(text: str):
    st.markdown(f'<div class="nw-tip">{text}</div>', unsafe_allow_html=True)



# ============================================================
# XML SETTINGS
# ============================================================

PROJECT_NAME = "Auto Clash Test Generator"
UNITS = "ft"
AUTO_SET_FOLDER = "_AUTO_CLASH_INPUTS"

# 1 inch tolerance in feet
DEFAULT_TOLERANCE = "0.0833333"
DEFAULT_TEST_TYPE = "hard"


# ============================================================
# EXAMPLE FILE NAMES
# Later these can come from upload, ACC, SharePoint, etc.
# ============================================================

default_files_text = """LSN_L1_ARCH_MODEL.nwc
LSN_L1_STR_MODEL.nwc
LSN_L1_MECH_MODEL.nwc
LSN_L1_ELEC_MODEL.nwc
LSN_L1_PLUMB_MODEL.nwc
LSN_L1_POOL_MODEL.nwc
LSN_L2_ARCH_MODEL.nwc
LSN_L2_STR_MODEL.nwc
LSN_L2_MECH_MODEL.nwc
LSN_L2_ELEC_MODEL.nwc
LSN_L2_PLUMB_MODEL.nwc
LSN_BS_ARCH_MODEL.nwc
LSN_BS_MECH_MODEL.nwc
LSN_BS_ELEC_MODEL.nwc
LSN_BS_PLUMB_MODEL.nwc
LSN_PH_ARCH_MODEL.nwc
LSN_PH_MECH_MODEL.nwc
LSN_L1_UNKNOWN_MODEL.nwc
LSN_AE_ARCH_MODEL.nwc
LSN_AE_MECH_MODEL.nwc
"""


# ============================================================
# FOLDER → FILE NAME LIST HELPERS
# ============================================================

def browse_for_folder_tk():
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.wm_attributes("-topmost", 1)
    root.update_idletasks()
    root.update()
    folder = filedialog.askdirectory(parent=root, mustexist=True)
    root.update()
    root.destroy()
    return folder or ""


def browse_for_folder_powershell():
    """Windows folder dialog in a separate process (works better with Streamlit)."""
    script = (
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$d = New-Object System.Windows.Forms.FolderBrowserDialog; "
        "$d.Description = 'Select a folder with NWC files'; "
        "$d.ShowNewFolderButton = $true; "
        "if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { "
        "  [Console]::Out.Write($d.SelectedPath) "
        "}"
    )
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-STA", "-Command", script],
        capture_output=True,
        text=True,
        creationflags=creationflags,
    )
    if result.returncode != 0 and not result.stdout.strip():
        err = (result.stderr or "").strip()
        raise RuntimeError(err or "PowerShell folder dialog failed.")
    return result.stdout.strip()


def browse_for_folder():
    """
    Open a local folder picker. Returns (path, error_message).
    error_message is None on success (path may still be "" if user cancelled).
    """
    if sys.platform == "win32":
        try:
            return browse_for_folder_powershell(), None
        except Exception as ps_err:
            try:
                return browse_for_folder_tk(), None
            except Exception as tk_err:
                return "", f"Could not open folder picker: {ps_err}; {tk_err}"

    try:
        return browse_for_folder_tk(), None
    except Exception as exc:
        return "", f"Could not open folder picker: {exc}"


def on_browse_folder(slot):
    """Streamlit callback — runs before widgets sync so the path field updates."""
    picked, err = browse_for_folder()
    msg_key = f"browse_msg_{slot}"
    path_key = f"folder_path_{slot}"
    if err:
        st.session_state[msg_key] = err
    elif picked:
        st.session_state[path_key] = picked
        st.session_state[msg_key] = ""
    else:
        st.session_state[msg_key] = "Folder selection cancelled."


def list_nwc_names_in_folder(folder_path, include_subfolders=False):
    path = Path(folder_path.strip())
    if not folder_path.strip():
        return None, "Enter a folder path first."
    if not path.exists():
        return None, f"Folder not found: {path}"
    if not path.is_dir():
        return None, f"Not a folder: {path}"

    if include_subfolders:
        files = sorted(
            p.name
            for p in path.rglob("*")
            if p.is_file() and p.suffix.lower() == ".nwc"
        )
    else:
        files = sorted(
            p.name
            for p in path.iterdir()
            if p.is_file() and p.suffix.lower() == ".nwc"
        )

    # Deduplicate while preserving order
    seen = set()
    unique = []
    for name in files:
        if name not in seen:
            seen.add(name)
            unique.append(name)
    return unique, None


def append_lines_to_file_list(existing_text, new_names):
    lines = [line.strip() for line in existing_text.splitlines() if line.strip()]
    known = set(lines)
    added = 0
    for name in new_names:
        if name not in known:
            lines.append(name)
            known.add(name)
            added += 1
    return "\n".join(lines), added


# ============================================================
# TRADE DETECTION
# ============================================================

trade_map = {
    "ARCH": "Architecture",
    "AR": "Architecture",
    "A": "Architecture",

    "STR": "Structure",
    "STRUCT": "Structure",
    "S": "Structure",

    "MECH": "Mechanical",
    "MECHANICAL": "Mechanical",
    "M": "Mechanical",

    "ELEC": "Electrical",
    "ELECTRICAL": "Electrical",
    "E": "Electrical",

    "PLUMB": "Plumbing",
    "PLUMBING": "Plumbing",
    "P": "Plumbing",

    "FIRE": "Fire Protection",
    "FP": "Fire Protection",
    "FIREPROTECTION": "Fire Protection",
}


def clean_auto_trade_name(trade_code: str) -> str:
    """Convert unknown trade abbreviation into a readable trade name."""
    trade_code = trade_code.strip().upper()

    manual_clean_names = {
        "LOWVOLTAGE": "Low Voltage",
        "LOW_VOLTAGE": "Low Voltage",
        "FIREALARM": "Fire Alarm",
        "FIRE_ALARM": "Fire Alarm",
        "MEDGAS": "Medical Gas",
        "MED_GAS": "Medical Gas",
    }

    if trade_code in manual_clean_names:
        return manual_clean_names[trade_code]

    return trade_code.replace("-", " ").replace("_", " ").title()


ALL_LEVELS = "All Levels"


def normalize_level_token(token: str) -> str:
    token = token.upper().strip()
    token = token.replace("-", "")
    token = token.replace(" ", "")
    return token


def get_stem_parts(filename: str) -> list[str]:
    name = filename.replace(".nwc", "").replace(".NWC", "")
    return name.split("_")


def resolve_trade_code(trade_code: str) -> str:
    """Readable trade label (optional display); detection uses file tokens."""
    trade_code = trade_code.upper().strip()
    if trade_code in trade_map:
        return trade_map[trade_code]
    return clean_auto_trade_name(trade_code)


UNASSIGNED_TRADE = "UNASSIGNED"


def extract_trade_token_from_filename(filename: str) -> str:
    """Trade segment exactly as it appears in the file name (uppercase)."""
    parts = get_stem_parts(filename)
    if len(parts) < 2:
        return UNASSIGNED_TRADE

    if part_is_ae_marker(parts[1]):
        if len(parts) >= 3 and parts[1].upper() == "AE":
            return f"{parts[1]}_{parts[2]}".upper()
        return parts[1].upper()

    if len(parts) >= 3:
        level_at_two = level_from_token(parts[1])
        if level_at_two != "Unknown":
            return parts[2].upper()
        level_at_three = level_from_token(parts[2])
        if level_at_three != "Unknown":
            return parts[1].upper()

    if len(parts) >= 2:
        return parts[1].upper()

    return UNASSIGNED_TRADE


def part_is_ae_marker(part: str) -> bool:
    u = part.upper().strip()
    return u == "AE" or u.startswith("AE") or "AE-" in u


def trade_from_ae_parts(parts: list[str]) -> str:
    """AE trade token(s) after prefix — general model, no floor in file name."""
    if len(parts) >= 3 and parts[1].upper() == "AE":
        return clean_auto_trade_name(f"{parts[1]}_{parts[2]}")
    return resolve_trade_code(parts[1])


def level_from_token(token: str) -> str:
    """Parse one underscore segment as a level (L1, BS, LEVEL2, etc.)."""
    part = normalize_level_token(token)

    if part in ["BASEMENT", "BSMT", "BS", "B"]:
        return "Basement"
    if part in ["B1", "B01"]:
        return "B1"
    if part in ["B2", "B02"]:
        return "B2"
    if part in ["LOWERLEVEL", "LOWER", "LL"]:
        return "Lower Level"
    if part in ["GROUND", "G", "GF", "GROUNDFLOOR"]:
        return "Ground Floor"
    if part in ["PENTHOUSE", "PH"]:
        return "Penthouse"
    if part in ["MECHANICALPENTHOUSE", "MPH", "MECHPH"]:
        return "Mechanical Penthouse"
    if part in ["ROOF", "RF"]:
        return "Roof"
    if part.startswith("LEVEL"):
        number_part = part.replace("LEVEL", "")
        if number_part.isdigit():
            return f"Level {int(number_part)}"
    if part.startswith("L") and len(part) > 1:
        number_part = part.replace("L", "")
        if number_part.isdigit():
            return f"Level {int(number_part)}"
    if part.isdigit():
        number = int(part)
        if 1 <= number <= 50:
            return f"Level {number}"

    return "Unknown"


def scan_parts_for_level(parts: list[str]) -> str:
    """Fallback: find the first level-like token anywhere after the prefix."""
    for token in parts[1:]:
        level = level_from_token(token)
        if level != "Unknown":
            return level
    return "Unknown"


def detect_trade_and_level(filename: str) -> tuple[str, str]:
    """
    File name rules (underscore-separated):

    Non-AE:  PREFIX_LEVEL_TRADE_...   e.g. LSN_L1_ARCH_MODEL.nwc → trade ARCH
    AE:      PREFIX_AE[_TRADE]_...    e.g. LSN_AE_ARCH_MODEL.nwc → trade AE_ARCH
    """
    parts = get_stem_parts(filename)
    trade = extract_trade_token_from_filename(filename)

    if trade == UNASSIGNED_TRADE or len(parts) < 2:
        return UNASSIGNED_TRADE, "Unknown"

    if part_is_ae_marker(parts[1]):
        return trade, ALL_LEVELS

    if len(parts) >= 3:
        level_at_two = level_from_token(parts[1])
        if level_at_two != "Unknown":
            return trade, level_at_two

        level_at_three = level_from_token(parts[2])
        if level_at_three != "Unknown":
            return trade, level_at_three

    if len(parts) >= 2:
        return trade, scan_parts_for_level(parts)

    return UNASSIGNED_TRADE, "Unknown"


def detect_trade(filename: str) -> str:
    trade, _ = detect_trade_and_level(filename)
    return trade


# ============================================================
# LEVEL OPTIONS
# ============================================================

level_options = [
    "Unknown",
    ALL_LEVELS,
    "Basement",
    "B2",
    "B1",
    "Lower Level",
    "Ground Floor",
    "Level 1",
    "Level 2",
    "Level 3",
    "Level 4",
    "Level 5",
    "Level 6",
    "Level 7",
    "Level 8",
    "Level 9",
    "Level 10",
    "Penthouse",
    "Mechanical Penthouse",
    "Roof",
]


def detect_level(filename: str) -> str:
    """Detect level from file name (see detect_trade_and_level)."""
    _, level = detect_trade_and_level(filename)
    return level


def merge_level_dropdown_choices(base_list, *extra_iterables):
    """Keep standard order first, then append any other levels alphabetically."""
    seen = set()
    out = []

    for x in base_list:
        if x not in seen:
            seen.add(x)
            out.append(x)

    extras = set()
    for it in extra_iterables:
        extras |= set(it)

    for x in sorted(extras - seen, key=lambda s: s.lower()):
        out.append(x)

    return out


# ============================================================
# XML GENERATOR FUNCTIONS
# ============================================================

def make_safe_key(text: str) -> str:
    """
    Create a safe internal name for search sets.

    The actual NWC file name is still preserved in the XML search condition.
    """
    stem = Path(text).stem
    safe = re.sub(r"[^A-Za-z0-9_]+", "_", stem)
    safe = re.sub(r"_+", "_", safe).strip("_")

    if not safe:
        safe = "MODEL"

    return safe.upper()


def make_unique_keys(files):
    """
    Build a dictionary:
    safe internal set name -> actual NWC file name

    Handles duplicate stems by adding _2, _3, etc.
    """
    models = {}
    used = {}

    for file_name in files:
        base_key = make_safe_key(file_name)

        if base_key not in used:
            used[base_key] = 1
            key = base_key
        else:
            used[base_key] += 1
            key = f"{base_key}_{used[base_key]}"

        models[key] = file_name

    return models


def add_file_search_set(parent, set_name, nwc_file_name):
    """
    Creates a Navisworks search set that selects everything
    from a specific NWC file name.
    """
    selectionset = et.SubElement(
        parent,
        "selectionset",
        {
            "name": set_name,
            "guid": str(uuid.uuid4())
        }
    )

    findspec = et.SubElement(
        selectionset,
        "findspec",
        {
            "mode": "all",
            "disjoint": "0"
        }
    )

    conditions = et.SubElement(findspec, "conditions")

    condition = et.SubElement(
        conditions,
        "condition",
        {
            "test": "contains",
            "flags": "10"
        }
    )

    prop = et.SubElement(condition, "property")
    prop_name = et.SubElement(
        prop,
        "name",
        {
            "internal": "LcOaPartitionFilename"
        }
    )
    prop_name.text = "File Name"

    value = et.SubElement(condition, "value")
    data = et.SubElement(
        value,
        "data",
        {
            "type": "wstring"
        }
    )
    data.text = nwc_file_name

    locator = et.SubElement(findspec, "locator")
    locator.text = "/"


def add_clash_test(
    parent,
    test_name,
    left_set_name,
    right_set_name,
    test_type=DEFAULT_TEST_TYPE,
    tolerance=DEFAULT_TOLERANCE
):
    """Creates one Navisworks clash test using two search sets."""

    clashtest = et.SubElement(
        parent,
        "clashtest",
        {
            "name": test_name,
            "test_type": test_type,
            "status": "new",
            "tolerance": str(tolerance),
            "merge_composites": "0"
        }
    )

    et.SubElement(clashtest, "linkage", {"mode": "none"})

    left = et.SubElement(clashtest, "left")
    left_selection = et.SubElement(
        left,
        "clashselection",
        {
            "selfintersect": "0",
            "primtypes": "1"
        }
    )

    left_locator = et.SubElement(left_selection, "locator")
    left_locator.text = f"lcop_selection_set_tree/{AUTO_SET_FOLDER}/{left_set_name}"

    right = et.SubElement(clashtest, "right")
    right_selection = et.SubElement(
        right,
        "clashselection",
        {
            "selfintersect": "0",
            "primtypes": "1"
        }
    )

    right_locator = et.SubElement(right_selection, "locator")
    right_locator.text = f"lcop_selection_set_tree/{AUTO_SET_FOLDER}/{right_set_name}"

    et.SubElement(clashtest, "rules")


def generate_navisworks_xml_bytes(
    models,
    test_pairs,
    project_name,
    test_type,
    tolerance,
):
    """
    Generate Navisworks clash XML and return it as bytes.

    models format:
        {
            "SAFE_SET_NAME": "Actual_File_Name.nwc"
        }

    test_pairs format:
        [
            ("Test Name", "SAFE_LEFT_SET_NAME", "SAFE_RIGHT_SET_NAME")
        ]
    """
    qnmAtt = et.QName(
        "http://www.w3.org/2001/XMLSchema-instance",
        "noNamespaceSchemaLocation"
    )

    root = et.Element(
        "exchange",
        {
            qnmAtt: "http://download.autodesk.com/us/navisworks/schemas/nw-exchange-12.0.xsd"
        },
        units=UNITS,
        filename="",
        filepath=""
    )

    batchtest = et.SubElement(
        root,
        "batchtest",
        {
            "name": project_name,
            "internal_name": project_name,
            "units": UNITS
        }
    )

    clashtests = et.SubElement(batchtest, "clashtests")

    for test_name, left_key, right_key in test_pairs:
        if left_key not in models:
            raise ValueError(f"Missing model key for Selection A: {left_key}")

        if right_key not in models:
            raise ValueError(f"Missing model key for Selection B: {right_key}")

        add_clash_test(
            parent=clashtests,
            test_name=test_name,
            left_set_name=left_key,
            right_set_name=right_key,
            test_type=test_type,
            tolerance=tolerance
        )

    selectionsets = et.SubElement(batchtest, "selectionsets")

    auto_folder = et.SubElement(
        selectionsets,
        "viewfolder",
        {
            "name": AUTO_SET_FOLDER,
            "guid": str(uuid.uuid4())
        }
    )

    for set_name, nwc_file_name in models.items():
        add_file_search_set(
            parent=auto_folder,
            set_name=set_name,
            nwc_file_name=nwc_file_name
        )

    xml_data = et.tostring(
        root,
        pretty_print=True,
        encoding="UTF-8",
        xml_declaration=True
    )

    return xml_data


# ============================================================
# XML IMPORT (MODIFY TAB)
# ============================================================


def _locator_set_name(locator_text: str | None) -> str | None:
    if not locator_text:
        return None
    prefix = f"lcop_selection_set_tree/{AUTO_SET_FOLDER}/"
    text = locator_text.strip()
    if text.startswith(prefix):
        return text[len(prefix) :]
    return None


def _search_set_nwc_file(selectionset) -> str:
    for data in selectionset.findall(".//data[@type='wstring']"):
        if data.text and data.text.strip():
            return data.text.strip()
    return ""


def parse_clash_test_label(test_name: str) -> tuple[str, str, str]:
    """Return level, trade_a, trade_b from clash test name."""
    name = re.sub(r"^\d{3}_", "", (test_name or "").strip())
    if " - " in name and " vs " in name:
        level, rest = name.split(" - ", 1)
        trade_a, trade_b = rest.split(" vs ", 1)
        return level.strip(), trade_a.strip(), trade_b.strip()
    return ALL_LEVELS, "", ""


def parse_navisworks_xml_bytes(xml_bytes: bytes) -> dict:
    """Reverse of generate_navisworks_xml_bytes for the Modify tab."""
    root = et.fromstring(xml_bytes)
    batchtest = root.find(".//batchtest")
    if batchtest is None:
        raise ValueError("Invalid Navisworks XML: missing batchtest element.")

    models: dict[str, str] = {}
    for folder in batchtest.findall(f".//viewfolder[@name='{AUTO_SET_FOLDER}']"):
        for sel in folder.findall("selectionset"):
            set_name = sel.get("name")
            nwc = _search_set_nwc_file(sel)
            if set_name and nwc:
                models[set_name] = nwc

    if not models:
        for sel in batchtest.findall(".//selectionset"):
            set_name = sel.get("name")
            nwc = _search_set_nwc_file(sel)
            if set_name and nwc:
                models[set_name] = nwc

    clash_rows = []
    test_type = DEFAULT_TEST_TYPE
    tolerance = DEFAULT_TOLERANCE

    for ct in batchtest.findall(".//clashtest"):
        test_name = ct.get("name") or ""
        test_type = ct.get("test_type") or test_type
        tolerance = ct.get("tolerance") or tolerance

        left_loc = ct.find("./left/clashselection/locator")
        right_loc = ct.find("./right/clashselection/locator")
        left_set = _locator_set_name(left_loc.text if left_loc is not None else None)
        right_set = _locator_set_name(right_loc.text if right_loc is not None else None)
        if not left_set or not right_set:
            continue

        file_a = models.get(left_set, "")
        file_b = models.get(right_set, "")
        level, trade_a, trade_b = parse_clash_test_label(test_name)
        if not trade_a and file_a:
            trade_a = extract_trade_token_from_filename(file_a)
        if not trade_b and file_b:
            trade_b = extract_trade_token_from_filename(file_b)

        clash_rows.append(
            {
                "Clash Test Name": test_name,
                "Level": level,
                "Trade A": trade_a,
                "Trade B": trade_b,
                "File A": file_a,
                "File B": file_b,
                "Left Set": left_set,
                "Right Set": right_set,
            }
        )

    return {
        "project_name": batchtest.get("name") or PROJECT_NAME,
        "test_type": test_type,
        "tolerance": tolerance,
        "models": models,
        "clash_rows": clash_rows,
    }


def files_by_trade_from_models(models: dict[str, str]) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for nwc in models.values():
        trade = extract_trade_token_from_filename(nwc)
        grouped.setdefault(trade, []).append(nwc)
    for trade in grouped:
        grouped[trade] = sorted(set(grouped[trade]))
    return grouped


def rebuild_clash_rows_from_matrix(
    selected_pairs: list[tuple[str, str]],
    files_by_trade: dict[str, list[str]],
    file_levels: dict[str, str],
) -> list[dict]:
    rows = []
    for trade_a, trade_b in selected_pairs:
        for file_a in files_by_trade.get(trade_a, []):
            for file_b in files_by_trade.get(trade_b, []):
                level_a = file_levels.get(file_a, "Unknown")
                level_b = file_levels.get(file_b, "Unknown")
                clash_level, include = clash_row_level(
                    trade_a, trade_b, level_a, level_b
                )
                if include:
                    rows.append(
                        {
                            "Level": clash_level,
                            "Clash Test Name": f"{clash_level} - {trade_a} vs {trade_b}",
                            "Trade A": trade_a,
                            "File A": file_a,
                            "Trade B": trade_b,
                            "File B": file_b,
                        }
                    )
    return rows


def tolerance_feet_to_inches(tolerance_feet: str) -> float:
    try:
        return float(tolerance_feet) * 12.0
    except ValueError:
        return 1.0


# ============================================================
# SMALL UI HELPERS
# ============================================================

UNKNOWN_MARKERS = {"Unknown", "Unassigned", UNASSIGNED_TRADE}


def is_unknown_marker(val) -> bool:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return False
    text = str(val).strip()
    if not text:
        return False
    if text in UNKNOWN_MARKERS:
        return True
    return text.lower() == "unknown"


def style_step2_table(df):
    def highlight_unknown(val):
        if is_unknown_marker(val):
            return (
                "color: #c62828; font-weight: 700; "
                "background-color: #ffebee;"
            )
        return ""

    subset = [
        col
        for col in ["Detected Level", "Final Level", "Final Trade"]
        if col in df.columns
    ]

    return df.style.map(highlight_unknown, subset=subset)


def inject_unknown_level_editor_highlight():
    """Color 'Unknown' cells red inside the Step 2 level data_editor."""
    components.html(
        """
        <script>
        (function () {
            const doc = window.parent.document;
            const RED = "#c62828";
            const BG = "#ffebee";

            function paint() {
                doc.querySelectorAll('[data-testid="stDataEditor"]').forEach((editor) => {
                    editor.querySelectorAll('[role="gridcell"]').forEach((cell) => {
                        const text = (cell.textContent || "").trim();
                        if (text === "Unknown") {
                            cell.style.color = RED;
                            cell.style.fontWeight = "700";
                            cell.style.backgroundColor = BG;
                        }
                    });
                });
            }

            paint();
            const target = doc.querySelector('[data-testid="stAppViewContainer"]') || doc.body;
            new MutationObserver(paint).observe(target, {
                childList: true,
                subtree: true,
            });
        })();
        </script>
        """,
        height=0,
    )


def is_ae_trade(trade_name: str) -> bool:
    """General models (AE_ARCH, AE_MECH, etc.) apply to all levels, not one floor."""
    if not trade_name or trade_name in ("Unassigned", UNASSIGNED_TRADE):
        return False
    u = trade_name.upper().replace(" ", "")
    return u == "AE" or u.startswith("AE_") or u.startswith("AE-") or "AE_" in u


def level_for_trade(trade_name: str, detected_level: str) -> str:
    """AE trades are always All Levels; other trades keep detected/edited level."""
    if is_ae_trade(trade_name):
        return ALL_LEVELS
    return detected_level


def is_all_levels_level(level: str) -> bool:
    """True when a model applies to every floor (AE trades or All Levels in Step 2)."""
    return level == ALL_LEVELS


def trade_is_all_levels(trade_name: str, level: str) -> bool:
    """All-levels models clash against every other concrete level."""
    return is_ae_trade(trade_name) or is_all_levels_level(level)


def clash_row_level(trade_a: str, trade_b: str, level_a: str, level_b: str):
    """
    Decide if a clash row should be created and which level label to use.

    - Both All Levels (AE or Step 2): one row per file pair, labeled All Levels.
    - One side All Levels: clashes every file on the other side that has a real level.
    - Both level-specific: same level only.
    """
    if level_a == "Unknown" or level_b == "Unknown":
        return None, False

    all_a = trade_is_all_levels(trade_a, level_a)
    all_b = trade_is_all_levels(trade_b, level_b)

    if all_a:
        level_a = ALL_LEVELS
    if all_b:
        level_b = ALL_LEVELS

    if all_a and all_b:
        return ALL_LEVELS, True

    if all_a and not all_b:
        if not is_all_levels_level(level_b):
            return level_b, True
        return None, False

    if not all_a and all_b:
        if not is_all_levels_level(level_a):
            return level_a, True
        return None, False

    if level_a == level_b:
        return level_a, True

    return None, False


def default_matrix_value(trade_a: str, trade_b: str) -> bool:
    """
    Default clash-matrix behavior.

    You can customize this later. For now, all different trade pairs are selected by default,
    except same-trade pairs.
    """
    return trade_a != trade_b


def matrix_checkbox_key(trade_a: str, trade_b: str, key_prefix: str = "") -> str:
    return f"{key_prefix}matrix_lower_{trade_a}_{trade_b}"


def ensure_matrix_column_state(
    active_trades: list[str],
    col_state_key: str = "matrix_col_on",
) -> None:
    """Track whether each matrix column is on (all pairs selectable) or off."""
    if col_state_key not in st.session_state:
        st.session_state[col_state_key] = {}
    for trade in active_trades:
        if trade not in st.session_state[col_state_key]:
            st.session_state[col_state_key][trade] = True
    for trade in list(st.session_state[col_state_key]):
        if trade not in active_trades:
            del st.session_state[col_state_key][trade]


def toggle_matrix_column(
    trade_col: str,
    active_trades: list[str],
    col_state_key: str = "matrix_col_on",
    key_prefix: str = "",
) -> None:
    """Turn all checkboxes in one matrix column on or off."""
    ensure_matrix_column_state(active_trades, col_state_key)
    new_on = not st.session_state[col_state_key].get(trade_col, True)
    st.session_state[col_state_key][trade_col] = new_on

    for i, trade_a in enumerate(active_trades):
        for j, trade_b in enumerate(active_trades):
            if j < i and trade_b == trade_col:
                st.session_state[matrix_checkbox_key(trade_a, trade_b, key_prefix)] = new_on


def matrix_cell_checked(
    trade_a: str,
    trade_b: str,
    col_state_key: str = "matrix_col_on",
    key_prefix: str = "",
    pair_default: bool | None = None,
) -> bool:
    """Checkbox value respecting column on/off and user toggles."""
    if not st.session_state[col_state_key].get(trade_b, True):
        return False
    key = matrix_checkbox_key(trade_a, trade_b, key_prefix)
    if key in st.session_state:
        return bool(st.session_state[key])
    if pair_default is not None:
        return pair_default
    return default_matrix_value(trade_a, trade_b)


def seed_matrix_checkboxes(
    active_trades: list[str],
    enabled_pairs: set[tuple[str, str]],
    key_prefix: str = "",
) -> None:
    for i, trade_a in enumerate(active_trades):
        for j, trade_b in enumerate(active_trades):
            if j < i:
                key = matrix_checkbox_key(trade_a, trade_b, key_prefix)
                st.session_state[key] = (trade_a, trade_b) in enabled_pairs


def render_lower_triangle_trade_matrix(
    active_trades: list[str],
    *,
    key_prefix: str = "",
    col_state_key: str = "matrix_col_on",
    enabled_pairs: set[tuple[str, str]] | None = None,
):
    """
    Render only the lower-left triangle of the trade matrix.

    Each trade pair appears once.
    Example: Mechanical vs Architecture appears, but Architecture vs Mechanical does not.
    """
    selected_pairs = []

    if len(active_trades) < 2:
        return selected_pairs

    ensure_matrix_column_state(active_trades, col_state_key)

    st.markdown('<div class="nw-matrix-wrap">', unsafe_allow_html=True)

    header_cols = st.columns(len(active_trades) + 1)
    with header_cols[0]:
        st.markdown('<p class="nw-matrix-corner">Row ↓ / Col →</p>', unsafe_allow_html=True)

    for col_index, trade in enumerate(active_trades):
        with header_cols[col_index + 1]:
            short = trade if len(trade) <= 12 else trade[:10] + "…"
            col_on = st.session_state[col_state_key].get(trade, True)
            st.button(
                short,
                key=f"{key_prefix}matrix_col_toggle_{trade}",
                on_click=toggle_matrix_column,
                args=(trade, active_trades, col_state_key, key_prefix),
                use_container_width=True,
                type="primary" if col_on else "secondary",
                help=(
                    f"Column **{trade}** is ON — click to turn off all pairs in this column."
                    if col_on
                    else f"Column **{trade}** is OFF — click to turn on all pairs in this column."
                ),
            )

    for i, trade_a in enumerate(active_trades):
        row_cols = st.columns(len(active_trades) + 1)

        with row_cols[0]:
            st.markdown(
                f'<p class="nw-matrix-row-label">{trade_a}</p>',
                unsafe_allow_html=True,
            )

        for j, trade_b in enumerate(active_trades):
            with row_cols[j + 1]:
                if j < i:
                    col_on = st.session_state[col_state_key].get(trade_b, True)
                    pair_on = (
                        (trade_a, trade_b) in enabled_pairs
                        if enabled_pairs is not None
                        else None
                    )
                    selected = st.checkbox(
                        f"{trade_a} vs {trade_b}",
                        value=matrix_cell_checked(
                            trade_a,
                            trade_b,
                            col_state_key,
                            key_prefix,
                            pair_on,
                        ),
                        key=matrix_checkbox_key(trade_a, trade_b, key_prefix),
                        label_visibility="collapsed",
                        disabled=not col_on,
                    )

                    if selected and col_on:
                        selected_pairs.append((trade_a, trade_b))

                elif j == i:
                    st.markdown(
                        '<p style="text-align:center;color:#94a3b8;margin:0;">—</p>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown("")

    st.markdown("</div>", unsafe_allow_html=True)

    return selected_pairs


# ============================================================
# MODIFY TAB
# ============================================================


def clear_modify_tab_state() -> bool:
    """Remove all Modify-tab session data (matrix, clashes, generated XML)."""
    keep = {"modify_xml_upload"}
    had_data = any(
        key.startswith("modify_") and key not in keep for key in st.session_state
    )
    for key in list(st.session_state.keys()):
        if key.startswith("modify_") and key not in keep:
            del st.session_state[key]
    return had_data


def render_modify_tab():
    """Upload XML, edit clash matrix, export updated XML."""
    st.markdown(
        """
        <div class="nw-hero">
            <h1>Modify Clash XML</h1>
            <p>Upload a Navisworks clash XML, review the trade-pair matrix and clash list,
            then export an updated file.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    uploaded = st.file_uploader(
        "Upload Navisworks clash XML",
        type=["xml"],
        key="modify_xml_upload",
    )

    if uploaded is None:
        if clear_modify_tab_state():
            st.rerun()
        st.info("Upload a clash XML file to load the matrix and clash tests.")
        return

    upload_sig = (uploaded.name, uploaded.size)
    if st.session_state.get("modify_upload_sig") != upload_sig:
        try:
            st.session_state.modify_parsed = parse_navisworks_xml_bytes(
                uploaded.getvalue()
            )
            st.session_state.modify_upload_sig = upload_sig
            st.session_state.modify_matrix_seeded = False
            for key in list(st.session_state.keys()):
                if key.startswith("modify_matrix_lower_") or key.startswith(
                    "modify_matrix_col_toggle_"
                ):
                    del st.session_state[key]
            st.session_state.pop("modify_clash_rows", None)
            st.session_state.pop("modify_generated_xml", None)
            st.session_state.pop("modify_generated_xml_name", None)
        except Exception as exc:
            st.error(f"Could not parse XML: {exc}")
            clear_modify_tab_state()
            return

    parsed = st.session_state.get("modify_parsed")
    if not parsed:
        st.info("Upload a clash XML file to load the matrix and clash tests.")
        return

    st.success(
        f"Loaded **{len(parsed['clash_rows'])}** clash test(s) and "
        f"**{len(parsed['models'])}** model search set(s)."
    )

    mod_project = st.text_input(
        "Project / batch test name",
        value=parsed["project_name"],
        key="modify_project_name",
    )
    mod_xml_name = st.text_input(
        "Download XML file name",
        value="navisworks_clash_tests_modified.xml",
        key="modify_xml_file_name",
    )
    mod_tolerance_in = st.number_input(
        "Clash tolerance (inches)",
        min_value=0.0,
        value=tolerance_feet_to_inches(parsed["tolerance"]),
        step=0.25,
        key="modify_tolerance_in",
    )
    mod_test_type = st.selectbox(
        "Clash test type",
        options=["hard", "clearance", "duplicates"],
        index=["hard", "clearance", "duplicates"].index(parsed["test_type"])
        if parsed["test_type"] in ("hard", "clearance", "duplicates")
        else 0,
        key="modify_test_type",
    )
    mod_tolerance_ft = mod_tolerance_in / 12

    st.subheader("Models in XML")
    models_df = pd.DataFrame(
        [{"Search set": k, "NWC file": v} for k, v in parsed["models"].items()]
    )
    st.dataframe(models_df, use_container_width=True, hide_index=True)

    files_by_trade = files_by_trade_from_models(parsed["models"])
    active_trades = sorted(
        [t for t in files_by_trade if t != UNASSIGNED_TRADE],
        key=lambda t: (not is_ae_trade(t), t.lower()),
    )

    if len(active_trades) < 2:
        st.warning("Need at least two trades in the XML to show a clash matrix.")
        return

    enabled_pairs = {
        (row["Trade A"], row["Trade B"])
        for row in parsed["clash_rows"]
        if row.get("Trade A") and row.get("Trade B")
    }

    st.divider()
    render_step_header(
        1,
        "Clash pair matrix",
        "Click a column header to turn that trade on or off. Adjust pairs, then rebuild clashes below.",
    )
    render_tip(
        "Matrix changes apply when you click **Rebuild clash table from matrix**. "
        "You can also edit individual rows in the table editor."
    )

    if not st.session_state.get("modify_matrix_seeded"):
        seed_matrix_checkboxes(active_trades, enabled_pairs, "modify_")
        st.session_state.modify_matrix_seeded = True

    selected_pairs = render_lower_triangle_trade_matrix(
        active_trades,
        key_prefix="modify_",
        col_state_key="modify_matrix_col_on",
        enabled_pairs=enabled_pairs,
    )

    if st.button("Rebuild clash table from matrix", type="primary", key="modify_rebuild_clashes"):
        file_levels = {}
        for nwc in parsed["models"].values():
            trade = extract_trade_token_from_filename(nwc)
            file_levels[nwc] = level_for_trade(trade, detect_level(nwc))
        for row in parsed["clash_rows"]:
            for col in ("File A", "File B"):
                nwc = row.get(col)
                if nwc and row.get("Level"):
                    file_levels[nwc] = row["Level"]

        rebuilt = rebuild_clash_rows_from_matrix(
            selected_pairs,
            files_by_trade,
            file_levels,
        )
        st.session_state.modify_clash_rows = rebuilt
        st.rerun()

    if "modify_clash_rows" not in st.session_state:
        st.session_state.modify_clash_rows = parsed["clash_rows"]

    st.subheader("Clash tests")
    clash_edit_df = pd.DataFrame(st.session_state.modify_clash_rows)
    display_cols = [
        c
        for c in [
            "Level",
            "Clash Test Name",
            "Trade A",
            "File A",
            "Trade B",
            "File B",
        ]
        if c in clash_edit_df.columns
    ]
    edited_clash = st.data_editor(
        clash_edit_df[display_cols],
        use_container_width=True,
        num_rows="dynamic",
        key="modify_clash_editor",
    )
    st.session_state.modify_clash_rows = edited_clash.to_dict("records")

    st.divider()
    render_step_header(
        2,
        "Export modified XML",
        "Generate a new Navisworks XML from the edited clash table.",
    )

    if st.button("Generate modified XML", type="primary", key="modify_generate_xml"):
        try:
            rows = st.session_state.modify_clash_rows
            if not rows:
                st.warning("Add at least one clash test row.")
            else:
                files_used = sorted(
                    {r["File A"] for r in rows if r.get("File A")}
                    | {r["File B"] for r in rows if r.get("File B")}
                )
                models = make_unique_keys(files_used)
                file_to_key = {fname: key for key, fname in models.items()}
                test_pairs = []
                for idx, row in enumerate(rows):
                    file_a = row.get("File A", "")
                    file_b = row.get("File B", "")
                    if not file_a or not file_b:
                        continue
                    test_name = row.get("Clash Test Name") or (
                        f"{row.get('Level', ALL_LEVELS)} - "
                        f"{row.get('Trade A', '')} vs {row.get('Trade B', '')}"
                    )
                    test_pairs.append(
                        (
                            f"{idx + 1:03d}_{test_name}",
                            file_to_key[file_a],
                            file_to_key[file_b],
                        )
                    )
                xml_bytes = generate_navisworks_xml_bytes(
                    models=models,
                    test_pairs=test_pairs,
                    project_name=mod_project,
                    test_type=mod_test_type,
                    tolerance=f"{mod_tolerance_ft:.7f}",
                )
                st.session_state.modify_generated_xml = xml_bytes
                st.session_state.modify_generated_xml_name = mod_xml_name
                st.success("Modified XML generated — download below.")
        except Exception as exc:
            st.error(f"XML generation failed: {exc}")

    if "modify_generated_xml" in st.session_state:
        st.download_button(
            label="Download modified Navisworks XML",
            data=st.session_state.modify_generated_xml,
            file_name=st.session_state.get(
                "modify_generated_xml_name",
                "navisworks_clash_tests_modified.xml",
            ),
            mime="application/xml",
            use_container_width=True,
            type="primary",
            key="modify_download_xml",
        )
        with st.expander("Preview modified XML", expanded=False):
            st.code(
                st.session_state.modify_generated_xml.decode("utf-8"),
                language="xml",
            )


# ============================================================
def render_generate_tab():
    """Build clash XML from NWC file names."""
    render_workflow_strip()

    # SIDEBAR INPUTS
    # ============================================================

    if "files_list_text_widget" not in st.session_state:
        st.session_state.files_list_text_widget = default_files_text

    if "folder_slot_count" not in st.session_state:
        st.session_state.folder_slot_count = 1

    st.sidebar.markdown("### Setup")
    st.sidebar.caption("Add models, then tune export settings at the bottom.")

    with st.sidebar.expander("Load from folders", expanded=True):
        st.caption(
            "Pick a folder to append `.nwc` file names to your list. "
            "Use **+ Add another folder** for multiple paths."
        )

        include_subfolders = st.checkbox(
            "Include .nwc files in subfolders",
            value=False,
            key="folder_scan_recursive",
        )

        for slot in range(st.session_state.folder_slot_count):
            st.markdown(f"**Folder {slot + 1}**")
            path_col, browse_col = st.columns([4, 1])

            path_key = f"folder_path_{slot}"
            with path_col:
                path_col.text_input(
                    "Folder path",
                    key=path_key,
                    placeholder=r"C:\Project\Models",
                    label_visibility="collapsed",
                )
            with browse_col:
                browse_col.button(
                    "…",
                    key=f"browse_folder_{slot}",
                    help="Browse for folder",
                    on_click=on_browse_folder,
                    args=(slot,),
                )

            browse_msg = st.session_state.get(f"browse_msg_{slot}")
            if browse_msg:
                st.caption(f":red[{browse_msg}]")

            if st.button(
                f"Append from folder {slot + 1}",
                key=f"append_folder_{slot}",
                use_container_width=True,
            ):
                folder_path = st.session_state.get(path_key, "")
                names, err = list_nwc_names_in_folder(
                    folder_path,
                    include_subfolders=include_subfolders,
                )
                if err:
                    st.error(err)
                elif not names:
                    st.warning("No .nwc files found in that folder.")
                else:
                    merged, added = append_lines_to_file_list(
                        st.session_state.files_list_text_widget,
                        names,
                    )
                    st.session_state.files_list_text_widget = merged
                    st.success(
                        f"Added {added} new name(s) ({len(names)} .nwc in folder)."
                    )

        if st.button("+ Add another folder", use_container_width=True):
            st.session_state.folder_slot_count += 1

    st.sidebar.divider()

    with st.sidebar.expander("NWC file list", expanded=True):
        files_text = st.text_area(
            "Paste file names (one per line)",
            height=320,
            key="files_list_text_widget",
            help="Example: LSN_L1_ARCH_MODEL.nwc",
        )

    with st.sidebar.expander("Navisworks export settings", expanded=False):
        project_name = st.text_input(
            "Project / batch test name",
            value=PROJECT_NAME,
        )

        xml_file_name = st.text_input(
            "Download XML file name",
            value="navisworks_auto_clash_tests.xml",
        )

        tolerance_inches = st.number_input(
            "Clash tolerance (inches)",
            min_value=0.0,
            value=1.0,
            step=0.25,
        )

        test_type = st.selectbox(
            "Clash test type",
            options=["hard", "clearance", "duplicates"],
            index=0,
            help="Hard = interference; clearance = proximity; duplicates = identical items.",
        )

    # Navisworks XML tolerance is in project units.
    # If project units are feet, 1 inch = 1 / 12 feet.
    tolerance_feet = tolerance_inches / 12

    nwc_files = [
        line.strip()
        for line in files_text.splitlines()
        if line.strip()
    ]

    # STOP EARLY IF NO FILES
    # ============================================================

    if not nwc_files:
        st.info(
            "**Get started** — Open **NWC file list** in the sidebar, paste at least two "
            "`.nwc` file names (one per line), or use **Load from folders** to scan a directory."
        )
        st.stop()

    if len(nwc_files) < 2:
        st.warning(
            "Add at least **two** NWC file names in the sidebar to build clash pairs."
        )
        st.stop()


    # ============================================================
    # DETECT INITIAL TRADES / LEVELS
    # ============================================================

    detected_trade_groups = []

    for file in nwc_files:
        detected_trade = detect_trade(file)

        if detected_trade != UNASSIGNED_TRADE:
            detected_trade_groups.append(detected_trade)

    trade_groups = sorted(list(set(detected_trade_groups)))
    all_groups = [UNASSIGNED_TRADE] + trade_groups

    grouped_files = {group: [] for group in all_groups}

    for file in nwc_files:
        detected_group = detect_trade(file)

        if detected_group not in grouped_files:
            grouped_files[UNASSIGNED_TRADE].append(file)
        else:
            grouped_files[detected_group].append(file)


    # ============================================================
    # AUTO-DETECTED FILE TABLE
    # ============================================================

    n_unassigned_preview = sum(
        1 for f in nwc_files if detect_trade(f) == UNASSIGNED_TRADE
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("NWC files", len(nwc_files))
    m2.metric("Trade groups", len(trade_groups))
    m3.metric(
        "Levels detected",
        len(
            {
                detect_level(f)
                for f in nwc_files
                if not is_ae_trade(detect_trade(f))
            }
        ),
    )
    m4.metric("Unassigned", n_unassigned_preview)

    st.markdown("### Detection overview")
    st.caption("How each file name was interpreted before you make corrections.")

    detected_rows = []

    for file in nwc_files:
        detected_trade = detect_trade(file)
        detected_rows.append(
            {
                "File": file,
                "Detected Trade": detected_trade,
                "Detected Level": level_for_trade(detected_trade, detect_level(file)),
            }
        )

    detected_df = pd.DataFrame(detected_rows)

    with st.container(border=True):
        st.dataframe(detected_df, use_container_width=True, hide_index=True)


    # ============================================================
    # STEP 1 — TRADE CORRECTION
    # ============================================================

    st.divider()
    render_step_header(
        1,
        "Review and fix trades",
        "Drag files between trade groups when auto-detection is wrong. "
        "Naming pattern: PREFIX_LEVEL_TRADE (e.g. LSN_L1_ARCH_MODEL.nwc).",
    )
    render_tip(
        "<strong>AE</strong> in a file name marks a general model (all levels). "
        "New trade abbreviations automatically become their own group."
    )

    detected_levels_unique = sorted(
        {
            detect_level(f)
            for f in nwc_files
            if not is_ae_trade(detect_trade(f))
        },
        key=lambda x: (x != "Unknown", x.lower()),
    )

    if "custom_project_levels" not in st.session_state:
        st.session_state.custom_project_levels = []

    with st.expander("Project levels (optional)", expanded=True):
        st.caption(
            "Levels detected from file names. Add custom names for floors not in the list."
        )

        if detected_levels_unique:
            st.markdown("**Detected from file names**")
            st.markdown("\n".join(f"- {lvl}" for lvl in detected_levels_unique))
        else:
            st.info("No levels detected.")

        if st.session_state.custom_project_levels:
            st.markdown("**You added**")
            st.markdown("\n".join(f"- {lvl}" for lvl in st.session_state.custom_project_levels))

        st.markdown("**Custom level name**")
        add_col, btn_col = st.columns([5, 1], vertical_alignment="bottom", gap="small")
        with add_col:
            new_level_name = st.text_input(
                "Custom level name",
                placeholder="e.g. Level 11, Podium",
                key="step1_new_level_input",
                label_visibility="collapsed",
            )
        with btn_col:
            add_clicked = st.button(
                "Add",
                key="step1_add_level_btn",
                use_container_width=True,
            )

        if add_clicked:
            name = (new_level_name or "").strip()

            if name:
                all_known = (
                    set(level_options)
                    | set(detected_levels_unique)
                    | set(st.session_state.custom_project_levels)
                )

                if name not in all_known:
                    st.session_state.custom_project_levels.append(name)
                    st.rerun()
                else:
                    st.warning("That level is already in the list.")
            else:
                st.warning("Enter a level name first.")


    groups_for_drag_drop = []

    for group_name in all_groups:
        groups_for_drag_drop.append(
            {
                "header": group_name,
                "items": grouped_files[group_name],
            }
        )

    st.markdown("**Drag files between trade groups**")
    st.caption("Each column is a trade. Move misclassified models to the correct group.")

    sorted_groups = sort_items(
        groups_for_drag_drop,
        multi_containers=True,
        direction="vertical",
        custom_style=SORTABLE_BRAND_STYLE,
    )

    final_grouped_data = {}

    for group in sorted_groups:
        final_grouped_data[group["header"]] = group["items"]

    file_to_trade = {}

    for group_name, files in final_grouped_data.items():
        for file in files:
            file_to_trade[file] = group_name

    unassigned_files = list(final_grouped_data.get(UNASSIGNED_TRADE, []))


    def unassigned_files_message(files: list[str], prefix: str) -> str:
        file_list = ", ".join(files[:8])
        if len(files) > 8:
            file_list += f", … (+{len(files) - 8} more)"
        return (
            f"{prefix} **{len(files)} unassigned file(s)** in **{UNASSIGNED_TRADE}**. "
            f"Drag each into a trade group in Step 1 before exporting XML. "
            f"Files: {file_list}"
        )


    if unassigned_files:
        st.error(unassigned_files_message(unassigned_files, "Cannot export XML —"))
        for key in ("generated_xml_bytes", "generated_xml_name"):
            st.session_state.pop(key, None)


    # ============================================================
    # STEP 2 — LEVEL CORRECTION
    # ============================================================

    level_options_merged = merge_level_dropdown_choices(
        level_options,
        detected_levels_unique,
        st.session_state.custom_project_levels,
    )

    st.divider()
    render_step_header(
        2,
        "Review and fix levels",
        "Confirm the floor for each model before clash pairing. "
        "AE trades stay on All Levels.",
    )
    render_tip(
        "<strong>Unknown</strong> levels and <strong>Unassigned</strong> trades are highlighted in "
        "<span style='color:#d32f2f;font-weight:bold'>red</span> in the review table."
    )

    level_rows = []

    for file in nwc_files:
        final_trade = file_to_trade.get(file, UNASSIGNED_TRADE)
        detected_level = level_for_trade(final_trade, detect_level(file))

        level_rows.append(
            {
                "File": file,
                "Final Trade": final_trade,
                "Detected Level": detected_level,
                "Final Level": detected_level,
            }
        )

    level_df = pd.DataFrame(level_rows)
    ae_level_mask = level_df["Final Trade"].apply(is_ae_trade)

    editor_key = "step2_level_editor"

    if ae_level_mask.any():
        st.info(
            f"{int(ae_level_mask.sum())} file(s) in AE trades are general models — "
            f"level is fixed to **{ALL_LEVELS}** (not editable)."
        )

    non_ae_level_df = level_df.loc[
        ~ae_level_mask, ["File", "Detected Level", "Final Level"]
    ]

    st.markdown("##### Edit levels")

    if non_ae_level_df.empty:
        level_edit_df = level_df[["File", "Detected Level", "Final Level"]].copy()
    else:
        level_edit_df = st.data_editor(
            non_ae_level_df,
            use_container_width=True,
            num_rows="fixed",
            column_config={
                "File": st.column_config.TextColumn(
                    "File",
                    disabled=True,
                ),
                "Detected Level": st.column_config.TextColumn(
                    "Detected Level",
                    disabled=True,
                ),
                "Final Level": st.column_config.SelectboxColumn(
                    "Final Level",
                    options=level_options_merged,
                    required=True,
                ),
            },
            key=editor_key,
            hide_index=True,
        )
        inject_unknown_level_editor_highlight()

    edited_level_df = level_df.drop(columns=["Final Level"]).merge(
        level_edit_df[["File", "Final Level"]],
        on="File",
        how="left",
    )

    edited_level_df.loc[ae_level_mask, "Final Level"] = ALL_LEVELS

    unknown_level_count = int(
        edited_level_df.apply(
            lambda row: is_unknown_marker(row["Final Level"])
            or is_unknown_marker(row.get("Detected Level")),
            axis=1,
        ).sum()
    )
    if unknown_level_count:
        st.warning(
            f"{unknown_level_count} unknown level value(s) — shown in **red** below. "
            "Pick a floor from **Final Level** before continuing."
        )

    with st.container(border=True):
        st.dataframe(
            style_step2_table(edited_level_df),
            use_container_width=True,
            hide_index=True,
        )

    file_to_level = dict(
        zip(
            edited_level_df["File"],
            edited_level_df["Final Level"]
        )
    )


    # ============================================================
    # STEP 3 — TRADE CLASH MATRIX
    # ============================================================

    st.divider()
    render_step_header(
        3,
        "Select clash pairs",
        "Check discipline pairs to include. Only selected pairs appear in the clash table and XML.",
    )

    active_trades = [
        trade
        for trade in trade_groups
        if trade != UNASSIGNED_TRADE
    ]

    # Stable matrix order: AE/general models first, then level-specific trades
    active_trades = sorted(
        active_trades,
        key=lambda t: (not is_ae_trade(t), t.lower())
    )

    selected_trade_pairs = []

    if not active_trades:
        st.error(
            "No trade groups detected. Check file names or drag files out of "
            f"**{UNASSIGNED_TRADE}** in Step 1."
        )
    elif len(active_trades) < 2:
        st.warning("At least two trades are required to build a clash matrix.")
    else:
        with st.expander("Trades in this matrix", expanded=False):
            st.write(", ".join(active_trades))

        render_tip(
            "Click a <strong>column header</strong> to turn that whole column on or off "
            "(all checkboxes in the column). Primary = on, grey = off."
        )

        selected_trade_pairs = render_lower_triangle_trade_matrix(active_trades)

        if selected_trade_pairs:
            selected_pairs_text = ", ".join(
                [f"{a} vs {b}" for a, b in selected_trade_pairs]
            )
            st.success(
                f"**{len(selected_trade_pairs)}** pair(s) selected — {selected_pairs_text}"
            )
        else:
            st.warning("No trade pairs selected. Check at least one cell in the matrix.")


    # ============================================================
    # STEP 4 — GENERATE SAME-LEVEL CLASH TABLE
    # ============================================================

    st.divider()
    render_step_header(
        4,
        "Preview clash tests",
        "File pairs from your matrix. **All Levels** models clash with every other level; "
        "other trades clash on the same level only.",
    )

    clash_df = pd.DataFrame()

    if len(active_trades) < 2:
        st.warning("Complete Step 3 with at least two trades to preview clashes.")
    elif not selected_trade_pairs:
        st.warning("Select at least one pair in the matrix above.")
    else:
        rows = []

        for trade_a, trade_b in selected_trade_pairs:
            files_a = final_grouped_data.get(trade_a, [])
            files_b = final_grouped_data.get(trade_b, [])

            for file_a in files_a:
                for file_b in files_b:
                    level_a = file_to_level.get(file_a, "Unknown")
                    level_b = file_to_level.get(file_b, "Unknown")

                    clash_level, include = clash_row_level(
                        trade_a, trade_b, level_a, level_b
                    )
                    if include:
                        rows.append(
                            {
                                "Level": clash_level,
                                "Clash Test Name": (
                                    f"{clash_level} - {trade_a} vs {trade_b}"
                                ),
                                "Trade A": trade_a,
                                "File A": file_a,
                                "Trade B": trade_b,
                                "File B": file_b,
                            }
                        )

        if rows:
            clash_df = pd.DataFrame(rows)

            clash_df = clash_df.sort_values(
                by=["Level", "Clash Test Name", "File A", "File B"]
            ).reset_index(drop=True)

            st.success(f"**{len(clash_df)}** clash tests ready for export.")

            with st.container(border=True):
                st.dataframe(clash_df, use_container_width=True, hide_index=True)

            csv = clash_df.to_csv(index=False).encode("utf-8")

            st.markdown(
                '<div class="nw-download-csv-marker" aria-hidden="true"></div>',
                unsafe_allow_html=True,
            )
            st.download_button(
                label="Download clash table (CSV)",
                data=csv,
                file_name="same_level_clash_tests.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary",
                key="download_clash_csv",
            )

        else:
            st.warning(
                "No clash tests were generated. Check that selected trade pairs share a level, "
                "or include an **All Levels** / AE model against level-specific trades."
            )


    # ============================================================
    # STEP 5 — GENERATE XML ON BUTTON CLICK
    # ============================================================

    st.divider()
    render_step_header(
        5,
        "Generate Navisworks XML",
        "Build the clash batch file from the preview table, then download and import into Navisworks.",
    )

    if clash_df.empty:
        st.info("Complete Steps 1–4 to produce at least one clash test before exporting XML.")

    elif unassigned_files:
        st.error(
            unassigned_files_message(
                unassigned_files,
                "XML export blocked —",
            )
        )

    else:
        st.markdown(
            '<div class="nw-gen-xml-marker" aria-hidden="true"></div>',
            unsafe_allow_html=True,
        )
        generate_clicked = st.button(
            "Generate Navisworks XML",
            type="primary",
            use_container_width=True,
            key="generate_navisworks_xml",
        )

        if generate_clicked:
            try:
                # Build search sets from all files that appear in the clash table only.
                files_used_in_clashes = sorted(
                    set(clash_df["File A"].tolist()) | set(clash_df["File B"].tolist())
                )

                models = make_unique_keys(files_used_in_clashes)

                # Reverse lookup:
                # actual NWC file name -> safe XML search set name
                file_to_model_key = {
                    file_name: model_key
                    for model_key, file_name in models.items()
                }

                test_pairs = []

                for idx, row in clash_df.iterrows():
                    left_file = row["File A"]
                    right_file = row["File B"]

                    left_key = file_to_model_key[left_file]
                    right_key = file_to_model_key[right_file]

                    # Add row number to prevent duplicate clash test names.
                    clean_test_name = f"{idx + 1:03d}_{row['Clash Test Name']}"

                    test_pairs.append(
                        (
                            clean_test_name,
                            left_key,
                            right_key,
                        )
                    )

                xml_bytes = generate_navisworks_xml_bytes(
                    models=models,
                    test_pairs=test_pairs,
                    project_name=project_name,
                    test_type=test_type,
                    tolerance=f"{tolerance_feet:.7f}",
                )

                st.session_state.generated_xml_bytes = xml_bytes
                st.session_state.generated_xml_name = xml_file_name

                st.success("XML generated successfully — download below.")

            except Exception as e:
                st.error(f"XML generation failed: {e}")

        if "generated_xml_bytes" in st.session_state and not unassigned_files:
            dl_col, _ = st.columns([1, 1])
            with dl_col:
                st.markdown(
                    '<div class="nw-download-xml-marker" aria-hidden="true"></div>',
                    unsafe_allow_html=True,
                )
                st.download_button(
                    label="Download Navisworks XML",
                    data=st.session_state.generated_xml_bytes,
                    file_name=st.session_state.get(
                        "generated_xml_name",
                        "navisworks_auto_clash_tests.xml",
                    ),
                    mime="application/xml",
                    use_container_width=True,
                    type="primary",
                    key="download_navisworks_xml",
                )

            with st.expander("Preview XML", expanded=False):
                st.code(
                    st.session_state.generated_xml_bytes.decode("utf-8"),
                    language="xml"
                )


    # ============================================================


# ============================================================
# APP TABS
# ============================================================

inject_app_styles()
render_app_header()

st.markdown(
    """
    <div class="nw-tab-bar-anchor">
        <p class="nw-app-mode-label">Mode</p>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_generate, tab_modify = st.tabs(["Generate", "Modify"])

with tab_generate:
    render_generate_tab()

with tab_modify:
    render_modify_tab()
