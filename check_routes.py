
import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend', 'app'))

from qualityfoundry.main import app
from fastapi.routing import APIRoute

print("Registered Routes:")
for route in app.routes:
    if isinstance(route, APIRoute):
        print(f"{route.methods} {route.path}")
