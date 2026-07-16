import streamlit as st
import folium
from streamlit_folium import st_folium
import gpxpy
import math
import os
from datetime import datetime, timedelta
import urllib.parse

from marathon_catalog import DEFAULT_RACE_NAME, get_fallback_route_points, get_race_config, get_race_names

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TrackTheRunner",
    page_icon="🏃",
    layout="wide",
)

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.main-title { font-size: 2.2rem; font-weight: 700; color: #1a1a2e; margin-bottom: 0; }
.subtitle { font-size: 1rem; color: #666; margin-top: 0.2rem; margin-bottom: 2rem; }
.runner-card { background: #f0f4ff; border-radius: 12px; padding: 1.2rem 1.5rem; margin-bottom: 1.5rem; border-left: 4px solid #3b5bdb; }
.runner-name { font-size: 1.4rem; font-weight: 700; color: #1a1a2e; }
.runner-bib { font-size: 0.9rem; color: #555; }
.stat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; margin-top: 0.8rem; }
.stat-box { background: white; border-radius: 8px; padding: 0.6rem 1rem; }
.stat-label { font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.05em; }
.stat-value { font-size: 1.1rem; font-weight: 600; color: #1a1a2e; }
.mile-table { width: 100%; border-collapse: collapse; margin-top: 1rem; }
.mile-table th { background: #1a1a2e; color: white; padding: 0.5rem 1rem; text-align: left; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }
.mile-table td { padding: 0.5rem 1rem; border-bottom: 1px solid #eee; font-size: 0.9rem; }
.mile-table tr:hover td { background: #f8f9ff; }
.share-box { background: #f8f9ff; border: 1px solid #dde3ff; border-radius: 10px; padding: 1rem 1.2rem; margin-top: 1.5rem; }
.share-title { font-weight: 600; font-size: 0.95rem; color: #1a1a2e; margin-bottom: 0.4rem; }
.share-hint { font-size: 0.8rem; color: #888; margin-bottom: 0.6rem; }
</style>
""", unsafe_allow_html=True)

# ── GPX path / race config ──────────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RACE_COURSES_DIR = os.path.join(BASE_DIR, "race_courses")

# ── GPX parsing ───────────────────────────────────────────────────────────────
@st.cache_data
def load_route(gpx_path=None):
    resolved_path = gpx_path
    if not resolved_path or not os.path.exists(resolved_path):
        # Fallback to Gasparilla if path not provided or doesn't exist
        resolved_path = os.path.join(RACE_COURSES_DIR, "gasparilla_distance_classic_half_marathon.gpx")
    if not os.path.exists(resolved_path):
        return [(0.0, 0.0)]
    with open(resolved_path, "r") as f:
        gpx = gpxpy.parse(f)
    points = []
    for track in gpx.tracks:
        for segment in track.segments:
            for pt in segment.points:
                points.append((pt.latitude, pt.longitude))
    return points if points else [(0.0, 0.0)]


def get_route_path(race_config):
    gpx_path = race_config.get("gpx_path")
    if gpx_path:
        resolved_path = os.path.join(BASE_DIR, gpx_path)
        if os.path.exists(resolved_path):
            return resolved_path
    return None


def load_route_for_race(race_config):
    route_path = get_route_path(race_config)
    if route_path:
        return load_route(route_path)
    fallback_points = get_fallback_route_points(race_config.get("name"))
    return [(lat, lon) for lat, lon in fallback_points]

def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.asin(math.sqrt(a))

def get_mile_markers(points):
    markers = [(0, points[0][0], points[0][1])]
    cumulative = 0.0
    last_mile = 0
    for i in range(1, len(points)):
        cumulative += haversine(points[i-1][0], points[i-1][1], points[i][0], points[i][1])
        mile = int(cumulative)
        if mile > last_mile:
            markers.append((mile, points[i][0], points[i][1]))
            last_mile = mile
    markers.append(("Finish", points[-1][0], points[-1][1]))
    return markers

def pace_to_seconds(pace_min, pace_sec):
    return pace_min * 60 + pace_sec

def build_schedule(start_dt, pace_secs, mile_markers, total_miles):
    schedule = []
    for item in mile_markers:
        mile = item[0]
        lat, lon = item[1], item[2]
        if mile == 0:
            elapsed_secs = 0
        elif mile == "Finish":
            elapsed_secs = int(total_miles * pace_secs)
        else:
            elapsed_secs = int(mile * pace_secs)
        arrival = start_dt + timedelta(seconds=elapsed_secs)
        h, rem = divmod(elapsed_secs, 3600)
        m, s = divmod(rem, 60)
        elapsed_str = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        schedule.append({"mile": mile, "lat": lat, "lon": lon, "arrival": arrival, "elapsed": elapsed_str})
    return schedule

def build_map(points, schedule):
    center = (sum(p[0] for p in points)/len(points), sum(p[1] for p in points)/len(points))
    m = folium.Map(location=center, zoom_start=13, tiles="CartoDB positron")
    folium.PolyLine(points, color="#3b5bdb", weight=3.5, opacity=0.85).add_to(m)
    folium.Marker(
        [schedule[0]["lat"], schedule[0]["lon"]],
        popup="Start",
        icon=folium.Icon(color="green", icon="play", prefix="fa")
    ).add_to(m)
    for item in schedule[1:-1]:
        folium.CircleMarker(
            location=[item["lat"], item["lon"]],
            radius=9, color="#1a1a2e", fill=True, fill_color="#3b5bdb", fill_opacity=0.9,
            popup=f"Mile {item['mile']} — {item['arrival'].strftime('%I:%M %p')}",
            tooltip=f"Mile {item['mile']}",
        ).add_to(m)
        folium.Marker(
            [item["lat"], item["lon"]],
            icon=folium.DivIcon(
                html=f'<div style="font-size:9px;font-weight:700;color:white;background:#3b5bdb;border-radius:50%;width:18px;height:18px;display:flex;align-items:center;justify-content:center;margin-left:-4px;margin-top:-4px">{item["mile"]}</div>',
                icon_size=(18, 18),
            )
        ).add_to(m)
    fin = schedule[-1]
    folium.Marker(
        [fin["lat"], fin["lon"]],
        popup=f"Finish — {fin['arrival'].strftime('%I:%M %p')}",
        icon=folium.Icon(color="red", icon="flag", prefix="fa")
    ).add_to(m)
    return m

# ── Read URL params ───────────────────────────────────────────────────────────
params = st.query_params
shared_mode = "name" in params

# ── Main UI ───────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">🏃 TrackTheRunner</div>', unsafe_allow_html=True)

if not shared_mode:
    st.markdown("### Enter your race details")
    col1, col2 = st.columns(2)
    with col1:
        runner_name = st.text_input("Your name", placeholder="Vishwa", key="name_input")
        bib = st.text_input("Bib number", placeholder="12345", key="bib_input")
    with col2:
        race_date = st.date_input("Race date", value=datetime(2026, 3, 1).date(), key="date_input")
        time_col1, time_col2, time_col3 = st.columns(3)
        with time_col1:
            start_hour_12 = st.selectbox("Hour", options=list(range(1, 13)), format_func=lambda x: f"{x:02d}", key="hour_select")
        with time_col2:
            start_minute_str = st.selectbox("Minute", options=[f"{m:02d}" for m in range(0, 60, 5)], key="min_select")
        with time_col3:
            am_pm = st.selectbox("AM/PM", options=["AM", "PM"], key="am_pm_select")
        
        # Convert 12-hour to 24-hour format
        start_hour = start_hour_12 if am_pm == "AM" and start_hour_12 != 12 else (0 if am_pm == "AM" and start_hour_12 == 12 else start_hour_12 + 12 if am_pm == "PM" and start_hour_12 != 12 else 12)
        start_min_input = int(start_minute_str)

    st.markdown("### Pick your marathon")
    race_names = get_race_names()
    selected_race_name = st.selectbox("Marathon", options=race_names, index=race_names.index(DEFAULT_RACE_NAME), key="race_select")
    race_config = get_race_config(selected_race_name)
    st.caption(f"{race_config['city']}, {race_config['country']} • {race_config['distance_miles']} miles")

    st.markdown("### Your expected pace")
    pcol1, pcol2 = st.columns(2)
    with pcol1:
        pace_min = st.number_input("Minutes", min_value=4, max_value=20, value=10, key="pace_min_input")
    with pcol2:
        pace_sec = st.number_input("Seconds", min_value=0, max_value=59, value=0, key="pace_sec_input")

    if st.button("Generate tracking plan", type="primary"):
        st.session_state["runner_name"] = runner_name
        st.session_state["bib"] = bib
        st.session_state["start_dt"] = datetime(race_date.year, race_date.month, race_date.day, start_hour, start_min_input)
        st.session_state["pace_secs"] = pace_to_seconds(pace_min, pace_sec)
        st.session_state["selected_race_name"] = race_config["name"]
        st.session_state["generated"] = True

    if not st.session_state.get("generated"):
        st.stop()

    runner_name = st.session_state["runner_name"]
    bib = st.session_state["bib"]
    start_dt = st.session_state["start_dt"]
    pace_secs = st.session_state["pace_secs"]
    selected_race_name = st.session_state["selected_race_name"]
    race_config = get_race_config(selected_race_name)

else:
    runner_name = params.get("name", "Runner")
    bib = params.get("bib", "")
    start_dt = datetime.fromisoformat(params.get("start", datetime.now().isoformat()))
    pace_secs = int(params.get("pace", 600))
    selected_race_name = params.get("race", DEFAULT_RACE_NAME)
    race_config = get_race_config(selected_race_name)

st.markdown(f'<div class="subtitle">{race_config["name"]} • {race_config["city"]}, {race_config["country"]}</div>', unsafe_allow_html=True)

pace_min_disp, pace_sec_disp = divmod(pace_secs, 60)
distance_miles = float(race_config.get("distance_miles", 13.1))
points = load_route_for_race(race_config)
mile_markers = get_mile_markers(points)
schedule = build_schedule(start_dt, pace_secs, mile_markers, total_miles=distance_miles)
finish = schedule[-1]
total_secs = int(distance_miles * pace_secs)
h, rem = divmod(total_secs, 3600)
m_dur, s_dur = divmod(rem, 60)
duration_str = f"{h}h {m_dur}m"
pace_display = f"{pace_min_disp}:{pace_sec_disp:02d}/mi"

# ── Runner card ───────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="runner-card">
    <div class="runner-name">{runner_name}</div>
    {"<div class='runner-bib'>Bib #" + bib + "</div>" if bib else ""}
    <div class="stat-grid">
        <div class="stat-box"><div class="stat-label">Start Time</div><div class="stat-value">{start_dt.strftime("%-I:%M %p")}</div></div>
        <div class="stat-box"><div class="stat-label">Expected Finish</div><div class="stat-value">{finish["arrival"].strftime("%-I:%M %p")}</div></div>
        <div class="stat-box"><div class="stat-label">Pace</div><div class="stat-value">{pace_display}</div></div>
        <div class="stat-box"><div class="stat-label">Duration</div><div class="stat-value">{duration_str}</div></div>
    </div>
</div>
""", unsafe_allow_html=True)

# ── Map ───────────────────────────────────────────────────────────────────────
race_map = build_map(points, schedule)
st_folium(race_map, width=None, height=480)

# ── Mile table ────────────────────────────────────────────────────────────────
st.markdown("### Mile markers")
rows = ""
for item in schedule:
    label = f"Mile {item['mile']}" if item['mile'] != "Finish" else "Finish"
    rows += f"<tr><td><b>{label}</b></td><td>{item['arrival'].strftime('%-I:%M %p')}</td><td>{item['elapsed']}</td></tr>"

st.markdown(f"""
<table class="mile-table">
<thead><tr><th>Mile</th><th>Arrives</th><th>Elapsed</th></tr></thead>
<tbody>{rows}</tbody>
</table>
""", unsafe_allow_html=True)

# ── Share link ────────────────────────────────────────────────────────────────
if not shared_mode:
    base_url = "http://localhost:8501"
    share_params = urllib.parse.urlencode({
        "name": runner_name,
        "bib": bib,
        "start": start_dt.isoformat(),
        "pace": pace_secs,
        "race": race_config["name"],
    })
    share_url = f"{base_url}?{share_params}"
    st.markdown(f"""
    <div class="share-box">
        <div class="share-title">📎 Share with your spectators</div>
        <div class="share-hint">Anyone with this link can see your race plan</div>
    </div>
    """, unsafe_allow_html=True)
    st.code(share_url, language=None)
    st.caption("Copy the link above and send it to friends and family.")
