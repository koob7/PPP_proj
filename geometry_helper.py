"""Geometry helpers: mesh, centering and transforms."""

from typing import List, Optional
import math

from logger import logger
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.gp import gp_Trsf, gp_Vec, gp_Pnt, gp_Dir, gp_Ax1
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform
from my_types import TransformType
from OCC.Core.gp import gp_Ax3


def simplify_shapes(shapes: List, linear_deflection: float = 1.0, angular_deflection: float = 0.8) -> List:
    """Generuje meshe dla shape'ów (przy okazji zwraca oryginalne shapes)."""
    simplified = []
    for shp in shapes:
        mesh = BRepMesh_IncrementalMesh(shp, linear_deflection, True, angular_deflection)
        mesh.Perform()
        simplified.append(shp)
    return simplified

def center_shapes(shapes: List) -> List:
    """Przesuwa każdy shape tak, żeby środek jego bounding box znalazł się w (0,0,0)."""
    centered = []
    for shape in shapes:
        bbox = Bnd_Box()
        brepbndlib.Add(shape, bbox)
        xmin, ymin, zmin, xmax, ymax, zmax = bbox.Get()
        cx = (xmin + xmax) / 2.0
        cy = (ymin + ymax) / 2.0
        cz = (zmin + zmax) / 2.0
        trsf = gp_Trsf()
        trsf.SetTranslation(gp_Vec(-cx, -cy, -cz))
        shp_centered = BRepBuilderAPI_Transform(shape, trsf, True).Shape()
        centered.append(shp_centered)
    return centered


def get_total_transform(transform: Optional[TransformType]):
    """Zastosuj rotacje i translacje względem globalnego układu (0,0,0).
    Rotacje są wykonywane w kolejności z listy, translacja jest stosowana PO rotacjach.
    """

    total_trsf = gp_Trsf()

    # Rotacje (kolejność z listy)
    for rot in transform.get("rotations", []):
        if not rot:
            continue
        axis = rot.get("axis")
        angle = rot.get("angle_deg")
        if not axis or angle is None:
            continue
        ax = gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(*axis))
        rot_trsf = gp_Trsf()
        rot_trsf.SetRotation(ax, math.radians(float(angle)))
        # kluczowe: mnożymy po prawej, żeby zachować kolejność rotacji
        total_trsf = total_trsf.Multiplied(rot_trsf)

    # Translacja — chcemy T * (R_n * ... * R1)
    tr = transform.get("translate")
    if tr:
        tr_trsf = gp_Trsf()
        tr_trsf.SetTranslation(gp_Vec(*tr))
        # ważne: translacja powinna być mnożona z lewej strony
        total_trsf = tr_trsf.Multiplied(total_trsf)

    return total_trsf

def apply_transform_to_shape(shape, transform: Optional[TransformType]):
    """Zastosuj rotacje i translacje względem globalnego układu (0,0,0).
    Rotacje są wykonywane w kolejności z listy, translacja jest stosowana PO rotacjach.
    """
    if not transform:
        return shape

    total_trsf = get_total_transform(transform)

    shp_transformed = BRepBuilderAPI_Transform(shape, total_trsf, True).Shape()
    return shp_transformed

def apply_default_transforms(shapes: List, transforms_table: List[TransformType]):
    """
    Zastosuj transformacje (rotacje i translacje) dla wszystkich shape'ów
    zgodnie z istniejącą tabelą transforms_table, korzystając z funkcji
    apply_transform_to_shape().
    """
    if not shapes or not transforms_table:
        print("⚠️ Brak shape'ów lub tabeli transformacji.")
        return shapes

    if len(shapes) != len(transforms_table):
        print("⚠️ Liczba shape'ów i transformacji się nie zgadza.")
        return shapes


    transformed = []
    for i, shape in enumerate(shapes):
        new_shape = apply_transform_to_shape(shape, transforms_table[i])
        transformed.append(new_shape)

    print(f"✅ Zastosowano transformacje do {len(transformed)} brył.")
    return transformed