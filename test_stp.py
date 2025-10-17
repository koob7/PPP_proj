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

# --- Tabela transformacji dla każdego pliku (wypełnij wartości później) ---
# Dla każdego pliku możesz podać słownik z kluczami:
#  - translate: (dx, dy, dz) lub None
#  - rotations: lista słowników opisujących obroty (możesz podać 0,1 lub 2 obroty)
#    każdy element listy ma postać { 'origin': (ox,oy,oz), 'axis': (ax,ay,az), 'angle_deg': value }
# Przykład: { 'translate': (0,100,0), 'rotations': [ { 'origin': (0,100,0), 'axis': (0,0,1), 'angle_deg': 90 }, None ] }
transforms_table = [
    { 'translate': (0, 0, 0), 'rotations': [ { 'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0 }, { 'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0 } ] },
    { 'translate': (0, 0, 0), 'rotations': [ { 'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0 }, { 'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0 } ] },
    { 'translate': (0, 0, 0), 'rotations': [ { 'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0 }, { 'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0 } ] },
    { 'translate': (0, 0, 0), 'rotations': [ { 'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0 }, { 'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0 } ] },
    { 'translate': (0, 0, 0), 'rotations': [ { 'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0 }, { 'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0 } ] },
    { 'translate': (0, 0, 0), 'rotations': [ { 'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0 }, { 'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0 } ] },
    { 'translate': (0, 0, 0), 'rotations': [ { 'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0 }, { 'origin': (0,0,0), 'axis': (0,0,1), 'angle_deg': 0 } ] },
]


def load_and_center(file_list, transforms=None):
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
    for idx, rdr in enumerate(readers):
        rdr.TransferRoots()
        shp = center_shape(rdr.Shape())

        # Apply per-shape transforms if provided
        if transforms and idx < len(transforms):
            tf = transforms[idx]
            # Rotation first (so rotation happens around specified origin)
            # Support either single 'rotate' (legacy) or a list 'rotations' with 0..2 entries
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

            # Then translation
            if tf.get('translate'):
                tr = tf['translate']
                if tr:
                    vec = gp_Vec(*tr)
                    tr_trsf = gp_Trsf()
                    tr_trsf.SetTranslation(vec)
                    shp = BRepBuilderAPI_Transform(shp, tr_trsf, True).Shape()

        shapes.append(shp)

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


    # --- Wyświetlenie modeli ---
    display.DisplayShape(shape0, color=rgb_color(0.6,0.6,0.6))       # podstawa
    display.DisplayShape(shape1, color=rgb_color(0.4,0.6,1))         # ramie1
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

start_display()
