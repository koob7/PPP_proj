"""
Funkcje i stałe do kinematyki prostej robota 6DOF (parametry DH, macierz DH, wymiary).
"""
import numpy as np
# --- Przykładowe wartości wymiarów (uzupełnij swoimi) ---
D1 = 104.0   # mm
A2 = 270.0   # mm
D4 = 300.0   # mm
D6 = 63.4    # mm

# --- Parametry geometryczne robota 
# Wszystkie jednostki w mm, kąty w radianach (do obliczeń)
ROBOT_DH_PARAMS = [
    # (a_i, alpha_i, d_i)
    (0,      np.pi/2,  D1),   # 1: d1
    (A2,     0,         0),   # 2: a2
    (0,      np.pi/2,   0),   # 3
    (0,     -np.pi/2,  D4),   # 4: d4
    (0,      np.pi/2,   0),   # 5
    (0,      0,        D6),   # 6: d6
]



# --- Funkcja generująca macierz DH dla jednego członu ---
def dh_matrix(a, alpha, d, theta):
    """Zwraca macierz transformacji DH dla podanych parametrów (radiany, mm)."""
    ca, sa = np.cos(alpha), np.sin(alpha)
    ct, st = np.cos(theta), np.sin(theta)
    return np.array([
        [ct, -st*ca,  st*sa, a*ct],
        [st,  ct*ca, -ct*sa, a*st],
        [0,      sa,     ca,    d],
        [0,       0,      0,    1]
    ])


def mat4_mul(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    """Pomnóż dwie macierze 4x4 (transformacje homogen.)

    - Akceptuje obiekty konwertowalne do tablic NumPy 4x4.
    - Zwraca A @ B (kolejno: najpierw A, potem B).
    """
    A = np.asarray(A, dtype=float)
    B = np.asarray(B, dtype=float)
    if A.shape != (4, 4) or B.shape != (4, 4):
        raise ValueError("mat4_mul: oczekiwano macierzy 4x4")
    return A @ B


def pose_from_transform(T: np.ndarray, degrees: bool = True):

    T = np.asarray(T, dtype=float)
    if T.shape != (4, 4):
        raise ValueError("pose_from_transform: oczekiwano macierzy 4x4")

    x, y, z = T[0, 3], T[1, 3], T[2, 3]
    R = T[:3, :3]

    r11, r12, r13 = R[0, 0], R[0, 1], R[0, 2]
    r21, r22, r23 = R[1, 0], R[1, 1], R[1, 2]
    r31, r32, r33 = R[2, 0], R[2, 1], R[2, 2]

    den = np.hypot(r32, r33)  # sqrt(r32^2 + r33^2)
    b = np.arctan2(-r31, den)

    # Wybór gałęzi wg obrazu (dla zakresu b)
    if np.cos(b) >= 0:  # b \in (-pi/2, pi/2)
        a_ang = np.arctan2(r21, r11)
        c_ang = np.arctan2(r32, r33)
    else:  # b \in (pi/2, 3pi/2)
        a_ang = np.arctan2(-r21, -r11)
        b = np.arctan2(-r31, -den)
        c_ang = np.arctan2(-r32, -r33)

    if degrees:
        
        a_out = np.degrees(a_ang)   #wokół osi Z
        b_out = np.degrees(b)       #wokół osi X
        c_out = np.degrees(c_ang)   #wokół osi Y
    else:
        a_out, b_out, c_out = a_ang, c_ang, b# wychodzi że x jest zamieniony z Y

    return float(x), float(y), float(z), float(a_out), float(b_out), float(c_out)
