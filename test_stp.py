from OCC.Core.STEPControl import STEPControl_Reader
from OCC.Display.SimpleGui import init_display
from OCC.Core.IFSelect import IFSelect_RetDone
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Ax1, gp_Trsf
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
import math

# --- Inicjalizacja okna ---
display, start_display, add_menu, add_function_to_menu = init_display()

# --- Wczytanie pliku STEP ---
reader = STEPControl_Reader()
status = reader.ReadFile(r"test.stp")

if status == IFSelect_RetDone:
    reader.TransferRoots()
    shape = reader.Shape()

    # --- OBRÓT ---
    origin = gp_Pnt(0, 300, 0)
    axis = gp_Ax1(origin, gp_Dir(0, 0, 1))
    rotation = gp_Trsf()
    rotation.SetRotation(axis, math.radians(90))
    transformer = BRepBuilderAPI_Transform(shape, rotation, True)
    rotated_shape = transformer.Shape()

    # --- WYŚWIETLENIE OBU MODELI ---
    display.DisplayShape(shape, color="LIGHTGRAY")       # oryginał
    display.DisplayShape(rotated_shape, color="RED")     # obrócony model

    display.View_Iso()
    display.FitAll()
    display.View.Update()
    print("✅ Displayed original and rotated models.")
else:
    print("❌ Failed to read STEP file.")

start_display()
