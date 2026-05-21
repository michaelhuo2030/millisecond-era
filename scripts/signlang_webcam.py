"""
HDC Sign Language — Live Webcam Demo
Real-time CSL/ASL recognition from camera, zero training, 1-shot per sign.

Controls:
  [1-9]       Register a new sign (press digit then show hand for 2 seconds)
  [SPACE]     Clear all registered signs
  [q / ESC]   Quit
  [s]         Save current sign set to disk
  [l]         Load sign set from disk

Usage:
  python3 signlang_webcam.py
  python3 signlang_webcam.py --d 10000 --signs "你好,谢谢,再见,我,爱"
"""

import sys, os, time, argparse, json
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from reram_hdc_sdk import encode_level

# ── HDC Setup ─────────────────────────────────────────────────────────────
D         = 10_000   # dimension (10K = 10MB RAM, fast on any Mac)
N_LEVELS  = 100
N_FRAMES  = 10       # temporal frames per gesture
N_CHANNELS = 63      # 21 landmarks × 3 axes


class Backend:
    def __init__(self, d):
        self.d = d
        self.rng = np.random.default_rng(42)
    def random_hv(self): return (self.rng.integers(0,2,self.d)*2-1).astype(np.int8)
    def bind(self,a,b): return (a*b).astype(np.int8)
    def bundle(self,hvs):
        s=hvs.sum(axis=0); r=np.where(s>=0,1,-1).astype(np.int8)
        ties=(s==0); r[ties]=(self.rng.integers(0,2,ties.sum())*2-1).astype(np.int8)
        return r
    def permute(self,hv,n): return np.roll(hv,n)
    def cos(self,a,b):
        af,bf=a.astype(np.float32),b.astype(np.float32)
        return float(np.dot(af,bf)/(np.linalg.norm(af)*np.linalg.norm(bf)+1e-9))


def make_level_hvs(n, d, seed=99):
    rng=np.random.default_rng(seed); base=(rng.integers(0,2,d)*2-1).astype(np.int8)
    lvls=[base.copy()]; nf=d//n
    for _ in range(1,n):
        hv=lvls[-1].copy(); idx=rng.choice(d,nf,replace=False); hv[idx]*=-1; lvls.append(hv)
    return np.array(lvls,dtype=np.int8)


be = Backend(D)
ch_hvs = np.array([be.random_hv() for _ in range(N_CHANNELS)])
lv_hvs = make_level_hvs(N_LEVELS, D)


def normalize_keypoints(landmarks) -> np.ndarray:
    """MediaPipe 21-landmark list → (63,) normalized float64 in [0,1]."""
    pts = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])  # (21,3)
    wrist = pts[0]
    centered = pts - wrist
    scale = np.max(np.abs(centered)) + 1e-6
    return np.clip((centered.flatten() / scale + 1) / 2, 0.0, 1.0)


def encode_sequence(frames: list) -> np.ndarray:
    """List of (63,) frames → single gesture HV."""
    n = len(frames)
    if n == 0:
        return be.random_hv()
    # Pad or subsample to N_FRAMES
    if n < N_FRAMES:
        idx = np.linspace(0, n-1, N_FRAMES).astype(int)
    else:
        idx = np.linspace(0, n-1, N_FRAMES).astype(int)
    sampled = [frames[i] for i in idx]
    fhvs = [be.permute(encode_level(f, ch_hvs, lv_hvs, be), t)
            for t, f in enumerate(sampled)]
    return be.bundle(np.stack(fhvs))


# ── Memory ─────────────────────────────────────────────────────────────────
class SignMemory:
    def __init__(self):
        self.prototypes = {}   # label → HV

    def register(self, label: str, hv: np.ndarray):
        if label in self.prototypes:
            # Bundle with existing prototype → multi-shot averaging
            self.prototypes[label] = be.bundle(np.stack([self.prototypes[label], hv]))
        else:
            self.prototypes[label] = hv.copy()

    def search(self, query: np.ndarray):
        if not self.prototypes:
            return None, 0.0
        sims = {lbl: be.cos(hv, query) for lbl, hv in self.prototypes.items()}
        best = max(sims, key=sims.get)
        return best, sims[best], sims

    def clear(self):
        self.prototypes.clear()

    def __len__(self):
        return len(self.prototypes)


# ── Drawing helpers ─────────────────────────────────────────────────────────
COLORS = {
    'bg': (20, 20, 20),
    'panel': (35, 35, 35),
    'green': (80, 200, 80),
    'red': (80, 80, 220),
    'yellow': (80, 200, 220),
    'white': (230, 230, 230),
    'gray': (120, 120, 120),
    'accent': (200, 140, 60),
    'bar_bg': (60, 60, 60),
}

PANEL_W = 320


def draw_panel(frame, memory, result, label_pending, record_progress, fps):
    """Draw right-side info panel onto frame."""
    h, w = frame.shape[:2]
    # Panel background
    cv2.rectangle(frame, (w-PANEL_W, 0), (w, h), COLORS['panel'], -1)
    cv2.line(frame, (w-PANEL_W, 0), (w-PANEL_W, h), COLORS['gray'], 1)

    x0 = w - PANEL_W + 12
    y = 28

    # Title
    cv2.putText(frame, "HDC Sign Language", (x0, y), cv2.FONT_HERSHEY_SIMPLEX,
                0.55, COLORS['accent'], 1, cv2.LINE_AA)
    y += 18
    cv2.putText(frame, f"D={D:,}  fps={fps:.0f}", (x0, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.38, COLORS['gray'], 1, cv2.LINE_AA)
    y += 22

    # Recording state
    if label_pending:
        cv2.rectangle(frame, (x0-8, y-14), (w-8, y+8), (60,0,0), -1)
        msg = f"RECORDING '{label_pending}' {record_progress*'|'}"
        cv2.putText(frame, msg, (x0, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.42, COLORS['red'], 1, cv2.LINE_AA)
        # Progress bar
        y += 14
        bar_w = PANEL_W - 24
        filled = int(bar_w * min(record_progress / N_FRAMES, 1.0))
        cv2.rectangle(frame, (x0-2, y), (x0-2+bar_w, y+6), COLORS['bar_bg'], -1)
        cv2.rectangle(frame, (x0-2, y), (x0-2+filled, y+6), COLORS['red'], -1)
        y += 16
    else:
        cv2.putText(frame, "READY", (x0, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.42, COLORS['green'], 1, cv2.LINE_AA)
        y += 22

    # Divider
    cv2.line(frame, (x0-4, y), (w-8, y), COLORS['gray'], 1); y += 14

    # Registered signs
    cv2.putText(frame, f"Signs registered: {len(memory)}", (x0, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLORS['white'], 1, cv2.LINE_AA)
    y += 16
    for lbl in list(memory.prototypes.keys())[:8]:
        cv2.putText(frame, f"  [{lbl}]", (x0, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, COLORS['yellow'], 1, cv2.LINE_AA)
        y += 14

    # Divider
    y += 4
    cv2.line(frame, (x0-4, y), (w-8, y), COLORS['gray'], 1); y += 14

    # Recognition result
    if result and len(memory) > 0:
        best_label, best_sim, all_sims = result
        cv2.putText(frame, "RECOGNIZED:", (x0, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, COLORS['gray'], 1, cv2.LINE_AA)
        y += 18
        # Big label
        cv2.putText(frame, best_label, (x0, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.75, COLORS['green'], 2, cv2.LINE_AA)
        y += 26
        # Confidence bar
        bar_w = PANEL_W - 24
        filled = int(bar_w * best_sim)
        cv2.rectangle(frame, (x0-2, y), (x0-2+bar_w, y+8), COLORS['bar_bg'], -1)
        color = COLORS['green'] if best_sim > 0.55 else COLORS['yellow']
        cv2.rectangle(frame, (x0-2, y), (x0-2+filled, y+8), color, -1)
        y += 12
        cv2.putText(frame, f"confidence: {best_sim:.2f}", (x0, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.37, COLORS['gray'], 1, cv2.LINE_AA)
        y += 18

        # All similarities
        for lbl, sim in sorted(all_sims.items(), key=lambda x: -x[1])[:6]:
            bar_w2 = int((PANEL_W-60) * sim)
            cv2.rectangle(frame, (x0, y-7), (x0+bar_w2, y-1), (50,80,50), -1)
            marker = ">" if lbl == best_label else " "
            cv2.putText(frame, f"{marker}{lbl[:12]:<12} {sim:.2f}", (x0, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.33,
                        COLORS['green'] if lbl == best_label else COLORS['gray'],
                        1, cv2.LINE_AA)
            y += 13
    else:
        hint = "Register signs with [1-9]" if len(memory) == 0 else "Show hand to recognize"
        cv2.putText(frame, hint, (x0, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.36, COLORS['gray'], 1, cv2.LINE_AA)
        y += 18

    # Controls footer
    y = h - 90
    cv2.line(frame, (x0-4, y), (w-8, y), COLORS['gray'], 1); y += 12
    for line in ["[1-9] register sign", "[SPACE] clear all",
                 "[s] save  [l] load", "[q/ESC] quit"]:
        cv2.putText(frame, line, (x0, y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.33, COLORS['gray'], 1, cv2.LINE_AA)
        y += 13

    return frame


def draw_hand_skeleton(frame, hand_landmarks, h, w, cam_w):
    """Draw hand skeleton on camera area (left of panel)."""
    import mediapipe as mp
    connections = mp.solutions.hands.HAND_CONNECTIONS
    lms = hand_landmarks.landmark
    # Draw connections
    for c in connections:
        p1 = lms[c[0]]; p2 = lms[c[1]]
        x1,y1 = int(p1.x*cam_w), int(p1.y*h)
        x2,y2 = int(p2.x*cam_w), int(p2.y*h)
        cv2.line(frame, (x1,y1), (x2,y2), (100,180,100), 1)
    # Draw joints
    for i, lm in enumerate(lms):
        cx, cy = int(lm.x*cam_w), int(lm.y*h)
        color = COLORS['accent'] if i == 0 else (80,160,80)
        cv2.circle(frame, (cx,cy), 4, color, -1)


# ── Main loop ──────────────────────────────────────────────────────────────
def main(sign_labels=None, save_path=None):
    import mediapipe as mp

    mp_hands = mp.solutions.hands
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.5
    )

    memory = SignMemory()
    save_path = save_path or os.path.join(os.path.dirname(__file__), "signlang_memory.json")

    # Pre-defined sign label slots
    if sign_labels is None:
        sign_labels = {
            '1': '你好', '2': '谢谢', '3': '再见',
            '4': '我',   '5': '爱',   '6': '中国',
            '7': '朋友', '8': '好',   '9': '不好',
        }

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("ERROR: Cannot open camera. Check permissions.")
        return

    # Window setup
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 960)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 540)
    WIN = "HDC Sign Language Demo — millisecond-era"
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, 960 + PANEL_W, 540)

    # State
    label_pending = None     # sign label being recorded
    record_buffer = []       # frames accumulating for current recording
    RECORD_FRAMES = 30       # frames to capture per sign (~1 second at 30fps)
    result = None
    query_buffer = []        # rolling buffer for live inference
    QUERY_FRAMES = 20

    fps_counter = [time.perf_counter()] * 10
    fps = 30.0

    print(f"\n{'='*50}")
    print("HDC Sign Language Webcam Demo")
    print(f"D={D:,}  n_levels={N_LEVELS}  frames_per_sign={RECORD_FRAMES}")
    print(f"\nSign slots:")
    for k, v in sign_labels.items():
        print(f"  [{k}] → {v}")
    print(f"\nControls: [1-9] register  [SPACE] clear  [s] save  [l] load  [q] quit")
    print("="*50)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)   # mirror
        h, w = frame.shape[:2]
        cam_w = w - PANEL_W

        # Crop to camera area for MediaPipe
        cam_frame = frame[:, :cam_w].copy()
        rgb = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        mp_result = hands.process(rgb)
        rgb.flags.writeable = True

        hand_kp = None
        if mp_result.multi_hand_landmarks:
            lms = mp_result.multi_hand_landmarks[0]
            draw_hand_skeleton(frame, lms, h, cam_w, cam_w)
            hand_kp = normalize_keypoints(lms.landmark)

        # ── Recording mode ───────────────────────────────────────
        if label_pending is not None:
            if hand_kp is not None:
                record_buffer.append(hand_kp)
            if len(record_buffer) >= RECORD_FRAMES:
                hv = encode_sequence(record_buffer)
                memory.register(label_pending, hv)
                print(f"  Registered '{label_pending}' ({len(record_buffer)} frames)")
                label_pending = None
                record_buffer = []
        else:
            # ── Live inference ───────────────────────────────────
            if hand_kp is not None:
                query_buffer.append(hand_kp)
                if len(query_buffer) > QUERY_FRAMES:
                    query_buffer.pop(0)
                if len(query_buffer) >= N_FRAMES and len(memory) > 0:
                    t0 = time.perf_counter()
                    q_hv = encode_sequence(query_buffer)
                    result = memory.search(q_hv)
                    latency_ms = (time.perf_counter() - t0) * 1000
            else:
                query_buffer.clear()
                if len(memory) == 0:
                    result = None

        # ── FPS ─────────────────────────────────────────────────
        now = time.perf_counter()
        fps_counter.pop(0); fps_counter.append(now)
        fps = (len(fps_counter)-1) / max(fps_counter[-1]-fps_counter[0], 1e-6)

        # ── Draw panel ───────────────────────────────────────────
        draw_panel(frame, memory, result, label_pending,
                   len(record_buffer), fps)

        # ── "No hand" overlay ───────────────────────────────────
        if not mp_result.multi_hand_landmarks and label_pending is None:
            cv2.putText(frame, "Show your hand", (20, h-20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS['gray'], 1, cv2.LINE_AA)

        cv2.imshow(WIN, frame)

        # ── Key handling ─────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF
        if key in (ord('q'), 27):   # q or ESC
            break
        elif key == ord(' '):
            memory.clear(); result = None; query_buffer.clear()
            print("  Memory cleared")
        elif key == ord('s'):
            data = {lbl: hv.tolist() for lbl, hv in memory.prototypes.items()}
            with open(save_path, 'w') as f:
                json.dump({'d': D, 'signs': data}, f)
            print(f"  Saved {len(memory)} signs → {save_path}")
        elif key == ord('l'):
            if os.path.exists(save_path):
                with open(save_path) as f:
                    data = json.load(f)
                memory.clear()
                for lbl, hv_list in data['signs'].items():
                    memory.prototypes[lbl] = np.array(hv_list, dtype=np.int8)
                print(f"  Loaded {len(memory)} signs ← {save_path}")
            else:
                print(f"  No saved file at {save_path}")
        elif chr(key) in sign_labels and label_pending is None:
            lbl = sign_labels[chr(key)]
            label_pending = lbl
            record_buffer = []
            print(f"  Recording '{lbl}' — show your sign...")

    cap.release()
    cv2.destroyAllWindows()
    hands.close()
    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--d', type=int, default=D)
    parser.add_argument('--signs', type=str, default=None,
                        help='Comma-separated labels for slots 1-9')
    args = parser.parse_args()

    D = args.d
    sign_labels = None
    if args.signs:
        labels = args.signs.split(',')
        sign_labels = {str(i+1): lbl.strip() for i, lbl in enumerate(labels[:9])}

    main(sign_labels=sign_labels)
