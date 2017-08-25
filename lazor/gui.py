import os
import tkinter as tk
from collections import OrderedDict
from functools import partial
from tkinter import ttk, filedialog, messagebox

import ezdxf

from lazor.actions import autofix, explode, add_tabs, combine_layers, \
    rename_layer, delete_layers, optimise
from lazor.analysis import ideal_laser_distance
from lazor.datastructures import Vec2
from lazor.dxf import unpack, draw
from lazor.exceptions import AbortAction


class Application(ttk.Frame):
    def __init__(self, master=False):
        super().__init__(master, padding="10 10 10 10")
        self.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self.filename = tk.StringVar()
        self.statusbar = tk.StringVar()
        self.layers = OrderedDict()

        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)
        self.rowconfigure(3, weight=0)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)

        ttk.Button(self, text="Open File", command=self.open_file).grid(column=0, row=0)

        ttk.Label(self, textvariable=self.filename, relief="sunken", padding="5 5 5 5").grid(column=1, columnspan=2, row=0, sticky=tk.W+tk.E+tk.N+tk.S)
        ttk.Label(self, textvariable=self.statusbar, relief="sunken", padding="5 5 5 5").grid(column=0, columnspan=3, row=3, sticky=tk.W+tk.E+tk.N+tk.S)

        self.canvas = tk.Canvas(self, relief="sunken", bg="white")
        self.canvas.grid(column=0, columnspan=2, row=1, rowspan=2, sticky=tk.W+tk.E+tk.N+tk.S)
        self.canvas.bind("<Configure>", self.redraw_on_event)

        self.layer_box = tk.Listbox(self, selectmode=tk.EXTENDED)
        self.layer_box.grid(column=2, row=1, sticky=tk.W+tk.E+tk.N+tk.S)
        self.layer_box.bind("<<ListboxSelect>>", self.select_layer)

        self.button_frame = ttk.Frame(self)
        self.button_frame.grid(row=2, column=2)

        for name, callback in [
            ("Autofix", autofix),
            ("Optimise", optimise),
            ("Add Tabs", add_tabs),
            ("Explode", explode),
            ("Combine", combine_layers),
            ("Rename", rename_layer),
            ("Delete", delete_layers),
        ]:
            self.add_button(name, callback)

        ttk.Button(self.button_frame, text="Save As", command=self.save_file).pack(anchor=tk.N)
        self.update_statusbar("Welcome to LAZOR")

    def update_statusbar(self, msg):
        self.statusbar.set(msg)
        self.master.update()

    def add_button(self, name, callback):
        ttk.Button(self.button_frame, text=name, command=partial(self.action, callback)).pack(anchor=tk.N)

    def open_file(self):
        filename = filedialog.askopenfilename(filetypes=[("dxf files", ".dxf"), ("All files", ".*")])

        if not filename:
            self.update_statusbar("Cancelled file open")
            return

        self.filename.set(filename)
        self.update_statusbar("Loading {}".format(filename))

        drawing = ezdxf.readfile(filename)
        self.layers = OrderedDict()
        self.layers.update(unpack(drawing.modelspace()))

        self.update_layerbox()
        self.update_canvas()
        self.update_statusbar("Loaded {}".format(filename))

    def save_file(self):
        if not self.layers:
            messagebox.showerror("Cannot Save", "You cannot save an empty file")
            raise AbortAction()

        if not self.filename:
            messagebox.showerror("Cannot Save", "You cannot save an empty file")
            raise AbortAction()

        initialdir, initialfile = os.path.split(self.filename.get())
        filename = filedialog.asksaveasfilename(filetypes=[("dxf files", ".dxf")], initialfile=initialfile, initialdir=initialdir, defaultextension="dxf")

        if not filename:
            self.update_statusbar("Cancelled file save")
            raise AbortAction()

        dxf = draw(**self.layers)
        dxf.saveas(filename)

        self.update_canvas()
        self.update_statusbar("Saved file as {}".format(filename))

    def update_layerbox(self):
        self.layer_box.delete(0, tk.END)

        for layer in self.layers:
            self.layer_box.insert(tk.END, layer)

    def redraw_on_event(self, event):
        self.update_canvas()

    def select_layer(self, event):
        layers = [self.layer_box.get(i) for i in self.layer_box.curselection()]
        if len(layers) == 1:
            layer = layers[0]
            self.update_statusbar(
                "Layer '{}' contains {} lines, travelling {}mm".format(
                    layer,
                    len(self.layers[layer]),
                    round(ideal_laser_distance(self.layers[layer]), 1)
                )
            )
        elif len(layers) > 1:
            self.update_statusbar(
                "Selected layers contain {} lines, travelling a total of {}mm".format(
                    sum([len(self.layers[layer]) for layer in layers]),
                    round(sum(ideal_laser_distance(self.layers[layer]) for layer in layers), 1)
                )
            )

        self.update_canvas()

    def update_canvas(self):
        self.canvas.delete(tk.ALL)
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        canvas_midpoint = Vec2(canvas_width / 2, canvas_height / 2)

        if not self.layers:
            self.canvas.create_text(
                *canvas_midpoint,
                text="NO FILE LOADED",
                fill="red"
            )
            return

        dxf_minpoint = Vec2(float('inf'), float('inf'))
        dxf_maxpoint = Vec2(float('-inf'), float('-inf'))

        for layer in self.layers.values():
            for start, end in layer:
                dxf_minpoint = Vec2(min(start.x, end.x, dxf_minpoint.x), min(start.y, end.y, dxf_minpoint.y))
                dxf_maxpoint = Vec2(max(start.x, end.x, dxf_maxpoint.x), max(start.y, end.y, dxf_maxpoint.y))

        dxf_midpoint = dxf_minpoint.midpoint(dxf_maxpoint)

        drawing_width, drawing_height = dxf_maxpoint - dxf_minpoint
        ratio = min((canvas_width*.9)/drawing_width, (canvas_height*.9)/drawing_height)

        selected_layers = [self.layer_box.get(i) for i in self.layer_box.curselection()]

        selected_colours = ("red", "green")

        for layer_name, layer in self.layers.items():
            for n, (start, end) in enumerate(layer):
                start = (start - dxf_midpoint) * ratio + canvas_midpoint
                end = (end - dxf_midpoint) * ratio + canvas_midpoint

                colour = selected_colours[n % len(selected_colours)] if layer_name in selected_layers else "black"

                self.canvas.create_line(start.x, start.y * -1 + canvas_height, end.x, end.y * -1 + canvas_height, fill=colour)

    def action(self, act):
        layers = self.layers
        selections = [self.layer_box.get(i) for i in self.layer_box.curselection()]

        try:
            self.layers = act(layers, selections, self.update_statusbar)
        except AbortAction:
            pass

        self.update_layerbox()
        self.update_canvas()


def main():
    root = tk.Tk()
    root.title("LAZOR")

    tk.Grid.rowconfigure(root, 0, weight=1)
    tk.Grid.columnconfigure(root, 0, weight=1)

    app = Application(master=root)
    app.mainloop()
