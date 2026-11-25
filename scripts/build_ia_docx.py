"""
Generates the complete, publication-grade IB DP Computer Science Internal Assessment
and Project Documentation in Microsoft Word (.docx) format:
  E:/Aasu/SYNTRIQ_IB_CS_Internal_Assessment.docx

Features:
- A4 layout, custom running headers/footers with dynamic Word Page X of Y fields
- High-resolution architecture (MVC + Firebase UID isolation) and UML/ERD diagrams
  rendered crisp via Chromium SVG -> PNG
- Live application screenshots captured from SYNTRIQ (including updated clean /login
  and /routines views alongside dashboard, study plan, simulator, time intelligence,
  add task, pomodoro timer, and mobile responsive views)
- Styled Criteria A-E structure aligned with IB CS IA exemplars and verified prose
  word count strictly below the 2,000-word IB limit
"""

import os
import sys
import gc
import time
import socket
import tempfile
import threading
from datetime import date, timedelta

from PIL import Image as PILImage
from playwright.sync_api import sync_playwright
from werkzeug.serving import make_server

import docx
from docx import Document
from docx.shared import Inches, Pt, Mm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

import database as db
import firebase_auth
from app import app

DEMO_UID = "ia_demo_arjun_uid"
DEMO_EMAIL = "arjunkahar02111@gmail.com"
DEMO_NAME = "Arjun Kahar"

SCRATCH_DIR = r"C:\Users\kahar\.gemini\antigravity-cli\brain\6f0761e0-6dff-4c37-9b21-4564ecdd83a2\scratch"
EXISTING_IA_SHOTS = os.path.join(BASE_DIR, "screenshots", "ia")
DOCX_ASSETS_DIR = os.path.join(SCRATCH_DIR, "docx_assets")
DEFAULT_DOCX_PATH = os.path.join(BASE_DIR, "SYNTRIQ_IB_CS_Internal_Assessment.docx")

# Palette matching SYNTRIQ & clean academic aesthetic
NAVY = RGBColor(0x0F, 0x17, 0x2A)
SLATE = RGBColor(0x33, 0x41, 0x55)
MUTED = RGBColor(0x64, 0x74, 0x8B)
BODY = RGBColor(0x1E, 0x29, 0x3B)
ORANGE = RGBColor(0xEA, 0x58, 0x0C)
DARK_ORANGE = RGBColor(0xC2, 0x41, 0x0C)


def count_words(text: str) -> int:
    return len([w for w in text.strip().split() if w])


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def populate_demo_database(db_path: str) -> None:
    """Populates a temporary isolated SQLite DB for /routines & session demo."""
    db.init_db(db_path)
    db.upsert_user_profile(DEMO_UID, DEMO_EMAIL, DEMO_NAME, "", db_path=db_path)
    db.add_routine(
        DEMO_UID,
        "Morning IB Math AA HL Calculus Drill",
        "Mathematics",
        "Monday",
        "07:00",
        "08:30",
        "Past Paper 1 & 2 Integration",
        db_path=db_path,
    )
    db.add_routine(
        DEMO_UID,
        "Computer Science IA Testing & Firestore Rules",
        "Computer Science",
        "Wednesday",
        "18:00",
        "19:30",
        "Criterion D & 52-test verification",
        db_path=db_path,
    )
    db.add_routine(
        DEMO_UID,
        "Physics HL Uncertainty & Paper 3 Lab",
        "Physics",
        "Friday",
        "16:30",
        "18:00",
        "Error propagation problem sets",
        db_path=db_path,
    )
    db.add_routine(
        DEMO_UID,
        "Active Recall Flashcards & Weekly Review",
        "Daily",
        "Daily",
        "20:30",
        "21:15",
        "Spaced repetition consolidation",
        db_path=db_path,
    )
    today = date.today()
    db.add_task(
        title="Computer Science IA Criterion D & Testing",
        subject="Computer Science",
        deadline=(today + timedelta(days=1)).strftime("%Y-%m-%d"),
        difficulty=5,
        importance=5,
        estimated_hours=5.0,
        db_path=db_path,
        user_uid=DEMO_UID,
    )


def get_demo_session_cookie() -> str:
    c = app.test_client()
    with c.session_transaction() as sess:
        sess["user"] = {
            "uid": DEMO_UID,
            "email": DEMO_EMAIL,
            "name": DEMO_NAME,
            "picture": "",
        }
    c.get("/dashboard")
    return c.get_cookie("session").value


def render_diagrams_and_fresh_screenshots(assets_dir: str) -> dict:
    """Renders crisp PNG diagrams and captures up-to-date /login and /routines screenshots."""
    os.makedirs(assets_dir, exist_ok=True)
    paths = {}

    # Existing verified high-DPI screenshots
    for key, fname in [
        ("dashboard", "ia_01_dashboard.png"),
        ("study_plan", "ia_02_study_plan.png"),
        ("simulator", "ia_03_what_if_simulator.png"),
        ("time_intel", "ia_04_time_intelligence.png"),
        ("add_task", "ia_05_add_task.png"),
        ("pomodoro", "ia_06_focus_timer.png"),
        ("mobile", "ia_07_mobile_dashboard.png"),
    ]:
        p = os.path.join(EXISTING_IA_SHOTS, fname)
        if not os.path.exists(p):
            raise FileNotFoundError(f"Missing expected IA screenshot: {p}")
        paths[key] = p

    # Render SVG architecture & UML/ERD diagrams + live /login and /routines views
    arch_svg = """
    <svg viewBox="0 0 820 265" width="820" height="265" xmlns="http://www.w3.org/2000/svg" style="font-family: 'Segoe UI', Arial, sans-serif; background:#ffffff;">
      <rect x="0" y="0" width="820" height="265" fill="#ffffff"/>
      <!-- View Layer -->
      <rect x="16" y="20" width="185" height="225" rx="8" fill="#fff7ed" stroke="#f97316" stroke-width="1.8"/>
      <text x="108" y="42" text-anchor="middle" font-size="11.5" font-weight="700" fill="#9a3412">VIEW (Browser UI)</text>
      <rect x="28" y="54" width="161" height="26" rx="4" fill="#ffffff" stroke="#fdba74"/>
      <text x="108" y="71" text-anchor="middle" font-size="9.5" fill="#1e293b">Google Sign-In (/login)</text>
      <rect x="28" y="88" width="161" height="26" rx="4" fill="#ffffff" stroke="#fdba74"/>
      <text x="108" y="105" text-anchor="middle" font-size="9.5" fill="#1e293b">Dashboard &amp; Heatmap</text>
      <rect x="28" y="122" width="161" height="26" rx="4" fill="#ffffff" stroke="#fdba74"/>
      <text x="108" y="139" text-anchor="middle" font-size="9.5" fill="#1e293b">Study Plan &amp; What-If Sim</text>
      <rect x="28" y="156" width="161" height="26" rx="4" fill="#ffffff" stroke="#fdba74"/>
      <text x="108" y="173" text-anchor="middle" font-size="9.5" fill="#1e293b">Weekly Routines &amp; Settings</text>
      <rect x="28" y="190" width="161" height="42" rx="4" fill="#ffffff" stroke="#fdba74"/>
      <text x="108" y="207" text-anchor="middle" font-size="9.3" fill="#1e293b">Time Intel &amp; Focus Timer</text>
      <text x="108" y="222" text-anchor="middle" font-size="8.4" fill="#64748b">(Firebase Web SDK + main.js)</text>

      <!-- Arrow View <-> Controller -->
      <line x1="201" y1="112" x2="256" y2="112" stroke="#475569" stroke-width="1.6"/>
      <polygon points="256,112 248,108 248,116" fill="#475569"/>
      <line x1="256" y1="145" x2="201" y2="145" stroke="#475569" stroke-width="1.6"/>
      <polygon points="201,145 209,141 209,149" fill="#475569"/>
      <text x="228" y="104" text-anchor="middle" font-size="8" fill="#475569">HTTPS + Token</text>
      <text x="228" y="158" text-anchor="middle" font-size="8" fill="#475569">HTML / JSON</text>

      <!-- Controller + Auth Layer -->
      <rect x="258" y="28" width="210" height="208" rx="8" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.8"/>
      <text x="363" y="50" text-anchor="middle" font-size="11.2" font-weight="700" fill="#1e40af">CONTROLLER &amp; AUTH</text>
      <text x="363" y="66" text-anchor="middle" font-size="9" font-weight="600" fill="#1d4ed8">(app.py + firebase_auth.py)</text>
      <text x="363" y="90" text-anchor="middle" font-size="9.2" fill="#1e293b">• Verify Firebase ID Tokens (UID)</text>
      <text x="363" y="110" text-anchor="middle" font-size="9.2" fill="#1e293b">• @login_required Route Guard</text>
      <text x="363" y="130" text-anchor="middle" font-size="9.2" fill="#1e293b">• Server Input Validation (HTTP 400)</text>
      <text x="363" y="150" text-anchor="middle" font-size="9.2" fill="#1e293b">• Time-Tracking &amp; Simulator APIs</text>
      <text x="363" y="170" text-anchor="middle" font-size="9.2" fill="#1e293b">• Routines, Settings &amp; .ics Export</text>
      <rect x="274" y="185" width="178" height="36" rx="5" fill="#ffffff" stroke="#93c5fd"/>
      <text x="363" y="201" text-anchor="middle" font-size="9.2" font-weight="700" fill="#1e3a8a">Dual-Store Router (store.py)</text>
      <text x="363" y="214" text-anchor="middle" font-size="8.2" fill="#475569">Routes by verified UID &amp; ID token</text>

      <!-- Arrows Controller -> Models -->
      <line x1="468" y1="80" x2="520" y2="58" stroke="#475569" stroke-width="1.6"/>
      <polygon points="520,58 511,57 514,65" fill="#475569"/>
      <line x1="468" y1="145" x2="520" y2="145" stroke="#475569" stroke-width="1.6"/>
      <polygon points="520,145 512,141 512,149" fill="#475569"/>
      <line x1="468" y1="204" x2="520" y2="218" stroke="#475569" stroke-width="1.6"/>
      <polygon points="520,218 514,212 511,220" fill="#475569"/>

      <!-- Algorithmic Model -->
      <rect x="522" y="16" width="282" height="80" rx="8" fill="#f0fdf4" stroke="#16a34a" stroke-width="1.8"/>
      <text x="663" y="36" text-anchor="middle" font-size="10.5" font-weight="700" fill="#166534">ALGORITHMIC MODEL (priority_calculator.py)</text>
      <text x="663" y="54" text-anchor="middle" font-size="9" fill="#1e293b">calculate_urgency() &bull; calculate_workload()</text>
      <text x="663" y="70" text-anchor="middle" font-size="9" fill="#1e293b">calculate_priority() = 0.4U + 0.3I + 0.2D + 0.1W</text>
      <text x="663" y="86" text-anchor="middle" font-size="9" fill="#1e293b">is_overdue() &bull; days_remaining()</text>

      <!-- Cloud Firestore Model -->
      <rect x="522" y="106" width="282" height="78" rx="8" fill="#fefce8" stroke="#ca8a04" stroke-width="1.8"/>
      <text x="663" y="126" text-anchor="middle" font-size="10.5" font-weight="700" fill="#854d0e">CLOUD FIRESTORE (firestore_store.py)</text>
      <text x="663" y="144" text-anchor="middle" font-size="8.9" fill="#1e293b">UID-Isolated Paths: users/{uid}/{collection}</text>
      <text x="663" y="160" text-anchor="middle" font-size="8.9" fill="#1e293b">Enforced by firestore.rules (request.auth.uid == uid)</text>
      <text x="663" y="175" text-anchor="middle" font-size="8.5" fill="#475569">profile, settings, routines, tasks, sessions</text>

      <!-- SQLite Fallback Model -->
      <rect x="522" y="193" width="282" height="58" rx="8" fill="#f8fafc" stroke="#334155" stroke-width="1.8"/>
      <text x="663" y="213" text-anchor="middle" font-size="10.5" font-weight="700" fill="#0f172a">RELATIONAL FALLBACK (database.py)</text>
      <text x="663" y="230" text-anchor="middle" font-size="8.8" fill="#1e293b">SQLite parameterized CRUD scoped by User_UID</text>
      <text x="663" y="244" text-anchor="middle" font-size="8.4" fill="#475569">Used for offline tests &amp; local development</text>
    </svg>
    """

    uml_erd_svg = """
    <svg viewBox="0 0 820 265" width="820" height="265" xmlns="http://www.w3.org/2000/svg" style="font-family: 'Segoe UI', Arial, sans-serif; background:#ffffff;">
      <rect x="0" y="0" width="820" height="265" fill="#ffffff"/>
      <text x="155" y="18" text-anchor="middle" font-size="11" font-weight="700" fill="#0f172a">UML Use Case Diagram</text>

      <!-- Actor -->
      <circle cx="44" cy="105" r="12" fill="none" stroke="#1e293b" stroke-width="1.8"/>
      <line x1="44" y1="117" x2="44" y2="160" stroke="#1e293b" stroke-width="1.8"/>
      <line x1="24" y1="133" x2="64" y2="133" stroke="#1e293b" stroke-width="1.8"/>
      <line x1="44" y1="160" x2="27" y2="190" stroke="#1e293b" stroke-width="1.8"/>
      <line x1="44" y1="160" x2="61" y2="190" stroke="#1e293b" stroke-width="1.8"/>
      <text x="44" y="208" text-anchor="middle" font-size="9.5" font-weight="700" fill="#1e293b">Student</text>
      <text x="44" y="220" text-anchor="middle" font-size="8" fill="#64748b">(Google Auth)</text>

      <!-- System Boundary -->
      <rect x="108" y="28" width="194" height="226" rx="6" fill="#f8fafc" stroke="#64748b" stroke-width="1.4"/>
      <g fill="#ffffff" stroke="#334155" stroke-width="1.2">
        <ellipse cx="205" cy="49" rx="82" ry="12"/>
        <ellipse cx="205" cy="80" rx="82" ry="12"/>
        <ellipse cx="205" cy="111" rx="82" ry="12"/>
        <ellipse cx="205" cy="142" rx="82" ry="12"/>
        <ellipse cx="205" cy="173" rx="82" ry="12"/>
        <ellipse cx="205" cy="204" rx="82" ry="12"/>
        <ellipse cx="205" cy="235" rx="82" ry="12"/>
      </g>
      <g font-size="8.6" text-anchor="middle" fill="#0f172a">
        <text x="205" y="52">Sign In &amp; Isolate Workspace</text>
        <text x="205" y="83">Manage Tasks &amp; Routines</text>
        <text x="205" y="114">View Prioritized Study Plan</text>
        <text x="205" y="145">Simulate What-If Priority</text>
        <text x="205" y="176">Track Live Focus Session</text>
        <text x="205" y="207">Inspect Time Intelligence</text>
        <text x="205" y="238">Export .ics Calendar</text>
      </g>
      <g stroke="#475569" stroke-width="1.1">
        <line x1="60" y1="122" x2="123" y2="49"/>
        <line x1="60" y1="126" x2="123" y2="80"/>
        <line x1="60" y1="130" x2="123" y2="111"/>
        <line x1="60" y1="135" x2="123" y2="142"/>
        <line x1="60" y1="140" x2="123" y2="173"/>
        <line x1="60" y1="145" x2="123" y2="204"/>
        <line x1="60" y1="150" x2="123" y2="235"/>
      </g>

      <!-- Divider -->
      <line x1="320" y1="12" x2="320" y2="253" stroke="#cbd5e1" stroke-dasharray="4,4"/>

      <!-- Right: UID-Isolated Schema ERD -->
      <text x="570" y="18" text-anchor="middle" font-size="11" font-weight="700" fill="#0f172a">Multi-User Data Schema (Firestore + SQLite ERD)</text>

      <!-- Tasks Table -->
      <rect x="336" y="30" width="225" height="224" rx="5" fill="#ffffff" stroke="#0f172a" stroke-width="1.4"/>
      <rect x="336" y="30" width="225" height="21" rx="4" fill="#fff7ed" stroke="#0f172a" stroke-width="1.2"/>
      <text x="448" y="44" text-anchor="middle" font-size="9.5" font-weight="700" fill="#9a3412">Tasks (users/{uid}/tasks)</text>
      <g font-size="8.2" fill="#1e293b" font-family="Consolas, monospace">
        <text x="343" y="65">PK Task_ID : INTEGER / TEXT</text>
        <text x="343" y="80">FK ownerUid / User_UID : TEXT</text>
        <text x="343" y="95">   Task_Title : TEXT NOT NULL</text>
        <text x="343" y="110">   Task_Subject : TEXT NOT NULL</text>
        <text x="343" y="125">   Task_Deadline : YYYY-MM-DD</text>
        <text x="343" y="140">   Task_Difficulty : INT (1..5)</text>
        <text x="343" y="155">   Task_Importance : INT (1..5)</text>
        <text x="343" y="170">   Target_Hours : REAL (Nullable)</text>
        <text x="343" y="185">   Total_Tracked_Seconds : INT</text>
        <text x="343" y="200">   Priority_Score : REAL</text>
        <text x="343" y="215">   Task_Status : Pending|Completed</text>
        <text x="343" y="230">   First_Tracked_At, Completed_At</text>
        <text x="343" y="245">   subtasks[] (1:N Subtasks)</text>
      </g>

      <!-- Routines & Profile -->
      <rect x="590" y="30" width="214" height="68" rx="5" fill="#ffffff" stroke="#0f172a" stroke-width="1.3"/>
      <rect x="590" y="30" width="214" height="19" rx="4" fill="#f0fdf4" stroke="#0f172a"/>
      <text x="697" y="43" text-anchor="middle" font-size="9" font-weight="700" fill="#166534">Routines, Profile &amp; Settings</text>
      <g font-size="8" fill="#1e293b" font-family="Consolas, monospace">
        <text x="596" y="61">users/{uid}/profile/main</text>
        <text x="596" y="74">users/{uid}/settings/preferences</text>
        <text x="596" y="87">users/{uid}/routines/{id}</text>
      </g>

      <!-- StudySessions -->
      <rect x="590" y="108" width="214" height="72" rx="5" fill="#ffffff" stroke="#0f172a" stroke-width="1.3"/>
      <rect x="590" y="108" width="214" height="19" rx="4" fill="#f1f5f9" stroke="#0f172a"/>
      <text x="697" y="121" text-anchor="middle" font-size="9" font-weight="700">StudySessions (1:N)</text>
      <g font-size="8" fill="#1e293b" font-family="Consolas, monospace">
        <text x="596" y="139">PK Session_ID, ownerUid</text>
        <text x="596" y="152">FK Task_ID -&gt; Tasks</text>
        <text x="596" y="165">   Start_Time, End_Time, Status</text>
        <text x="596" y="176">   Duration_Seconds, Session_Date</text>
      </g>

      <!-- ActiveSession -->
      <rect x="590" y="190" width="214" height="64" rx="5" fill="#ffffff" stroke="#0f172a" stroke-width="1.3"/>
      <rect x="590" y="190" width="214" height="19" rx="4" fill="#eff6ff" stroke="#0f172a"/>
      <text x="697" y="203" text-anchor="middle" font-size="9" font-weight="700">ActiveSession (1 per UID)</text>
      <g font-size="8" fill="#1e293b" font-family="Consolas, monospace">
        <text x="596" y="221">PK active_session/current</text>
        <text x="596" y="234">FK Task_ID, Session_ID, ownerUid</text>
        <text x="596" y="246">   Start_Timestamp, Accumulated_Sec</text>
      </g>

      <!-- Connectors -->
      <g stroke="#334155" stroke-width="1.2">
        <line x1="561" y1="65" x2="590" y2="65"/>
        <line x1="561" y1="145" x2="590" y2="145"/>
        <line x1="561" y1="222" x2="590" y2="222"/>
      </g>
    </svg>
    """

    tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp_db_path = tmp_db.name
    tmp_db.close()

    orig_default = db.DEFAULT_DB_PATH
    db.DEFAULT_DB_PATH = tmp_db_path
    app.config["DB_FILE"] = tmp_db_path
    app.config["TESTING"] = True

    port = find_free_port()
    server = make_server("127.0.0.1", port, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)

    try:
        populate_demo_database(tmp_db_path)
        cookie_val = get_demo_session_cookie()
        thread.start()
        base_url = f"http://127.0.0.1:{port}"

        with sync_playwright() as p:
            browser = p.chromium.launch()

            # Render diagrams cleanly at 2x DPI
            for key, svg_str, h in [
                ("arch_diagram", arch_svg, 265),
                ("uml_erd_diagram", uml_erd_svg, 265),
            ]:
                dpage = browser.new_page(viewport={"width": 820, "height": h}, device_scale_factor=2)
                dpage.set_content(f"<html><body style='margin:0;padding:0;background:#fff'>{svg_str}</body></html>")
                out_p = os.path.join(assets_dir, f"{key}.png")
                dpage.screenshot(path=out_p, full_page=False)
                paths[key] = out_p
                dpage.close()

            # Capture clean updated /login screenshot (without the removed setup banner)
            anon_ctx = browser.new_context(viewport={"width": 1366, "height": 820}, device_scale_factor=2)
            anon_pg = anon_ctx.new_page()
            anon_pg.goto(f"{base_url}/login", wait_until="domcontentloaded")
            anon_pg.wait_for_timeout(400)
            p_login = os.path.join(assets_dir, "ia_00_login_clean.png")
            anon_pg.screenshot(path=p_login, full_page=False)
            paths["login"] = p_login
            anon_ctx.close()

            # Capture /routines page screenshot
            auth_ctx = browser.new_context(viewport={"width": 1366, "height": 920}, device_scale_factor=2)
            auth_ctx.add_cookies([{"name": "session", "value": cookie_val, "domain": "127.0.0.1", "path": "/"}])
            r_pg = auth_ctx.new_page()
            r_pg.goto(f"{base_url}/routines", wait_until="networkidle")
            r_pg.wait_for_timeout(500)
            p_routines = os.path.join(assets_dir, "ia_08_routines.png")
            r_pg.screenshot(path=p_routines, full_page=False)
            paths["routines"] = p_routines
            auth_ctx.close()

            browser.close()
    finally:
        server.shutdown()
        db.DEFAULT_DB_PATH = orig_default
        app.config.pop("DB_FILE", None)
        gc.collect()
        if os.path.exists(tmp_db_path):
            try:
                os.remove(tmp_db_path)
            except Exception:
                pass

    return paths


# =============================================================================
# python-docx XML Styling Helpers
# =============================================================================

def set_cell_shading(cell, hex_color: str):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def set_cell_margins(cell, top=90, bottom=90, left=130, right=130):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement("w:tcMar")
    for m, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{m}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def set_table_borders(table, color="94A3B8", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:left w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:right w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def prevent_row_split(row):
    trPr = row._tr.get_or_add_trPr()
    trPr.append(OxmlElement("w:cantSplit"))


def add_p_bottom_border(paragraph, color="F97316", sz="12"):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'  <w:bottom w:val="single" w:sz="{sz}" w:space="4" w:color="{color}"/>'
        f'</w:pBdr>'
    )
    pPr.append(pBdr)


def add_field(paragraph, field_name: str):
    run = paragraph.add_run()
    run.font.size = Pt(8.5)
    run.font.color.rgb = MUTED
    fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls("w"))
    instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> %s </w:instrText>' % (nsdecls("w"), field_name))
    fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls("w"))
    fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls("w"))
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)


def add_criterion_heading(doc: Document, text: str, page_break: bool = True):
    if page_break:
        doc.add_page_break()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(10)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(15)
    r.font.color.rgb = NAVY
    add_p_bottom_border(p, color="F97316", sz="14")


def add_sub_heading(doc: Document, text: str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(11.5)
    r.font.color.rgb = NAVY
    return p


def add_dev_heading(doc: Document, text: str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.bold = True
    r.underline = True
    r.font.size = Pt(10.8)
    r.font.color.rgb = DARK_ORANGE
    return p


def add_body_para(doc: Document, text: str, justify: bool = True):
    p = doc.add_paragraph()
    if justify:
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.18
    r = p.add_run(text)
    r.font.size = Pt(10)
    r.font.color.rgb = BODY
    return p


def add_word_badge(doc: Document, words: int, label: str = "Words"):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(8)
    r = p.add_run(f"{label}: {words}")
    r.bold = True
    r.font.size = Pt(9.2)
    r.font.color.rgb = SLATE


def add_code_box(doc: Document, code_text: str):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.75)
    set_cell_shading(cell, "F8FAFC")
    set_cell_margins(cell, top=90, bottom=90, left=140, right=120)
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        f'  <w:left w:val="single" w:sz="24" w:space="0" w:color="F97316"/>'
        f'  <w:bottom w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        f'  <w:right w:val="single" w:sz="4" w:space="0" w:color="CBD5E1"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)
    prevent_row_split(tbl.rows[0])

    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.08
    r = p.add_run(code_text)
    r.font.name = "Consolas"
    r.font.size = Pt(8.2)
    r.font.color.rgb = NAVY

    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(4)


def add_figure(doc: Document, image_path: str, caption: str, max_width_in: float = 6.5, max_height_in: float = 4.6):
    with PILImage.open(image_path) as im:
        w_px, h_px = im.size
    aspect = h_px / float(w_px)
    width_in = max_width_in
    height_in = width_in * aspect
    if height_in > max_height_in:
        height_in = max_height_in
        width_in = height_in / aspect

    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    cell.width = Inches(6.75)
    set_cell_shading(cell, "FFFFFF")
    set_cell_margins(cell, top=100, bottom=90, left=100, right=100)
    set_table_borders(tbl, color="CBD5E1", sz="6")
    prevent_row_split(tbl.rows[0])

    p_img = cell.paragraphs[0]
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(0)
    p_img.paragraph_format.space_after = Pt(5)
    p_img.paragraph_format.keep_with_next = True
    run_img = p_img.add_run()
    run_img.add_picture(image_path, width=Inches(width_in))

    p_cap = cell.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(2)
    p_cap.paragraph_format.space_after = Pt(0)
    r_cap = p_cap.add_run(caption)
    r_cap.bold = True
    r_cap.font.size = Pt(8.8)
    r_cap.font.color.rgb = MUTED

    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(6)


def build_docx(paths: dict, output_path: str):
    doc = Document()

    # Configure A4 page & margins
    section = doc.sections[0]
    section.page_width = Mm(210)
    section.page_height = Mm(297)
    section.top_margin = Mm(17)
    section.bottom_margin = Mm(17)
    section.left_margin = Mm(18)
    section.right_margin = Mm(18)
    section.different_first_page_header_footer = True

    # Base Normal font
    normal_style = doc.styles["Normal"]
    normal_style.font.name = "Calibri"
    normal_style.font.size = Pt(10)
    normal_style.font.color.rgb = BODY

    # Running Header (Pages 2+)
    hdr = section.header
    hp = hdr.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = hp.add_run("")
    hr.font.size = Pt(8.5)
    hr.font.color.rgb = MUTED

    # Running Footer (Pages 2+): Title left, Page X of Y right via borderless 2-col table
    ftr = section.footer
    ftbl = ftr.add_table(rows=1, cols=2, width=Inches(6.75))
    ftbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    c_left, c_right = ftbl.cell(0, 0), ftbl.cell(0, 1)
    c_left.width = Inches(4.5)
    c_right.width = Inches(2.25)
    pl = c_left.paragraphs[0]
    rl = pl.add_run("")
    rl.font.size = Pt(8.5)
    rl.font.color.rgb = MUTED
    pr = c_right.paragraphs[0]
    pr.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r1 = pr.add_run("Page ")
    r1.font.size = Pt(8.5)
    r1.font.color.rgb = MUTED
    add_field(pr, "PAGE")
    r2 = pr.add_run(" of ")
    r2.font.size = Pt(8.5)
    r2.font.color.rgb = MUTED
    add_field(pr, "NUMPAGES")

    # =========================================================================
    # Structured Prose Content (Exact Word Count Tracked <= 2,000 Words)
    # =========================================================================
    crit_a_scenario = (
        "As an International Baccalaureate Diploma Programme student managing six demanding subjects alongside "
        "Internal Assessments and the Extended Essay, I frequently struggle to allocate daily study time "
        "effectively. Each assignment differs in deadline urgency, academic importance, cognitive difficulty, and "
        "expected workload. Static paper checklists and basic spreadsheets only record task names and due dates "
        "without automated prioritization or secure multi-device synchronization. Consequently, low-impact "
        "homework is often finished prematurely while urgent coursework is delayed, and real focus hours per "
        "subject remain unmeasured. To resolve this, I developed SYNTRIQ, a multi-user Smart Study Planner and "
        "Real-Time Time Intelligence web platform that mathematically ranks assignments, secures personal weekly "
        "routines behind Google Sign-In, and tracks verified focus sessions."
    )

    crit_a_client = (
        "The primary clients are myself and fellow IB Diploma students at my school (tested by peer learners) who "
        "need a private, distraction-free study workspace accessible from school laptops and personal phones. "
        "Client consultation revealed three mandatory constraints: each student's schedule and routines must be "
        "strictly isolated by account login, task creation must remain fast without forcing duration estimates, "
        "and study timers must measure genuine focus time without losing seconds during page reloads."
    )

    crit_a_context = (
        "I selected a web architecture using Python, Flask, Firebase Google Authentication, Cloud Firestore, "
        "SQLite, and HTML5/CSS3/Vanilla JavaScript instead of a local desktop executable or spreadsheet macro. "
        "Python offers clean datetime arithmetic and high readability, while Flask stays lightweight for serverless "
        "Vercel deployment. Cloud Firestore provides NoSQL UID-scoped persistence and real-time rules enforcement, "
        "while parameterized SQLite ensures fast offline testing despite ephemeral serverless filesystem limits."
    )
    crit_a_words = count_words(crit_a_scenario + " " + crit_a_client + " " + crit_a_context)

    crit_c_prose = (
        "The SYNTRIQ system model decomposes into browser presentation templates, a Flask authentication and routing "
        "controller, a deterministic weighted priority algorithm, and a dual-mode persistence layer enforcing UID "
        "isolation across Cloud Firestore and relational SQLite. Client interactions flow through authenticated REST "
        "endpoints verified by cryptographic Firebase ID tokens before touching database records. Together with an "
        "event-driven timestamp lock and unit, integration, and cross-UID security tests, these components ensure "
        "accurate ranking and leak-free synchronization."
    )
    crit_c_words = count_words(crit_c_prose)

    crit_d_blocks = [
        {
            "title": "1. Modular MVC & Dual-Store UID Abstraction",
            "code": (
                "E:\\Aasu\\\n"
                "├── priority_calculator.py  # Pure priority scoring & date helpers (Algorithmic Model)\n"
                "├── firebase_auth.py        # Google/Firebase ID token cryptographic verification\n"
                "├── store.py                # Verified-UID router between Cloud Firestore & SQLite\n"
                "├── firestore_store.py      # REST client scoped under users/{uid}/... via ID token\n"
                "├── database.py             # Parameterized SQLite schema & CRUD scoped by User_UID\n"
                "├── app.py                  # Flask routes, @login_required, input validation & APIs\n"
                "└── static/js/              # firebase-auth.js (OAuth) & main.js (Pomodoro, UI sync)"
            ),
            "prose": (
                "Decoupling Flask route controllers (app.py) from algorithmic logic (priority_calculator.py) and storage "
                "abstraction (store.py) keeps each layer modular and independently testable. Flask was chosen over "
                "heavier frameworks like Django because SYNTRIQ needs no ORM migration overhead on serverless Vercel "
                "functions; the disadvantage is implementing explicit session guards (@login_required) manually. Every "
                "request routes by verified Firebase UID into Cloud Firestore (firestore_store.py) in production or "
                "isolated SQLite tables locally. While the testing strategy effectively validates functional routes and "
                "UID dispatch, structural separation itself relies on code organization rather than unit assertions."
            ),
        },
        {
            "title": "2. Weighted Priority Algorithm & Neutral Workload Fallback",
            "code": (
                "def calculate_priority(deadline, difficulty, importance, estimated_hours=None, current_date=None):\n"
                "    difficulty_val, importance_val = int(difficulty), int(importance)\n"
                "    if not (1 <= difficulty_val <= 5) or not (1 <= importance_val <= 5):\n"
                "        raise ValueError(\"Difficulty and Importance must be between 1 and 5.\")\n"
                "    urgency = calculate_urgency(deadline, current_date)\n"
                "    workload = calculate_workload(estimated_hours)  # Returns 3 when omitted\n"
                "    score = (0.4 * urgency) + (0.3 * importance_val) + (0.2 * difficulty_val) + (0.1 * workload)\n"
                "    return round(score, 2)"
            ),
            "prose": (
                "Implementing the ranking engine in Python provides exact date-delta arithmetic and readable exception "
                "handling compared to fragile spreadsheet formulas, though Python's interpreted execution is slower "
                "than compiled C++—negligible for sub-1,000 student tasks. The weighted equation emphasizes deadline "
                "urgency (40%) and importance (30%) over difficulty (20%) and workload (10%), returning normalized scores "
                "from 1.00 to 5.00. Crucially, calculate_workload() substitutes a neutral value of 3 when target hours "
                "are omitted, preserving ranking fairness. Deterministic unit tests thoroughly validate full-input "
                "boundaries (5.00 max) and neutral-workload edge cases (0.30 contribution)."
            ),
        },
        {
            "title": "3. Firebase Google OAuth & Strict Database-Level UID Isolation",
            "code": (
                "// firestore.rules (enforced server-side by Google Cloud Firestore)\n"
                "function isOwner(uid) { return request.auth != null && request.auth.uid == uid; }\n"
                "function ownerUnchanged() {\n"
                "  return resource == null || !('ownerUid' in resource.data)\n"
                "      || request.resource.data.ownerUid == resource.data.ownerUid;\n"
                "}\n"
                "match /users/{uid}/tasks/{taskId} {\n"
                "  allow read, delete: if isOwner(uid);\n"
                "  allow create: if isOwner(uid) && request.resource.data.ownerUid == uid;\n"
                "  allow update: if isOwner(uid) && request.resource.data.ownerUid == uid && ownerUnchanged();\n"
                "}"
            ),
            "prose": (
                "Relying solely on Firebase Auth eliminates password-storage risk and accelerates login, at the cost "
                "of requiring Google accounts and active internet during OAuth sign-in. After Google login, "
                "firebase_auth.verify_firebase_id_token() validates JWT signatures before setting an HttpOnly Flask "
                "session cookie. Because firestore_store.py forwards the user's Bearer ID token directly to Firestore's "
                "REST API, server-side firestore.rules verify request.auth.uid == uid and guard ownerUnchanged() against "
                "null resources during document creation. The testing strategy effectively verifies two-user workspace "
                "isolation and cross-UID rejection (HTTP 404/401) across tasks, routines, and timers."
            ),
        },
        {
            "title": "4. Two-Tier Input Validation & Parameterized Data Integrity",
            "code": (
                "if not title or not subject or not deadline:\n"
                "    flash(\"Please complete all required fields\", \"danger\")\n"
                "    return render_template(\"add_task.html\", form_data=request.form), 400\n"
                "try:\n"
                "    diff_int, imp_int = int(difficulty), int(importance)\n"
                "    hours_float = float(estimated_hours) if estimated_hours else None\n"
                "except (ValueError, TypeError):\n"
                "    flash(\"Invalid input\", \"danger\")\n"
                "    return render_template(\"add_task.html\", form_data=request.form), 400"
            ),
            "prose": (
                "Validation operates defensively across both Flask controllers and database schemas. In app.py, "
                "route handlers strip strings, catch ValueError/TypeError exceptions, and reject out-of-range metrics "
                "with HTTP 400 while preserving entered form fields. At the storage layer, firestore.rules validate "
                "field types, difficulty/importance bounds (1–5), and Pending/Completed enumerations, while SQLite "
                "uses CHECK constraints and parameterized placeholders (?) to block SQL injection. Combining NoSQL "
                "flexibility with strict rules trades rigid relational joins for effortless cloud scaling. Automated "
                "HTTP POST tests reliably verify rejection of malformed inputs."
            ),
        },
        {
            "title": "5. Dynamic Study Plan Ranking & What-If Priority Simulator",
            "code": (
                "def get_study_plan(uid, id_token=None, current_date=None):\n"
                "    pending = get_pending_tasks(uid, current_date)\n"
                "    for task in pending:\n"
                "        score = calculate_priority(task[\"Task_Deadline\"], task[\"Task_Difficulty\"],\n"
                "                                   task[\"Task_Importance\"], task.get(\"Estimated_Hours\"), current_date)\n"
                "        task[\"Priority_Score\"] = score\n"
                "    pending.sort(key=lambda t: (-t[\"Priority_Score\"], t[\"Task_Deadline\"]))\n"
                "    return pending"
            ),
            "prose": (
                "Because urgency increases dynamically every calendar day, cached priority scores would quickly become "
                "inaccurate. Consequently, get_study_plan() recalculates every pending task under the signed-in UID "
                "against today's date, attaches sub-milestones, flags overdue tasks, and sorts records using Python's "
                "O(n log n) Timsort with compound key (-Priority_Score, Task_Deadline) to break priority ties by "
                "earliest deadline. Furthermore, /api/simulate-priority lets students test hypothetical deadline shifts "
                "in memory without altering database records. The testing strategy effectively validates descending rank "
                "ordering and exact What-If score deltas."
            ),
        },
        {
            "title": "6. Drift-Free Real-Time Tracking & Per-User Single-Session Lock",
            "code": (
                "# Elapsed calculation surviving reloads & browser throttling:\n"
                "elapsed = accum if is_paused else accum + max(0, round(time.time() - start_ts))\n"
                "# Switching tasks prompts confirmation; force_switch preserves previous session:\n"
                "if existing_active and existing_active[\"Task_ID\"] != str(task_id):\n"
                "    if not force: return {\"conflict\": True, \"has_conflict\": True, ...}\n"
                "    stop_tracking_session(uid, id_token)"
            ),
            "prose": (
                "JavaScript setInterval clocks lose seconds whenever browsers throttle background tabs or close. "
                "SYNTRIQ solves this by persisting a UNIX Start_Timestamp and Accumulated_Seconds per user inside "
                "active_session/current (or SQLite ActiveSession scoped by User_UID). Pausing commits elapsed seconds "
                "into Accumulated_Seconds, while launching another task returns a conflict payload unless force_switch "
                "cleanly stops and preserves the prior session. Server timestamps trade a lightweight network sync request "
                "for cross-device clock accuracy. Integration tests verify conflict detection, pause/resume retention, "
                "logout preservation, and completion auto-stop."
            ),
        },
        {
            "title": "7. Time Intelligence Analytics & Personal Weekly Routines",
            "code": (
                "# Aggregating completed StudySessions + live ActiveSession elapsed seconds\n"
                "live_today = today_seconds + active_elapsed\n"
                "subject_breakdown.sort(key=lambda x: x[\"seconds\"], reverse=True)\n"
                "# Weekly Routines sorted chronologically by day order and startTime\n"
                "routines.sort(key=lambda r: (DAYS_ORDER.get(r[\"dayOfWeek\"], 9), r[\"startTime\"]))"
            ),
            "prose": (
                "The Time Intelligence engine aggregates completed StudySessions alongside live ActiveSession seconds so "
                "daily, weekly, monthly, and subject breakdowns update continuously mid-session. Consecutive study "
                "streaks derive strictly from verified session and completion dates rather than login hits. Choosing "
                "Python server-side aggregation over raw SQL GROUP BY inside Firestore simplifies dual-backend parity "
                "(Firestore + SQLite), though very large multi-year histories would benefit from monthly rollup caches. "
                "Alongside analytics, /routines isolates personal weekly slots chronologically per UID. Automated suites "
                "verify live metric updates, streaks, and zero cross-account routine visibility."
            ),
        },
        {
            "title": "8. Client Live Preview, Focus Kitchen Timer & Legacy Migration",
            "code": (
                "function renderActiveDigits() {\n"
                "  let currentElapsed = data.elapsed_seconds || 0;\n"
                "  if (!data.is_paused) {\n"
                "    currentElapsed = Math.round(currentElapsed + ((Date.now() / 1000) - clientSyncTime));\n"
                "  }\n"
                "  if (digitsEl) digitsEl.textContent = formatDurationHms(currentElapsed);\n"
                "}"
            ),
            "prose": (
                "Using HTML5, CSS3, and vanilla JavaScript (main.js and firebase-auth.js) instead of a heavy frontend "
                "SPA framework like React eliminates bundler build steps and keeps page loads fast, though complex UI "
                "widgets require disciplined DOM state updates. The client synchronizes Pomodoro SVG countdowns against "
                "Date.now() and Page Visibility API events, plays offline Web Audio chimes, and clears memory cleanly on "
                "logout. An explicit /api/migrate-legacy-data guard quarantines pre-auth records under __legacy__. "
                "While Python suites verify APIs and DOM presence, audio synthesis and visual polish rely on manual QA."
            ),
        },
    ]
    crit_d_words = sum(count_words(b["prose"]) for b in crit_d_blocks)

    crit_e_criteria = [
        ("1. Two-tier input validation", "Achieved — Both app.py route handlers (HTTP 400 + flash warnings) and Firestore/SQLite rules reject blank fields, invalid dates, non-numeric inputs, and out-of-range ratings across automated POST tests."),
        ("2. Google Auth & strict UID isolation", "Achieved — Firebase Google OAuth + JWT verification isolates every workspace under users/{uid}/... enforced by firestore.rules and SQLite User_UID; cross-UID requests return 404/401."),
        ("3. Add/Edit/Delete tasks with optional hours", "Achieved — Full CRUD lifecycle verified: new tasks save with 0m focus time, edits immediately recompute Priority_Score, and deletions cascade subtasks and active sessions cleanly."),
        ("4. Weighted priority & neutral fallback", "Achieved — priority_calculator.py executes 0.4U + 0.3I + 0.2D + 0.1W reliably and substitutes a neutral workload score of 3 whenever target hours are omitted."),
        ("5. Algorithmic Study Plan & Simulator", "Achieved — /study-plan displays pending tasks sorted strictly descending by Priority_Score with earliest-deadline tie-breaking, paired with the non-destructive What-If Simulator."),
        ("6. Dashboard, overdue & 7-day heatmap", "Achieved — Dashboard highlights overdue items, isolates 7-day upcoming deadlines, renders the 7-Day Workload Heatmap, and flags daily overload beyond configurable capacity."),
        ("7. Personal Weekly Routines & Settings", "Achieved — Authenticated users manage private recurring weekly schedules (/routines) and personal capacity/Pomodoro preferences (/settings) synchronized across devices."),
        ("8. Completion & sub-milestones", "Achieved — One-click completion logs Completed_At timestamps and auto-stops active timers on that task, while AJAX endpoints toggle task sub-milestones seamlessly."),
        ("9. Real-time tracking & Time Intelligence", "Achieved — Server UNIX timestamps maintain drift-free accuracy across pause/resume/logout and populate real-time subject breakdowns, calendar spans, and focus streaks."),
        ("10. Cloud persistence, responsive UI & .ics export", "Achieved — Live Vercel deployment + Cloud Firestore persists data across sessions, responsive CSS adapts desktop/mobile drawers, and /export/calendar.ics generates RFC-5545 feeds."),
    ]

    crit_e_tech_eval = (
        "Evaluating the chosen technology stack confirms clear architectural strengths alongside manageable trade-offs. "
        "Python and Flask accelerated backend prototyping and unit testing compared to Java or C++, though lacking "
        "static compile-time type checks requires disciplined runtime validation. Cloud Firestore resolved Vercel's "
        "read-only serverless storage limitation while enforcing hardware-isolated security rules per UID, unlike "
        "single-file SQLite or flat CSV storage; however, Firestore's REST API introduces minor network latency on "
        "initial workspace load. Finally, vanilla JavaScript and Jinja2 avoided React bundle overhead and simplified "
        "maintenance, while Firebase Auth removed custom credential risks despite introducing Google-account dependency."
    )

    crit_e_improvements = (
        "To further elevate accuracy and user value beyond the 52 verified automated tests, three extensions are "
        "recommended. First, implementing an adaptive calibration model comparing historical Estimated_Hours against "
        "actual Total_Tracked_Seconds per subject would personalize workload predictions dynamically. Second, adding "
        "an IndexedDB offline write queue would allow students to pause or log sessions without connectivity and sync "
        "when back online. Third, integrating automated Playwright end-to-end UI tests into GitHub Actions alongside "
        "bidirectional Google Calendar synchronization would verify live DOM timing interactions continuously and send "
        "proactive assignment alerts."
    )
    crit_e_words = count_words(" ".join(d for _, d in crit_e_criteria) + " " + crit_e_tech_eval + " " + crit_e_improvements)
    total_words = crit_a_words + crit_c_words + crit_d_words + crit_e_words

    # =========================================================================
    # COVER PAGE
    # =========================================================================
    for _ in range(5):
        sp = doc.add_paragraph()
        sp.paragraph_format.space_after = Pt(10)

    p_kicker = doc.add_paragraph()
    p_kicker.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_kicker.paragraph_format.space_after = Pt(2)
    rk = p_kicker.add_run("Computer Science")
    rk.bold = True
    rk.font.size = Pt(16)
    rk.font.color.rgb = SLATE

    p_subk = doc.add_paragraph()
    p_subk.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_subk.paragraph_format.space_after = Pt(28)
    rs = p_subk.add_run("Internal Assessment")
    rs.font.size = Pt(13.5)
    rs.font.color.rgb = MUTED

    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_after = Pt(10)
    rt = p_title.add_run("SYNTRIQ: Smart Study Planner &\nTime Intelligence System")
    rt.bold = True
    rt.font.size = Pt(24)
    rt.font.color.rgb = NAVY

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_after = Pt(28)
    rsub = p_sub.add_run(
        "Algorithmic Task Prioritization, Multi-User Firebase UID Isolation &\nDrift-Free Academic Focus Analytics"
    )
    rsub.font.size = Pt(12)
    rsub.font.color.rgb = ORANGE

    # Centered metadata pill table
    meta_tbl = doc.add_table(rows=4, cols=2)
    meta_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(meta_tbl, color="CBD5E1", sz="6")
    meta_rows = [
        ("Developer / Author", "Arjun Kahar"),
        ("Project Stack", "Python Flask, Firebase Auth (Google OAuth), Cloud Firestore, SQLite, JS"),
        ("Live Production URL", "https://study-nine-flame.vercel.app/"),
        ("Total IB IA Word Count", f"{total_words} words (Criterion A–E Prose; IB Maximum: 2,000 words)"),
    ]
    for i, (k, v) in enumerate(meta_rows):
        row = meta_tbl.rows[i]
        prevent_row_split(row)
        c0, c1 = row.cells[0], row.cells[1]
        c0.width = Inches(2.0)
        c1.width = Inches(4.4)
        set_cell_shading(c0, "FFF7ED" if i == 3 else "F8FAFC")
        set_cell_shading(c1, "FFFFFF")
        set_cell_margins(c0, top=80, bottom=80, left=120, right=120)
        set_cell_margins(c1, top=80, bottom=80, left=120, right=120)
        r0 = c0.paragraphs[0].add_run(k)
        r0.bold = True
        r0.font.size = Pt(9.5)
        r0.font.color.rgb = DARK_ORANGE if i == 3 else NAVY
        r1 = c1.paragraphs[0].add_run(v)
        r1.bold = (i == 3)
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = BODY

    p_wc = doc.add_paragraph()
    p_wc.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_wc.paragraph_format.space_before = Pt(28)
    rwc = p_wc.add_run(
        f"Prose Word Breakdown:  Criterion A: {crit_a_words}  •  "
        f"Criterion C Overview: {crit_c_words}  •  "
        f"Criterion D: {crit_d_words}  •  "
        f"Criterion E: {crit_e_words}  •  "
        f"Total: {total_words} words"
    )
    rwc.font.size = Pt(9)
    rwc.font.color.rgb = MUTED

    # =========================================================================
    # CRITERION A
    # =========================================================================
    add_criterion_heading(doc, "Criterion A - Problem Specification", page_break=True)
    add_sub_heading(doc, "Problem Scenario")
    add_body_para(doc, crit_a_scenario)
    add_sub_heading(doc, "Client & End-User Requirements")
    add_body_para(doc, crit_a_client)
    add_sub_heading(doc, "Computational Context & Technology Selection")
    add_body_para(doc, crit_a_context)
    add_word_badge(doc, crit_a_words)

    add_sub_heading(doc, "Technology & Language Justification (Advantages vs. Disadvantages)")
    tech_rows = [
        ("Python 3 + Flask", "Rapid MVC development, clean datetime/math libraries, native JSON APIs, lightweight for Vercel serverless.", "Dynamic typing catches fewer errors at compile time; Flask requires manual auth/session guards unlike Django."),
        ("Cloud Firestore + Rules", "Zero-server scaling on Vercel, real-time cross-device sync, cryptographic UID rules enforced at database level.", "NoSQL lacks relational JOIN queries; requires active internet and careful rules design to prevent permission errors."),
        ("SQLite (Local / QA)", "Zero-config ACID transactions, CHECK constraints, foreign-key cascades, deterministic offline test isolation.", "File-based locking limits high write concurrency; serverless containers reset ephemeral local files between deploys."),
        ("Firebase Google OAuth", "Industry-standard OAuth security, zero password storage liability, automatic persistent sessions across refreshes.", "Depends on Google Identity providers and Firebase Console domain allowlisting before production login works."),
        ("HTML5, CSS3 & Vanilla JS", "Zero bundler build overhead, instant page loads, direct Date.now() & Web Audio API control for drift-free timers.", "Verbose DOM updates for highly dynamic views compared to component-state frameworks such as React."),
    ]
    tt_tbl = doc.add_table(rows=1 + len(tech_rows), cols=3)
    tt_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(tt_tbl, color="94A3B8", sz="4")
    tt_widths = [Inches(1.45), Inches(2.65), Inches(2.65)]
    prevent_row_split(tt_tbl.rows[0])
    for j, th in enumerate(["Technology / Language", "Advantages (Why Chosen)", "Disadvantages & Trade-Offs"]):
        c = tt_tbl.cell(0, j)
        c.width = tt_widths[j]
        set_cell_shading(c, "F1F5F9")
        set_cell_margins(c, top=65, bottom=65, left=80, right=80)
        r = c.paragraphs[0].add_run(th)
        r.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = NAVY
    for i, tr in enumerate(tech_rows, 1):
        row = tt_tbl.rows[i]
        prevent_row_split(row)
        for j, val in enumerate(tr):
            c = row.cells[j]
            c.width = tt_widths[j]
            set_cell_margins(c, top=55, bottom=55, left=80, right=80)
            rc = c.paragraphs[0].add_run(val)
            rc.bold = (j == 0)
            rc.font.size = Pt(8.2)
            rc.font.color.rgb = BODY

    add_sub_heading(doc, "Success Criteria")
    p_intro = doc.add_paragraph("My application will:")
    p_intro.paragraph_format.space_after = Pt(3)
    p_intro.runs[0].font.size = Pt(10)

    success_criteria = [
        "Authenticate users via Firebase Google OAuth and enforce strict database-level UID isolation so each user only reads and writes their own routines, tasks, settings, and study sessions.",
        "Validate all task and routine inputs at both controller and schema layers (non-empty strings, valid dates, 1–5 integer bounds, positive target hours) with clear error feedback.",
        "Add, edit, and delete study tasks while dynamically recalculating Priority_Score and cascading subtask/active-timer cleanup safely.",
        "Calculate weighted priority scores (0.4×Urgency + 0.3×Importance + 0.2×Difficulty + 0.1×Workload) with a neutral workload fallback of 3 when target hours are omitted.",
        "Generate an Algorithmic Study Plan sorted descending by priority score (ties broken by earliest deadline) paired with an interactive What-If simulator.",
        "Highlight overdue tasks and upcoming 7-day deadlines alongside a 7-Day Workload Heatmap and configurable Daily Capacity Meter.",
        "Provide per-user Personal Weekly Routines (/routines) and Account Preferences (/settings) synchronized across devices.",
        "Support one-click task completion with timestamps and interactive AJAX sub-milestones per task.",
        "Track drift-free real-time focus sessions using server UNIX timestamps, per-UID single-session locks, and a live Time Intelligence analytics dashboard.",
        "Persist workspace data on Cloud Firestore (with SQLite fallback), render responsively across desktop and mobile viewports, and export RFC-5545 (.ics) calendars.",
    ]
    for idx, item in enumerate(success_criteria, 1):
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.first_line_indent = Inches(-0.2)
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(2.5)
        p.paragraph_format.line_spacing = 1.12
        rn = p.add_run(f"{idx}. ")
        rn.bold = True
        rn.font.size = Pt(9.5)
        rn.font.color.rgb = DARK_ORANGE
        rt = p.add_run(item)
        rt.font.size = Pt(9.5)
        rt.font.color.rgb = BODY

    # =========================================================================
    # CRITERION B
    # =========================================================================
    add_criterion_heading(doc, "Criterion B - Planning", page_break=True)
    add_sub_heading(doc, "Decomposing Problems")

    decomp_cards = [
        (
            "1. Multi-User Auth & UID Persistence",
            [
                "Identity: Verify Google/Firebase ID tokens in firebase_auth.py using google-auth / Admin SDK.",
                "Cloud Firestore: Route verified UID operations to users/{uid}/... via firestore_store.py.",
                "Security & Fallback: Enforce firestore.rules ownership checks; scope SQLite tables with User_UID.",
            ],
        ),
        (
            "2. Priority Engine (priority_calculator.py)",
            [
                "Date Logic: parse_date(), days_remaining(), and is_overdue() deterministic helpers.",
                "Factor Mapping: Urgency (1–5) from deadline proximity; Workload (1–5, neutral fallback 3).",
                "Composite Score: 0.4U + 0.3I + 0.2D + 0.1W normalized between 1.00 and 5.00.",
            ],
        ),
        (
            "3. Controller & Validation (app.py)",
            [
                "Routes: /login, /dashboard, /study-plan, /routines, /settings, /time-intelligence, /add-task.",
                "REST APIs: /auth/session, subtasks, /api/simulate-priority, and /api/timer/* endpoints.",
                "Validation: HTTP 400 with flash warnings plus CSRF-safe HttpOnly session cookies.",
            ],
        ),
        (
            "4. Real-Time Time Intelligence Engine",
            [
                "Single-Session Lock: active_session/current (or SQLite ID=1 per UID) prevents concurrent drift.",
                "Drift-Free Clock: Server Start_Timestamp + Accumulated_Seconds survive browser reloads.",
                "Analytics: Subject breakdown, streak count, focus vs. calendar span, and session history.",
            ],
        ),
        (
            "5. Responsive UI & Focus Tools",
            [
                "Templates: Consistent SYNTRIQ design across login, profile dropdown, heatmap, and mobile drawer.",
                "Client JS: Live priority preview, circular SVG Pomodoro modal, Web Audio chimes, account switching.",
                "Export: One-click RFC-5545 .ics calendar export and print stylesheet.",
            ],
        ),
        (
            "6. Verification, Deployment & QA",
            [
                "Criterion B & Feature Tests: run_tests.py (14), test_syntriq3.py (20), Time Intel (11).",
                "Security Verification: test_multi_user_auth.py (7) testing cross-UID rejection and isolation.",
                "Production: GitHub CI pushes auto-deployed live to Vercel with Cloud Firestore rules active.",
            ],
        ),
    ]

    dtbl = doc.add_table(rows=3, cols=2)
    dtbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(dtbl, color="CBD5E1", sz="6")
    for idx, (card_title, bullets) in enumerate(decomp_cards):
        r_idx, c_idx = divmod(idx, 2)
        if c_idx == 0:
            prevent_row_split(dtbl.rows[r_idx])
        cell = dtbl.cell(r_idx, c_idx)
        cell.width = Inches(3.35)
        set_cell_shading(cell, "F8FAFC")
        set_cell_margins(cell, top=80, bottom=80, left=110, right=110)
        p0 = cell.paragraphs[0]
        p0.paragraph_format.space_after = Pt(4)
        rh = p0.add_run(card_title)
        rh.bold = True
        rh.font.size = Pt(9.6)
        rh.font.color.rgb = NAVY
        add_p_bottom_border(p0, color="E2E8F0", sz="6")
        for b in bullets:
            pb = cell.add_paragraph()
            pb.paragraph_format.left_indent = Inches(0.14)
            pb.paragraph_format.first_line_indent = Inches(-0.14)
            pb.paragraph_format.space_after = Pt(2)
            pb.paragraph_format.line_spacing = 1.12
            rb = pb.add_run(f"• {b}")
            rb.font.size = Pt(8.6)
            rb.font.color.rgb = BODY

    add_sub_heading(doc, "Planning the Computational Thinking Process")
    plan_rows = [
        ("PHASE", "Phase 1: Problem Specification & Setup (Week 1)", "", "", "", ""),
        ("ROW", "Define scope, success criteria & configure Python/Flask/SQLite/Git", "4 days", "None", "Environment setup", "Plan requirements, design repo structure, install Flask, confirm readiness"),
        ("PHASE", "Phase 2: System Architecture & Schema Design (Week 2)", "", "", "", ""),
        ("ROW", "MVC diagrams, UI wireframes, relational SQLite & Firestore schema", "5 days", "Phase 1 complete", "Priority formula design", "Design ERD, UML & users/{uid} paths, create schema constraints"),
        ("PHASE", "Phase 3: Priority Engine & Core CRUD (Weeks 3–4)", "", "", "", ""),
        ("ROW", "Implement priority_calculator.py & parameterized CRUD helpers", "8 days", "Schema design", "Dashboard templates", "Code scoring math, CRUD & get_study_plan(), unit-test edge cases"),
        ("PHASE", "Phase 4: Flask Controller, Interactive UI & Time Intel (Weeks 5–7)", "", "", "", ""),
        ("ROW", "Routes, What-If Simulator, Pomodoro modal & ActiveSession timer", "10 days", "Priority & CRUD", "Responsive CSS styling", "Build Jinja2 forms, main.js sync & Time Intelligence aggregations"),
        ("PHASE", "Phase 5: Firebase Google Auth & Multi-User UID Isolation (Weeks 8–9)", "", "", "", ""),
        ("ROW", "firebase_auth.py, store.py, firestore_store.py, firestore.rules, /routines", "7 days", "Phase 4 complete", "Login/Settings UI", "Verify ID tokens, enforce strict Firestore rules, add migration guard"),
        ("PHASE", "Phase 6: Automated QA, Vercel Deployment & Evaluation (Week 10)", "", "", "", ""),
        ("ROW", "Run 52 automated tests, cross-viewport Playwright QA & live deployment", "6 days", "All modules complete", "IA Documentation", "Execute 4 test suites, deploy live on Vercel, evaluate success criteria"),
    ]

    ptbl = doc.add_table(rows=1 + len(plan_rows), cols=5)
    ptbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(ptbl, color="94A3B8", sz="4")
    p_widths = [Inches(1.65), Inches(0.65), Inches(1.25), Inches(1.15), Inches(2.05)]
    p_headers = ["Task", "Duration", "Dependencies", "Concurrencies", "CT Subtasks (Plan / Design / Develop / Test / Evaluate)"]
    prevent_row_split(ptbl.rows[0])
    for j, htxt in enumerate(p_headers):
        cell = ptbl.cell(0, j)
        cell.width = p_widths[j]
        set_cell_shading(cell, "F1F5F9")
        set_cell_margins(cell, top=70, bottom=70, left=80, right=80)
        r = cell.paragraphs[0].add_run(htxt)
        r.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = NAVY

    for i, item in enumerate(plan_rows, 1):
        row = ptbl.rows[i]
        prevent_row_split(row)
        if item[0] == "PHASE":
            merged = row.cells[0].merge(row.cells[4])
            set_cell_shading(merged, "FFF7ED")
            set_cell_margins(merged, top=60, bottom=60, left=80, right=80)
            rp = merged.paragraphs[0].add_run(item[1])
            rp.bold = True
            rp.font.size = Pt(8.6)
            rp.font.color.rgb = RGBColor(0x9A, 0x34, 0x12)
        else:
            for j in range(5):
                cell = row.cells[j]
                cell.width = p_widths[j]
                set_cell_margins(cell, top=65, bottom=65, left=80, right=80)
                rc = cell.paragraphs[0].add_run(item[j + 1])
                rc.font.size = Pt(8.3)
                rc.font.color.rgb = BODY

    # =========================================================================
    # CRITERION C
    # =========================================================================
    add_criterion_heading(doc, "Criterion C - System Overview", page_break=True)
    add_body_para(doc, crit_c_prose)
    add_word_badge(doc, crit_c_words)

    add_sub_heading(doc, "System Models")
    add_figure(
        doc,
        paths["arch_diagram"],
        "Image 1: Overall System Structure, MVC Layers & Firebase UID-Isolated Dual-Store Architecture",
        max_width_in=6.6,
        max_height_in=2.7,
    )
    add_figure(
        doc,
        paths["uml_erd_diagram"],
        "Image 2: UML Use Case Diagram (Left) and UID-Isolated Firestore / SQLite Schema ERD (Right)",
        max_width_in=6.6,
        max_height_in=2.7,
    )

    add_sub_heading(doc, "Implemented User Interface & Application Screenshots")
    screenshots_meta = [
        ("login", "Image 3: Firebase Google OAuth Authentication Screen (/login) Protecting Personal Study Workspaces", 5.8, 3.6),
        ("dashboard", "Image 4: Study Dashboard Showing 7-Day Workload Heatmap, Capacity Meter, Overdue Banner, Task Table & Live Session Pill", 6.2, 4.7),
        ("study_plan", "Image 5: Algorithmic Study Plan Sorted Descending by Priority Score with Factor Tags & Sub-Milestones", 6.2, 4.7),
        ("routines", "Image 6: Personal UID-Isolated Weekly Study Routines Manager (/routines)", 6.2, 4.0),
        ("time_intel", "Image 7: Real-Time Time Intelligence Dashboard Displaying Live Session Clock, Subject Distribution & Session Logs", 5.6, 5.2),
        ("add_task", "Image 8: Add Study Task Form with Quick Deadline Chips, Optional Target Hours & Live Priority Score Preview", 6.1, 3.9),
        ("simulator", "Image 9: Interactive What-If Priority Simulator Computing Non-Destructive Score Deltas", 6.1, 3.9),
        ("pomodoro", "Image 10: Focus Kitchen Pomodoro Timer Modal with Circular SVG Countdown & Offline Soundscapes", 5.8, 3.7),
        ("mobile", "Image 11: Responsive Mobile Viewport (390px) Adapting Cards, Heatmap & Touch Controls", 3.1, 5.0),
    ]
    for key, cap, mw, mh in screenshots_meta:
        add_figure(doc, paths[key], cap, max_width_in=mw, max_height_in=mh)

    add_sub_heading(doc, "Algorithms as Components in a System Model")
    algo_tbl = doc.add_table(rows=1, cols=2)
    algo_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(algo_tbl, color="CBD5E1", sz="6")
    prevent_row_split(algo_tbl.rows[0])
    ac0, ac1 = algo_tbl.cell(0, 0), algo_tbl.cell(0, 1)
    ac0.width, ac1.width = Inches(3.38), Inches(3.38)
    set_cell_shading(ac0, "F8FAFC")
    set_cell_shading(ac1, "F8FAFC")
    set_cell_margins(ac0, top=80, bottom=80, left=100, right=100)
    set_cell_margins(ac1, top=80, bottom=80, left=100, right=100)

    sql_text = (
        "Core SQLite / Firestore Data Model:\n\n"
        "CREATE TABLE Tasks (\n"
        "  Task_ID INTEGER PRIMARY KEY,\n"
        "  User_UID TEXT NOT NULL,\n"
        "  Task_Title TEXT NOT NULL,\n"
        "  Task_Subject TEXT NOT NULL,\n"
        "  Task_Deadline TEXT NOT NULL,\n"
        "  Task_Difficulty INT CHECK(1..5),\n"
        "  Task_Importance INT CHECK(1..5),\n"
        "  Target_Hours REAL DEFAULT NULL,\n"
        "  Total_Tracked_Seconds INT DEFAULT 0,\n"
        "  Priority_Score REAL NOT NULL,\n"
        "  Task_Status TEXT DEFAULT 'Pending'\n"
        ");\n\n"
        "Firestore Path Ownership Rule:\n"
        "  users/{uid}/tasks/{taskId}\n"
        "  users/{uid}/routines/{routineId}\n"
        "  users/{uid}/study_sessions/{id}\n"
        "  allow read: if request.auth.uid == uid;"
    )
    pseudo_text = (
        "Priority & Tracking Pseudocode:\n\n"
        "FUNCTION calculate_priority(dl, diff, imp, hrs):\n"
        "  days = dl - today\n"
        "  IF days <= 1 THEN u = 5\n"
        "  ELSE IF days <= 3 THEN u = 4\n"
        "  ELSE IF days <= 7 THEN u = 3\n"
        "  ELSE IF days <= 14 THEN u = 2\n"
        "  ELSE u = 1\n"
        "  IF hrs IS NULL OR hrs <= 0 THEN w = 3\n"
        "  ELSE w = map_hours_1_to_5(hrs)\n"
        "  RETURN ROUND(0.4*u+0.3*imp+0.2*diff+0.1*w, 2)\n\n"
        "FUNCTION start_tracking(uid, task_id, force):\n"
        "  curr = get_active_session(uid)\n"
        "  IF curr AND curr.task != task_id:\n"
        "    IF NOT force: RETURN conflict_prompt\n"
        "    ELSE: stop_tracking_session(uid)\n"
        "  save_active(uid, task_id, now(), accum=0)"
    )
    r_sql = ac0.paragraphs[0].add_run(sql_text)
    r_sql.font.name = "Consolas"
    r_sql.font.size = Pt(7.9)
    r_sql.font.color.rgb = NAVY
    r_pse = ac1.paragraphs[0].add_run(pseudo_text)
    r_pse.font.name = "Consolas"
    r_pse.font.size = Pt(7.9)
    r_pse.font.color.rgb = NAVY

    add_sub_heading(doc, "Testing Strategies")
    test_rows = [
        ("1. Input validation", "Submit POST /add-task with blank fields, non-numeric values, difficulty/importance outside 1–5, and negative hours.", "HTTP 400 returned with flash warning; invalid write blocked by both controller and schema constraints."),
        ("2. Google Auth & UID isolation", "Authenticate User A and User B via isolated clients; attempt cross-UID GET, edit, delete, timer, and routine requests.", "Users see only their own routines/tasks; cross-UID endpoints return 404/401; invalid Firebase tokens return 401."),
        ("3. Add/Edit/Delete tasks", "Create tasks with/without Estimated_Hours, update deadline and importance via /edit-task/<id>, and call delete_task().", "Task_ID generated with 0m tracked time; edits recompute Priority_Score; deletion cascades subtasks and active session."),
        ("4. Weighted priority & fallback", "Invoke calculate_priority() across boundary deadlines (today, +2d, +10d) with full hours and hours=None.", "Max inputs return 5.00; omitted hours yield exact neutral workload contribution of 0.30 (e.g., 3.40 score)."),
        ("5. Study Plan & Simulator", "Insert tasks of varying priorities; query /study-plan and POST /api/simulate-priority.", "Pending tasks sort strictly descending by Priority_Score; What-If simulator reports exact non-destructive delta."),
        ("6. Dashboard, overdue & heatmap", "Seed past-due and +3d tasks; load /dashboard and evaluate get_daily_capacity() and heatmap helpers.", "Past task flagged overdue; 7-day heatmap tallies daily hours; >6.0h capacity triggers overload alert."),
        ("7. Weekly Routines & Settings", "Add Monday/Wednesday routines and update maxSafeHours/focus length via /routines and /settings.", "Routines sort chronologically and remain invisible to other users; updated capacity persists across reloads."),
        ("8. Completion & sub-milestones", "Add/toggle subtasks via /api/tasks/<id>/subtasks and invoke complete_task() while tracking active timer.", "Subtasks toggle cleanly; task transitions to Completed with Completed_At and active session finalizes cleanly."),
        ("9. Time tracking & Time Intel", "Start timer, trigger second-task conflict with/without force_switch, pause/resume, logout, inspect /time-intelligence.", "Conflict prompts safely; force switches and preserves session; pause retains seconds; dashboard updates live."),
        ("10. Persistence & .ics export", "Reload routes across fresh DB/client sessions, inspect mobile/desktop templates, and fetch /export/calendar.ics.", "Saved data persists; routes return HTTP 200; valid text/calendar RFC-5545 VCALENDAR stream downloads cleanly."),
    ]
    ttbl = doc.add_table(rows=1 + len(test_rows), cols=3)
    ttbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_borders(ttbl, color="94A3B8", sz="4")
    t_widths = [Inches(1.65), Inches(2.55), Inches(2.55)]
    prevent_row_split(ttbl.rows[0])
    for j, th in enumerate(["Success Criterion", "Testing Strategy", "Expected Result"]):
        c = ttbl.cell(0, j)
        c.width = t_widths[j]
        set_cell_shading(c, "F1F5F9")
        set_cell_margins(c, top=70, bottom=70, left=80, right=80)
        r = c.paragraphs[0].add_run(th)
        r.bold = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = NAVY
    for i, tr in enumerate(test_rows, 1):
        row = ttbl.rows[i]
        prevent_row_split(row)
        for j, val in enumerate(tr):
            c = row.cells[j]
            c.width = t_widths[j]
            set_cell_margins(c, top=60, bottom=60, left=80, right=80)
            rc = c.paragraphs[0].add_run(val)
            rc.bold = (j == 0)
            rc.font.size = Pt(8.3)
            rc.font.color.rgb = BODY

    # =========================================================================
    # CRITERION D
    # =========================================================================
    add_criterion_heading(doc, "Criterion D - Development", page_break=True)
    for block in crit_d_blocks:
        add_dev_heading(doc, block["title"])
        add_code_box(doc, block["code"])
        add_body_para(doc, block["prose"])
    add_word_badge(doc, crit_d_words)

    # =========================================================================
    # CRITERION E
    # =========================================================================
    add_criterion_heading(doc, "Criterion E - Evaluation", page_break=True)
    add_sub_heading(doc, "Meeting Success Criteria")
    for title, desc in crit_e_criteria:
        pe = doc.add_paragraph()
        pe.paragraph_format.space_before = Pt(1)
        pe.paragraph_format.space_after = Pt(3.5)
        pe.paragraph_format.line_spacing = 1.14
        pe.paragraph_format.keep_with_next = False
        rt = pe.add_run(f"{title}: ")
        rt.bold = True
        rt.font.size = Pt(9.5)
        rt.font.color.rgb = NAVY
        rd = pe.add_run(desc)
        rd.font.size = Pt(9.4)
        rd.font.color.rgb = BODY

    # Automated verification box
    v_tbl = doc.add_table(rows=1, cols=1)
    v_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    vc = v_tbl.cell(0, 0)
    vc.width = Inches(6.75)
    set_cell_shading(vc, "F0FDF4")
    set_cell_margins(vc, top=80, bottom=80, left=120, right=120)
    set_table_borders(v_tbl, color="16A34A", sz="6")
    prevent_row_split(v_tbl.rows[0])
    vp = vc.paragraphs[0]
    rv0 = vp.add_run("Automated Verification Summary (52/52 Passed): ")
    rv0.bold = True
    rv0.font.size = Pt(9.3)
    rv0.font.color.rgb = RGBColor(0x16, 0x65, 0x34)
    rv1 = vp.add_run(
        "All 52 automated tests across run_tests.py (14/14 Criterion B tests), scripts/test_syntriq3.py "
        "(20/20 commercial QA tests), scripts/test_time_intelligence.py (11/11 Time Intelligence tests), "
        "and scripts/test_multi_user_auth.py (7/7 Firebase UID isolation & security tests) passed with zero failures."
    )
    rv1.font.size = Pt(9.2)
    rv1.font.color.rgb = BODY

    add_sub_heading(doc, "Evaluation of Chosen Technologies & Architecture")
    add_body_para(doc, crit_e_tech_eval)

    add_sub_heading(doc, "Suggesting Improvements")
    add_body_para(doc, crit_e_improvements)
    add_word_badge(doc, crit_e_words)

    p_fin = doc.add_paragraph()
    p_fin.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    rf = p_fin.add_run(f"Total IB CS IA Prose Word Count: {total_words} / 2,000 words")
    rf.bold = True
    rf.font.size = Pt(10)
    rf.font.color.rgb = DARK_ORANGE

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    doc.save(output_path)
    return {
        "output_path": output_path,
        "crit_a_words": crit_a_words,
        "crit_c_words": crit_c_words,
        "crit_d_words": crit_d_words,
        "crit_e_words": crit_e_words,
        "total_words": total_words,
    }


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DOCX_PATH
    assets = render_diagrams_and_fresh_screenshots(DOCX_ASSETS_DIR)
    stats = build_docx(assets, out_path)
    print(
        f"Generated DOCX: {stats['output_path']} | "
        f"Words: A={stats['crit_a_words']}, C={stats['crit_c_words']}, "
        f"D={stats['crit_d_words']}, E={stats['crit_e_words']}, Total={stats['total_words']}"
    )


if __name__ == "__main__":
    main()
