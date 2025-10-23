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

def simplify_shapes(shapes, linear_deflection=1.0, angular_deflection=0.8):
    """Upraszcza listę kształtów poprzez modyfikację siatki."""
    simplified = []
    for shape in shapes:
        mesh = BRepMesh_IncrementalMesh(shape, linear_deflection, True, angular_deflection)
        mesh.Perform()
        simplified.append(shape)
    return simplified

def center_shapes(shapes):
    """Centruje listę kształtów względem początku układu współrzędnych."""
    centered = []
    for shape in shapes:
        bbox = Bnd_Box()
        brepbndlib.Add(shape, bbox)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
        cx = (xmin + xmax) / 2
        cy = (ymin + ymax) / 2
        cz = (zmin + zmax) / 2

        trsf = gp_Trsf()
        trsf.SetTranslation(gp_Vec(-cx, -cy, -cz))
        transformer = BRepBuilderAPI_Transform(shape, trsf, True)
        centered.append(transformer.Shape())

    return centered

def load_shapes(file_list):
    """Wczytuje i przetwarza pliki STEP."""
    readers = []
    statuses = []
    for f in file_list:
        rdr = STEPControl_Reader()
        statuses.append(rdr.ReadFile(f))
        readers.append(rdr)

    if not all(s == IFSelect_RetDone for s in statuses):
        return None, statuses
    
    return readers, statuses


def apply_transform_to_shape(shape, transform):
    """Stosuje rotację i translację do kształtu (względem jego aktualnej pozycji)."""
    shp = shape

    if not transform:
        return shp

    # 🔹 Rotacje
    rotations = []
    if transform.get('rotations'):
        rotations = transform['rotations'] or []
    elif transform.get('rotate'):
        rotations = [transform['rotate']]

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

    # 🔹 Translacja
    if transform.get('translate'):
        tr = transform['translate']
        if tr:
            vec = gp_Vec(*tr)
            tr_trsf = gp_Trsf()
            tr_trsf.SetTranslation(vec)
            shp = BRepBuilderAPI_Transform(shp, tr_trsf, True).Shape()

    return shp

def apply_transforms_to_shapes(shapes, transforms):
    """Stosuje zestaw transformacji do listy kształtów.
    
    Każdy element z `transforms` odpowiada kształtowi o tym samym indeksie w `shapes`.
    """
    if not transforms:
        return shapes

    transformed_shapes = []
    for idx, shape in enumerate(shapes):
        if idx < len(transforms):
            tf = transforms[idx]
            new_shape = apply_transform_to_shape(shape, tf)
            transformed_shapes.append(new_shape)
        else:
            # jeśli brak transformacji dla danego kształtu — zostaje bez zmian
            transformed_shapes.append(shape)

    return transformed_shapes


def update_shape_transform(shape, transform, display, color=None):
    """Aktualizuje pojedynczy kształt poprzez zastosowanie transformacji
    i ponowne narysowanie go w widoku.
    
    Args:
        shape: Kształt (TopoDS_Shape), który ma zostać zaktualizowany.
        transform: Słownik zawierający dane transformacji (rotate / rotations / translate).
        display: Obiekt wyświetlający (np. current_display).
        color: Kolor kształtu (opcjonalny, np. (r, g, b)).
    """
    if not shape or not display:
        return None

    # 🔹 Zastosuj transformację
    new_shape = apply_transform_to_shape(shape, transform)

    # 🔹 Usuń stary kształt z widoku
    display.EraseShape(shape)

    # 🔹 Narysuj nowy kształt
    if color:
        display.DisplayShape(new_shape, color=color)
    else:
        display.DisplayShape(new_shape)

    # 🔹 Odśwież widok
    display.View_Iso()
    display.FitAll()
    display.View.Update()

    return new_shape


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

shape_colors = [
    rgb_color(0.6,0.6,0.6),  # podstawa
    rgb_color(0.4,0.6,1),    # ramie1
    rgb_color(0.4,0.6,1),    # ramie2
    rgb_color(0.4,0.6,1),    # ramie3
    rgb_color(0.6,0.8,0.4),  # ramie4
    rgb_color(0.6,0.5,0.9),  # ramie5
    rgb_color(0.9,0.6,0.4),  # ramie6
]
def centered_shapes

# --- Utworzenie okna z suwakiem ---
root = tk.Tk()
root.title("Kontrola obrotu")
root.geometry("300x100")

frame = ttk.Frame(root, padding="10")
frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

rotation_slider = ttk.Scale(
    frame,
    from_=0,
    to=180,
    orient=tk.HORIZONTAL,
    command=update_shape_transform(centered_shapes[2], {'translate': (0,0,0), 'rotations': [{'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': angle}, {'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0}]}, current_display, shape_colors[2] )
)

#-------MAIN CODE-------


# --- Wczytanie i inicjalizacja modeli ---
shapes, statuses = load_shapes(filenames)


if shapes is None:
    print("❌ Failed to read STEP files. Statuses:", statuses)
    exit(1)

#uproszczenie kształtów
simplify_shapes(shapes)
#wycentrowanie kształtów
center_shapes(shapes)
centered_shapes = shapes

apply_transforms_to_shapes(shapes, transforms_table)



for i, shape in enumerate(shapes):
    display.DisplayShape(shape, shape_colors[i])

marker_radius = 10.0
sphere_marker = BRepPrimAPI_MakeSphere(gp_Pnt(0, 0, 0), marker_radius).Shape()
display.DisplayShape(sphere_marker, color=rgb_color(1.0, 0.0, 0.0))

display.View_Iso()
display.FitAll()
display.View.Update()
print("✅ Displayed centered and rotated models (ramie0..ramie6).")


ttk.Label(frame, text="Kąt obrotu:").grid(row=0, column=0, sticky=tk.W)

rotation_slider.grid(row=1, column=0, sticky=(tk.W, tk.E))
rotation_slider.set(0)

current_display = display
current_shapes = shapes

root.mainloop()
start_display()
