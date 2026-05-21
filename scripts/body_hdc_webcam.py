"""
HDC Body Gesture Demo — Sports Coach + 3D Avatar Driver
Covers priority P1 (sports form) and P1+ (3D avatar gesture blend weights)

Two modes (toggle with [TAB]):
  COACH mode:  1-shot reference pose → real-time form score (0–100%)
               MediaPipe Pose (33 body keypoints)
               Great for: squat, yoga, physiotherapy, martial arts

  AVATAR mode: gesture library → real-time blend weights for all gestures
               MediaPipe Hands (21 keypoints)
               Output: dict {gesture_name: similarity_score} → drives animation blending
               Great for: game gestures, VR avatar control, sign language

Controls:
  [r]      COACH: record reference pose (~2s) / AVATAR: start recording new gesture
  [1-9]    AVATAR: register gesture to slot
  [TAB]    Switch between COACH and AVATAR modes
  [SPACE]  Clear all registered gestures/pose
  [s/l]    Save / load gesture memory
  [q/ESC]  Quit

Run:
  python3 body_hdc_webcam.py               # starts in COACH mode
  python3 body_hdc_webcam.py --mode avatar # starts in AVATAR mode
"""

import sys, os, time, argparse, json
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reram_hdc_sdk import encode_level

# ── HDC constants ──────────────────────────────────────────────────────────
D          = 10_000
N_LEVELS   = 100
N_FRAMES   = 15       # temporal frames per gesture/pose
RECORD_SEC = 2.0      # seconds to record a reference
BODY_CH    = 99       # 33 body landmarks × 3
HAND_CH    = 63       # 21 hand landmarks × 3

PANEL_W = 340

COLORS = {
    'bg': (20,20,20), 'panel': (30,30,30),
    'green': (80,200,80), 'red': (80,80,220),
    'yellow': (80,200,220), 'white': (230,230,230),
    'gray': (110,110,110), 'accent': (200,140,60),
    'bar_bg': (55,55,55), 'orange': (60,160,220),
}


# ── HDC backend ────────────────────────────────────────────────────────────
class Backend:
    def __init__(self, d):
        self.d = d; self.rng = np.random.default_rng(42)
    def random_hv(self): return (self.rng.integers(0,2,self.d)*2-1).astype(np.int8)
    def bind(self,a,b): return (a*b).astype(np.int8)
    def bundle(self,hvs):
        s=hvs.sum(axis=0); r=np.where(s>=0,1,-1).astype(np.int8)
        ties=(s==0); r[ties]=(self.rng.integers(0,2,ties.sum())*2-1).astype(np.int8)
        return r
    def permute(self,hv,n): return np.roll(hv,n)
    def cos(self,a,b):
        af=a.astype(np.float32); bf=b.astype(np.float32)
        return float(np.dot(af,bf)/(np.linalg.norm(af)*np.linalg.norm(bf)+1e-9))


def make_level_hvs(n, d, seed=99):
    rng=np.random.default_rng(seed); base=(rng.integers(0,2,d)*2-1).astype(np.int8)
    lvls=[base.copy()]; nf=d//n
    for _ in range(1,n):
        hv=lvls[-1].copy(); idx=rng.choice(d,nf,replace=False); hv[idx]*=-1; lvls.append(hv)
    return np.array(lvls,dtype=np.int8)


be = Backend(D)
# Channel HVs for both body (99ch) and hand (63ch)
body_ch_hvs = np.array([be.random_hv() for _ in range(BODY_CH)])
hand_ch_hvs = np.array([be.random_hv() for _ in range(HAND_CH)])
lv_hvs      = make_level_hvs(N_LEVELS, D)


def normalize_body(landmarks) -> np.ndarray:
    """33 pose landmarks → (99,) normalized [0,1] centered on hip midpoint."""
    pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])  # (33,3)
    # Center on midpoint of hips (landmarks 23, 24)
    hip = (pts[23] + pts[24]) / 2
    centered = pts - hip
    scale = np.max(np.abs(centered)) + 1e-6
    return np.clip((centered.flatten() / scale + 1) / 2, 0.0, 1.0)


def normalize_hand(landmarks) -> np.ndarray:
    """21 hand landmarks → (63,) normalized [0,1] centered on wrist."""
    pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])  # (21,3)
    wrist = pts[0]
    centered = pts - wrist
    scale = np.max(np.abs(centered)) + 1e-6
    return np.clip((centered.flatten() / scale + 1) / 2, 0.0, 1.0)


def encode_sequence(frames, ch_hvs) -> np.ndarray:
    """List of (n_ch,) frames → single HV via level+temporal encoding."""
    if not frames: return be.random_hv()
    n = len(frames)
    idx = np.linspace(0, n-1, N_FRAMES).astype(int)
    sampled = [frames[i] for i in idx]
    fhvs = [be.permute(encode_level(f, ch_hvs, lv_hvs, be), t)
            for t, f in enumerate(sampled)]
    return be.bundle(np.stack(fhvs))


# ── Memory ─────────────────────────────────────────────────────────────────
class GestureMemory:
    def __init__(self):
        self.protos = {}

    def register(self, label, hv):
        if label in self.protos:
            self.protos[label] = be.bundle(np.stack([self.protos[label], hv]))
        else:
            self.protos[label] = hv.copy()

    def search_all(self, query):
        """Return dict of all similarities — the avatar blend weight map."""
        return {lbl: be.cos(hv, query) for lbl, hv in self.protos.items()}

    def best(self, query):
        sims = self.search_all(query)
        if not sims: return None, 0.0, {}
        best = max(sims, key=sims.get)
        return best, sims[best], sims

    def clear(self): self.protos.clear()
    def __len__(self): return len(self.protos)


# ── Drawing ────────────────────────────────────────────────────────────────
def draw_form_score(frame, score, x0, y, w_panel):
    """Draws the big form score for COACH mode."""
    # Score circle (big number)
    pct = int(score * 100)
    color = COLORS['green'] if pct >= 70 else (COLORS['yellow'] if pct >= 40 else COLORS['red'])
    cv2.putText(frame, f"{pct:3d}%", (x0, y+50),
                cv2.FONT_HERSHEY_SIMPLEX, 1.8, color, 3, cv2.LINE_AA)
    # Bar
    bar_w = w_panel - 24
    filled = int(bar_w * score)
    cv2.rectangle(frame, (x0-2, y+60), (x0-2+bar_w, y+72), COLORS['bar_bg'], -1)
    cv2.rectangle(frame, (x0-2, y+60), (x0-2+filled, y+72), color, -1)
    y += 86
    label = "EXCELLENT" if pct >= 80 else ("GOOD" if pct >= 60 else ("ADJUST" if pct >= 40 else "TRY AGAIN"))
    cv2.putText(frame, label, (x0, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    return y + 20


def draw_blend_weights(frame, sims, x0, y):
    """Draws the gesture blend weight bars for AVATAR mode."""
    cv2.putText(frame, "Blend weights (avatar output):", (x0, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, COLORS['gray'], 1, cv2.LINE_AA)
    y += 14
    for lbl, sim in sorted(sims.items(), key=lambda x: -x[1])[:8]:
        bar_w = int((PANEL_W - 80) * max(sim, 0))
        cv2.rectangle(frame, (x0, y-7), (x0+bar_w, y-1),
                      (40, int(sim*180), 80), -1)
        cv2.putText(frame, f"{lbl[:14]:<14} {sim:.3f}", (x0, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.34,
                    COLORS['green'] if sim == max(sims.values()) else COLORS['gray'],
                    1, cv2.LINE_AA)
        y += 14
    return y


def draw_panel(frame, mode, memory, sims, form_score,
               recording, rec_progress, rec_label, fps):
    h, w = frame.shape[:2]
    cam_w = w - PANEL_W
    cv2.rectangle(frame, (cam_w, 0), (w, h), COLORS['panel'], -1)
    cv2.line(frame, (cam_w, 0), (cam_w, h), COLORS['gray'], 1)
    x0 = cam_w + 12
    y = 28

    # Header
    mode_label = "COACH (body form)" if mode == 'coach' else "AVATAR (gesture blend)"
    cv2.putText(frame, "HDC Body Gesture", (x0, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.52, COLORS['accent'], 1, cv2.LINE_AA)
    y += 18
    cv2.putText(frame, f"[TAB] → {mode_label}", (x0, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, COLORS['yellow'], 1, cv2.LINE_AA)
    y += 18
    cv2.putText(frame, f"D={D:,}  fps={fps:.0f}", (x0, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, COLORS['gray'], 1, cv2.LINE_AA)
    y += 20

    cv2.line(frame, (x0-4, y), (w-8, y), COLORS['gray'], 1); y += 14

    # Recording state
    if recording:
        cv2.rectangle(frame, (x0-8, y-14), (w-8, y+8), (60,0,0), -1)
        msg = f"RECORDING {rec_label} {'|'*(rec_progress//3)}"
        cv2.putText(frame, msg, (x0, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLORS['red'], 1, cv2.LINE_AA)
        y += 12
        bar_w = PANEL_W - 24
        filled = int(bar_w * min(rec_progress / 60, 1.0))
        cv2.rectangle(frame, (x0-2,y),(x0-2+bar_w,y+6), COLORS['bar_bg'],-1)
        cv2.rectangle(frame, (x0-2,y),(x0-2+filled,y+6), COLORS['red'],-1)
        y += 18
    else:
        status = f"{len(memory)} gestures" if mode=='avatar' else ("pose registered" if len(memory)>0 else "press [r] to record reference")
        cv2.putText(frame, status, (x0, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38,
                    COLORS['green'] if len(memory)>0 else COLORS['gray'],
                    1, cv2.LINE_AA)
        y += 20

    cv2.line(frame, (x0-4, y), (w-8, y), COLORS['gray'], 1); y += 14

    # Results
    if mode == 'coach' and form_score is not None and len(memory) > 0:
        cv2.putText(frame, "FORM SCORE:", (x0, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.42, COLORS['gray'], 1, cv2.LINE_AA)
        y += 6
        y = draw_form_score(frame, form_score, x0, y, PANEL_W)
    elif mode == 'avatar' and sims:
        y = draw_blend_weights(frame, sims, x0, y)
    else:
        hint = "[r] record reference pose" if mode=='coach' else "[1-9] register gestures"
        cv2.putText(frame, hint, (x0, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, COLORS['gray'], 1, cv2.LINE_AA)
        y += 18

    # Registered gestures list
    if mode == 'avatar' and len(memory) > 0:
        y += 4
        cv2.line(frame, (x0-4, y), (w-8, y), COLORS['gray'], 1); y += 12
        for lbl in list(memory.protos.keys())[:6]:
            cv2.putText(frame, f"  [{lbl}]", (x0, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, COLORS['yellow'], 1, cv2.LINE_AA)
            y += 13

    # Controls footer
    y = h - 95
    cv2.line(frame, (x0-4, y), (w-8, y), COLORS['gray'], 1); y += 12
    ctrl = [
        "[r] record ref/gesture",
        "[1-9] gesture slots (AVATAR)",
        "[TAB] switch mode",
        "[SPACE] clear  [s/l] save/load",
        "[q/ESC] quit",
    ]
    for line in ctrl:
        cv2.putText(frame, line, (x0, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.31, COLORS['gray'], 1, cv2.LINE_AA)
        y += 13

    return frame


def draw_pose_skeleton(frame, lms, h, cam_w):
    """Draw body skeleton."""
    import mediapipe as mp
    conns = mp.solutions.pose.POSE_CONNECTIONS
    for c in conns:
        p1, p2 = lms[c[0]], lms[c[1]]
        if p1.visibility > 0.3 and p2.visibility > 0.3:
            x1,y1 = int(p1.x*cam_w), int(p1.y*h)
            x2,y2 = int(p2.x*cam_w), int(p2.y*h)
            cv2.line(frame, (x1,y1),(x2,y2),(100,180,100),2)
    for lm in lms:
        if lm.visibility > 0.3:
            cx,cy = int(lm.x*cam_w), int(lm.y*h)
            cv2.circle(frame,(cx,cy),4,(80,200,80),-1)


def draw_hand_skeleton(frame, lms, h, cam_w):
    """Draw hand skeleton."""
    import mediapipe as mp
    for c in mp.solutions.hands.HAND_CONNECTIONS:
        p1,p2 = lms[c[0]],lms[c[1]]
        cv2.line(frame, (int(p1.x*cam_w),int(p1.y*h)),
                 (int(p2.x*cam_w),int(p2.y*h)), (100,160,100), 1)
    for i,lm in enumerate(lms):
        color = COLORS['accent'] if i==0 else (80,160,80)
        cv2.circle(frame,(int(lm.x*cam_w),int(lm.y*h)),3,color,-1)


# ── Main ───────────────────────────────────────────────────────────────────
AVATAR_SLOTS = {
    '1':'wave',    '2':'point',   '3':'thumbs_up',
    '4':'fist',    '5':'open',    '6':'peace',
    '7':'pinch',   '8':'rock',    '9':'ok',
}


def main(start_mode='coach'):
    import mediapipe as mp

    mode = start_mode
    mp_pose  = mp.solutions.pose
    mp_hands = mp.solutions.hands
    pose  = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)
    hands = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.6,
                           min_tracking_confidence=0.5)

    memory = GestureMemory()
    save_path = os.path.join(os.path.dirname(__file__), "body_gesture_memory.json")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: camera unavailable"); return
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
    WIN = "HDC Sports Coach + Avatar Driver — millisecond-era"
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, 960+PANEL_W, 540)

    recording   = False
    rec_buffer  = []
    rec_label   = ""
    RECORD_FRAMES = 60    # ~2s at 30fps

    query_buffer = []
    QUERY_FRAMES = 20
    form_score   = None
    sims         = {}

    fps_hist = [time.perf_counter()] * 10
    fps = 30.0

    print(f"\nHDC Body Gesture — D={D:,}")
    print(f"Start mode: {mode.upper()}")
    print("TAB to switch modes. [r] to record reference/gesture.")

    while True:
        ret, frame = cap.read()
        if not ret: break
        frame = cv2.flip(frame, 1)
        h, w = frame.shape[:2]
        cam_w = w - PANEL_W
        cam_frame = frame[:, :cam_w].copy()
        rgb = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False

        body_kp = None
        hand_kp = None

        if mode == 'coach':
            res = pose.process(rgb)
            if res.pose_landmarks:
                lms = res.pose_landmarks.landmark
                draw_pose_skeleton(frame, lms, h, cam_w)
                body_kp = normalize_body(lms)
        else:  # avatar
            res = hands.process(rgb)
            if res.multi_hand_landmarks:
                lms = res.multi_hand_landmarks[0].landmark
                draw_hand_skeleton(frame, lms, h, cam_w)
                hand_kp = normalize_hand(lms)

        rgb.flags.writeable = True
        current_kp = body_kp if mode == 'coach' else hand_kp
        ch_hvs = body_ch_hvs if mode == 'coach' else hand_ch_hvs

        # ── Recording ────────────────────────────────────────────
        if recording:
            if current_kp is not None:
                rec_buffer.append(current_kp)
            if len(rec_buffer) >= RECORD_FRAMES:
                hv = encode_sequence(rec_buffer, ch_hvs)
                label = "reference_pose" if mode == 'coach' else rec_label
                memory.register(label, hv)
                print(f"  Registered '{label}'")
                recording = False; rec_buffer = []
        else:
            # ── Live inference ───────────────────────────────────
            if current_kp is not None:
                query_buffer.append(current_kp)
                if len(query_buffer) > QUERY_FRAMES: query_buffer.pop(0)
                if len(query_buffer) >= N_FRAMES and len(memory) > 0:
                    q_hv = encode_sequence(query_buffer, ch_hvs)
                    if mode == 'coach':
                        all_sims = memory.search_all(q_hv)
                        form_score = all_sims.get('reference_pose', 0.0)
                        sims = {}
                    else:
                        sims = memory.search_all(q_hv)
                        form_score = None
            else:
                query_buffer.clear()

        # FPS
        now = time.perf_counter()
        fps_hist.pop(0); fps_hist.append(now)
        fps = (len(fps_hist)-1) / max(fps_hist[-1]-fps_hist[0], 1e-6)

        frame = draw_panel(frame, mode, memory, sims, form_score,
                           recording, len(rec_buffer), rec_label, fps)

        # No landmark overlay
        if current_kp is None and not recording:
            tip = "Stand back so body is visible" if mode=='coach' else "Show your hand"
            cv2.putText(frame, tip, (20, h-20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['gray'], 1, cv2.LINE_AA)

        cv2.imshow(WIN, frame)
        key = cv2.waitKey(1) & 0xFF

        if key in (ord('q'), 27): break
        elif key == 9:   # TAB
            mode = 'avatar' if mode == 'coach' else 'coach'
            memory.clear(); form_score=None; sims={}; query_buffer.clear()
            print(f"  Switched to {mode.upper()}")
        elif key == ord('r') and not recording:
            recording = True; rec_buffer = []
            rec_label = "reference_pose" if mode == 'coach' else 'gesture'
            print(f"  Recording '{rec_label}' — hold your pose/gesture...")
        elif key == ord(' '):
            memory.clear(); form_score=None; sims={}
            print("  Memory cleared")
        elif key == ord('s'):
            data = {lbl: hv.tolist() for lbl, hv in memory.protos.items()}
            with open(save_path, 'w') as f:
                json.dump({'d': D, 'mode': mode, 'signs': data}, f)
            print(f"  Saved {len(memory)} gestures")
        elif key == ord('l'):
            if os.path.exists(save_path):
                with open(save_path) as f: data = json.load(f)
                memory.clear()
                for lbl, hv in data['signs'].items():
                    memory.protos[lbl] = np.array(hv, dtype=np.int8)
                print(f"  Loaded {len(memory)} gestures")
        elif mode == 'avatar' and chr(key) in AVATAR_SLOTS and not recording:
            rec_label = AVATAR_SLOTS[chr(key)]
            recording = True; rec_buffer = []
            print(f"  Recording gesture '{rec_label}'...")

    cap.release(); cv2.destroyAllWindows()
    pose.close(); hands.close()
    print("Done.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['coach','avatar'], default='coach')
    args = parser.parse_args()
    main(start_mode=args.mode)
