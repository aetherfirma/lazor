import tkinter as tk
from collections import OrderedDict
from tkinter import ttk, filedialog

import ezdxf

from lazor.analysis import ideal_laser_distance, optimise_line_set_ordering
from lazor.dxf import unpack


class Application(ttk.Frame):
    def __init__(self, master=False):
        super().__init__(master, padding="10 10 10 10")
        self.grid(column=0, row=0, sticky=(tk.N, tk.W, tk.E, tk.S))

        self.filename = tk.StringVar()
        self.layers = OrderedDict()

        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)

        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=0)

        ttk.Button(self, text="Open File", command=self.open_file).grid(column=0, row=0)

        ttk.Label(self, textvariable=self.filename, relief="sunken", padding="5 5 5 5").grid(column=1, columnspan=2, row=0, sticky=tk.W+tk.E+tk.N+tk.S)

        self.layer_box = tk.Listbox(self, selectmode=tk.EXTENDED)
        self.layer_box.grid(column=1, row=1, sticky=tk.W+tk.E+tk.N+tk.S)
        self.layer_box.bind("<<ListboxSelect>>", self.select_layer)

    def open_file(self):
        filename = filedialog.askopenfilename(filetypes=[("dxf files", ".dxf"), ("All files", ".*")])

        if not filename:
            return

        self.filename.set(filename)

        drawing = ezdxf.readfile(filename)
        self.layers = OrderedDict()
        self.layers.update(unpack(drawing.modelspace()))

        self.update_layerbox()

    def update_layerbox(self):
        self.layer_box.delete(0, tk.END)

        for layer in self.layers:
            self.layer_box.insert(tk.END, layer)

    def select_layer(self, event):
        layers = [self.layer_box.get(i) for i in self.layer_box.curselection()]
        if len(layers) == 1:
            layer = layers[0]
            print("{} vs {}".format(ideal_laser_distance(self.layers[layer]), ideal_laser_distance(
                optimise_line_set_ordering(self.layers[layer]))))
        elif len(layers) > 1:
            print(sum(
                ideal_laser_distance(self.layers[layer]) for layer in layers))


def main():
    root = tk.Tk()
    root.title("LAZOR")

    tk.Grid.rowconfigure(root, 0, weight=1)
    tk.Grid.columnconfigure(root, 0, weight=1)

    app = Application(master=root)
    app.mainloop()


if __name__ == "__main__":
    main()