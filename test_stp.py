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

# --- Wczytanie plików STEP ---
reader1 = STEPControl_Reader()
reader2 = STEPControl_Reader()
reader3 = STEPControl_Reader()

status1 = reader1.ReadFile(r"ramie1.step")
status2 = reader2.ReadFile(r"ramie2.step")
status3 = reader3.ReadFile(r"ramie3.step")

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

# --- Sprawdzenie wczytania STEP ---
if status1 == IFSelect_RetDone and status2 == IFSelect_RetDone and status3 == IFSelect_RetDone:
    reader1.TransferRoots()
    shape1 = center_shape(reader1.Shape())  # Wyśrodkowanie
    
    reader2.TransferRoots()
    shape2 = center_shape(reader2.Shape())
    
    reader3.TransferRoots()
    shape3 = center_shape(reader3.Shape())

    # --- Obrót pierwszego modelu ---
    origin = gp_Pnt(0, 0, 0)
    axis = gp_Ax1(origin, gp_Dir(0, 0, 1))
    rotation = gp_Trsf()
    rotation.SetRotation(axis, math.radians(135))
    rotated_shape1 = BRepBuilderAPI_Transform(shape1, rotation, True).Shape()

    # --- Wyświetlenie modeli ---
    display.DisplayShape(shape1, color=rgb_color(0.4,0.6,1))       # oryginał
    display.DisplayShape(rotated_shape1, color=rgb_color(0.4,1,0.3)) # obrócony
    display.DisplayShape(shape2, color=rgb_color(0.4,0.6,1))
    display.DisplayShape(shape3, color=rgb_color(0.4,0.6,1))

    # --- Wyświetlenie punktu z kulką ---
    marker_radius = 10.0
    sphere_marker = BRepPrimAPI_MakeSphere(gp_Pnt(0, 0, 0), marker_radius).Shape()
    display.DisplayShape(sphere_marker, color=rgb_color(1.0, 0.0, 0.0))

    display.View_Iso()
    display.FitAll()
    display.View.Update()
    print("✅ Displayed centered and rotated models.")
else:
    print("❌ Failed to read STEP file.")

start_display()
