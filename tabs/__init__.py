"""Tabs for the STEP viewer application."""

from .manual_control_tab import ManualControlTab
from .visibility_tab import VisibilityTab
from .axis_control_tab import AxisControlTab
from .forward_kinematics_tab import ForwardKinematicsTab
from .inverse_kinematics_tab import InverseKinematicsTab

__all__ = [
    "ManualControlTab",
    "VisibilityTab",
    "AxisControlTab",
    "ForwardKinematicsTab",
    "InverseKinematicsTab",
]
