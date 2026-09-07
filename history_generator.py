import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from pipeline.topic_generator import generate_topic

if __name__ == "__main__":
    generate_topic("history")
