
import cv2
import numpy as np

def _normalize_pair(a, b):
    total = max(a + b, 1e-9)
    x = a / total * 100.0
    y = b / total * 100.0
    lo, hi = sorted([x, y])
    return round(lo, 1), round(hi, 1)

def estimate_centering_from_image(image_path):
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError("Unable to read image")
    h, w = img.shape[:2]
    scale = 1200.0 / max(h, w) if max(h, w) > 1200 else 1.0
    if scale < 1.0:
        img = cv2.resize(img, (int(w*scale), int(h*scale)))
        h, w = img.shape[:2]

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(cv2.GaussianBlur(gray, (5,5), 0), 40, 120)
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    card_rect, best_area = None, 0
    for c in contours:
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        area = cv2.contourArea(c)
        if len(approx) == 4 and area > best_area and area > 0.25*w*h:
            card_rect = approx.reshape(4,2).astype(np.float32)
            best_area = area

    if card_rect is None:
        mx, my = int(w*0.04), int(h*0.04)
        card_rect = np.array([[mx,my],[w-mx,my],[w-mx,h-my],[mx,h-my]], dtype=np.float32)

    def order_points(pts):
        rect = np.zeros((4,2), dtype=np.float32)
        s = pts.sum(axis=1)
        d = np.diff(pts, axis=1).reshape(-1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        rect[1] = pts[np.argmin(d)]
        rect[3] = pts[np.argmax(d)]
        return rect

    tl,tr,br,bl = order_points(card_rect)
    maxW = max(int(np.linalg.norm(br-bl)), int(np.linalg.norm(tr-tl)), 300)
    maxH = max(int(np.linalg.norm(tr-br)), int(np.linalg.norm(tl-bl)), 420)
    dst = np.array([[0,0],[maxW-1,0],[maxW-1,maxH-1],[0,maxH-1]], dtype=np.float32)
    warped = cv2.warpPerspective(img, cv2.getPerspectiveTransform(np.array([tl,tr,br,bl]), dst), (maxW,maxH))
    wg = cv2.cvtColor(warped, cv2.COLOR_BGR2GRAY)

    gx = np.mean(np.abs(cv2.Sobel(wg, cv2.CV_64F, 1, 0, ksize=3)), axis=0)
    gy = np.mean(np.abs(cv2.Sobel(wg, cv2.CV_64F, 0, 1, ksize=3)), axis=1)

    def strongest(profile, start, end):
        start, end = max(1,int(start)), min(len(profile)-1,int(end))
        return start + int(np.argmax(profile[start:end]))

    lx = strongest(gx, maxW*0.02, maxW*0.30)
    rx = strongest(gx, maxW*0.70, maxW*0.98)
    ty = strongest(gy, maxH*0.02, maxH*0.30)
    by = strongest(gy, maxH*0.70, maxH*0.98)

    left, right = float(lx), float(maxW-1-rx)
    top, bottom = float(ty), float(maxH-1-by)
    lr = _normalize_pair(left, right)
    tb = _normalize_pair(top, bottom)
    overall = lr if abs(lr[1]-50) >= abs(tb[1]-50) else tb
    confidence = 0.72 if best_area else 0.48

    return {
        "left_right": lr,
        "top_bottom": tb,
        "overall": overall,
        "confidence": confidence,
    }

def centering_score(front=None, back=None):
    pairs = [r["overall"] for r in (front, back) if r]
    if not pairs:
        return None
    worst = max(p[1] for p in pairs)
    if worst <= 51.0: return 10.0
    if worst <= 52.5: return 9.5
    if worst <= 55.0: return 9.0
    if worst <= 57.5: return 8.5
    if worst <= 60.0: return 8.0
    if worst <= 65.0: return 7.0
    return 6.0

def estimated_grades(centering, corners, edges, surface):
    vals = [v for v in [centering, corners, edges, surface] if v is not None]
    if not vals:
        return {"psa": None, "bgs": None, "black_label": "Unknown"}
    c = centering or 8.0
    co = corners or 8.0
    e = edges or 8.0
    s = surface or 8.0
    avg = (c+co+e+s)/4
    weakest = min(c,co,e,s)
    bgs = min(round(avg*2)/2, weakest+1.0)
    psa_raw = 0.20*c + 0.25*co + 0.25*e + 0.30*s
    if weakest < 8:
        psa_raw = min(psa_raw, weakest+1)
    psa = int(round(max(1,min(10,psa_raw))))
    if all(v >= 10 for v in [c,co,e,s]):
        bl = "High"
    elif all(v >= 9.5 for v in [c,co,e,s]) and sum(v >= 10 for v in [c,co,e,s]) >= 2:
        bl = "Low–Medium"
    else:
        bl = "Low"
    return {"psa":psa,"bgs":bgs,"black_label":bl}
