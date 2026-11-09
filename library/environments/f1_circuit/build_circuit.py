"""Build the circuit and save blend/circuit.blend.

"C:/Program Files/Blender Foundation/Blender 5.2/blender.exe" -b --factory-startup --python library/environments/f1_circuit/build_circuit.py -- [--time day|golden|overcast|night] [--nosave]
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import circuit_blender as cb

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
mode = argv[argv.index("--time") + 1] if "--time" in argv else "day"
cb.build_circuit(mode, save="--nosave" not in argv)
