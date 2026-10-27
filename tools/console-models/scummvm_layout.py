"""The ScummVM card's measurements, for scummvm.py (which builds it). Plain Python: Blender's Python imports it too.

ScummVM has no hardware: it's the engine its games run on, so its card is the green S of its icon, made solid. OUTLINE
is the S's face traced from ScummVM's own icon (icons/scummvm.svg in its repository: the bright green path, its curves
flattened and the points thinned to within 0.6 of the icon's 512 units), in millimetres: x across from the S's middle
(left to right), z up from its foot, the S 100 mm tall; anticlockwise. The letter is DEPTH deep, its face's and back's
edges rounded (ROUND), its face the icon's bright green and its sides the darker green of the icon's extrusion
(COLOURS).
"""

OUTLINE = [(-4.3, 99.9), (-8.5, 99.4), (-12.5, 98.5), (-15.4, 97.6), (-19.0, 96.0), (-21.5, 94.5), (-25.9, 91.0),
           (-27.8, 89.0), (-29.5, 86.7), (-30.9, 84.2), (-32.0, 81.5), (-32.9, 78.6), (-33.3, 75.5), (-33.5, 72.2),
           (-33.3, 68.7), (-32.5, 64.5), (-31.0, 60.6), (-28.9, 57.1), (-25.9, 53.1), (-22.3, 49.5), (-17.6, 45.7),
           (-14.3, 43.5), (-1.7, 35.9), (4.1, 31.7), (5.6, 30.0), (6.5, 28.3), (6.6, 25.9), (6.1, 23.9), (5.5, 23.1),
           (4.4, 22.3), (1.6, 21.6), (-2.1, 21.6), (-6.2, 22.4), (-11.2, 24.2), (-15.9, 26.5), (-20.8, 29.7),
           (-24.4, 33.0), (-26.0, 33.4), (-26.8, 33.2), (-27.5, 32.7), (-38.0, 19.6), (-33.0, 13.6), (-28.9, 9.8),
           (-24.6, 6.6), (-20.1, 4.1), (-15.0, 2.1), (-9.5, 0.8), (-3.4, 0.1), (3.2, 0.0), (6.5, 0.3), (11.0, 1.0),
           (17.6, 2.8), (21.6, 4.5), (24.4, 6.0), (27.1, 7.8), (29.5, 9.9), (31.7, 12.2), (33.6, 14.7), (36.2, 19.5),
           (36.9, 21.6), (37.7, 25.0), (38.0, 28.7), (38.0, 32.6), (37.3, 37.4), (35.5, 42.8), (32.9, 47.5),
           (29.7, 51.6), (26.0, 55.1), (21.2, 58.8), (17.0, 61.3), (4.6, 68.1), (0.1, 71.2), (-1.4, 72.7),
           (-2.2, 74.3), (-2.4, 75.9), (-2.1, 77.4), (-0.9, 79.1), (1.1, 80.0), (4.3, 80.1), (7.8, 79.4),
           (11.4, 78.2), (15.8, 76.2), (21.5, 72.9), (25.8, 69.7), (27.4, 69.4), (28.3, 69.7), (28.9, 70.3),
           (37.5, 83.2), (33.3, 87.1), (28.9, 90.5), (24.5, 93.4), (19.9, 95.8), (15.1, 97.6), (10.0, 98.9),
           (4.6, 99.7), (-1.1, 100.0)]

DEPTH = 24.0
ROUND = 1.8
COLOURS = dict(face="#00C832", side="#006A1B")

FPS = 30
LENGTH = 150                 # 5 s
