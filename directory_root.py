import sys
import os

# Get the absolute path to the root directory
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the root directory to sys.path
sys.path.append(ROOT_DIR)

# Now you can import modules from the root directory
