from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Display.SimpleGui import init_display
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax1, gp_Trsf, gp_Vec
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere
from OCC.Display.OCCViewer import rgb_color
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
import math
import tkinter as tk
from tkinter import ttk


# --- Zmienne globalne ---
current_shapes = None
current_display = None
simplified_shapes = None
displayed_shapes = None
transforms_table = None


# --- Funkcje pomocnicze ---
def simplify_shapes(shapes, linear_deflection=1.0, angular_deflection=0.8):
    simplified = []
    for shape in shapes:
        mesh = BRepMesh_IncrementalMesh(shape, linear_deflection, True, angular_deflection)
        mesh.Perform()
        simplified.append(shape)
    return simplified


def center_shapes(shapes):
    centered = []
    for shape in shapes:
        bbox = Bnd_Box()
        brepbndlib.Add(shape, bbox)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()  # lub Get(xmin, ymin, zmin, xmax, ymax, zmax) w starszych wersjach
        cx = (xmin + xmax) / 2
        cy = (ymin + ymax) / 2
        cz = (zmin + zmax) / 2
        # przesuwamy tak, aby środek bounding box znalazł się w (0,0,0)
        trsf = gp_Trsf()
        trsf.SetTranslation(gp_Vec(-cx, -cy, -cz))
        shp_centered = BRepBuilderAPI_Transform(shape, trsf, True).Shape()
        centered.append(shp_centered)
    return centered



def load_shapes(file_list):
    readers = []
    statuses = []
    for f in file_list:
        rdr = STEPControl_Reader()
        statuses.append(rdr.ReadFile(f))
        readers.append(rdr)
    if not all(s == IFSelect_RetDone for s in statuses):
        return None, statuses
    shapes = []
    for rdr in readers:
        rdr.TransferRoots()
        shapes.append(rdr.Shape())
    return shapes, statuses


def apply_transform_to_shape(shape, transform):
    """
    Zastosuj translację i obrót do kształtu.
    Obrót zawsze względem środka układu współrzędnych (0,0,0)
    """
    shp = shape
    if not transform:
        return shp

    # Obrót wokół środka układu
    rotations = transform.get('rotations', [])
    for rot in rotations:
        if not rot:
            continue
        axis = rot.get('axis')
        angle = rot.get('angle_deg')
        if axis and angle is not None:
            ax_pnt = gp_Pnt(0, 0, 0)  # punkt obrotu: środek układu
            ax_dir = gp_Dir(*axis)
            ax = gp_Ax1(ax_pnt, ax_dir)
            rot_trsf = gp_Trsf()
            rot_trsf.SetRotation(ax, math.radians(angle))
            shp = BRepBuilderAPI_Transform(shp, rot_trsf, True).Shape()

    # Translacja (opcjonalna)
    tr = transform.get('translate')
    if tr:
        vec = gp_Vec(*tr)
        tr_trsf = gp_Trsf()
        tr_trsf.SetTranslation(vec)
        shp = BRepBuilderAPI_Transform(shp, tr_trsf, True).Shape()

    return shp





def redraw_scene(display, shapes, colors, marker_radius=10.0):


    if display is None:
        print("❌ Display is None")
        return

    display.EraseAll()



    # Rysuj kształty (pomijając ukryte według draw_table)
    for i, shape in enumerate(shapes):
        if i < len(draw_table) and draw_table[i]:
            display.DisplayShape(shape, color=colors[i])

    # Dodaj marker w środku sceny
    marker = BRepPrimAPI_MakeSphere(gp_Pnt(0, 0, 0), marker_radius).Shape()
    display.DisplayShape(marker, color=rgb_color(1.0, 0.0, 0.0))

    # Odśwież widok
    display.View_Iso()
    display.FitAll()
    display.View.Update()
    current_display = display


# --- Inicjalizacja wyświetlania ---
display, start_display, add_menu, add_function_to_menu = init_display()

filenames = [
    "ramie0.step", "ramie1.step", "ramie2.step",
    "ramie3.step", "ramie4.step", "ramie5.step", "ramie6.step",
]

transforms_table = [ {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
                     {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
                     {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
                     {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
                     {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
                     {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
                     {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
]

shape_colors = [
    rgb_color(0.6, 0.6, 0.6),
    rgb_color(0.4, 0.6, 1),
    rgb_color(0.4, 0.6, 1),
    rgb_color(0.4, 0.6, 1),
    rgb_color(0.6, 0.8, 0.4),
    rgb_color(0.6, 0.5, 0.9),
    rgb_color(0.9, 0.6, 0.4),
]

draw_table = [False, False, True, False, False, False, False]


# --- Wczytanie i przetworzenie modeli ---
shapes, statuses = load_shapes(filenames)
if shapes is None:
    print("❌ Nie udało się wczytać plików STEP:", statuses)
    exit(1)

simplified_shapes = simplify_shapes(shapes)
centerd_shapes = center_shapes(simplified_shapes)
displayed_shapes = centerd_shapes
# --- Rysowanie początkowe za pomocą funkcji ---
redraw_scene(display, displayed_shapes, shape_colors)



# --- Funkcja obsługi suwaka ---
def on_slider_change(angle):
    """Callback zmiany kąta z suwaka."""
    idx = 2  # np. 3. ramię
    transforms_table[idx]['rotations'][0]['angle_deg'] = float(angle)
    # Zaktualizuj transformację tylko jednego kształtu
    displayed_shapes[idx] = apply_transform_to_shape(centerd_shapes[idx], transforms_table[idx])
    # Ponownie narysuj całą scenę tą samą funkcją
    redraw_scene(display, displayed_shapes, shape_colors)


# --- GUI Tkinter ---
root = tk.Tk()
root.title("Kontrola obrotu ramienia")
root.geometry("300x100")

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

ttk.Label(frame, text="Kąt obrotu:").grid(row=0, column=0, sticky=tk.W)


rotation_slider = ttk.Scale(
    frame, from_=0, to=360, orient=tk.HORIZONTAL
)
rotation_slider.grid(row=1, column=0, sticky=(tk.W, tk.E))
rotation_slider.set(0)

# Callback wywoływany tylko po puszczeniu suwaka
def on_slider_release(event):
    value = rotation_slider.get()
    on_slider_change(value)

rotation_slider.bind("<ButtonRelease-1>", on_slider_release)

root.mainloop()
start_display()
