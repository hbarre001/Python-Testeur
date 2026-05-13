import serial
import serial.tools.list_ports
import tkinter as tk
from tkinter import ttk, messagebox
import time
from collections import deque

# --- CONFIGURATION ---
BAUD_RATE = 250000
NB_TOTAL_AFFICHER = 512 
MARQUEUR_SYNC = 0xFE

class DmxDualMonitor:
    def __init__(self, root, serial_port):
        self.root = root
        self.ser = serial_port
        self.root.title("DMX Analyzer - Adaptatif & Stable")
        self.root.geometry("1200x850")
        self.root.configure(bg="#121212")
        
        self.running = True
        self.dmx_frame = []
        self.last_values = [0] * NB_TOTAL_AFFICHER
        self.last_time = time.time()
        self.fps_buffer = deque(maxlen=50)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # --- Header ---
        header = tk.Frame(root, bg="#121212")
        header.pack(fill="x", pady=10)
        self.lbl_fps = tk.Label(header, text="-- FPS", font=("Consolas", 22, "bold"), bg="#121212", fg="#00ff00")
        self.lbl_fps.pack()
        
        # --- Zone Canvas ---
        self.container = tk.Frame(root, bg="#121212")
        self.container.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.canvas = tk.Canvas(self.container, bg="#000000", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.container, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.bars = []
        self.value_texts = []
        self.bg_rects = []

        self.root.bind("<Configure>", self.on_resize)
        
        self.setup_grid()
        self.run_update()

    def setup_grid(self):
        self.canvas.delete("all")
        self.bars = []
        self.value_texts = []
        self.bg_rects = []

        win_width = self.canvas.winfo_width()
        if win_width < 100: win_width = 1150
        
        largeur_item = 38
        canaux_par_ligne = max(8, (win_width - 60) // largeur_item)
        offset_x = (win_width - (canaux_par_ligne * largeur_item)) // 2
        
        largeur_barre = 24
        espacement_y = 160
        h_max = 80
        
        for i in range(NB_TOTAL_AFFICHER):
            ligne, col = i // canaux_par_ligne, i % canaux_par_ligne
            x0, y_base = col * largeur_item + offset_x, (ligne + 1) * espacement_y 
            
            self.canvas.create_rectangle(x0, y_base - h_max, x0 + largeur_barre, y_base, outline="#1a1a1a", fill="#0a0a0a")
            bar = self.canvas.create_rectangle(x0, y_base, x0 + largeur_barre, y_base, fill="#00d4ff", outline="")
            self.bars.append(bar)
            
            txt_val = self.canvas.create_text(x0 + largeur_barre/2, y_base - h_max - 12, 
                                            text="0", fill="#333", font=("Consolas", 9, "bold"))
            self.value_texts.append(txt_val)
            self.canvas.create_text(x0 + largeur_barre/2, y_base + 15, text=f"{i + 1}", fill="#555", font=("Arial", 7))

        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.last_values = [-1] * NB_TOTAL_AFFICHER

    def on_resize(self, event):
        if hasattr(self, 'last_width') and abs(self.last_width - event.width) < 20:
            return
        self.last_width = event.width
        self.setup_grid()

    def on_closing(self):
        self.running = False
        try: self.ser.close()
        except: pass
        self.root.destroy()

    def run_update(self):
        if not self.running: return
        try:
            # On vide TOUT ce qui est disponible pour éviter le lag
            while self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting)
                for byte in data:
                    if byte == MARQUEUR_SYNC:
                        # --- CORRECTION : Validation de la trame ---
                        # On n'affiche que si on a bien 512 octets entre deux marqueurs
                        if len(self.dmx_frame) == 512:
                            self.update_visuals()
                        self.dmx_frame = [] # Reset dans tous les cas
                    else:
                        # On limite à 512 pour éviter que dmx_frame ne grossisse à l'infini
                        if len(self.dmx_frame) < 512:
                            self.dmx_frame.append(byte)
        except: pass
        self.root.after(5, self.run_update)

    def update_visuals(self):
        if not self.running: return
        now = time.time()
        self.fps_buffer.append(now - self.last_time)
        self.last_time = now

        if len(self.fps_buffer) >= 20:
            fps = 1 / (sum(self.fps_buffer) / len(self.fps_buffer))
            self.lbl_fps.config(text=f"{int(fps)} FPS")

        h_max = 80
        for i in range(NB_TOTAL_AFFICHER):
            val = self.dmx_frame[i]
            if val != self.last_values[i]:
                try:
                    h = int((val / 255) * h_max)
                    coords = self.canvas.coords(self.bars[i])
                    self.canvas.coords(self.bars[i], coords[0], coords[3] - h, coords[2], coords[3])
                    
                    color_txt = "#FFF" if val > 0 else "#333"
                    self.canvas.itemconfig(self.value_texts[i], text=str(val), fill=color_txt)
                    
                    color_bar = "#%02x%02x%02x" % (val, min(160 + val, 255), 255) if val > 0 else "#111"
                    self.canvas.itemconfig(self.bars[i], fill=color_bar)
                    
                    self.last_values[i] = val
                except: break

class SerialSelector:
    def __init__(self, root):
        self.root = root
        self.root.title("DMX Connexion")
        self.root.geometry("400x200")
        tk.Label(root, text="DMX ANALYZER - START", pady=20, font=("Arial", 12, "bold")).pack()
        self.port_var = tk.StringVar()
        self.combo = ttk.Combobox(root, textvariable=self.port_var, state="readonly")
        self.combo.pack(pady=10, padx=40, fill='x')
        btn_frame = tk.Frame(root)
        btn_frame.pack(pady=20)
        tk.Button(btn_frame, text="Actualiser", command=self.refresh_ports).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Lancer", command=self.start_app, bg="#00d4ff").pack(side=tk.LEFT, padx=10)
        self.refresh_ports()

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        self.combo['values'] = [p.device for p in ports]
        if self.combo['values']: self.combo.current(0)

    def start_app(self):
        port = self.port_var.get()
        if not port: return
        try:
            ser = serial.Serial(port, BAUD_RATE, timeout=0)
            for widget in self.root.winfo_children(): widget.destroy()
            DmxDualMonitor(self.root, ser)
        except Exception as e:
            messagebox.showerror("Erreur", str(e))

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialSelector(root)
    root.mainloop()