import os
import tkinter as tk
from collections import OrderedDict
from tkinter import ttk
from tkinter import filedialog

import ezdxf

from lazor.analysis import join_lines, collate_lines
from lazor.datastructures import Vec2
from lazor.dxf import unpack, draw


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
        self.rowconfigure(4, weight=0)
        self.rowconfigure(5, weight=0)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)

        ttk.Button(self, text="Open File", command=self.open_file).grid(column=0, row=0)

        ttk.Label(self, textvariable=self.filename, relief="sunken", padding="5 5 5 5").grid(column=1, columnspan=2, row=0, sticky=tk.W+tk.E+tk.N+tk.S)
        ttk.Label(self, textvariable=self.statusbar, relief="sunken", padding="5 5 5 5").grid(column=0, columnspan=3, row=6, sticky=tk.W+tk.E+tk.N+tk.S)

        self.canvas = tk.Canvas(self, relief="sunken", bg="white")
        self.canvas.grid(column=0, columnspan=2, row=1, rowspan=5, sticky=tk.W+tk.E+tk.N+tk.S)
        self.canvas.bind("<Configure>", self.redraw_on_event)

        self.layer_box = tk.Listbox(self, selectmode=tk.EXTENDED)
        self.layer_box.grid(column=2, row=1, sticky=tk.W+tk.E+tk.N+tk.S)
        self.layer_box.bind("<<ListboxSelect>>", self.select_layer)

        ttk.Button(self, text="Autofix", command=self.autofix).grid(column=2, row=2)
        ttk.Button(self, text="Add Tabs", command=self.tab).grid(column=2, row=3)
        ttk.Button(self, text="Explode Components", command=self.explode).grid(column=2, row=4)
        ttk.Button(self, text="Save As", command=self.save_file).grid(column=2, row=5)

    def update_statusbar(self, msg):
        self.statusbar.set(msg)
        self.master.update()

    def open_file(self):
        filename = filedialog.askopenfilename(filetypes=[("dxf files", ".dxf"), ("All files", ".*")])

        if not filename:
            return

        self.filename.set(filename)
        self.update_statusbar("Loading {}".format(filename))

        drawing = ezdxf.readfile(filename)
        self.layers = OrderedDict()
        self.layers["drawing"] = unpack(drawing.modelspace())

        self.update_layerbox()
        self.update_canvas()
        self.update_statusbar("Loaded {}".format(filename))

    def save_file(self):
        if not self.layers:
            return

        if not self.filename:
            return

        initialdir, initialfile = os.path.split(self.filename.get())
        filename = filedialog.asksaveasfilename(filetypes=[("dxf files", ".dxf")], initialfile=initialfile, initialdir=initialdir)

        if not filename:
            return

        dxf = draw(**self.layers)
        dxf.saveas(filename)

        self.update_layerbox()
        self.update_canvas()

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
            self.update_statusbar("Layer '{}' contains {} lines".format(layer, len(self.layers[layer])))
        elif len(layers) > 1:
            self.update_statusbar("Selected layers contain {} lines".format(sum([len(self.layers[layer]) for layer in layers])))

        self.update_canvas()

    def update_canvas(self):
        self.canvas.delete(tk.ALL)
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()

        midpoint = Vec2(width / 2, height / 2)

        if not self.layers:
            self.canvas.create_text(
                *midpoint,
                text="NO FILE LOADED",
                fill="red"
            )
            return

        min_point = Vec2(float('inf'), float('inf'))
        max_point = Vec2(float('-inf'), float('-inf'))

        for layer in self.layers.values():
            for start, end in layer:
                min_point = Vec2(min(start.x, end.x, min_point.x), min(start.y, end.y, min_point.y))
                max_point = Vec2(max(start.x, end.x, max_point.x), max(start.y, end.y, max_point.y))

        drawing_width, drawing_height = max_point - min_point
        ratio = min((width - 10)/drawing_width, (height - 10)/drawing_height)

        selected_layers = [self.layer_box.get(i) for i in self.layer_box.curselection()]

        for layer_name, layer in self.layers.items():
            colour = "red" if layer_name in selected_layers else "black"

            for start, end in layer:
                start = start * ratio + midpoint
                end = end * ratio + midpoint
                self.canvas.create_line(start.x, start.y * -1 + height, end.x, end.y * -1 + height, fill=colour)

    def autofix(self):
        if not self.layers:
            return

        layers = [self.layer_box.get(i) for i in self.layer_box.curselection()]
        if not layers:
            return

        for layer in layers:
            self.layers[layer] = join_lines(self.layers[layer])

        self.update_layerbox()
        self.update_canvas()

    def explode(self):
        if not self.layers:
            return

        layers = [self.layer_box.get(i) for i in self.layer_box.curselection()]
        if not layers:
            return

        for layer_name in layers:
            layer = self.layers[layer_name]
            del self.layers[layer_name]

            new_layers = collate_lines(layer)
            if len(new_layers) == 1:
                self.layers[layer_name] = new_layers[0]
            else:
                for n, new_layer in enumerate(new_layers):
                    self.layers["{} {}".format(layer_name, n+1)] = new_layer

        self.update_layerbox()
        self.update_canvas()

    def tab(self):
        if not self.layers:
            return

        layers = [self.layer_box.get(i) for i in self.layer_box.curselection()]
        if not layers:
            return

        for layer_name in layers:
            layer = self.layers[layer_name]

            new_layer = []
            for line in layer:
                _, new_lines = line.add_tab(29)
                new_layer += new_lines

                self.layers[layer_name] = new_layer

        self.update_canvas()

    def noop(self):
        print("Button pressed")


def main():
    root = tk.Tk()
    root.title("LAZOR")

    tk.Grid.rowconfigure(root, 0, weight=1)
    tk.Grid.columnconfigure(root, 0, weight=1)

    app = Application(master=root)
    app.mainloop()


if __name__ == "__main__":
    main()
