import tkinter as tk
from tkinter import filedialog, messagebox, font
import subprocess
import os
import keyword
import re

class AutoCompleteListbox(tk.Listbox):
    def __init__(self, master, callback, **kwargs):
        super().__init__(master, **kwargs)
        self.callback = callback
        self.bind("<Double-Button-1>", self.on_select)
        self.bind("<Return>", self.on_select)
        self.bind("<Escape>", lambda e: self.hide())
        self.bind("<FocusOut>", lambda e: self.hide())

    def on_select(self, event):
        if self.curselection():
            index = self.curselection()[0]
            value = self.get(index)
            self.callback(value)
        self.hide()

    def show(self, x, y):
        self.place(x=x, y=y)
        self.lift()
        self.focus_set()

    def hide(self):
        self.place_forget()

class PyCoderr:
    def __init__(self, root):
        self.root = root
        self.root.title("PyCoderr")
        self.root.geometry("950x650")
        self.filename = None
        self.default_font = ("Consolas", 14)

        # Dark Theme Colors
        self.bg_color = "#1e1e1e"
        self.text_bg = "#252526"
        self.text_fg = "#d4d4d4"
        self.linenumber_bg = "#2d2d2d"
        self.linenumber_fg = "#858585"
        self.btn_bg = "#0e639c"
        self.btn_fg = "#ffffff"
        self.btn_hover_bg = "#1177bb"
        self.status_bg = "#007acc"
        self.status_fg = "#ffffff"

        self.root.configure(bg=self.bg_color)

        # For autocomplete
        self.completions = sorted(set(keyword.kwlist + [
            "print", "len", "range", "int", "str", "float", "list", "dict",
            "set", "tuple", "input", "open", "with", "as", "def", "class",
            "import", "from", "for", "while", "if", "else", "elif", "try",
            "except", "finally", "return", "yield", "lambda", "True", "False",
            "None", "and", "or", "not", "assert", "break", "continue", "global",
            "nonlocal", "pass", "raise", "del", "async", "await"
        ]))

        self.create_widgets()
        self.bind_events()

    def create_widgets(self):
        # Top frame with buttons
        top_frame = tk.Frame(self.root, bg=self.bg_color, pady=5)
        top_frame.pack(side=tk.TOP, fill=tk.X)

        btn_padx = 8
        btn_pady = 5

        self.new_btn = self.make_button(top_frame, "New", self.new_file)
        self.open_btn = self.make_button(top_frame, "Open", self.open_file)
        self.save_btn = self.make_button(top_frame, "Save", self.save_file)
        self.font_btn = self.make_button(top_frame, "Font", self.set_font)
        self.about_btn = self.make_button(top_frame, "About", self.show_about)
        self.run_btn = self.make_button(top_frame, "Run ▶", self.run_code, bg="#28a745")

        self.new_btn.pack(side=tk.LEFT, padx=btn_padx, pady=btn_pady)
        self.open_btn.pack(side=tk.LEFT, padx=btn_padx, pady=btn_pady)
        self.save_btn.pack(side=tk.LEFT, padx=btn_padx, pady=btn_pady)
        self.about_btn.pack(side=tk.RIGHT, padx=btn_padx, pady=btn_pady)
        self.run_btn.pack(side=tk.RIGHT, padx=btn_padx, pady=btn_pady)
        self.font_btn.pack(side=tk.RIGHT, padx=btn_padx, pady=btn_pady)

        # Middle frame with line numbers and text editor
        mid_frame = tk.Frame(self.root, bg=self.bg_color)
        mid_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))

        # Line numbers
        self.linenumbers = tk.Text(mid_frame, width=4, padx=4, takefocus=0, border=0,
                                   background=self.linenumber_bg, fg=self.linenumber_fg, state="disabled", wrap="none",
                                   font=self.default_font)
        self.linenumbers.pack(side=tk.LEFT, fill=tk.Y)

        # Text editor
        self.text = tk.Text(mid_frame, wrap="none", font=self.default_font,
                            bg=self.text_bg, fg=self.text_fg, undo=True, relief=tk.FLAT, insertbackground="white")
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Scrollbars
        yscroll = tk.Scrollbar(mid_frame, command=self.on_vertical_scroll)
        yscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.config(yscrollcommand=yscroll.set)

        xscroll = tk.Scrollbar(self.root, command=self.text.xview, orient="horizontal")
        xscroll.pack(side=tk.BOTTOM, fill=tk.X)
        self.text.config(xscrollcommand=xscroll.set)

        # Status bar
        self.status = tk.Label(self.root, text="Ln 1, Col 1", anchor="w",
                               bg=self.status_bg, fg=self.status_fg, font=("Consolas", 10))
        self.status.pack(side=tk.BOTTOM, fill=tk.X)

        # Syntax tags
        self.text.tag_configure("keyword", foreground="#569CD6")    # blue
        self.text.tag_configure("string", foreground="#D69D85")     # light orange
        self.text.tag_configure("comment", foreground="#6A9955")    # green
        self.text.tag_configure("builtin", foreground="#C586C0")    # purple

        # Autocomplete listbox (hidden initially)
        self.autocomplete = AutoCompleteListbox(self.root, self.insert_completion, height=6, bg=self.text_bg,
                                                fg=self.text_fg, font=self.default_font, highlightthickness=1,
                                                relief=tk.SOLID)
        self.autocomplete.hide()

        self.update_line_numbers()

    def make_button(self, parent, text, command, bg=None):
        b = tk.Button(parent, text=text, command=command,
                      bg=bg if bg else self.btn_bg, fg=self.btn_fg,
                      activebackground=self.btn_hover_bg, activeforeground=self.btn_fg,
                      relief=tk.FLAT, width=8, cursor="hand2", font=("Segoe UI", 10, "bold"))
        # Hover effect
        b.bind("<Enter>", lambda e: b.config(bg=self.btn_hover_bg))
        b.bind("<Leave>", lambda e: b.config(bg=bg if bg else self.btn_bg))
        return b

    def bind_events(self):
        self.text.bind("<KeyRelease>", self.on_key_release)
        self.text.bind("<Return>", self.auto_indent)
        self.text.bind("<Tab>", self.handle_tab)
        self.text.bind("<Button-1>", self.update_cursor_info)
        self.text.bind("<Up>", self.update_cursor_info)
        self.text.bind("<Down>", self.update_cursor_info)
        self.text.bind("<FocusIn>", self.update_cursor_info)
        self.text.bind("<MouseWheel>", self.sync_scroll)  # Windows scroll
        self.text.bind("<Button-4>", self.sync_scroll)    # Linux scroll up
        self.text.bind("<Button-5>", self.sync_scroll)    # Linux scroll down

        # Special key for quote auto-pairing
        self.text.bind("<Key>", self.handle_keypress)

    def on_vertical_scroll(self, *args):
        self.text.yview(*args)
        self.linenumbers.yview(*args)

    def sync_scroll(self, event=None):
        self.linenumbers.yview_moveto(self.text.yview()[0])
        return

    def update_line_numbers(self):
        self.linenumbers.config(state="normal")
        self.linenumbers.delete(1.0, tk.END)

        line_count = int(self.text.index('end-1c').split('.')[0])
        line_numbers_string = "\n".join(str(i) for i in range(1, line_count + 1))
        self.linenumbers.insert(1.0, line_numbers_string)
        self.linenumbers.config(state="disabled")

    def on_key_release(self, event=None):
        self.highlight_syntax()
        self.update_line_numbers()
        self.update_cursor_info()
        #self.handle_autocomplete()

    def update_cursor_info(self, event=None):
        line, col = self.text.index(tk.INSERT).split('.')
        self.status.config(text=f"Ln {line}, Col {int(col)+1}")

    def auto_indent(self, event):
        line = self.text.get("insert linestart", "insert")
        indent = re.match(r'(\s*)', line).group(1)
        self.text.insert("insert", "\n" + indent)
        return "break"

    def handle_tab(self, event):
        self.text.insert(tk.INSERT, " " * 4)
        return "break"

    # Auto insert matching quotes when typing " or '
    def handle_keypress(self, event):
        if event.char in ('"', "'"):
            cursor = self.text.index(tk.INSERT)
            next_char = self.text.get(cursor)
            # If next char is same quote, just move cursor
            if next_char == event.char:
                self.text.mark_set(tk.INSERT, f"{cursor}+1c")
                return "break"
            else:
                # Insert pair quotes and place cursor in middle
                self.text.insert(cursor, event.char * 2)
                self.text.mark_set(tk.INSERT, f"{cursor}+1c")
                return "break"

    def highlight_syntax(self):
        self.text.tag_remove("keyword", "1.0", tk.END)
        self.text.tag_remove("string", "1.0", tk.END)
        self.text.tag_remove("comment", "1.0", tk.END)
        self.text.tag_remove("builtin", "1.0", tk.END)

        code = self.text.get("1.0", tk.END)

        # Comments
        for match in re.finditer(r"#.*", code):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text.tag_add("comment", start, end)

        # Strings (single and double quotes)
        for match in re.finditer(r"(['\"])(?:(?=(\\?))\2.)*?\1", code):
            start = f"1.0+{match.start()}c"
            end = f"1.0+{match.end()}c"
            self.text.tag_add("string", start, end)

        # Keywords
        for kw in keyword.kwlist:
            for match in re.finditer(rf"\b{kw}\b", code):
                start = f"1.0+{match.start()}c"
                end = f"1.0+{match.end()}c"
                self.text.tag_add("keyword", start, end)

        # Builtins
        builtins = ["print", "len", "range", "int", "str", "float", "list", "dict", "set", "tuple", "input"]
        for b in builtins:
            for match in re.finditer(rf"\b{b}\b", code):
                start = f"1.0+{match.start()}c"
                end = f"1.0+{match.end()}c"
                self.text.tag_add("builtin", start, end)

    # ------------- Autocomplete --------------------
    def handle_autocomplete(self):
        cursor_pos = self.text.index(tk.INSERT)
        line_start = self.text.index(f"{cursor_pos} linestart")
        text_to_cursor = self.text.get(line_start, cursor_pos)

        # Only trigger autocomplete on word chars or underscore
        if not text_to_cursor or not re.search(r"[\w_]$", text_to_cursor):
            self.autocomplete.hide()
            return

        # Extract the last word for completion
        match = re.search(r"(\w+)$", text_to_cursor)
        if match:
            prefix = match.group(1)
            suggestions = [w for w in self.completions if w.startswith(prefix)]
            if suggestions:
                bbox = self.text.bbox(cursor_pos)
                if bbox:
                    x, y, width, height = bbox
                    abs_x = self.text.winfo_rootx() + x
                    abs_y = self.text.winfo_rooty() + y + height
                    self.show_autocomplete(suggestions, abs_x, abs_y)
                    self.autocomplete_prefix = prefix
                else:
                    self.autocomplete.hide()
            else:
                self.autocomplete.hide()
        else:
            self.autocomplete.hide()

    def show_autocomplete(self, suggestions, x, y):
        self.autocomplete.delete(0, tk.END)
        for word in suggestions:
            self.autocomplete.insert(tk.END, word)
        self.autocomplete.show(x - self.root.winfo_rootx(), y - self.root.winfo_rooty())

    def insert_completion(self, word):
        cursor_pos = self.text.index(tk.INSERT)
        line_start = self.text.index(f"{cursor_pos} linestart")
        text_to_cursor = self.text.get(line_start, cursor_pos)

        # Remove the current prefix
        new_text = text_to_cursor[:-len(self.autocomplete_prefix)] + word
        self.text.delete(line_start, cursor_pos)
        self.text.insert(line_start, new_text)
        self.autocomplete.hide()

    # ------------------------------
    # File Handling
    # ------------------------------
    def new_file(self):
        self.filename = None
        self.text.delete(1.0, tk.END)

    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("Python Files", "*.py")])
        if path:
            self.filename = path
            with open(path, "r", encoding="utf-8") as file:
                self.text.delete(1.0, tk.END)
                self.text.insert(tk.END, file.read())
            self.highlight_syntax()
            self.update_line_numbers()

    def save_file(self):
        if not self.filename:
            self.save_as()
        else:
            with open(self.filename, "w", encoding="utf-8") as file:
                file.write(self.text.get(1.0, tk.END))

    def save_as(self):
        path = filedialog.asksaveasfilename(defaultextension=".py", filetypes=[("Python Files", "*.py")])
        if path:
            self.filename = path
            self.save_file()

    # ------------------------------
    # Font Settings
    # ------------------------------
    def set_font(self):
        font_win = tk.Toplevel(self.root)
        font_win.title("Set Font")
        font_win.geometry("300x120")
        font_win.configure(bg=self.bg_color)

        tk.Label(font_win, text="Font Family:", bg=self.bg_color, fg=self.text_fg).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        font_family = tk.Entry(font_win)
        font_family.insert(0, self.default_font[0])
        font_family.grid(row=0, column=1, padx=10, pady=10)

        tk.Label(font_win, text="Font Size:", bg=self.bg_color, fg=self.text_fg).grid(row=1, column=0, padx=10, pady=10, sticky="w")
        font_size = tk.Entry(font_win)
        font_size.insert(0, self.default_font[1])
        font_size.grid(row=1, column=1, padx=10, pady=10)

        def apply_font():
            try:
                family = font_family.get()
                size = int(font_size.get())
                self.default_font = (family, size)
                self.text.config(font=self.default_font)
                self.linenumbers.config(font=self.default_font)
                self.autocomplete.config(font=self.default_font)
                font_win.destroy()
            except:
                messagebox.showerror("Error", "Invalid font size")

        tk.Button(font_win, text="Apply", bg=self.btn_bg, fg=self.btn_fg, command=apply_font).grid(row=2, column=0, columnspan=2, pady=10)

    # ------------------------------
    # Run Code in System Terminal
    # ------------------------------
    def run_code(self):
        if not self.filename:
            self.filename = "temp_code.py"
            with open(self.filename, "w", encoding="utf-8") as file:
                file.write(self.text.get(1.0, tk.END))
        else:
            self.save_file()

        if os.name == "nt":  # Windows
            subprocess.Popen(f'start cmd /K python "{self.filename}"', shell=True)
        else:  # macOS / Linux
            subprocess.Popen(f'gnome-terminal -- bash -c "python3 \\"{self.filename}\\"; exec bash"', shell=True)

    # ------------------------------
    # About Popup - Improved
    # ------------------------------
    def show_about(self):
        about_win = tk.Toplevel(self.root)
        about_win.title("About PyCoderr")
        about_win.geometry("400x350")
        about_win.configure(bg=self.bg_color)
        about_win.resizable(False, False)
        about_win.grab_set()  # Make modal

        # Frame for border and padding
        frame = tk.Frame(about_win, bg="#333333", padx=15, pady=15)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        title = tk.Label(frame, text="PyCoderr", font=("Segoe UI", 20, "bold"), bg="#333333", fg="#00c8ff")
        title.pack(pady=(0, 10))

        subtitle = tk.Label(frame, text="Simple Python Editor by Mevinu Abeysinghe", font=("Segoe UI", 11, "italic"),
                            bg="#333333", fg="#bbbbbb")
        subtitle.pack(pady=(0, 15))

        text = (
            "Features:\n"
            "• Syntax highlighting\n"
            "• Auto-indent & Tab support\n"
            "• Font customization\n"
            "• Run code in system terminal\n\n"
            "Designed to be simple, lightweight, and user-friendly."
        )
        label = tk.Label(frame, text=text, bg="#333333", fg=self.text_fg,
                         font=("Segoe UI", 11), justify=tk.LEFT)
        label.pack()

        ok_btn = tk.Button(frame, text="Close", width=10, bg=self.btn_bg, fg=self.btn_fg,
                           command=about_win.destroy, relief=tk.FLAT)
        ok_btn.pack(pady=15)

if __name__ == "__main__":
    root = tk.Tk()
    app = PyCoderr(root)
    root.mainloop()
