import cv2
import subprocess
import re

def list_cameras_windows():
    print("\n--- Scanne Windows-System nach Kameras (DirectShow) ---")
    
    # 1. Namen aus Windows via PowerShell auslesen (Plug & Play Geräte)
    # Wir suchen nach Geräten der Klassen 'Camera' oder 'Image', die 'OK' sind.
    try:
        ps_cmd = 'Get-PnpDevice -Class Camera,Image | Where-Object Status -eq "OK" | Select-Object -ExpandProperty FriendlyName'
        # Startet PowerShell und fängt die Ausgabe ab
        proc = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, encoding='utf-8')
        
        # Bereinigt die Liste der Namen
        device_names = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        
        if not device_names:
            print("Keine aktiven Kameras im System gefunden.")
            return

    except FileNotFoundError:
        print("FEHLER: PowerShell konnte nicht gestartet werden.")
        return

    # 2. Parallel dazu OpenCV Indizes prüfen ( DirectShow)
    # OpenCV zählt einfach hoch. Wir prüfen die ersten 10 Plätze.
    available_opencv_indices = []
    print("\nPrüfe OpenCV DirectShow-Ports (bitte warten)...")
    for i in range(10): 
        # CAP_DSHOW ist entscheidend, da das PTZ-Script dieses Backend nutzt
        cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
        if cap.isOpened():
            available_opencv_indices.append(i)
            cap.release() # Sofort wieder freigeben
    
    # 3. Ergebnisse zusammenführen
    print("\n==========================================")
    print("GEFUNDENE KAMERAS (Windows-Name -> Index)")
    print("==========================================\n")
    
    # Da OpenCV und Windows die Indizes nicht garantiert in derselben Reihenfolge
    # auflisten, listen wir hier die gefundenen Systemnamen auf und zeigen
    # die verfügbaren OpenCV-Nummern daneben.
    
    print("Gefundene Gerätenamen im System:")
    for name in device_names:
        print(f" - {name}")
        
    print(f"\nVerfügbare OpenCV DirectShow-Indizes: {available_opencv_indices}")
    print("\n------------------------------------------")
    print("HINWEIS FÜR DAS PTZ-SCRIPT:")
    
    # Automatische Zuordnungs-Idee (basierend auf häufigster Verteilung)
    print("Trage die gewünschte Nummer oben im Multicam-Skript ein.")
    for i, name in enumerate(device_names):
        # Wenn EMEET Pixy der erste Name ist, ist es oft Index 0
        potential_index = "unbekannt"
        if i < len(available_opencv_indices):
            potential_index = available_opencv_indices[i]
            
        print(f"Probier '{name}' mit Index: {potential_index}")
    print("==========================================\n")

if __name__ == "__main__":
    list_cameras_windows()