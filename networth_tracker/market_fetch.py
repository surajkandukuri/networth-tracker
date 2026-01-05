from __future__ import annotations

from functools import lru_cache

import requests

HEADERS = {"User-Agent": "NetWorthTracker/1.0 (personal use)"}
TIMEOUT = 30

# Collin CAD parcels (ArcGIS)
CCAD_PARCELS_QUERY = (
    "https://gismaps.cityofallen.org/arcgis/rest/services/"
    "ReferenceData/Collin_County_Appraisal_District_Parcels/MapServer/1/query"
)
CCAD_PARCELS_LAYER = CCAD_PARCELS_QUERY.rsplit("/", 1)[0]

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


@lru_cache(maxsize=1)
def _load_ccad_fields() -> list[dict]:
    r = requests.get(CCAD_PARCELS_LAYER, params={"f": "pjson"}, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    fields = data.get("fields")
    if not fields:
        raise RuntimeError("CCAD metadata missing fields.")
    return fields


def _match_field(fields: list[dict], candidates: list[str], numeric_only: bool = False) -> dict | None:
    numeric_types = {
        "esriFieldTypeDouble",
        "esriFieldTypeInteger",
        "esriFieldTypeSmallInteger",
        "esriFieldTypeSingle",
    }
    for cand in candidates:
        for f in fields:
            name = f.get("name", "")
            up_name = name.upper()
            if numeric_only and f.get("type") not in numeric_types:
                continue
            if up_name == cand or up_name.endswith(cand) or up_name.startswith(cand) or cand in up_name:
                return f
    return None


@lru_cache(maxsize=1)
def _ccad_field_map() -> dict:
    fields = _load_ccad_fields()

    city_field = _match_field(fields, ["SITUS_CITY", "CITY", "SITUSCITY"])
    num_field = _match_field(fields, ["SITUS_NUM", "STREET_NUM", "ADDR_NUM", "HOUSE_NUM", "SITUSNUMBER"], numeric_only=True)
    street_field = _match_field(fields, ["SITUS_STREET", "STREET_NAME", "STREET", "ADDR_STREET", "ROADNAME"])
    market_field = _match_field(fields, ["CERT_MARKET", "MKT_VALUE", "MARKET_VALUE", "TOTAL_MARKET", "TOT_MARKET"], numeric_only=True)

    missing = []
    for name, field in (("city", city_field), ("number", num_field), ("street", street_field), ("market", market_field)):
        if field is None:
            missing.append(name)
    if missing:
        raise RuntimeError(f"CCAD field discovery failed: missing {', '.join(missing)}")

    return {
        "city": city_field,
        "number": num_field,
        "street": street_field,
        "market": market_field,
    }


def _format_where_value(value: str | float, field: dict) -> str:
    if field.get("type") == "esriFieldTypeString":
        return f"'{value}'"
    return str(value)


def get_ccad_market_by_address(street_num: str, street_name_like: str, city: str) -> float:
    fields = _ccad_field_map()

    city_field = fields["city"]["name"]
    num_field = fields["number"]["name"]
    street_field = fields["street"]["name"]
    market_field = fields["market"]["name"]

    where = (
        f"({city_field} = {_format_where_value(city.upper(), fields['city'])}) AND "
        f"({num_field} = {_format_where_value(street_num, fields['number'])}) AND "
        f"({street_field} LIKE {_format_where_value(street_name_like.upper() + '%', fields['street'])})"
    )
    data = _arcgis_query(
        CCAD_PARCELS_QUERY,
        {"where": where, "outFields": "*", "returnGeometry": "false", "resultRecordCount": 5},
    )
    feats = data.get("features", [])
    if not feats:
        raise RuntimeError("No CCAD match for address.")
    attrs = feats[0]["attributes"]
    if market_field not in attrs:
        raise RuntimeError("CCAD market value field not found.")
    return float(attrs[market_field])


def get_ccad_market_by_point(lat: float, lon: float) -> float:
    fields = _ccad_field_map()
    market_field = fields["market"]["name"]

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
    if market_field not in attrs:
        raise RuntimeError("CCAD market value field not found for point parcel.")
    return float(attrs[market_field])


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
