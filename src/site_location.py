"""Georeference of the house, from the permit site plan registered to the NLSC e-map.

1. Permit p1 配置圖 (1:500) was registered to NLSC Taiwan e-Map road edges and the No.21
   wall (rotation 0.4 deg, residual 0.25 m RMS); see output/realism/site-registration.json.
2. The model's building projection (1F + porch + covered SW strip) was fitted to the
   drawing's footprint (IoU 0.94), then refined against the 13 lot-line distances of the
   permit light-and-ventilation table (0.08 m RMS).
EN = local east/north metres about the original GPS pin (LON0, LAT0).
Model x/z = plan x/y - (7.18, 8.3); plan is mirror-handed to EN, so ROT is a reflection.
The user's four map-click corners (2026-09-10, ~3 m resolution) are kept for comparison.
"""
import json, math
from pathlib import Path
import numpy as np
LON0 = 120.25725453748464; LAT0 = 23.178193459074407
K = 111319.49079327358
CORNERS_DMS = [['120-15-26.1', '23-10-42.0'], ['120-15-26.7', '23-10-41.5'], ['120-15-26.3', '23-10-41.0'], ['120-15-25.8', '23-10-41.4']]
def degrees(s):
    d, m, sec = map(float, s.split('-')); return d + m / 60 + sec / 3600
CORNERS = np.array([[degrees(lon), degrees(lat)] for lon, lat in CORNERS_DMS])
def eastnorth(lon, lat): return np.array([(lon - LON0) * K * math.cos(math.radians(LAT0)), (lat - LAT0) * K])
EN = np.array([eastnorth(lon, lat) for lon, lat in CORNERS])     # user clicks (reference only)

REG = json.loads((Path(__file__).resolve().parents[1] / 'output/realism/site-registration.json').read_text(encoding='utf-8'))
_phi = math.radians(REG['house_plan_to_en']['phi_deg']); _t = np.array(REG['house_plan_to_en']['t'])
_A = np.array([[math.cos(_phi), math.sin(_phi)], [math.sin(_phi), -math.cos(_phi)]])   # plan -> EN (reflection)
# row-vector form used across the project: en = xz @ ROT + OFFSET, xz = plan - (7.18, 8.3)
ROT = _A.T
OFFSET = np.array([7.18, 8.3]) @ ROT + _t
PARCEL_EN = np.array(REG['parcel_en'])
def to_model(en): return (np.asarray(en) - OFFSET) @ ROT.T
PARCEL_MODEL = to_model(PARCEL_EN)
PARCEL_PLAN = PARCEL_MODEL + [7.18, 8.3]
MODEL = PARCEL_MODEL                                            # site ground = permit lot 318

def metadata():
    clicked = to_model(EN)
    return dict(source='Permit p1 site plan (lot 318) registered to NLSC e-map; house fitted to the drawn footprint and permit lot-line distances',
                datum='WGS84 local east/north about the site pin', site_pin_lon_lat=[LON0, LAT0],
                model_xz_to_east_north_matrix=ROT.tolist(), origin_east_north_metres=OFFSET.tolist(),
                house_registration=REG['house_plan_to_en'], site_plan_registration=REG['site_plan_to_en'],
                parcel_area_m2=REG['parcel_area_m2_extracted'], parcel_area_m2_permit=REG['parcel_area_m2_permit'],
                user_clicked_corners_lon_lat=CORNERS.tolist(), user_clicked_corners_model_xz=clicked.tolist(),
                limitation='Site plan and e-map are not survey data; expect about 0.3-1 m absolute error. Building dimensions are untouched (rigid placement only).')
