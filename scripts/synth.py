"""Validation of the geometric chain on synthetic data with known ground truth."""
import numpy as np, cv2, math

def Ry(d):  # rotation about the vertical axis (y down) = heading change
    a = math.radians(d); c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])

def cam_from_azimuth(az_deg):
    """R_wc: world(East,Down,North) -> camera. Azimuth 0 = north, clockwise."""
    return Ry(-az_deg)

W = H = 1400
f = 28.0/36.0*W
K = np.array([[f,0,W/2],[0,f,H/2],[0,0,1.0]])

def horiz_angle(v): return math.atan2(v[0], v[2])

rng = np.random.default_rng(0)
print(' azA_true azB_true | azA_est azB_est | error')
bad = 0
for trial in range(8):
    azA = rng.uniform(0, 360); azB = azA + rng.uniform(-50, 50)   # overlapping fields of view
    # world positions: axes (East, Down, North)
    bearing = rng.uniform(0, 360); base = rng.uniform(20, 120)
    CA = np.array([0.0, 0.0, 0.0])
    CB = np.array([base*math.sin(math.radians(bearing)), 0.0, base*math.cos(math.radians(bearing))])
    RA, RB = cam_from_azimuth(azA), cam_from_azimuth(azB)
    # 3D points in front of both cameras
    # points drawn IN FRONT of camera A then filtered for B (avoids an infinite loop)
    P, tries = [], 0
    while len(P) < 400 and tries < 20000:
        tries += 1
        loc = np.array([rng.uniform(-200,200), rng.uniform(-30,10), rng.uniform(30,400)])
        p = RA.T @ loc + CA                      # camera-A frame -> world
        if (RB@(p-CB))[2] > 20: P.append(p)
    if len(P) < 60: print('  (trial skipped: insufficient overlap)'); continue
    P = np.array(P)
    def proj(R, C):
        X = (R@(P-C).T).T
        u = (K@X.T).T; return u[:,:2]/u[:,2:3]
    p1, p2 = proj(RA,CA), proj(RB,CB)
    m = (p1[:,0]>0)&(p1[:,0]<W)&(p1[:,1]>0)&(p1[:,1]<H)&(p2[:,0]>0)&(p2[:,0]<W)&(p2[:,1]>0)&(p2[:,1]<H)
    if m.sum() < 30: continue
    p1, p2 = np.float32(p1[m]), np.float32(p2[m])
    Emat, mask = cv2.findEssentialMat(p1, p2, K, method=cv2.RANSAC, prob=0.999, threshold=1.0)
    ninl, R, t, _ = cv2.recoverPose(Emat, p1, p2, K, mask=mask)
    # --- the chain under test (identical to azimuth.py) ---
    dA = (-R.T@t).ravel(); dB = (t).ravel()
    thAB = math.atan2(CB[0]-CA[0], CB[2]-CA[2]); thBA = thAB+math.pi
    eA = math.degrees((thAB - horiz_angle(dA)) % (2*math.pi))
    eB = math.degrees((thBA - horiz_angle(dB)) % (2*math.pi))
    errA = abs((eA-azA+180)%360-180); errB = abs((eB-azB+180)%360-180)
    if max(errA,errB) > 5: bad += 1
    print('  %6.1f %6.1f | %6.1f %6.1f | %5.1f %5.1f %s'
          %(azA,azB,eA,eB,errA,errB,'  <-- WRONG' if max(errA,errB)>5 else ''))
print('\n%d/8 trials wrong' % bad)
