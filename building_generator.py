# =========================================================
# 5-Story Full Structural Building Generator (Slabs + Columns + Beams)
# =========================================================
# - 5 floor slabs
# - Columns between floors (no columns above roof)
# - Beams along X and Z directions on each structural level
# - 5x5 column grid (25 columns per floor level)
# - Embedded buffer (no external .bin file)
#
# Output:
#   models.gltf
#
# =========================================================

import json
import base64
import struct
from pathlib import Path

# ---------- Geometry Helper ----------
def create_box(width, height, depth, tx=0, ty=0, tz=0):
    w, h, d = width/2, height/2, depth/2
    vertices = [
        (-w, -h,  d), ( w, -h,  d), ( w,  h,  d), (-w,  h,  d),
        (-w, -h, -d), ( w, -h, -d), ( w,  h, -d), (-w,  h, -d),
    ]
    vertices = [(x+tx, y+ty, z+tz) for x,y,z in vertices]

    indices = [
        0,1,2, 2,3,0,
        1,5,6, 6,2,1,
        5,4,7, 7,6,5,
        4,0,3, 3,7,4,
        3,2,6, 6,7,3,
        4,5,1, 1,0,4
    ]
    return vertices, indices


# ---------- Parameters ----------
floors = 5
floor_height = 3.5
building_width = 20
grid_size = 5
column_spacing = building_width / (grid_size - 1)

column_size = 0.4
beam_height = 0.5
beam_width = 0.4
slab_thickness = 0.3

all_vertices = []
all_indices = []
vertex_offset = 0


# ---------- Generation ----------
for f in range(floors):

    y_base = f * floor_height

    # ----- Slab -----
    v, i = create_box(building_width, slab_thickness, building_width, 0, y_base, 0)
    all_vertices.extend(v)
    all_indices.extend([idx + vertex_offset for idx in i])
    vertex_offset += len(v)

    # ----- Columns (not above last slab) -----
    if f < floors - 1:

        for gx in range(grid_size):
            for gz in range(grid_size):
                x = -building_width/2 + gx * column_spacing
                z = -building_width/2 + gz * column_spacing

                v, i = create_box(
                    column_size,
                    floor_height,
                    column_size,
                    x,
                    y_base + floor_height/2,
                    z
                )

                all_vertices.extend(v)
                all_indices.extend([idx + vertex_offset for idx in i])
                vertex_offset += len(v)

        # ----- Beams along X direction -----
        for gz in range(grid_size):
            z = -building_width/2 + gz * column_spacing
            for gx in range(grid_size - 1):
                x_start = -building_width/2 + gx * column_spacing
                x_end = x_start + column_spacing
                mid_x = (x_start + x_end) / 2

                v, i = create_box(
                    column_spacing,
                    beam_height,
                    beam_width,
                    mid_x,
                    y_base + floor_height - beam_height/2,
                    z
                )

                all_vertices.extend(v)
                all_indices.extend([idx + vertex_offset for idx in i])
                vertex_offset += len(v)

        # ----- Beams along Z direction -----
        for gx in range(grid_size):
            x = -building_width/2 + gx * column_spacing
            for gz in range(grid_size - 1):
                z_start = -building_width/2 + gz * column_spacing
                z_end = z_start + column_spacing
                mid_z = (z_start + z_end) / 2

                v, i = create_box(
                    beam_width,
                    beam_height,
                    column_spacing,
                    x,
                    y_base + floor_height - beam_height/2,
                    mid_z
                )

                all_vertices.extend(v)
                all_indices.extend([idx + vertex_offset for idx in i])
                vertex_offset += len(v)


# ---------- Convert to Binary ----------
vertex_bytes = b''.join([struct.pack('<3f', *v) for v in all_vertices])
index_bytes = b''.join([struct.pack('<I', i) for i in all_indices])  # 32-bit indices
combined = vertex_bytes + index_bytes
encoded = base64.b64encode(combined).decode('ascii')


# ---------- glTF Structure ----------
gltf = {
    "asset": {"version": "2.0"},
    "buffers": [{
        "uri": f"data:application/octet-stream;base64,{encoded}",
        "byteLength": len(combined)
    }],
    "bufferViews": [
        {"buffer": 0, "byteOffset": 0, "byteLength": len(vertex_bytes), "target": 34962},
        {"buffer": 0, "byteOffset": len(vertex_bytes), "byteLength": len(index_bytes), "target": 34963}
    ],
    "accessors": [
        {
            "bufferView": 0,
            "componentType": 5126,
            "count": len(all_vertices),
            "type": "VEC3",
            "max": [max(v[i] for v in all_vertices) for i in range(3)],
            "min": [min(v[i] for v in all_vertices) for i in range(3)]
        },
        {
            "bufferView": 1,
            "componentType": 5125,  # UNSIGNED_INT
            "count": len(all_indices),
            "type": "SCALAR"
        }
    ],
    "meshes": [{
        "primitives": [{
            "attributes": {"POSITION": 0},
            "indices": 1
        }]
    }],
    "nodes": [{"mesh": 0}],
    "scenes": [{"nodes": [0]}],
    "scene": 0
}

output_path = Path("./model.gltf")
with open(output_path, "w") as f:
    json.dump(gltf, f)

output_path
