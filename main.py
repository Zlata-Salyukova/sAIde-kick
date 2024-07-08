import os
import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk
from openai import OpenAI
import base64
import io
import time
from mss import mss  # For reliable multi-monitor support

class ChatWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("sAIde-Kick")
        self.geometry("1000x800")
        self.configure(bg="#2C2C2C")

        # OpenAI API key: set key with terminal command >set OPENAI_API_KEY=your_api_key_here
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("No OpenAI API key found. Please set the OPENAI_API_KEY environment variable.")

        self.client = OpenAI(api_key=api_key)

        self.chat_history = []
        self.selected_screenshots = []
        self.current_screenshots = []

        self.create_widgets()
        self.toggle_pin()
        self.update_screenshots()

    def create_widgets(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header_frame = tk.Frame(self, bg="#2C2C2C")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(10, 5))
        header_frame.grid_columnconfigure(0, weight=1)

        self.header = tk.Label(header_frame, text="sAIde-Kick", font=("Arial", 48, "bold"), bg="#2C2C2C", fg="#A020F0")
        self.header.grid(row=0, column=0)

        # Pin Checkbox
        self.pin_var = tk.IntVar(value=1)
        self.pin_checkbox = tk.Checkbutton(header_frame, text="Pin", variable=self.pin_var, command=self.toggle_pin, 
                                           bg="#2C2C2C", fg="#FFFFFF", font=("Arial", 24), 
                                           selectcolor="#A020F0", activebackground="#2C2C2C")
        self.pin_checkbox.grid(row=0, column=1, padx=(0, 20))

        # Chat Display
        self.chat_display = scrolledtext.ScrolledText(self, wrap=tk.WORD, bg="#2C2C2C", fg="#000000", 
                                                      font=("Arial", 14), state="disabled")
        self.chat_display.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        # Input Field
        input_frame = tk.Frame(self, bg="#2C2C2C")
        input_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(5, 10))
        input_frame.grid_columnconfigure(0, weight=1)
        input_frame.grid_rowconfigure(0, weight=1)

        self.input_field = tk.Text(input_frame, font=("Arial", 14), bg="#FFFFFF", wrap=tk.WORD, height=1)
        self.input_field.grid(row=0, column=0, sticky="nsew")
        self.input_field.bind("<KeyRelease>", self.on_input_change)
        self.input_field.bind("<Return>", self.send_message)

        # Add a scrollbar to the input field
        input_scrollbar = tk.Scrollbar(input_frame, command=self.input_field.yview)
        input_scrollbar.grid(row=0, column=1, sticky="ns")
        self.input_field.config(yscrollcommand=input_scrollbar.set)

        self.send_button = tk.Button(input_frame, text="Chat", command=self.send_message, font=("Arial", 24), bg="#A020F0", fg="#FFFFFF")
        self.send_button.grid(row=0, column=2, padx=(10, 0))

        # Screenshots Frame
        self.screenshots_frame = tk.Frame(self, bg="#2C2C2C")
        self.screenshots_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=(5, 10))
        self.screenshots_frame.grid_columnconfigure(0, weight=1)
        self.screenshots_frame.grid_rowconfigure(0, weight=1)

        self.screenshots_container = tk.Frame(self.screenshots_frame, bg="#2C2C2C")
        self.screenshots_container.grid(row=0, column=0)

    def toggle_pin(self):
        if self.pin_var.get() == 1:
            self.attributes("-topmost", True)
            self.pin_checkbox.config(fg="#32a852")
        else:
            self.attributes("-topmost", False)
            self.pin_checkbox.config(fg="#FFFFFF")

    def on_input_change(self, event):
        content = self.input_field.get("1.0", tk.END)
        lines = content.split('\n')
        height = min(max(len(lines), 1), 5)  # Ensure minimum of 1 and maximum of 5 lines
        
        # Calculate pixel height (assuming each line is about 30 pixels high)
        pixel_height = height * 30
        
        self.input_field.config(height=height)
        self.input_field.master.config(height=pixel_height)
        
        # Force update of the layout
        self.update_idletasks()
        
        # Scroll to the end to show the latest typed text
        self.input_field.see(tk.END)

    def send_message(self, event=None):
        user_message = self.input_field.get("1.0", tk.END).strip()
        if user_message:
            self.display_message("user", user_message)
            self.input_field.delete("1.0", tk.END)
            self.process_message(user_message)
        if event:
            return "break"  # Prevents the newline character from being inserted

    def display_message(self, role, message):
        self.chat_display.configure(state="normal")
        tag = "user" if role == "user" else "assistant"
        self.chat_display.insert(tk.END, f"{role.capitalize()}: ", tag + "_tag")
        self.chat_display.insert(tk.END, message + "\n\n", tag)
        self.chat_display.tag_config("user_tag", foreground="#A020F0", font=("Arial", 14, "bold"))
        self.chat_display.tag_config("assistant_tag", foreground="#FFFFFF", font=("Arial", 14, "bold"))
        self.chat_display.tag_config("user", foreground="#FFFFFF", font=("Arial", 14))
        self.chat_display.tag_config("assistant", foreground="#FFFFFF", background="#A020F0", font=("Arial", 14))
        self.chat_display.configure(state="disabled")
        self.chat_display.see(tk.END)

        self.chat_history.append({"role": role, "content": message})
        if len(self.chat_history) > 20:
            self.chat_history = self.chat_history[-20:]

    def process_message(self, user_message):
        messages = self.chat_history + [
            {"role": "system", "content": "You are sAIde-kick, images attached are the users computer. Use these screenshots for context to any and every answer. if no image is attached, just answer the users question."},
            {"role": "user", "content": user_message},
        ]

        selected_images = [img for i, img in enumerate(self.current_screenshots) if self.is_screenshot_selected(i)]
        
        if selected_images:
            for screenshot in selected_images:
                buffered = io.BytesIO()
                screenshot.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode()
                messages.append({
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Here is a selected screenshot:"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str}"}}
                    ]
                })

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=2500
        )

        if response.choices and len(response.choices) > 0:
            assistant_message = response.choices[0].message.content
            self.display_message("assistant", assistant_message)
        else:
            self.display_message("assistant", "Error: No response from assistant.")

    def update_screenshots(self):
        for widget in self.screenshots_container.winfo_children():
            widget.destroy()

        self.current_screenshots = []
        with mss() as sct:
            for i, monitor in enumerate(sct.monitors[1:]):
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX")
                img.thumbnail((200, 200))
                photo = ImageTk.PhotoImage(img)

                frame = tk.Frame(self.screenshots_container, borderwidth=2, relief="solid")
                frame.pack(side=tk.LEFT, padx=5, pady=5)

                label = tk.Label(frame, image=photo)
                label.image = photo
                label.pack()

                self.current_screenshots.append(img)
                label.bind("<Button-1>", lambda e, idx=i: self.select_screenshot(e, idx))

                # Reapply selection if this screenshot was previously selected
                if self.is_screenshot_selected(i):
                    self.apply_selection_style(frame)

        self.after(1000, self.update_screenshots)

    def select_screenshot(self, event, idx):
        frame = event.widget.master
        if self.is_screenshot_selected(idx):
            self.selected_screenshots[idx] = False
            frame.config(borderwidth=2, highlightbackground="black", highlightcolor="black", highlightthickness=2)
        else:
            if idx >= len(self.selected_screenshots):
                self.selected_screenshots.extend([False] * (idx - len(self.selected_screenshots) + 1))
            self.selected_screenshots[idx] = True
            self.apply_selection_style(frame)

    def is_screenshot_selected(self, idx):
        return idx < len(self.selected_screenshots) and self.selected_screenshots[idx]

    def apply_selection_style(self, frame):
        frame.config(borderwidth=4, highlightbackground="#32a852", highlightcolor="#32a852", highlightthickness=4)

if __name__ == "__main__":
    app = ChatWindow()
    app.mainloop()