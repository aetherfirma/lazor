import os
import tkinter as tk
from collections import OrderedDict
from functools import partial
from tkinter import ttk, filedialog, messagebox, Button

import ezdxf
import math

from colour import Color

from lazor.actions import autofix, explode, add_tabs, combine_layers, \
    rename_layer, delete_layers, optimise, laser_estimation, \
    laser_engraving_estimation, change_colour
from lazor.analysis import ideal_laser_distance
from lazor.datastructures import Vec2
from lazor.dxf import unpack, draw
from lazor.exceptions import AbortAction

BG_COLOUR = "#808080"
COLOURS_FOR_4GROUND = [
    (1, "Cut"),
    (30, "Cut (2nd pass)"),
    (5, "Line"),
    (6, "Etch"),
    (17, "Score"),
    (7, "Sprue")
]


class Application(ttk.Frame):
    def __init__(self, master=False):
        super().__init__(master, padding="10 10 10 10")
        self.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self.filename = tk.StringVar()
        self.statusbar = tk.StringVar()
        self.layers = OrderedDict()
        self.colours = OrderedDict()

        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)
        self.rowconfigure(3, weight=0)
        self.rowconfigure(4, weight=0)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)

        self.use_4ground_colours = False

        ttk.Button(self, text="Open File", command=self.open_file).grid(column=0, row=0)

        ttk.Label(self, textvariable=self.filename, relief="sunken", padding="5 5 5 5").grid(column=1, columnspan=2, row=0, sticky=tk.W+tk.E+tk.N+tk.S)
        ttk.Label(self, textvariable=self.statusbar, relief="sunken", padding="5 5 5 5").grid(column=0, columnspan=3, row=4, sticky=tk.W+tk.E+tk.N+tk.S)

        self.canvas = tk.Canvas(self, relief="sunken", bg="white")
        self.canvas.grid(column=0, columnspan=2, row=1, rowspan=2, sticky=tk.W+tk.E+tk.N+tk.S)
        self.canvas.bind("<Configure>", self.redraw_on_event)

        self.layer_box = tk.Listbox(self, selectmode=tk.EXTENDED, bg=BG_COLOUR)
        self.layer_box.grid(column=2, row=1, sticky=tk.W+tk.E+tk.N+tk.S)
        self.layer_box.bind("<<ListboxSelect>>", self.select_layer)

        self.button_frame = ttk.Frame(self)
        self.button_frame.grid(row=2, column=2)

        self.colour_frame = ttk.Frame(self)
        self.colour_frame.grid(row=3, column=0, columnspan=3)

        for name, callback in [
            ("Autofix", autofix),
            ("Optimise", optimise),
            ("Estimate", laser_estimation),
            ("Estimate Engraving", laser_engraving_estimation),
            ("Add Tabs", add_tabs),
            ("Explode", explode),
            ("Combine", combine_layers),
            ("Rename", rename_layer),
            ("Delete", delete_layers),
        ]:
            self.add_button(name, callback)

        self.set_colour_buttons()

        ttk.Button(self.button_frame, text="Toggle Colour Mode", command=self.toggle_colour_mode).pack(anchor=tk.N)
        ttk.Button(self.button_frame, text="Save As", command=self.save_file).pack(anchor=tk.N)
        self.update_statusbar("Welcome to LAZOR")

    def toggle_colour_mode(self):
        self.use_4ground_colours = not self.use_4ground_colours
        self.set_colour_buttons()

    def set_colour_buttons(self):
        self.colour_frame.destroy()
        self.colour_frame = ttk.Frame(self)
        self.colour_frame.grid(row=3, column=0, columnspan=3)

        colours = self.layer_colours()

        if self.use_4ground_colours:
            for n, text in COLOURS_FOR_4GROUND:
                colour = colours[n]
                print(colour.get_luminance())
                fg = "black" if colour.get_luminance() >= 0.5 else "white"
                btn = Button(self.colour_frame, text=text, command=self.change_colour(n), bg=colour, fg=fg)
                btn.pack(anchor=tk.E, side=tk.LEFT)
        else:
            for n, colour in enumerate(colours[:20]):
                print(colour.get_luminance())
                fg = "black" if colour.get_luminance() >= 0.5 else "white"
                btn = Button(self.colour_frame, text=n, command=self.change_colour(n), bg=colour, fg=fg)
                btn.pack(anchor=tk.E, side=tk.LEFT)

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
        layers, self.colours = unpack(drawing)
        self.layers.update(layers)

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

        dxf = draw(self.layers, self.colours)
        dxf.saveas(filename)

        self.update_canvas()
        self.update_statusbar("Saved file as {}".format(filename))

    def update_layerbox(self):
        self.layer_box.delete(0, tk.END)

        layer_colours = self.layer_colours()

        for n, layer in enumerate(self.layers):
            self.layer_box.insert(tk.END, layer)
            colour = layer_colours[self.colours[layer]]
            self.layer_box.itemconfigure(n, fg=colour, selectbackground=colour, selectforeground=BG_COLOUR)

        # for (n, _), colour in zip(enumerate(self.layers), layer_colours):
        #     self.layer_box.itemconfigure(n, fg=colour, selectbackground=colour, selectforeground=BG_COLOUR)

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

    def layer_colours(self):
        return [
            Color(rgb=(0 / 255, 0 / 255, 0 / 255)),
            Color(rgb=(255 / 255, 0 / 255, 0 / 255)),
            Color(rgb=(255 / 255, 255 / 255, 0 / 255)),
            Color(rgb=(0 / 255, 255 / 255, 0 / 255)),
            Color(rgb=(0 / 255, 255 / 255, 255 / 255)),
            Color(rgb=(0 / 255, 0 / 255, 255 / 255)),
            Color(rgb=(255 / 255, 0 / 255, 255 / 255)),
            Color(rgb=(255 / 255, 255 / 255, 255 / 255)),
            Color(rgb=(65 / 255, 65 / 255, 65 / 255)),
            Color(rgb=(128 / 255, 128 / 255, 128 / 255)),
            Color(rgb=(255 / 255, 0 / 255, 0 / 255)),
            Color(rgb=(255 / 255, 170 / 255, 170 / 255)),
            Color(rgb=(189 / 255, 0 / 255, 0 / 255)),
            Color(rgb=(189 / 255, 126 / 255, 126 / 255)),
            Color(rgb=(129 / 255, 0 / 255, 0 / 255)),
            Color(rgb=(129 / 255, 86 / 255, 86 / 255)),
            Color(rgb=(104 / 255, 0 / 255, 0 / 255)),
            Color(rgb=(104 / 255, 69 / 255, 69 / 255)),
            Color(rgb=(79 / 255, 0 / 255, 0 / 255)),
            Color(rgb=(79 / 255, 53 / 255, 53 / 255)),
            Color(rgb=(255 / 255, 63 / 255, 0 / 255)),
            Color(rgb=(255 / 255, 191 / 255, 170 / 255)),
            Color(rgb=(189 / 255, 46 / 255, 0 / 255)),
            Color(rgb=(189 / 255, 141 / 255, 126 / 255)),
            Color(rgb=(129 / 255, 31 / 255, 0 / 255)),
            Color(rgb=(129 / 255, 96 / 255, 86 / 255)),
            Color(rgb=(104 / 255, 25 / 255, 0 / 255)),
            Color(rgb=(104 / 255, 78 / 255, 69 / 255)),
            Color(rgb=(79 / 255, 19 / 255, 0 / 255)),
            Color(rgb=(79 / 255, 59 / 255, 53 / 255)),
            Color(rgb=(255 / 255, 127 / 255, 0 / 255)),
            Color(rgb=(255 / 255, 212 / 255, 170 / 255)),
            Color(rgb=(189 / 255, 94 / 255, 0 / 255)),
            Color(rgb=(189 / 255, 157 / 255, 126 / 255)),
            Color(rgb=(129 / 255, 64 / 255, 0 / 255)),
            Color(rgb=(129 / 255, 107 / 255, 86 / 255)),
            Color(rgb=(104 / 255, 52 / 255, 0 / 255)),
            Color(rgb=(104 / 255, 86 / 255, 69 / 255)),
            Color(rgb=(79 / 255, 39 / 255, 0 / 255)),
            Color(rgb=(79 / 255, 66 / 255, 53 / 255)),
            Color(rgb=(255 / 255, 191 / 255, 0 / 255)),
            Color(rgb=(255 / 255, 234 / 255, 170 / 255)),
            Color(rgb=(189 / 255, 141 / 255, 0 / 255)),
            Color(rgb=(189 / 255, 173 / 255, 126 / 255)),
            Color(rgb=(129 / 255, 96 / 255, 0 / 255)),
            Color(rgb=(129 / 255, 118 / 255, 86 / 255)),
            Color(rgb=(104 / 255, 78 / 255, 0 / 255)),
            Color(rgb=(104 / 255, 95 / 255, 69 / 255)),
            Color(rgb=(79 / 255, 59 / 255, 0 / 255)),
            Color(rgb=(79 / 255, 73 / 255, 53 / 255)),
            Color(rgb=(255 / 255, 255 / 255, 0 / 255)),
            Color(rgb=(255 / 255, 255 / 255, 170 / 255)),
            Color(rgb=(189 / 255, 189 / 255, 0 / 255)),
            Color(rgb=(189 / 255, 189 / 255, 126 / 255)),
            Color(rgb=(129 / 255, 129 / 255, 0 / 255)),
            Color(rgb=(129 / 255, 129 / 255, 86 / 255)),
            Color(rgb=(104 / 255, 104 / 255, 0 / 255)),
            Color(rgb=(104 / 255, 104 / 255, 69 / 255)),
            Color(rgb=(79 / 255, 79 / 255, 0 / 255)),
            Color(rgb=(79 / 255, 79 / 255, 53 / 255)),
            Color(rgb=(191 / 255, 255 / 255, 0 / 255)),
            Color(rgb=(234 / 255, 255 / 255, 170 / 255)),
            Color(rgb=(141 / 255, 189 / 255, 0 / 255)),
            Color(rgb=(173 / 255, 189 / 255, 126 / 255)),
            Color(rgb=(96 / 255, 129 / 255, 0 / 255)),
            Color(rgb=(118 / 255, 129 / 255, 86 / 255)),
            Color(rgb=(78 / 255, 104 / 255, 0 / 255)),
            Color(rgb=(95 / 255, 104 / 255, 69 / 255)),
            Color(rgb=(59 / 255, 79 / 255, 0 / 255)),
            Color(rgb=(73 / 255, 79 / 255, 53 / 255)),
            Color(rgb=(127 / 255, 255 / 255, 0 / 255)),
            Color(rgb=(212 / 255, 255 / 255, 170 / 255)),
            Color(rgb=(94 / 255, 189 / 255, 0 / 255)),
            Color(rgb=(157 / 255, 189 / 255, 126 / 255)),
            Color(rgb=(64 / 255, 129 / 255, 0 / 255)),
            Color(rgb=(107 / 255, 129 / 255, 86 / 255)),
            Color(rgb=(52 / 255, 104 / 255, 0 / 255)),
            Color(rgb=(86 / 255, 104 / 255, 69 / 255)),
            Color(rgb=(39 / 255, 79 / 255, 0 / 255)),
            Color(rgb=(66 / 255, 79 / 255, 53 / 255)),
            Color(rgb=(63 / 255, 255 / 255, 0 / 255)),
            Color(rgb=(191 / 255, 255 / 255, 170 / 255)),
            Color(rgb=(46 / 255, 189 / 255, 0 / 255)),
            Color(rgb=(141 / 255, 189 / 255, 126 / 255)),
            Color(rgb=(31 / 255, 129 / 255, 0 / 255)),
            Color(rgb=(96 / 255, 129 / 255, 86 / 255)),
            Color(rgb=(25 / 255, 104 / 255, 0 / 255)),
            Color(rgb=(78 / 255, 104 / 255, 69 / 255)),
            Color(rgb=(19 / 255, 79 / 255, 0 / 255)),
            Color(rgb=(59 / 255, 79 / 255, 53 / 255)),
            Color(rgb=(0 / 255, 255 / 255, 0 / 255)),
            Color(rgb=(170 / 255, 255 / 255, 170 / 255)),
            Color(rgb=(0 / 255, 189 / 255, 0 / 255)),
            Color(rgb=(126 / 255, 189 / 255, 126 / 255)),
            Color(rgb=(0 / 255, 129 / 255, 0 / 255)),
            Color(rgb=(86 / 255, 129 / 255, 86 / 255)),
            Color(rgb=(0 / 255, 104 / 255, 0 / 255)),
            Color(rgb=(69 / 255, 104 / 255, 69 / 255)),
            Color(rgb=(0 / 255, 79 / 255, 0 / 255)),
            Color(rgb=(53 / 255, 79 / 255, 53 / 255)),
            Color(rgb=(0 / 255, 255 / 255, 63 / 255)),
            Color(rgb=(170 / 255, 255 / 255, 191 / 255)),
            Color(rgb=(0 / 255, 189 / 255, 46 / 255)),
            Color(rgb=(126 / 255, 189 / 255, 141 / 255)),
            Color(rgb=(0 / 255, 129 / 255, 31 / 255)),
            Color(rgb=(86 / 255, 129 / 255, 96 / 255)),
            Color(rgb=(0 / 255, 104 / 255, 25 / 255)),
            Color(rgb=(69 / 255, 104 / 255, 78 / 255)),
            Color(rgb=(0 / 255, 79 / 255, 19 / 255)),
            Color(rgb=(53 / 255, 79 / 255, 59 / 255)),
            Color(rgb=(0 / 255, 255 / 255, 127 / 255)),
            Color(rgb=(170 / 255, 255 / 255, 212 / 255)),
            Color(rgb=(0 / 255, 189 / 255, 94 / 255)),
            Color(rgb=(126 / 255, 189 / 255, 157 / 255)),
            Color(rgb=(0 / 255, 129 / 255, 64 / 255)),
            Color(rgb=(86 / 255, 129 / 255, 107 / 255)),
            Color(rgb=(0 / 255, 104 / 255, 52 / 255)),
            Color(rgb=(69 / 255, 104 / 255, 86 / 255)),
            Color(rgb=(0 / 255, 79 / 255, 39 / 255)),
            Color(rgb=(53 / 255, 79 / 255, 66 / 255)),
            Color(rgb=(0 / 255, 255 / 255, 191 / 255)),
            Color(rgb=(170 / 255, 255 / 255, 234 / 255)),
            Color(rgb=(0 / 255, 189 / 255, 141 / 255)),
            Color(rgb=(126 / 255, 189 / 255, 173 / 255)),
            Color(rgb=(0 / 255, 129 / 255, 96 / 255)),
            Color(rgb=(86 / 255, 129 / 255, 118 / 255)),
            Color(rgb=(0 / 255, 104 / 255, 78 / 255)),
            Color(rgb=(69 / 255, 104 / 255, 95 / 255)),
            Color(rgb=(0 / 255, 79 / 255, 59 / 255)),
            Color(rgb=(53 / 255, 79 / 255, 73 / 255)),
            Color(rgb=(0 / 255, 255 / 255, 255 / 255)),
            Color(rgb=(170 / 255, 255 / 255, 255 / 255)),
            Color(rgb=(0 / 255, 189 / 255, 189 / 255)),
            Color(rgb=(126 / 255, 189 / 255, 189 / 255)),
            Color(rgb=(0 / 255, 129 / 255, 129 / 255)),
            Color(rgb=(86 / 255, 129 / 255, 129 / 255)),
            Color(rgb=(0 / 255, 104 / 255, 104 / 255)),
            Color(rgb=(69 / 255, 104 / 255, 104 / 255)),
            Color(rgb=(0 / 255, 79 / 255, 79 / 255)),
            Color(rgb=(53 / 255, 79 / 255, 79 / 255)),
            Color(rgb=(0 / 255, 191 / 255, 255 / 255)),
            Color(rgb=(170 / 255, 234 / 255, 255 / 255)),
            Color(rgb=(0 / 255, 141 / 255, 189 / 255)),
            Color(rgb=(126 / 255, 173 / 255, 189 / 255)),
            Color(rgb=(0 / 255, 96 / 255, 129 / 255)),
            Color(rgb=(86 / 255, 118 / 255, 129 / 255)),
            Color(rgb=(0 / 255, 78 / 255, 104 / 255)),
            Color(rgb=(69 / 255, 95 / 255, 104 / 255)),
            Color(rgb=(0 / 255, 59 / 255, 79 / 255)),
            Color(rgb=(53 / 255, 73 / 255, 79 / 255)),
            Color(rgb=(0 / 255, 127 / 255, 255 / 255)),
            Color(rgb=(170 / 255, 212 / 255, 255 / 255)),
            Color(rgb=(0 / 255, 94 / 255, 189 / 255)),
            Color(rgb=(126 / 255, 157 / 255, 189 / 255)),
            Color(rgb=(0 / 255, 64 / 255, 129 / 255)),
            Color(rgb=(86 / 255, 107 / 255, 129 / 255)),
            Color(rgb=(0 / 255, 52 / 255, 104 / 255)),
            Color(rgb=(69 / 255, 86 / 255, 104 / 255)),
            Color(rgb=(0 / 255, 39 / 255, 79 / 255)),
            Color(rgb=(53 / 255, 66 / 255, 79 / 255)),
            Color(rgb=(0 / 255, 63 / 255, 255 / 255)),
            Color(rgb=(170 / 255, 191 / 255, 255 / 255)),
            Color(rgb=(0 / 255, 46 / 255, 189 / 255)),
            Color(rgb=(126 / 255, 141 / 255, 189 / 255)),
            Color(rgb=(0 / 255, 31 / 255, 129 / 255)),
            Color(rgb=(86 / 255, 96 / 255, 129 / 255)),
            Color(rgb=(0 / 255, 25 / 255, 104 / 255)),
            Color(rgb=(69 / 255, 78 / 255, 104 / 255)),
            Color(rgb=(0 / 255, 19 / 255, 79 / 255)),
            Color(rgb=(53 / 255, 59 / 255, 79 / 255)),
            Color(rgb=(0 / 255, 0 / 255, 255 / 255)),
            Color(rgb=(170 / 255, 170 / 255, 255 / 255)),
            Color(rgb=(0 / 255, 0 / 255, 189 / 255)),
            Color(rgb=(126 / 255, 126 / 255, 189 / 255)),
            Color(rgb=(0 / 255, 0 / 255, 129 / 255)),
            Color(rgb=(86 / 255, 86 / 255, 129 / 255)),
            Color(rgb=(0 / 255, 0 / 255, 104 / 255)),
            Color(rgb=(69 / 255, 69 / 255, 104 / 255)),
            Color(rgb=(0 / 255, 0 / 255, 79 / 255)),
            Color(rgb=(53 / 255, 53 / 255, 79 / 255)),
            Color(rgb=(63 / 255, 0 / 255, 255 / 255)),
            Color(rgb=(191 / 255, 170 / 255, 255 / 255)),
            Color(rgb=(46 / 255, 0 / 255, 189 / 255)),
            Color(rgb=(141 / 255, 126 / 255, 189 / 255)),
            Color(rgb=(31 / 255, 0 / 255, 129 / 255)),
            Color(rgb=(96 / 255, 86 / 255, 129 / 255)),
            Color(rgb=(25 / 255, 0 / 255, 104 / 255)),
            Color(rgb=(78 / 255, 69 / 255, 104 / 255)),
            Color(rgb=(19 / 255, 0 / 255, 79 / 255)),
            Color(rgb=(59 / 255, 53 / 255, 79 / 255)),
            Color(rgb=(127 / 255, 0 / 255, 255 / 255)),
            Color(rgb=(212 / 255, 170 / 255, 255 / 255)),
            Color(rgb=(94 / 255, 0 / 255, 189 / 255)),
            Color(rgb=(157 / 255, 126 / 255, 189 / 255)),
            Color(rgb=(64 / 255, 0 / 255, 129 / 255)),
            Color(rgb=(107 / 255, 86 / 255, 129 / 255)),
            Color(rgb=(52 / 255, 0 / 255, 104 / 255)),
            Color(rgb=(86 / 255, 69 / 255, 104 / 255)),
            Color(rgb=(39 / 255, 0 / 255, 79 / 255)),
            Color(rgb=(66 / 255, 53 / 255, 79 / 255)),
            Color(rgb=(191 / 255, 0 / 255, 255 / 255)),
            Color(rgb=(234 / 255, 170 / 255, 255 / 255)),
            Color(rgb=(141 / 255, 0 / 255, 189 / 255)),
            Color(rgb=(173 / 255, 126 / 255, 189 / 255)),
            Color(rgb=(96 / 255, 0 / 255, 129 / 255)),
            Color(rgb=(118 / 255, 86 / 255, 129 / 255)),
            Color(rgb=(78 / 255, 0 / 255, 104 / 255)),
            Color(rgb=(95 / 255, 69 / 255, 104 / 255)),
            Color(rgb=(59 / 255, 0 / 255, 79 / 255)),
            Color(rgb=(73 / 255, 53 / 255, 79 / 255)),
            Color(rgb=(255 / 255, 0 / 255, 255 / 255)),
            Color(rgb=(255 / 255, 170 / 255, 255 / 255)),
            Color(rgb=(189 / 255, 0 / 255, 189 / 255)),
            Color(rgb=(189 / 255, 126 / 255, 189 / 255)),
            Color(rgb=(129 / 255, 0 / 255, 129 / 255)),
            Color(rgb=(129 / 255, 86 / 255, 129 / 255)),
            Color(rgb=(104 / 255, 0 / 255, 104 / 255)),
            Color(rgb=(104 / 255, 69 / 255, 104 / 255)),
            Color(rgb=(79 / 255, 0 / 255, 79 / 255)),
            Color(rgb=(79 / 255, 53 / 255, 79 / 255)),
            Color(rgb=(255 / 255, 0 / 255, 191 / 255)),
            Color(rgb=(255 / 255, 170 / 255, 234 / 255)),
            Color(rgb=(189 / 255, 0 / 255, 141 / 255)),
            Color(rgb=(189 / 255, 126 / 255, 173 / 255)),
            Color(rgb=(129 / 255, 0 / 255, 96 / 255)),
            Color(rgb=(129 / 255, 86 / 255, 118 / 255)),
            Color(rgb=(104 / 255, 0 / 255, 78 / 255)),
            Color(rgb=(104 / 255, 69 / 255, 95 / 255)),
            Color(rgb=(79 / 255, 0 / 255, 59 / 255)),
            Color(rgb=(79 / 255, 53 / 255, 73 / 255)),
            Color(rgb=(255 / 255, 0 / 255, 127 / 255)),
            Color(rgb=(255 / 255, 170 / 255, 212 / 255)),
            Color(rgb=(189 / 255, 0 / 255, 94 / 255)),
            Color(rgb=(189 / 255, 126 / 255, 157 / 255)),
            Color(rgb=(129 / 255, 0 / 255, 64 / 255)),
            Color(rgb=(129 / 255, 86 / 255, 107 / 255)),
            Color(rgb=(104 / 255, 0 / 255, 52 / 255)),
            Color(rgb=(104 / 255, 69 / 255, 86 / 255)),
            Color(rgb=(79 / 255, 0 / 255, 39 / 255)),
            Color(rgb=(79 / 255, 53 / 255, 66 / 255)),
            Color(rgb=(255 / 255, 0 / 255, 63 / 255)),
            Color(rgb=(255 / 255, 170 / 255, 191 / 255)),
            Color(rgb=(189 / 255, 0 / 255, 46 / 255)),
            Color(rgb=(189 / 255, 126 / 255, 141 / 255)),
            Color(rgb=(129 / 255, 0 / 255, 31 / 255)),
            Color(rgb=(129 / 255, 86 / 255, 96 / 255)),
            Color(rgb=(104 / 255, 0 / 255, 25 / 255)),
            Color(rgb=(104 / 255, 69 / 255, 78 / 255)),
            Color(rgb=(79 / 255, 0 / 255, 19 / 255)),
            Color(rgb=(79 / 255, 53 / 255, 59 / 255)),
            Color(rgb=(51 / 255, 51 / 255, 51 / 255)),
            Color(rgb=(80 / 255, 80 / 255, 80 / 255)),
            Color(rgb=(105 / 255, 105 / 255, 105 / 255)),
            Color(rgb=(130 / 255, 130 / 255, 130 / 255)),
            Color(rgb=(190 / 255, 190 / 255, 190 / 255)),
            Color(rgb=(255 / 255, 255 / 255, 255 / 255)),
        ]
        return [Color(hsl=(255/len(self.layers)*n, 1, 0.75)).get_hex_l() for n, _ in enumerate(self.layers)]

    def update_canvas(self):
        self.canvas.delete(tk.ALL)
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        self.canvas.midpoint = Vec2(canvas_width / 2, canvas_height / 2)

        self.canvas.create_rectangle(0, 0, canvas_width, canvas_height, outline=None, fill=BG_COLOUR)

        if not self.layers:
            self.canvas.create_text(
                *self.canvas.midpoint,
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

        self.canvas.dxf_midpoint = dxf_minpoint.midpoint(dxf_maxpoint)

        drawing_width, drawing_height = dxf_maxpoint - dxf_minpoint
        self.canvas.drawing_ratio = min((canvas_width*.9)/drawing_width, (canvas_height*.9)/drawing_height)

        for n in range(1, int(math.ceil(canvas_width / (self.canvas.drawing_ratio * 10)))):
            self.canvas.create_line(n * self.canvas.drawing_ratio * 10, 0, n * self.canvas.drawing_ratio * 10, canvas_height, fill="#444444", dash=(2, 2))

        for n in range(1, int(math.ceil(canvas_height / (self.canvas.drawing_ratio * 10)))):
            self.canvas.create_line(0, n * self.canvas.drawing_ratio * 10, canvas_width, n * self.canvas.drawing_ratio * 10, fill="#444444", dash=(2, 2))

        selected_layers = [self.layer_box.get(i) for i in self.layer_box.curselection()]

        layer_colours = self.layer_colours()

        for layer_name, layer in self.layers.items():
            for n, (start, end) in enumerate(layer):
                start = (start - self.canvas.dxf_midpoint) * self.canvas.drawing_ratio + self.canvas.midpoint
                end = (end - self.canvas.dxf_midpoint) * self.canvas.drawing_ratio + self.canvas.midpoint

                self.canvas.create_line(start.x, start.y * -1 + canvas_height, end.x, end.y * -1 + canvas_height, fill=layer_colours[self.colours[layer_name]], width=2 if layer_name in selected_layers else 1)

    def action(self, act):
        layers = self.layers
        selections = [self.layer_box.get(i) for i in self.layer_box.curselection()]

        try:
            self.layers, self.colours = act(self.layers, self.colours, selections, self.update_statusbar, self.update_canvas, self.canvas)
        except AbortAction:
            pass

        self.update_layerbox()
        self.update_canvas()

    def change_colour(self, colour_index):
        def changer():
            selections = [self.layer_box.get(i) for i in self.layer_box.curselection()]
            for selection in selections:
                self.colours[selection] = colour_index
            self.update_canvas()
            self.update_layerbox()

        return changer


def main():
    root = tk.Tk()
    root.title("LAZOR")

    tk.Grid.rowconfigure(root, 0, weight=1)
    tk.Grid.columnconfigure(root, 0, weight=1)

    app = Application(master=root)
    app.mainloop()
