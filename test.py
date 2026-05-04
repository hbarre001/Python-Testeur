import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk, messagebox
import time
from collections import deque

# --- CONFIGURATION ---
BAUD_RATE = 250000
NB_TOTAL_AFFICHER = 40
MARQUEUR_SYNC = 0xFE

class DmxDualMonitor:
    def __init__(self, root, serial_port):
        self.root = root
        self.ser = serial_port
        self.root.title("DMX Analyzer - Double Rack (1-40)")
        self.root.geometry("900x700")
        self.root.configure(bg="#121212")
        
        # Variables
        self.dmx_frame = []
        self.last_time = time.time()
        self.fps_buffer = deque(maxlen=75)

        # --- Header ---
        self.lbl_fps = tk.Label(root, text="-- FPS", font=("Consolas", 22, "bold"), bg="#121212", fg="#00ff00")
        self.lbl_fps.pack(pady=10)
        
        self.lbl_info = tk.Label(root, text=f"Connecté sur {self.ser.port}", font=("Consolas", 10), bg="#121212", fg="#888888")
        self.lbl_info.pack()

        # --- Zone Graphique ---
        self.canvas = tk.Canvas(root, width=850, height=550, bg="#000000", highlightthickness=0)
        self.canvas.pack(pady=10)
        
        self.bars = []
        
        # Création des deux rangées
        for rangee in range(2): 
            y_base = 250 + (rangee * 260) 
            for i in range(20):
                canal_idx = (rangee * 20) + i
                x0 = i * 42 + 15
                self.canvas.create_rectangle(x0, y_base-200, x0 + 32, y_base, outline="#222", fill="#111")
                bar = self.canvas.create_rectangle(x0, y_base, x0 + 32, y_base, fill="#00d4ff", outline="")
                self.bars.append(bar)
                self.canvas.create_text(x0 + 16, y_base + 15, text=f"{canal_idx + 1}", fill="#666", font=("Arial", 9))

        # Lancement de la boucle de mise à jour
        self.run_update()

    def run_update(self):
        try:
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting)
                for byte in data:
                    if byte == MARQUEUR_SYNC: # Détection du marqueur 0xFE de l'Arduino
                        self.update_visuals()
                        self.dmx_frame = []
                    else:
                        self.dmx_frame.append(byte)
        except Exception as e:
            print(f"Erreur lecture : {e}")
            
        self.root.after(5, self.run_update)

    def update_visuals(self):
        now = time.time()
        dt = now - self.last_time
        self.last_time = now

        if dt > 0.001:
            self.fps_buffer.append(dt)

        if len(self.fps_buffer) > 70:
            fps = 1 / (sum(self.fps_buffer) / len(self.fps_buffer))
            self.lbl_fps.config(text=f"{round(fps / 5) * 5} FPS")
            self.lbl_info.config(text=f"Trame reçue : {len(self.dmx_frame)} canaux")

        for i in range(min(len(self.dmx_frame), NB_TOTAL_AFFICHER)):
            val = self.dmx_frame[i]
            h = int((val / 255) * 200) 
            rangee = i // 20
            y_base = 250 + (rangee * 260)
            x0 = (i % 20) * 42 + 15
            self.canvas.coords(self.bars[i], x0, y_base - h, x0 + 32, y_base)
            color = "#%02x%02x%02x" % (val, 180 + (val//4), 255)
            self.canvas.itemconfig(self.bars[i], fill=color)

class SerialSelector:
    def __init__(self, root):
        self.root = root
        self.root.title("Connexion DMX")
        self.root.geometry("350x200")
        self.root.configure(bg="#1e1e1e")

        tk.Label(root, text="SÉLECTEUR PORT COM", font=("Arial", 12, "bold"), bg="#1e1e1e", fg="white").pack(pady=15)

        self.port_var = tk.StringVar()
        self.combo = ttk.Combobox(root, textvariable=self.port_var, state="readonly")
        self.combo.pack(pady=10, padx=20, fill='x')

        btn_frame = tk.Frame(root, bg="#1e1e1e")
        btn_frame.pack(pady=15)
        
        tk.Button(btn_frame, text="Actualiser", command=self.refresh_ports, bg="#333", fg="white").pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Lancer l'Analyseur", command=self.start_app, bg="#00d4ff", fg="black", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=10)

        self.refresh_ports()

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        port_list = [p.device for p in ports]
        self.combo['values'] = port_list
        if port_list:
            self.combo.current(0)

    def start_app(self):
        selected_port = self.port_var.get()
        if not selected_port:
            messagebox.showwarning("Erreur", "Veuillez sélectionner un port COM.")
            return

        try:
            # Ouverture du port à 250000 bauds selon ta documentation[cite: 1]
            ser = serial.Serial(selected_port, BAUD_RATE, timeout=0)
            
            # On détruit l'interface de sélection
            for widget in self.root.winfo_children():
                widget.destroy()
            
            # On lance l'application principale dans la même fenêtre
            DmxDualMonitor(self.root, ser)
            
        except Exception as e:
            messagebox.showerror("Erreur Port", f"Impossible d'ouvrir {selected_port}\n{e}")

if __name__ == "__main__":
    root = tk.Tk()
    # On commence par l'interface de sélection[cite: 1]
    selector = SerialSelector(root)
    root.mainloop()