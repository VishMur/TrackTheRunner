from __future__ import annotations

import os
from typing import Dict, List

DEFAULT_RACE_NAME = "Gasparilla Distance Classic Half Marathon"

# Mapping of filename patterns to proper race names
NAME_CORRECTIONS = {
    "gasparilla_distance_classic_half_marathon": "Gasparilla Distance Classic Half Marathon",
    "chicago_bank_of_america_marathon": "Chicago Bank of America Marathon",
    "new_york_city_marathon": "New York City Marathon",
    "los_angeles_marathon": "Los Angeles Marathon",
    "walt_disney_world_marathon": "Walt Disney World Marathon",
    "big_sur_international_marathon": "Big Sur International Marathon",
    "rock_n_roll_san_diego_marathon": "Rock 'n' Roll San Diego Marathon",
    "medtronic_twin_cities_marathon": "Medtronic Twin Cities Marathon",
    "garmin_kansas_city_marathon": "Garmin Kansas City Marathon",
    "chevron_houston_marathon": "Chevron Houston Marathon",
    "ameris_bank_jacksonville_marathon": "Ameris Bank Jacksonville Marathon",
    "flying_pig_cincinnati_marathon": "Flying Pig Cincinnati Marathon",
    "university_hospitals_cleveland_marathon": "University Hospitals Cleveland Marathon",
    "detroit_free_press_marathon": "Detroit Free Press Marathon",
    "napa_to_sonoma_wine_country_half_marathon": "Napa to Sonoma Wine Country Half Marathon",
    "run_sedona_half_mararathon": "Run Sedona Half Marathon",
    "publix_atlanta_half_marathon": "Publix Atlanta Half Marathon",
    "mount_tamalpais_half_marathon": "Mount Tamalpais Half Marathon",
    "boulderthon_half_marathon": "Boulderthon Half Marathon",
    "bmw_dallas_marathon": "BMW Dallas Marathon",
    "pittsburg_marathon": "Pittsburgh Marathon",
}


def _filename_to_name(filename_without_ext: str) -> str:
    """Convert filename to proper race name."""
    if filename_without_ext in NAME_CORRECTIONS:
        return NAME_CORRECTIONS[filename_without_ext]
    
    # Default: convert underscores to spaces and title case
    name = filename_without_ext.replace("_", " ").title()
    return name


def _load_catalog() -> List[Dict[str, object]]:
    """Dynamically load catalog from GPX files in race_courses folder."""
    catalog: List[Dict[str, object]] = []
    base_dir = os.path.dirname(os.path.abspath(__file__))
    race_courses_dir = os.path.join(base_dir, "race_courses")
    
    # Scan marathons folder
    marathons_dir = os.path.join(race_courses_dir, "marathons")
    if os.path.isdir(marathons_dir):
        for filename in sorted(os.listdir(marathons_dir)):
            if filename.endswith(".gpx"):
                name = _filename_to_name(filename[:-4])
                gpx_path = f"race_courses/marathons/{filename}"
                slug = filename[:-4].lower()
                
                catalog.append({
                    "name": name,
                    "city": "Various",
                    "country": "United States",
                    "distance_miles": 26.2,
                    "gpx_path": gpx_path,
                    "slug": slug,
                })
    
    # Scan half marathons folder
    half_marathons_dir = os.path.join(race_courses_dir, "halfmarathons")
    if os.path.isdir(half_marathons_dir):
        for filename in sorted(os.listdir(half_marathons_dir)):
            if filename.endswith(".gpx"):
                name = _filename_to_name(filename[:-4])
                gpx_path = f"race_courses/halfmarathons/{filename}"
                slug = filename[:-4].lower()
                
                catalog.append({
                    "name": name,
                    "city": "Various",
                    "country": "United States",
                    "distance_miles": 13.1,
                    "gpx_path": gpx_path,
                    "slug": slug,
                })
    
    return catalog


# Lazy-load the catalog
_MARATHON_CATALOG: List[Dict[str, object]] | None = None


def _get_catalog() -> List[Dict[str, object]]:
    """Get cached catalog, loading on first access."""
    global _MARATHON_CATALOG
    if _MARATHON_CATALOG is None:
        _MARATHON_CATALOG = _load_catalog()
    return _MARATHON_CATALOG


def load_marathon_catalog() -> List[Dict[str, object]]:
    return [dict(entry) for entry in _get_catalog()]


def get_race_config(name: str | None) -> Dict[str, object]:
    if not name:
        catalog = _get_catalog()
        return dict(catalog[0]) if catalog else {}

    candidate = name.strip()
    if not candidate:
        catalog = _get_catalog()
        return dict(catalog[0]) if catalog else {}

    normalized = candidate.lower()
    for entry in _get_catalog():
        if normalized in {entry["name"].lower(), entry["slug"].lower()}:  # type: ignore[index]
            return dict(entry)

    # Fallback to first entry if not found
    catalog = _get_catalog()
    return dict(catalog[0]) if catalog else {}


def get_race_names() -> List[str]:
    return [entry["name"] for entry in _get_catalog()]  # type: ignore[misc]


def get_fallback_route_points(race_name: str | None) -> List[tuple[float, float]]:
    """Get fallback route points for races without GPX files."""
    fallback_points = {
        "Gasparilla Distance Classic Half Marathon": [
            (27.9484, -82.4593), (27.9496, -82.4608), (27.9510, -82.4621),
            (27.9530, -82.4640), (27.9550, -82.4660), (27.9572, -82.4684),
            (27.9594, -82.4710), (27.9618, -82.4735), (27.9641, -82.4762),
            (27.9660, -82.4790),
        ],
    }
    if not race_name:
        return fallback_points.get("Gasparilla Distance Classic Half Marathon", [])
    return fallback_points.get(race_name, [])
