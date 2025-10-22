from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Display.SimpleGui import init_display
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax1, gp_Trsf, gp_Vec
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere
from OCC.Display.OCCViewer import rgb_color
from OCC.Core.Geom import Geom_CartesianPoint
from OCC.Core.AIS import AIS_Point
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
import math
import tkinter as tk
from tkinter import ttk

# --- Zmienne globalne do przechowywania referencji ---
current_shapes = None
current_display = None
last_angle = 0
simplified_shapes = None  # Zdefiniowane na początku

def simplify_shape(shape, linear_deflection=1.0, angular_deflection=0.8):
    """Upraszcza kształt poprzez modyfikację siatki."""
    mesh = BRepMesh_IncrementalMesh(shape, linear_deflection, True, angular_deflection)
    mesh.Perform()
    return shape

def center_shape(shape):
    """Centruje kształt względem początku układu współrzędnych."""
    bbox = Bnd_Box()
    brepbndlib.Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    cx = (xmin + xmax) / 2
    cy = (ymin + ymax) / 2
    cz = (zmin + zmax) / 2
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(-cx, -cy, -cz))
    transformer = BRepBuilderAPI_Transform(shape, trsf, True)
    return transformer.Shape()

def load_and_center(file_list, transforms=None, simplify=True):
    """Wczytuje i przetwarza pliki STEP."""
    readers = []
    statuses = []
    for f in file_list:
        rdr = STEPControl_Reader()
        statuses.append(rdr.ReadFile(f))
        readers.append(rdr)

    if not all(s == IFSelect_RetDone for s in statuses):
        return None, statuses

    shapes = []
    for idx, rdr in enumerate(readers):
        rdr.TransferRoots()
        shp = rdr.Shape()
        
        if simplify:
            shp = simplify_shape(shp)
        shp = center_shape(shp)

        if transforms and idx < len(transforms):
            tf = transforms[idx]
            rotations = []
            if tf.get('rotations'):
                rotations = tf['rotations'] or []
            elif tf.get('rotate'):
                rotations = [tf['rotate']]

            for rot in rotations:
                if not rot:
                    continue
                origin = rot.get('origin')
                axis = rot.get('axis')
                angle = rot.get('angle_deg')
                if origin and axis and angle is not None:
                    ax_pnt = gp_Pnt(*origin)
                    ax_dir = gp_Dir(*axis)
                    ax = gp_Ax1(ax_pnt, ax_dir)
                    rot_trsf = gp_Trsf()
                    rot_trsf.SetRotation(ax, math.radians(angle))
                    shp = BRepBuilderAPI_Transform(shp, rot_trsf, True).Shape()

            if tf.get('translate'):
                tr = tf['translate']
                if tr:
                    vec = gp_Vec(*tr)
                    tr_trsf = gp_Trsf()
                    tr_trsf.SetTranslation(vec)
                    shp = BRepBuilderAPI_Transform(shp, tr_trsf, True).Shape()

        shapes.append(shp)

    return shapes, statuses

def update_rotation(angle):
    """Aktualizuje rotację modeli."""
    global current_shapes, current_display, last_angle, simplified_shapes
    if not simplified_shapes or not current_display:
        return
        
    angle = float(angle)

    transforms_table[2]['rotations'][0]['angle_deg'] = angle
    
    shapes = []
    for idx, shape in enumerate(simplified_shapes):
        shp = shape
        if transforms_table and idx < len(transforms_table):
            tf = transforms_table[idx]
            rotations = tf.get('rotations', [])
            for rot in rotations:
                if not rot:
                    continue
                origin = rot.get('origin')
                axis = rot.get('axis')
                angle = rot.get('angle_deg')
                if origin and axis and angle is not None:
                    ax_pnt = gp_Pnt(*origin)
                    ax_dir = gp_Dir(*axis)
                    ax = gp_Ax1(ax_pnt, ax_dir)
                    rot_trsf = gp_Trsf()
                    rot_trsf.SetRotation(ax, math.radians(angle))
                    shp = BRepBuilderAPI_Transform(shp, rot_trsf, True).Shape()

            if tf.get('translate'):
                tr = tf['translate']
                if tr:
                    vec = gp_Vec(*tr)
                    tr_trsf = gp_Trsf()
                    tr_trsf.SetTranslation(vec)
                    shp = BRepBuilderAPI_Transform(shp, tr_trsf, True).Shape()
        
        shapes.append(shp)

    if shapes:
        current_shapes = shapes
        current_display.EraseAll()
        
        colors = [
            rgb_color(0.6,0.6,0.6),  # podstawa
            rgb_color(0.4,0.6,1),    # ramie1
            rgb_color(0.4,0.6,1),    # ramie2
            rgb_color(0.4,0.6,1),    # ramie3
            rgb_color(0.6,0.8,0.4),  # ramie4
            rgb_color(0.6,0.5,0.9),  # ramie5
            rgb_color(0.9,0.6,0.4),  # ramie6
        ]
        
        for i, (shape, color) in enumerate(zip(shapes, colors)):
            if hide_table[i]:
                current_display.DisplayShape(shape, color=color)
                
        current_display.View_Iso()
        current_display.FitAll()
        current_display.View.Update()

# --- Inicjalizacja ---
display, start_display, add_menu, add_function_to_menu = init_display()

filenames = [
    "ramie0.step", "ramie1.step", "ramie2.step", "ramie3.step",
    "ramie4.step", "ramie5.step", "ramie6.step",
]

transforms_table = [
    {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
    {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
    {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
    {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
    {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
    {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
    {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]},
]

hide_table = [False, False, True, False, False, False, False]

# --- Wczytanie i inicjalizacja modeli ---
shapes, statuses = load_and_center(filenames, simplify=True)
if shapes is None:
    print("❌ Failed to read STEP files. Statuses:", statuses)
else:
    simplified_shapes = shapes.copy()
    shape0, shape1, shape2, shape3, shape4, shape5, shape6 = shapes

    if hide_table[0]:
        display.DisplayShape(shape0, color=rgb_color(0.6,0.6,0.6))
    if hide_table[1]:
        display.DisplayShape(shape1, color=rgb_color(0.4,0.6,1))
    if hide_table[2]:
        display.DisplayShape(shape2, color=rgb_color(0.4,0.6,1))
    if hide_table[3]:
        display.DisplayShape(shape3, color=rgb_color(0.4,0.6,1))
    if hide_table[4]:
        display.DisplayShape(shape4, color=rgb_color(0.6,0.8,0.4))
    if hide_table[5]:
        display.DisplayShape(shape5, color=rgb_color(0.6,0.5,0.9))
    if hide_table[6]:
        display.DisplayShape(shape6, color=rgb_color(0.9,0.6,0.4))

    marker_radius = 10.0
    sphere_marker = BRepPrimAPI_MakeSphere(gp_Pnt(0, 0, 0), marker_radius).Shape()
    display.DisplayShape(sphere_marker, color=rgb_color(1.0, 0.0, 0.0))

    display.View_Iso()
    display.FitAll()
    display.View.Update()
    print("✅ Displayed centered and rotated models (ramie0..ramie6).")

# --- Utworzenie okna z suwakiem ---
root = tk.Tk()
root.title("Kontrola obrotu")
root.geometry("300x100")

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

ttk.Label(frame, text="Kąt obrotu:").grid(row=0, column=0, sticky=tk.W)

rotation_slider = ttk.Scale(
    frame,
    from_=0,
    to=180,
    orient=tk.HORIZONTAL,
    command=update_rotation
)
rotation_slider.grid(row=1, column=0, sticky=(tk.W, tk.E))
rotation_slider.set(0)

current_display = display
current_shapes = shapes

root.mainloop()
start_display()
