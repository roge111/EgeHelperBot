import os
import sys
from pathlib import Path

file_path = Path(__file__).resolve()
root_path = file_path.parent.parent

print(root_path)