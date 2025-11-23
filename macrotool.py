import tkinter as tk
from tkinter import messagebox
from pynput import mouse, keyboard
import threading
import time
import ast
import base64

LOG_FILE = 'macrotool.mtl'

class MacroTool:
    def __init__(self,root):
        self.root = root
        self.root.title("MacroTool")

        #Recording State
        self.is_recording =False
        self.events = []
        self.start_time = None
        self.mouse_listener =None
        self.keyboard_listener = None
        self.lock = threading.Lock()

        #playback state
        self.is_playing = False
        self.stop_playback_event = threading.Event()
        self.esc_listener = None 
        self.speed_multipler = 1 

        self.build_gui()

    def build_gui(self):
        main_frame = tk.Frame(self.root, padx=10, pady=10)
        main_frame.pack()

        #recording controlls 
        record_frame = tk.LabelFrame(main_frame,text="Recording")
        record_frame.grid(row=0,column=0,padx=5,pady=5,sticky="ew")

        self.record_btn = tk.Button(record_frame, text = "Record", width=12, command=self.toggle_record)
        self.record_btn.pack(side=tk.LEFT, padx = 5, pady= 5)

        self.stop_btn = tk.Button(record_frame, text="stop record",width=12, command= self.stop_record,state=tk.DISABLED )
        self.stop_btn.pack(side=tk.LEFT, padx = 5, pady= 5)


        #play back controls
        play_frame = tk.LabelFrame(main_frame,text="Playback")
        play_frame.grid(row=1,column=0,padx=5,pady=5,sticky="ew")

        tk.Label(play_frame,text="Repeat:").pack(side=tk.LEFT,padx=(5,0))
        self.repeat_var = tk.StringVar(value='1')
        self.repeat_entry = tk.Entry(play_frame,width=5, textvariable=self.repeat_var)
        self.repeat_entry.pack(side=tk.LEFT, padx = 5)


        self.speed_toggle_btn = tk.Button(play_frame,text=f"Speed: x{self.speed_multipler}",width=10,command=self.toggle_speed)
        self.speed_toggle_btn.pack(side=tk.LEFT, padx = 5)

        self.play_btn = tk.Button(play_frame,text = "Play", width = 8, command=self.play_macro)
        self.play_btn.pack(side=tk.LEFT, padx = 5)

        self.stop_play_btn = tk.Button(play_frame, text ="STOP", width=8, command = self.stop_playback, state=tk.DISABLED)
        self.stop_play_btn.pack(side=tk.LEFT, padx = 5)

        #status bar
        self.status_var = tk.StringVar(value="Status:Idle")
        status_label = tk.Label(main_frame,textvariable=self.status_var,relief=tk.SUNKEN, anchor='w')
        status_label.grid(row=2,column=0,sticky="ew",padx=5, pady=(10,0))


    def toggle_speed(self):
        self.speed_multipler = self.speed_multipler +1
        if self.speed_multipler >= 5 :
            self.speed_multipler = 1

        self.speed_toggle_btn.config(text=f"Speed: x{self.speed_multipler}")
    
    def toggle_record(self):
        if self.is_playing:
            messagebox.showwarning("Bussy","Cannot record while playing")
            return
        if self.is_recording:
            self.stop_record()

        with open(LOG_FILE, 'w') as f : 
            f.write('')

        self.events.clear()
        self.start_time = time.time()
        self.is_recording = True
        self.record_btn.config(relief=tk.SUNKEN,text="Recording...")
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set("Status:Recording ...")
        self.start_listeners()

    def stop_record(self):
        if not self.is_recording: return
        self.is_recording = False
        self.record_btn.config(relief=tk.RAISED, text="Record")
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Status:Idle")
        self.stop_listeners()
        self.save_events()

    def start_listeners(self):
        self.mouse_listener = mouse.Listener(on_click=self.on_click, on_move = self.on_move, on_scroll=self.on_scroll)
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.mouse_listener.start()
        self.keyboard_listener.start()

    def stop_listeners(self):
        if self.mouse_listener: self.mouse_listener.stop(); self.mouse_listener = None
        if self.keyboard_listener: self.keyboard_listener.stop(); self.keyboard_listener = None    
    
    def add_event(self,event_type,details):
        if not self.is_recording: return
        timestamp = time.time() - self.start_time
        with self.lock : 
            self.events.append((timestamp,event_type,details))

    def on_click(self,x,y,button,pressed): self.add_event('mouse_click',{'x':x,'y':y,'button':str(button),'pressed':pressed})
    def on_move(self,x,y):self.add_event('mouse_move',{'x':x,'y':y})
    def on_scroll(self,x,y,dx,dy): self.add_event('mouse_scroll',{'x':x,'y':y,'dx':dx,'dy':dy})
    def on_press(self,key): self.add_event('key_press',{'key':self.get_key_str(key)})
    def on_release(self,key): self.add_event('key_release',{'key':self.get_key_str(key)})

    def get_key_str(self,key):
        try: return key.char
        except AttributeError: return str(key)

    def save_events(self):
        with open(LOG_FILE, 'w') as f:
            for e in self.events:
                f.write(repr(e)+'\n')
        messagebox.showinfo("Saved",f"Recorded {len(self.events)} events to {LOG_FILE}")

    def load_events(self):
        loaded_events = []
        try:
            with open(LOG_FILE, 'r') as f:
                for line in f:
                    if line.strip(): loaded_events.append(ast.literal_eval(line))
        except Exception as e : 
            messagebox.showerror("Error",f"Failed to load log : {e}")
        return loaded_events
    

    def play_macro(self):
        if self.is_recording or self.is_playing:
            messagebox.showwarning("Busy","Cannot play while recording or already playing")
            return
        try:
            repeat = int(self.repeat_var.get())
            if repeat < 1 : raise ValueError()
        except ValueError:
            messagebox.showerror("Invalid input","Repeat must be positive integer")
            return
        
        events = self.load_events()
        if not events:
            messagebox.showwarning("No Events","Record events")
            return
        
        self.is_playing =True
        self.stop_playback_event.clear()

        self.record_btn.config(state=tk.DISABLED)
        self.play_btn.config(state=tk.DISABLED)
        self.speed_toggle_btn.config(state=tk.DISABLED)
        self.stop_play_btn.config(state=tk.NORMAL)

        self.start_esc_listener()
        
        current_speed = self.speed_multipler
        threading.Thread(target=self.run_playback, args=(events, repeat, current_speed),daemon=True).start()


    def stop_playback(self):
        if self.is_playing:
            self.stop_playback_event.set()
            self.status_var.set("Status: stopping...")

    def on_esc_press(self,key):
        if key == keyboard.Key.esc:
            self.stop_playback()
            return False
        
    def start_esc_listener(self):
        if not self.esc_listener:
            self.esc_listener = keyboard.Listener(on_press=self.on_esc_press)
            self.esc_listener.start()

    def stop_esc_listener(self):
        if self.esc_listener: self.esc_listener.stop(); self.esc_listener = None 

    def run_playback(self,events,repeat,speed_multiplier):
        mouse_controller = mouse.Controller()
        keyboard_controller = keyboard.Controller()

        for i in range(repeat):
            if self.stop_playback_event.is_set(): break

            self.status_var.set(f"Status: Playing loop {i+1} of {repeat} at x{self.speed_multipler} speed")

            last_timestamp =0.0

            for timestamp, event_type, details in events:
                if self.stop_playback_event.is_set():break

                #apply the speed multipler 
                delay = timestamp - last_timestamp
                adjusted_delay = delay  / speed_multiplier
                time.sleep(max(adjusted_delay,0))

                # executiong logic
                if event_type == 'mouse_move':
                    mouse_controller.position=(details['x'],details['y'])
                elif event_type == 'mouse_click':
                    btn = getattr(mouse.Button,details['button'].split('.')[-1])
                    if details['pressed']:mouse_controller.press(btn)
                    else:mouse_controller.release(btn)
                elif event_type == 'mouse_scroll':
                    mouse_controller.scroll(details['dx'],details['dy'])
                elif event_type in ('key_press', 'key_release'):
                    key = self.parse_key_str(details['key'])
                    if key:
                        if event_type == 'key_press':keyboard_controller.press(key)
                        else: keyboard_controller.release(key)
            
                last_timestamp = timestamp 
        self.root.after(0,self.playback_finished)

    def playback_finished(self):
        self.is_playing = False
        self.stop_esc_listener()

        # re enable all state
        self.record_btn.config(state=tk.NORMAL)
        self.play_btn.config(state=tk.NORMAL)
        self.speed_toggle_btn.config(state=tk.NORMAL)
        self.stop_play_btn.config(state=tk.DISABLED)

        if self.stop_playback_event.is_set():
            self.status_var.set("Status: playback stopped.")
        else:
            self.status_var.set("Status: playback finished.")

    def parse_key_str(self,key_str):
        if len(key_str) == 1 : return key_str
        if key_str.startswith('Key.'):
            try: return getattr(keyboard.Key, key_str.split('.')[1])
            except AttributeError: return None 
        return None            


if __name__ == "__main__":
    root = tk.Tk()
    root.attributes("-topmost",True)
    app = MacroTool(root)
    def on_closing():
        app.stop_listeners()
        app.stop_esc_listener()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW",on_closing)

    #img_data = "ABC"
    #photo = tk.PhotoImage(data=base64.b64decode(img_data))
    #root.iconphoto(True,photo)
    root.mainloop()







