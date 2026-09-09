"""Rigid georeferencing from four user-clicked NLSC WGS84 points; no scale change."""
import numpy as np,math
LON0=120.25725453748464;LAT0=23.178193459074407
CORNERS_DMS=[['120-15-26.1','23-10-42.0'],['120-15-26.7','23-10-41.5'],['120-15-26.3','23-10-41.0'],['120-15-25.8','23-10-41.4']]
def degrees(s):
 d,m,sec=map(float,s.split('-'));return d+m/60+sec/3600
CORNERS=np.array([[degrees(lon),degrees(lat)] for lon,lat in CORNERS_DMS])
def eastnorth(lon,lat):return np.array([(lon-LON0)*111319.49079327358*math.cos(math.radians(LAT0)),(lat-LAT0)*111319.49079327358])
EN=np.array([eastnorth(lon,lat) for lon,lat in CORNERS])
# Existing approximate site-ground boundary, in the same model x/z frame.
MODEL=np.array([[-1.7,-1],[17,-2.2],[17.2,17.3],[-1.9,20]])-[7.18,8.3]
# Plan rear-left maps to geographic east; proceed around the plot.
TARGET=EN[[1,2,3,0]]
a=MODEL-MODEL.mean(axis=0);b=TARGET-TARGET.mean(axis=0)
u,s,vt=np.linalg.svd(a.T@b);ROT=u@vt
# Geographic E/N has opposite handedness to right-handed model X/Z on the ground.
OFFSET=TARGET.mean(axis=0)-MODEL.mean(axis=0)@ROT
FITTED=MODEL@ROT+OFFSET
RESIDUAL=np.linalg.norm(FITTED-TARGET,axis=1)
def to_model(en):return (np.asarray(en)-OFFSET)@ROT.T
def metadata():
 return dict(source='User-provided four NLSC map-click coordinates, 2026-09-10',datum='WGS84',input_dms=CORNERS_DMS,corners_lon_lat=CORNERS.tolist(),corners_model_xz=to_model(EN).tolist(),method='Least-squares rigid alignment to existing approximate site outline. Rotation and translation only; building not scaled or deformed.',model_xz_to_east_north_matrix=ROT.tolist(),origin_east_north_metres=OFFSET.tolist(),corner_residual_metres=RESIDUAL.tolist(),rms_residual_metres=float(np.sqrt(np.mean(RESIDUAL**2))),coordinate_resolution='0.1 arcsecond (~3 m); map-click positions, NOT survey measurements',limitation='The four clicked corners and existing approximate site outline do not exactly coincide. Preserve the PDF house dimensions; residual mismatch is reported rather than deforming the house.')
