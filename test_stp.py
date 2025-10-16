from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Display.SimpleGui import init_display
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax1, gp_Trsf
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeSphere
from OCC.Display.OCCViewer import rgb_color
from OCC.Core.gp import gp_Pnt
from OCC.Core.AIS import AIS_Point
from OCC.Core.Geom import Geom_CartesianPoint
import math

# --- Inicjalizacja okna ---
display, start_display, add_menu, add_function_to_menu = init_display()

# --- Wczytanie pliku STEP ---
reader = STEPControl_Reader()
reader2 = STEPControl_Reader()
reader3 = STEPControl_Reader()
status = reader.ReadFile(r"ramie1.step")
status2 = reader2.ReadFile(r"ramie2.step")
status3 = reader3.ReadFile(r"ramie3.step")



# Tworzymy widoczny punkt (AIS_Point expects an underlying gp_Pnt or a Geom_CartesianPoint wrapper)
# Use gp_Pnt to create the point directly
cart_point = Geom_CartesianPoint(gp_Pnt(0, 0, 0))
ais_point = AIS_Point(cart_point)

# --- Dodatkowy, większy marker punktu: mała kula ---
# Zmienna radius określa wielkość markera (dostosuj do jednostek modelu)
marker_radius = 10.0
# Tworzymy kulę w miejscu punktu, aby punkt był lepiej widoczny
sphere_marker = BRepPrimAPI_MakeSphere(gp_Pnt(0, 0, 0), marker_radius).Shape()


if status == IFSelect_RetDone and status2 == IFSelect_RetDone and status3 == IFSelect_RetDone:
    reader.TransferRoots()
    shape = reader.Shape()

    reader2.TransferRoots()
    shape2 = reader2.Shape()

    reader3.TransferRoots()
    shape3 = reader3.Shape()

    # --- OBRÓT ---
    origin = gp_Pnt(0, 300, 0)
    axis = gp_Ax1(origin, gp_Dir(0, 0, 1))
    rotation = gp_Trsf()
    rotation.SetRotation(axis, math.radians(90))
    transformer = BRepBuilderAPI_Transform(shape, rotation, True)
    rotated_shape = transformer.Shape()

    # --- WYŚWIETLENIE OBU MODELI ---
    display.DisplayShape(shape, color=rgb_color(0.4,0.6,1))       # oryginał
    display.DisplayShape(rotated_shape, color=rgb_color(0.4,1,0.3))     # obrócony model

    display.DisplayShape(shape2, color=rgb_color(0.4,0.6,1))       # oryginał
    display.DisplayShape(shape3, color=rgb_color(0.4,0.6,1))       # oryginał

    # Wyświetlamy go w display
    display.DisplayShape(sphere_marker, color=rgb_color(1.0, 0.0, 0.0))

    display.View_Iso()
    display.FitAll()
    display.View.Update()
    print("✅ Displayed original and rotated models.")
else:
    print("❌ Failed to read STEP file.")

start_display()
