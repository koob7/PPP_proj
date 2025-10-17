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
from OCC.Core.BRepBndLib import brepbndlib_Add
import math

# --- Inicjalizacja okna ---
display, start_display, add_menu, add_function_to_menu = init_display()

# --- Wczytanie plików STEP (lista plików: ramie0..ramie6) ---
filenames = [
    "ramie0.step",
    "ramie1.step",
    "ramie2.step",
    "ramie3.step",
    "ramie4.step",
    "ramie5.step",
    "ramie6.step",
]


def load_and_center(file_list):
    """Wczyta listę plików STEP, przetransferuje i wycentruje każdy kształt.
    Zwraca (shapes, statuses). Jeśli któryś plik nie został poprawnie wczytany,
    shapes będzie None i zwracane będą statusy dla diagnostyki."""
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
        shapes.append(center_shape(rdr.Shape()))

    return shapes, statuses

# --- Funkcja do wyśrodkowania modelu ---
def center_shape(shape):
    bbox = Bnd_Box()
    brepbndlib_Add(shape, bbox)
    xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
    # Obliczenie środka
    cx = (xmin + xmax) / 2
    cy = (ymin + ymax) / 2
    cz = (zmin + zmax) / 2
    # Translacja do początku układu
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(-cx, -cy, -cz))
    transformer = BRepBuilderAPI_Transform(shape, trsf, True)
    return transformer.Shape()

# --- Wczytaj i wycentruj wszystkie pliki z listy ---
shapes, statuses = load_and_center(filenames)
if shapes is None:
    print("❌ Failed to read STEP files. Statuses:", statuses)
else:
    # Rozpakuj listę do zmiennych dla czytelności
    shape0, shape1, shape2, shape3, shape4, shape5, shape6 = shapes

    # --- Obrót pierwszego modelu ---
    dx, dy, dz = 0, 100, 0
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(dx, dy, dz))
    moved_shape1 = BRepBuilderAPI_Transform(shape1, trsf, True).Shape()
    origin = gp_Pnt(0, 100, 0)
    axis = gp_Ax1(origin, gp_Dir(0, 0, 1))
    rotation = gp_Trsf()
    rotation.SetRotation(axis, math.radians(90))
    rotated_shape1 = BRepBuilderAPI_Transform(moved_shape1, rotation, True).Shape()

    # --- Wyświetlenie modeli ---
    display.DisplayShape(shape0, color=rgb_color(0.6,0.6,0.6))       # podstawa
    display.DisplayShape(shape1, color=rgb_color(0.4,0.6,1))         # ramie1 (oryginał)
    display.DisplayShape(rotated_shape1, color=rgb_color(0.4,1,0.3)) # ramie1 (obrócony)
    display.DisplayShape(shape2, color=rgb_color(0.4,0.6,1))         # ramie2
    display.DisplayShape(shape3, color=rgb_color(0.4,0.6,1))         # ramie3
    display.DisplayShape(shape4, color=rgb_color(0.6,0.8,0.4))       # ramie4
    display.DisplayShape(shape5, color=rgb_color(0.6,0.5,0.9))       # ramie5
    display.DisplayShape(shape6, color=rgb_color(0.9,0.6,0.4))       # ramie6

    # --- Wyświetlenie punktu z kulką ---
    marker_radius = 10.0
    sphere_marker = BRepPrimAPI_MakeSphere(gp_Pnt(0, 0, 0), marker_radius).Shape()
    display.DisplayShape(sphere_marker, color=rgb_color(1.0, 0.0, 0.0))

    display.View_Iso()
    display.FitAll()
    display.View.Update()
    print("✅ Displayed centered and rotated models (ramie0..ramie6).")

# --- Ustawienia widoku ---
display.hide_triedron()  # pokazuje układ osi

start_display()
