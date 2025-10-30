from typing import Dict, Any
from typing import  List, Dict, Any

TransformType = Dict[str, Any]  # {'translate': (x,y,z), 'rotations': [{'axis': (x,y,z), 'angle_deg': float}, ...]}

# Funkcja pomocnicza do sumowania transformów
def sum_transforms(t1: Dict, t2: Dict) -> Dict:
    """Sumuje dwie transformacje: translacje (składnik po składniku) i rotacje (kąty)."""
    result = {
        'translate': (
            t1['translate'][0] + t2['translate'][0],
            t1['translate'][1] + t2['translate'][1],
            t1['translate'][2] + t2['translate'][2],
        ),
        'rotations': [
            {
                'origin': t1['rotations'][0]['origin'],
                'axis': t1['rotations'][0]['axis'],
                'angle_deg': t1['rotations'][0]['angle_deg'] + t2['rotations'][0]['angle_deg']
            },
            {
                'origin': t1['rotations'][1]['origin'],
                'axis': t1['rotations'][1]['axis'],
                'angle_deg': t1['rotations'][1]['angle_deg'] + t2['rotations'][1]['angle_deg']
            },
            {
                'origin': t1['rotations'][2]['origin'],
                'axis': t1['rotations'][2]['axis'],
                'angle_deg': t1['rotations'][2]['angle_deg'] + t2['rotations'][2]['angle_deg']
            },
        ]
    }
    return result