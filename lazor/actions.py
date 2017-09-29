from tkinter import messagebox, simpledialog

from lazor.analysis import join_lines, collate_lines, \
    optimise_line_set_ordering, ideal_laser_distance, estimated_laser_time, \
    estimated_engrave_time
from lazor.exceptions import AbortAction


def autofix(layers, selections, update_statusbar, update_canvas, canvas):
    if not layers:
        messagebox.showerror("Cannot perform autofix", "You must load a file first")
        raise AbortAction()

    if not selections:
        messagebox.showerror("Cannot perform autofix", "You must select one or more layers to fix")
        raise AbortAction()

    pre_fix = sum([len(layers[l]) for l in selections])
    if len(selections) == 1:
        update_statusbar("Fixing '{}'...".format(selections[0]))
    else:
        update_statusbar("Fixing {} layers...".format(len(selections)))

    for layer in selections:
        layers[layer] = join_lines(layers[layer])

    post_fix = sum([len(layers[l]) for l in selections])

    prefix = "Layer '{}' had".format(selections[0]) if len(selections) == 1 else "Selected layers had"

    update_statusbar("{} {} lines, reduced to {} ({}% saving)".format(
        prefix,
        pre_fix,
        post_fix,
        int((1-(post_fix/pre_fix))*100)
    ))

    return layers


def optimise(layers, selections, update_statusbar, update_canvas, canvas):
    if not layers:
        messagebox.showerror("Cannot perform optimisation", "You must load a file first")
        raise AbortAction()

    if not selections:
        messagebox.showerror("Cannot perform optimisation", "You must select one or more layers to optimise")
        raise AbortAction()

    pre_fix = sum([ideal_laser_distance(layers[l]) for l in selections])
    if len(selections) == 1:
        update_statusbar("Optimising '{}'...".format(selections[0]))
    else:
        update_statusbar("Optimising {} layers...".format(len(selections)))

    for layer in selections:
        layers[layer] = optimise_line_set_ordering(layers[layer])

    post_fix = sum([ideal_laser_distance(layers[l]) for l in selections])

    prefix = "Layer '{}' travelled".format(selections[0]) if len(selections) == 1 else "Selected layers travelled"

    update_statusbar("{} {}mm, reduced to {}mm ({}% saving)".format(
        prefix,
        round(pre_fix, 1),
        round(post_fix, 1),
        int((1-(post_fix/pre_fix))*100)
    ))

    return layers


def explode(layers, selections, update_statusbar, update_canvas, canvas):
    if not layers:
        messagebox.showerror("Cannot perform explode", "You must load a file first")
        raise AbortAction()

    if not selections:
        messagebox.showerror("Cannot perform explode", "You must select one or more layers to explode")
        raise AbortAction()

    new_layers = []

    for layer_name in selections:
        layer = layers[layer_name]
        del layers[layer_name]

        new_layers = collate_lines(layer)
        if len(new_layers) == 1:
            layers[layer_name] = new_layers[0]
        else:
            for n, new_layer in enumerate(new_layers):
                layers["{} {}".format(layer_name, n + 1)] = new_layer

    update_statusbar("Created {} new layers".format(len(new_layers)))

    return layers


def laser_estimation(layers, selections, update_statusbar, update_canvas, canvas):
    if not layers:
        messagebox.showerror("Cannot estimate laser time", "You must load a file first")
        raise AbortAction()

    if not selections:
        messagebox.showerror("Cannot estimate laser time", "You must select one or more layers to estimate")
        raise AbortAction()

    idle_speed = simpledialog.askfloat("Idle Speed", "Please enter the tool idle speed", initialvalue=100)
    active_speed = simpledialog.askfloat("Active Speed", "Please enter the tool active speed", initialvalue=35)

    time = 0

    for layer_name in selections:
        layer = layers[layer_name]

        time += estimated_laser_time(layer, idle_speed, active_speed)

    prefix = "This layer" if len(selections) == "1" else "These layers"

    update_statusbar("{} should take ~{} seconds".format(
        prefix,
        int(round(time, 0))
    ))

    return layers


def laser_engraving_estimation(layers, selections, update_statusbar, update_canvas, canvas):
    if not layers:
        messagebox.showerror("Cannot estimate laser time", "You must load a file first")
        raise AbortAction()

    if not selections:
        messagebox.showerror("Cannot estimate laser time", "You must select one or more layers to estimate")
        raise AbortAction()

    idle_speed = simpledialog.askfloat("Idle Speed", "Please enter the tool idle speed", initialvalue=10)
    active_speed = simpledialog.askfloat("Active Speed", "Please enter the tool active speed", initialvalue=800)
    scanline = simpledialog.askfloat("Scanline Distance", "Please enter the scanline distance", initialvalue=0.05)

    update_statusbar("Estimating engraving time")

    lines = sum((list(layers[layer_name]) for layer_name in selections), [])

    idle_time, time = estimated_engrave_time(lines, active_speed, idle_speed, scanline, update_canvas, canvas)

    update_statusbar("Engraving will take ~{} seconds, spending ~{} seconds idle".format(
        int(round(time, 0)),
        int(round(idle_time, 0))
    ))

    return layers


def add_tabs(layers, selections, update_statusbar, update_canvas, canvas):
    if not layers:
        messagebox.showerror("Cannot add tabs", "You must load a file first")
        raise AbortAction()

    if not selections:
        messagebox.showerror("Cannot add tabs", "You must select one or more layers to add tabs to")
        raise AbortAction()

    tab_distance = simpledialog.askfloat("Tab Distance", "Please enter the distance between tabs in mm", initialvalue=15.0)
    tab_width = simpledialog.askfloat("Tab Width", "Please enter the tab width in mm", initialvalue=0.5)

    for layer_name in selections:
        layer = layers[layer_name]

        # TODO: Use collate_lines to explode, convert to polygons

        new_layer = []
        for line in layer:
            _, new_lines = line.add_tab(tab_distance, tab_width)
            new_layer += new_lines

            layers[layer_name] = new_layer

    if len(selections) == 1:
        update_statusbar("Added tabs to '{}'".format(selections[0]))
    else:
        update_statusbar("Added tabs to {} layers".format(len(selections)))

    return layers


def combine_layers(layers, selections, update_statusbar, update_canvas, canvas):
    if not layers:
        messagebox.showerror("Cannot combine layers",
                             "You must load a file first")
        raise AbortAction()
    if len(selections) < 2:
        messagebox.showerror("Cannot combine layers",
                             "You must select two or more layers to combine")
        raise AbortAction()
    new_layer_name = simpledialog.askstring("New layer name",
                                            "Please enter the new layer name",
                                            initialvalue=selections[0])
    new_layer = []
    for layer in (layers[l] for l in selections):
        for line in layer:
            new_layer.append(line)
    for layer in selections:
        del layers[layer]
    layers[new_layer_name] = new_layer
    update_statusbar("Merged {} layers into '{}'".format(len(selections),
                                                         new_layer_name))

    return layers


def rename_layer(layers, selections, update_statusbar, update_canvas, canvas):
    if not layers:
        messagebox.showerror("Cannot rename layer",
                             "You must load a file first")
        raise AbortAction()
    if len(selections) != 1:
        messagebox.showerror("Cannot rename layer",
                             "You must select one layer to rename")
        raise AbortAction()
    old_layer_name = selections[0]
    new_layer_name = simpledialog.askstring("New layer name",
                                            "Please enter the new layer name")
    layer = layers[old_layer_name]
    del layers[old_layer_name]
    layers[new_layer_name] = layer
    update_statusbar(
        "Renamed '{}' to '{}'".format(old_layer_name, new_layer_name))

    return layers


def delete_layers(layers, selections, update_statusbar, update_canvas, canvas):
    if not layers:
        messagebox.showerror("Cannot delete layers",
                             "You must load a file first")
        raise AbortAction()
    if not selections:
        messagebox.showerror("Cannot delete layers",
                             "You must select one or more layers to delete")
        raise AbortAction()
    for layer_name in selections:
        del layers[layer_name]
    if len(selections) == 1:
        update_statusbar("Deleted '{}'".format(selections[0]))
    else:
        update_statusbar("Deleted {} layers".format(len(selections)))

    return layers