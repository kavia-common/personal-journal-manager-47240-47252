import json
import os

from src.api.main import app

# Usage:
#   python -m src.api.generate_openapi
# Writes the current app.openapi() to interfaces/openapi.json for interface discovery.

# Get the OpenAPI schema
openapi_schema = app.openapi()

# Write to file
output_dir = "interfaces"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "openapi.json")

with open(output_path, "w") as f:
    json.dump(openapi_schema, f, indent=2)
