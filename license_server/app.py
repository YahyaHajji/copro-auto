import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent / "src"))

from license_server.app import create_app


app = create_app()
