from __future__ import annotations

import requests

HEADERS = {"User-Agent": "NetWorthTracker/1.0 (personal use)"}
TIMEOUT = 30

# Collin CAD parcels (ArcGIS)
CCAD_PARCELS_QUERY = (
    "https://gismaps.cityofallen.org/arcgis/rest/services/"
    "ReferenceData/Collin_County_Appraisal_District_Parcels/MapServer/1/query"
)

# Dallas County parcels (ArcGIS)
DALLAS_COUNTY_PARCELS_QUERY = (
    "https://services6.arcgis.com/2yF1BNcZtu43QAOt/ArcGIS/rest/services/"
    "Dallas_County_Parcel_Clipped/FeatureServer/0/query"
)


def _arcgis_query(url: str, params: dict) -> dict:
    params = {**params, "f": "json"}
    r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    if "error" in data:
        raise RuntimeError(f"ArcGIS error: {data['error']}")
    return data


def _find_field(attrs: dict, endswith_candidates: list[str]) -> str | None:
    for k in attrs.keys():
        uk = k.upper()
        for c in endswith_candidates:
            if uk.endswith(c):
                return k
    return None


def get_ccad_market_by_address(street_num: str, street_name_like: str, city: str) -> float:
    where = (
        f"(situs_city = '{city.upper()}') AND "
        f"(situs_num = '{street_num}') AND "
        f"(situs_street LIKE '{street_name_like.upper()}%')"
    )
    data = _arcgis_query(
        CCAD_PARCELS_QUERY,
        {"where": where, "outFields": "*", "returnGeometry": "false", "resultRecordCount": 5},
    )
    feats = data.get("features", [])
    if not feats:
        raise RuntimeError("No CCAD match for address.")
    attrs = feats[0]["attributes"]

    mf = _find_field(attrs, ["CERT_MARKET", "MKT_VALUE", "MARKET_VALUE"])
    if not mf:
        raise RuntimeError("CCAD market value field not found.")
    return float(attrs[mf])


def get_ccad_market_by_point(lat: float, lon: float) -> float:
    geometry = f"{lon},{lat}"
    data = _arcgis_query(
        CCAD_PARCELS_QUERY,
        {
            "geometry": geometry,
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "false",
            "resultRecordCount": 5,
        },
    )
    feats = data.get("features", [])
    if not feats:
        raise RuntimeError("No CCAD parcel found at given coordinates.")
    attrs = feats[0]["attributes"]

    mf = _find_field(attrs, ["CERT_MARKET", "MKT_VALUE", "MARKET_VALUE"])
    if not mf:
        raise RuntimeError("CCAD market value field not found for point parcel.")
    return float(attrs[mf])


def get_dallas_mkt_value_by_address(street_num: str, street_name_like: str, city: str) -> float:
    where = (
        f"(SITUS_CITY = '{city.upper()}') AND "
        f"(SITUS_ADDR LIKE '{street_num} {street_name_like.upper()}%')"
    )
    data = _arcgis_query(
        DALLAS_COUNTY_PARCELS_QUERY,
        {
            "where": where,
            "outFields": "SITUS_ADDR,SITUS_CITY,MKT_VALUE",
            "returnGeometry": "false",
            "resultRecordCount": 5,
        },
    )
    feats = data.get("features", [])
    if not feats:
        raise RuntimeError("No Dallas County parcel match for address.")
    attrs = feats[0]["attributes"]
    if attrs.get("MKT_VALUE") is None:
        raise RuntimeError("Dallas MKT_VALUE missing.")
    return float(attrs["MKT_VALUE"])
