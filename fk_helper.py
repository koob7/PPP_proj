"""
Funkcje i stałe do kinematyki prostej i odwrotnej robota 6DOF (parametry DH, macierz DH, wymiary).
"""
import numpy as np
# --- Przykładowe wartości wymiarów (uzupełnij swoimi) ---
D1 = 104.0   # mm (d1)
A2 = 270.0   # mm (a2)
D4 = 300.0   # mm (d4)
D6 = 63.4    # mm (d6)

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

    den = np.sqrt(r32**2 + r33**2)#????????????
    b_ang = np.arctan2(-r31, den)

    # Wybór gałęzi wg obrazu (dla zakresu b)

    a_ang = np.arctan2(r21, r11)
    c_ang = np.arctan2(r32, r33)



    if degrees:
        
        a_out = a_ang * 180 / np.pi
        b_out = b_ang * 180 / np.pi
        c_out = c_ang * 180 / np.pi
    else:
        a_out, b_out, c_out = a_ang, b_ang, c_ang

    return float(x), float(y), float(z), float(a_out), float(b_out), float(c_out) # obrót wokół ZYX


def calculate_ik(x: float, y: float, z: float, phi_in: float, beta_in: float, psi_in: float) -> tuple[float, float, float, float, float, float]:

    
    theta = [0.0] * 6
    
    # Konwersja kątów orientacji ze stopni na radiany
    phi = np.deg2rad(phi_in)
    beta = np.deg2rad(beta_in)
    psi = np.deg2rad(psi_in)

    # Macierz rotacji z kątów Eulera
    r11 = np.cos(phi) * np.sin(beta) * np.cos(psi) + np.sin(phi) * np.sin(psi)
    r21 = np.sin(phi) * np.sin(beta) * np.cos(psi) - np.cos(phi) * np.sin(psi)
    r31 = np.cos(beta) * np.cos(psi)
    
    r12 = np.cos(phi) * np.cos(beta)
    r22 = np.sin(phi) * np.cos(beta)
    r32 = -np.sin(beta)
    
    r13 = np.cos(phi) * np.sin(beta) * np.sin(psi) - np.sin(phi) * np.cos(psi)
    r23 = np.sin(phi) * np.sin(beta) * np.sin(psi) + np.cos(phi) * np.cos(psi)
    r33 = np.cos(beta) * np.sin(psi)
    
    # Pozycja nadgarstka
    Wx = x - D6 * r13
    Wy = y - D6 * r23
    Wz = z - D6 * r33
    r = np.sqrt(Wx * Wx + Wy * Wy)
    s = Wz - D1
    
    # theta[0] - pierwsza oś
    theta[0] = np.arctan2(Wy, Wx)
    
    # theta[2] - trzecia oś
    cos_theta2 = (r * r + s * s - A2 * A2 - D4 * D4) / (2 * A2 * D4)
    theta[2] = np.arctan2(-np.sqrt(1 - cos_theta2 * cos_theta2), cos_theta2)
    
    # theta[1] - druga oś
    k1 = A2 + D4 * np.cos(theta[2])
    k2 = D4 * np.sin(theta[2])
    theta[1] = np.arctan2(s, r) - np.arctan2(k2, k1)
    theta[2] += np.pi / 2
    
    # Orientacja końcówki
    ax = (r13 * np.cos(theta[0]) * np.cos(theta[1] + theta[2]) +
          r23 * np.cos(theta[1] + theta[2]) * np.sin(theta[0]) +
          r33 * np.sin(theta[1] + theta[2]))
    ay = -r23 * np.cos(theta[0]) + r13 * np.sin(theta[0])
    az = (-r33 * np.cos(theta[1] + theta[2]) +
          r13 * np.cos(theta[0]) * np.sin(theta[1] + theta[2]) +
          r23 * np.sin(theta[0]) * np.sin(theta[1] + theta[2]))
    sz = (-r32 * np.cos(theta[1] + theta[2]) +
          r12 * np.cos(theta[0]) * np.sin(theta[1] + theta[2]) +
          r22 * np.sin(theta[0]) * np.sin(theta[1] + theta[2]))
    nz = (-r31 * np.cos(theta[1] + theta[2]) +
          r11 * np.cos(theta[0]) * np.sin(theta[1] + theta[2]) +
          r21 * np.sin(theta[0]) * np.sin(theta[1] + theta[2]))
    
    epsilon = 0.1
    if abs(ax) < epsilon:
        ax += epsilon if ax >= 0 else -epsilon
    if abs(ay) < epsilon:
        ay += epsilon if ay >= 0 else -epsilon
    
    # Osie nadgarstka (theta[3], theta[4], theta[5])
    if True:  # Warunek Wz>20 - można dostosować
        theta[3] = np.arctan2(-ay, -ax)
        theta[4] = np.arctan2(-np.sqrt(ax * ax + ay * ay), az)
        theta[5] = np.arctan2(-sz, nz)
    else:
        theta[3] = np.arctan2(-ay, ax)
        theta[4] = np.arctan2(np.sqrt(ax * ax + ay * ay), az)
        theta[5] = np.arctan2(sz, -nz)

    theta[3] += np.pi / 2
    theta[4] += np.pi / 2
    theta[5] += np.pi / 2
    
    
    for i in range(6):
        theta[i] = np.degrees(theta[i])
    
    return tuple(theta)



def calculate_ik2(x: float, y: float, z: float, phi_in: float, beta_in: float, psi_in: float) -> tuple[float, float, float, float, float, float]:
    
    theta = [0.0] * 6

    phi_in += 0.001
    beta_in += 0.001
    psi_in += 0.001
    
    # Konwersja kątów orientacji ze stopni na radiany
    phi = phi_in*np.pi/180
    beta = beta_in*np.pi/180
    psi = psi_in*np.pi/180

    c_alfa, s_alfa = np.cos(phi), np.sin(phi)
    c_beta, s_beta = np.cos(beta), np.sin(beta)
    c_delta, s_delta = np.cos(psi), np.sin(psi)

    #wiersz, kolumna

    #ZYX
    r21 = c_alfa * c_beta
    r22 = c_alfa * s_beta * s_delta - c_delta * s_alfa
    r23 = s_alfa * s_delta + c_alfa * c_delta *s_beta

    r31 = c_beta * s_alfa
    r32 = c_alfa * c_delta + s_alfa * s_beta * s_delta
    r33 = c_delta * s_alfa * s_beta - c_alfa * s_delta

    r11 = -s_beta
    r12 = c_beta * s_delta
    r13 = c_beta * c_delta


    # Pozycja nadgarstka
    Wx = x - D6 * r13
    Wy = y - D6 * r23
    Wz = z - D6 * r33
    r = np.sqrt(Wx * Wx + Wy * Wy)
    s = Wz - D1



    # theta[0] - pierwsza oś
    theta[0] = np.arctan2(Wy, Wx)
    
    # theta[2] - trzecia oś
    cos_theta2 = (r * r + s * s - A2 * A2 - D4 * D4) / (2 * A2 * D4)
    theta[2] = np.arctan2(-np.sqrt(1 - cos_theta2 * cos_theta2), cos_theta2)
    
    # theta[1] - druga oś
    k1 = A2 + D4 * np.cos(theta[2])
    k2 = D4 * np.sin(theta[2])
    theta[1] = np.arctan2(s, r) - np.arctan2(k2, k1)
    theta[2] += np.pi / 2


    #nx sx ax
    #ny sy ay
    #nz sz az

    ax = r33*np.sin(theta[1]+theta[2]) + r13*np.cos(theta[1]+theta[2])*np.cos(theta[0]) + r23*np.cos(theta[1]+theta[2])*np.sin(theta[0])
    ay = r13*np.sin(theta[0]) - r23*np.cos(theta[0])
    az = r13*np.sin(theta[1] + theta[2])*np.cos(theta[0]) - r33*np.cos(theta[1] + theta[2]) + r23*np.sin(theta[1] + theta[2])*np.sin(theta[0])
    sz = r12*np.sin(theta[1] + theta[2])*np.cos(theta[0]) - r32*np.cos(theta[1] + theta[2]) + r22*np.sin(theta[1] + theta[2])*np.sin(theta[0])
    nz = r11*np.sin(theta[1] + theta[2])*np.cos(theta[0]) - r31*np.cos(theta[1] + theta[2]) + r21*np.sin(theta[1] + theta[2])*np.sin(theta[0])


    theta[3] = np.arctan2(ay,ax)
    theta[4] = np.atan2(np.sqrt(ax*ax+ay*ay),az)
    theta[5] = np.arctan2(sz, -nz)
    
    
    for i in range(6):
        theta[i] = theta[i]*180/np.pi

    return tuple(theta)