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


def apply_transform_to_shape(shape, transform: Optional[TransformType]):
    """Zastosuj rotacje i translacje do kształtu. Rotacje są względem (0,0,0)."""
    shp = shape
    if not transform:
        return shp

    rotations = transform.get("rotations", [])
    for rot in rotations:
        if not rot:
            continue
        axis = rot.get("axis")
        angle = rot.get("angle_deg")
        if axis and (angle is not None):
            ax_pnt = gp_Pnt(0, 0, 0)
            ax_dir = gp_Dir(*axis)
            ax = gp_Ax1(ax_pnt, ax_dir)
            rot_trsf = gp_Trsf()
            rot_trsf.SetRotation(ax, math.radians(float(angle)))
            shp = BRepBuilderAPI_Transform(shp, rot_trsf, True).Shape()

    tr = transform.get("translate")
    if tr:
        vec = gp_Vec(*tr)
        tr_trsf = gp_Trsf()
        tr_trsf.SetTranslation(vec)
        shp = BRepBuilderAPI_Transform(shp, tr_trsf, True).Shape()

    return shp

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