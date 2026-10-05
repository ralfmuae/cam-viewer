import cv2
import threading
import time

# --- Konfiguration: Kamera-Indizes ---
CAM_INDEX_PIXY = 0
CAM_INDEX_BRIO = 1
CAM_INDEX_USBCAM = 2
CAM_INDEX_S600 = 3
CAM_INDEX_VCAM = 4
CAM_INDEX_OBS = 5

DEFAULT_CAMERA_INDEX = CAM_INDEX_PIXY

FRAME_WIDTH = 2560
FRAME_HEIGHT = 1440
WINDOW_NAME = "Cam Viewer RM Special Edition "

ZOOM_DEFAULT = 100 
PAN_DEFAULT = 0
TILT_DEFAULT = 0

# --- PRESETS (Pan, Tilt, Zoom) ---
PRESET_F1 = {'pan': 0, 'tilt': 0, 'zoom': 100}
PRESET_F2 = {'pan': -8, 'tilt': 2, 'zoom': 150}
PRESET_F3 = {'pan': 0, 'tilt': -32, 'zoom': 150}
PRESET_F4 = {'pan': -100, 'tilt': 10, 'zoom': 100}
PRESET_F5 = {'pan': 88, 'tilt': -10, 'zoom': 100}
PRESET_F6 = {'pan': 0, 'tilt': -45, 'zoom': 150}
PRESET_F7 = {'pan': 0, 'tilt': -50, 'zoom': 100}
PRESET_F8 = {'pan': -12, 'tilt': 50, 'zoom': 100}
PRESET_F9 = {'pan': 140, 'tilt': 45, 'zoom': 100}
PRESET_F10 = {'pan': 0, 'tilt': 0, 'zoom': 100}
PRESET_F11 = {'pan': 0, 'tilt': 0, 'zoom': 100}
PRESET_F12 = {'pan': 0, 'tilt': 0, 'zoom': 100}


class WarmCameraStream:
    """Hintergrund-Thread für warm gebundene EMEET-Kameras."""
    def __init__(self, index, name):
        self.index = index
        self.name = name
        self.cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
        
        self.grabbed, self.frame = self.cap.read()
        self.started = False
        self.read_lock = threading.Lock()

    def start(self):
        if not self.cap.isOpened():
            return None
        self.started = True
        self.thread = threading.Thread(target=self.update, args=(), daemon=True)
        self.thread.start()
        return self

    def update(self):
        while self.started:
            grabbed, frame = self.cap.read()
            with self.read_lock:
                self.grabbed = grabbed
                self.frame = frame
            time.sleep(0.01)

    def read(self):
        with self.read_lock:
            frame_copy = self.frame.copy() if self.grabbed and self.frame is not None else None
            return self.grabbed, frame_copy

    def apply_ptz(self, pan, tilt, zoom):
        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_PAN, pan)
            self.cap.set(cv2.CAP_PROP_TILT, tilt)
            self.cap.set(cv2.CAP_PROP_ZOOM, zoom)

    def stop(self):
        self.started = False
        if hasattr(self, 'thread'):
            self.thread.join(timeout=1.0)
        if self.cap:
            self.cap.release()


class HybridCameraManager:
    def __init__(self):
        self.warm_streams = {}
        self.cold_cap = None
        self.active_index = -1
        self.window_created = False

        self.cam_names = {
            CAM_INDEX_PIXY: "EMEET Pixy (Warm)",
            CAM_INDEX_BRIO: "Logitech Brio (Cold)",
            CAM_INDEX_USBCAM: "USBCam (Cold)",
            CAM_INDEX_S600: "EMEET S600 (Warm)",
            CAM_INDEX_VCAM: "vCam (Cold)",
            CAM_INDEX_OBS: "OBS Virtual Cam (Cold)"
        }

        # PTZ-Speicher für Pixy
        self.pixy_pan = PAN_DEFAULT
        self.pixy_tilt = TILT_DEFAULT
        self.pixy_zoom = ZOOM_DEFAULT

        # GUI Status Toggles
        self.show_info = True
        self.show_help = False

    def add_warm_camera(self, index, name):
        """Warm-Binden der EMEET-Kameras beim Start."""
        stream = WarmCameraStream(index, name)
        if stream.start():
            self.warm_streams[index] = stream
            if index == CAM_INDEX_PIXY:
                stream.apply_ptz(self.pixy_pan, self.pixy_tilt, self.pixy_zoom)

    def switch_to(self, index):
        """Schaltet blitzschnell zwischen Warm- und Cold-Quellen um."""
        if index == self.active_index:
            return

        # Bisherige Cold-Kamera freigeben
        if self.cold_cap is not None:
            self.cold_cap.release()
            self.cold_cap = None

        # Falls Cold-Kamera angefordert wird, jetzt öffnen
        if index not in self.warm_streams:
            self.cold_cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if self.cold_cap.isOpened():
                self.cold_cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_WIDTH)
                self.cold_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_HEIGHT)
            else:
                # Fallback auf Pixy
                index = CAM_INDEX_PIXY

        self.active_index = index

        if not self.window_created:
            cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
            cv2.resizeWindow(WINDOW_NAME, FRAME_WIDTH, FRAME_HEIGHT)
            self.window_created = True

    def get_current_frame(self):
        """Holt das aktuelle Frame aus der aktiven Quelle."""
        if self.active_index in self.warm_streams:
            return self.warm_streams[self.active_index].read()
        elif self.cold_cap is not None and self.cold_cap.isOpened():
            ret, frame = self.cold_cap.read()
            return ret, frame
        return False, None

    def apply_ptz_hardware(self, pan, tilt, zoom):
        """Sendet DirectShow UVC-Befehle an die Pixy."""
        if CAM_INDEX_PIXY in self.warm_streams:
            self.warm_streams[CAM_INDEX_PIXY].apply_ptz(pan, tilt, zoom)

    def set_preset(self, preset):
        """Fährt ein bestimmtes Preset an (Nur Pixy)."""
        if self.active_index == CAM_INDEX_PIXY:
            self.pixy_pan = preset['pan']
            self.pixy_tilt = preset['tilt']
            self.pixy_zoom = preset['zoom']
            self.apply_ptz_hardware(self.pixy_pan, self.pixy_tilt, self.pixy_zoom)

    def update_pixy_ptz(self, pan_adj, tilt_adj, zoom_adj):
        """Manuelle Anpassung per Pfeiltasten."""
        self.pixy_pan += pan_adj
        self.pixy_tilt += tilt_adj
        self.pixy_zoom = max(100, self.pixy_zoom + zoom_adj)

        self.pixy_pan = max(-180, min(180, self.pixy_pan))
        self.pixy_tilt = max(-40, min(40, self.pixy_tilt))
        self.pixy_zoom = max(100, min(400, self.pixy_zoom))

        self.apply_ptz_hardware(self.pixy_pan, self.pixy_tilt, self.pixy_zoom)

    def reset_pixy(self):
        self.set_preset(PRESET_F1)

    def show_frame(self):
        # Prüfen, ob das Fenster vom User über das 'X' geschlossen wurde
        if self.window_created and cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            return False

        ret, frame = self.get_current_frame()        
        ret, frame = self.get_current_frame()
        if ret and frame is not None:
            is_ptz_active = (self.active_index == CAM_INDEX_PIXY)

            # --- INFO-ZEILE EINBLENDEN (HALBTRANSPARENT) ---
            if self.show_info:
                cam_name = self.cam_names.get(self.active_index, "Unbekannt")
                ptz_status = "PTZ OK" if is_ptz_active else "No PTZ"
                info = f"Cam: {cam_name} ({self.active_index}) | {ptz_status} | P:{self.pixy_pan} T:{self.pixy_tilt} Z:{self.pixy_zoom} | 2560x1440 | H: Hilfe"

                # Overlay-Kopie erstellen
                info_overlay = frame.copy()

                # Schwarzer Hintergrund-Kasten auf dem Overlay (Alpha 0.5)
                cv2.rectangle(info_overlay, (20, 20), (1250, 75), (0, 0, 0), -1)
                
                # Mit Originalbild mischen (0.5 = 50% Transparenz)
                cv2.addWeighted(info_overlay, 0.5, frame, 0.5, 0, frame)

                # Text gut lesbar auf das gemischte Frame zeichnen
                cv2.putText(frame, info, (30, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

            # --- HILFE-OVERLAY EINBLENDEN ---
            if self.show_help:
                overlay = frame.copy()
                cv2.rectangle(overlay, (50, 50), (900, 750), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

                help_lines = [
                    "=== STEUERUNG & HILFE (H) ===",
                    "",
                    "KAMERA UMSCHALTEN:",
                    "  0 : EMEET Pixy (PTZ - Warm Hold)",
                    "  1 : Logitech Brio (Cold)",
                    "  2 : USBCam (Cold)",
                    "  3 : EMEET S600 (Warm Hold)",
                    "  4 : vCam (Cold)",
                    "  5 : OBS Virtual Cam (Cold)",
                    "",
                    "PRESETS (Nur Pixy):",
                    "  F1 : P:0 T:0 Z:100 (Home)",
                    "  F2 : P:-8 T:6 Z:150",
                    "  F3 : P:-100 T:10 Z:100",
                    "  F4 : P:88 T:-40 Z:100",
                    "  F5 : P:0 T:-40 Z:150",
                    "",
                    "MANUELL (Nur Pixy):",
                    "  Pfeiltasten : Pan / Tilt",
                    "  + / -       : Zoom In / Out",
                    "  R           : Reset Position",
                    "",
                    "GUI:",
                    "  I           : Infozeile An/Aus",
                    "  H           : Diese Hilfe An/Aus",
                    "  Q / ESC     : Beenden"
                ]

                y_offset = 90
                for line in help_lines:
                    color = (0, 255, 255) if line.startswith("===") or line.endswith(":") else (255, 255, 255)
                    cv2.putText(frame, line, (80, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    y_offset += 25

            cv2.imshow(WINDOW_NAME, frame)
            return True
        return False

    def stop_all(self):
        for stream in self.warm_streams.values():
            stream.stop()
        if self.cold_cap is not None:
            self.cold_cap.release()
        cv2.destroyAllWindows()


def main():
    manager = HybridCameraManager()

    # EMEET Kameras WARM im Hintergrund laden
    manager.add_warm_camera(CAM_INDEX_PIXY, "EMEET Pixy")
    manager.add_warm_camera(CAM_INDEX_S600, "EMEET S600")

    # Start-Kamera wählen
    manager.switch_to(DEFAULT_CAMERA_INDEX)

    move_step = 2
    zoom_step = 10

    while True:
        if not manager.show_frame():
            break

        key = cv2.waitKeyEx(1)

        # Falls unklar ist was gedrückt wurde
        #if key != -1:
        #    print(f"Gedrückte Taste Code: {key}")

        # Beenden
        if key in [27, ord('q'), ord('Q')]:
            break

        # --- GUI TOGGLES ---
        elif key in [ord('i'), ord('I')]:
            manager.show_info = not manager.show_info

        elif key in [ord('h'), ord('H')]:
            manager.show_help = not manager.show_help

        # --- KAMERA UMSCHALTEN (0-5) ---
        elif key == ord('0'): manager.switch_to(CAM_INDEX_PIXY)
        elif key == ord('1'): manager.switch_to(CAM_INDEX_BRIO)
        elif key == ord('2'): manager.switch_to(CAM_INDEX_USBCAM)
        elif key == ord('3'): manager.switch_to(CAM_INDEX_S600)
        elif key == ord('4'): manager.switch_to(CAM_INDEX_VCAM)
        elif key == ord('5'): manager.switch_to(CAM_INDEX_OBS)

        # --- PTZ / PRESET STEUERUNG (Nur Pixy) ---
        elif manager.active_index == CAM_INDEX_PIXY:

            # Presets F1 - F12
            if key == 7340032:   manager.set_preset(PRESET_F1)
            elif key == 7405568: manager.set_preset(PRESET_F2)
            elif key == 7471104: manager.set_preset(PRESET_F3)
            elif key == 7536640: manager.set_preset(PRESET_F4)
            elif key == 7602176: manager.set_preset(PRESET_F5)
            elif key == 7667712: manager.set_preset(PRESET_F6)
            elif key == 7733248: manager.set_preset(PRESET_F7)
            elif key == 7798784: manager.set_preset(PRESET_F8)
            elif key == 7864320: manager.set_preset(PRESET_F9)
            elif key == 7929856: manager.set_preset(PRESET_F10)
            elif key == 7995392: manager.set_preset(PRESET_F11)
            elif key == 8060928: manager.set_preset(PRESET_F12)

            # Manual Reset
            elif key in [ord('r'), ord('R')]:
                manager.reset_pixy()

            # Pfeiltasten
            elif key == 2424832: manager.update_pixy_ptz(move_step, 0, 0)   # Links
            elif key == 2555904: manager.update_pixy_ptz(-move_step, 0, 0)  # Rechts
            elif key == 2490368: manager.update_pixy_ptz(0, move_step, 0)   # Hoch
            elif key == 2621440: manager.update_pixy_ptz(0, -move_step, 0)  # Runter

            # Zoom (+ / -)
            elif key in [43, 171]: manager.update_pixy_ptz(0, 0, zoom_step)
            elif key in [45, 173]: manager.update_pixy_ptz(0, 0, -zoom_step)

    manager.stop_all()


if __name__ == "__main__":
    main()