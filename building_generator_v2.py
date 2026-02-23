# =========================================================
# ADVANCED STRUCTURE (Corrected Version - No LOD corruption)
# =========================================================

import json, base64, struct, math
from pathlib import Path

# ---------------- Parameters ----------------
floors = 5
floor_height = 3.5
building_width = 20
grid_size = 5
column_spacing = building_width / (grid_size - 1)

column_size = 0.4
beam_height = 0.5
beam_width = 0.4
slab_thickness = 0.3
brace_thickness = 0.2
core_size = 4
wall_thickness = 0.3

# ---------------- Geometry Helpers ----------------
def create_box(w, h, d, tx=0, ty=0, tz=0):
    hw, hh, hd = w/2, h/2, d/2
    verts = [
        (-hw,-hh, hd),( hw,-hh, hd),( hw, hh, hd),(-hw, hh, hd),
        (-hw,-hh,-hd),( hw,-hh,-hd),( hw, hh,-hd),(-hw, hh,-hd)
    ]
    verts = [(x+tx,y+ty,z+tz) for x,y,z in verts]
    indices = [
        0,1,2,2,3,0,
        1,5,6,6,2,1,
        5,4,7,7,6,5,
        4,0,3,3,7,4,
        3,2,6,6,7,3,
        4,5,1,1,0,4
    ]
    return verts, indices

def compute_normals(vertices, indices):
    normals = [[0,0,0] for _ in vertices]
    for i in range(0,len(indices),3):
        i0,i1,i2 = indices[i:i+3]
        v0,v1,v2 = vertices[i0],vertices[i1],vertices[i2]
        ux,uy,uz = [v1[j]-v0[j] for j in range(3)]
        vx,vy,vz = [v2[j]-v0[j] for j in range(3)]
        nx = uy*vz - uz*vy
        ny = uz*vx - ux*vz
        nz = ux*vy - uy*vx
        for idx in (i0,i1,i2):
            normals[idx][0]+=nx
            normals[idx][1]+=ny
            normals[idx][2]+=nz
    out=[]
    for n in normals:
        l=math.sqrt(n[0]**2+n[1]**2+n[2]**2)+1e-6
        out.append((n[0]/l,n[1]/l,n[2]/l))
    return out

# ---------------- Build Geometry ----------------
all_vertices=[]
all_indices=[]
offset=0

def add_mesh(v,i):
    global offset
    all_vertices.extend(v)
    all_indices.extend([idx+offset for idx in i])
    offset+=len(v)

for f in range(floors):
    y=f*floor_height

    # Slab
    v,i=create_box(building_width,slab_thickness,building_width,0,y,0)
    add_mesh(v,i)

    if f < floors-1:

        # Columns
        for gx in range(grid_size):
            for gz in range(grid_size):
                x=-building_width/2+gx*column_spacing
                z=-building_width/2+gz*column_spacing
                v,i=create_box(column_size,floor_height,column_size,
                               x,y+floor_height/2,z)
                add_mesh(v,i)

        # Beams X
        for gz in range(grid_size):
            z=-building_width/2+gz*column_spacing
            for gx in range(grid_size-1):
                xs=-building_width/2+gx*column_spacing
                xe=xs+column_spacing
                mx=(xs+xe)/2
                v,i=create_box(column_spacing,beam_height,beam_width,
                               mx,y+floor_height-beam_height/2,z)
                add_mesh(v,i)

        # Beams Z
        for gx in range(grid_size):
            x=-building_width/2+gx*column_spacing
            for gz in range(grid_size-1):
                zs=-building_width/2+gz*column_spacing
                ze=zs+column_spacing
                mz=(zs+ze)/2
                v,i=create_box(beam_width,beam_height,column_spacing,
                               x,y+floor_height-beam_height/2,mz)
                add_mesh(v,i)

        # Diagonal Bracing
        x=-building_width/2+column_spacing/2
        z=-building_width/2+column_spacing/2
        v,i=create_box(brace_thickness,floor_height,
                       brace_thickness,x,y+floor_height/2,z)
        add_mesh(v,i)

# Shear Walls
for f in range(floors-1):
    y=f*floor_height+floor_height/2
    v,i=create_box(wall_thickness,floor_height,building_width,
                   -building_width/2,y,0)
    add_mesh(v,i)

# Core
for f in range(floors-1):
    y=f*floor_height+floor_height/2
    v,i=create_box(core_size,floor_height,core_size,0,y,0)
    add_mesh(v,i)

# ---------------- Normals ----------------
normals=compute_normals(all_vertices,all_indices)

# ---------------- Binary ----------------
vertex_bytes=b''.join([struct.pack('<3f',*v) for v in all_vertices])
normal_bytes=b''.join([struct.pack('<3f',*n) for n in normals])
index_bytes=b''.join([struct.pack('<I',i) for i in all_indices])
combined=vertex_bytes+normal_bytes+index_bytes
encoded=base64.b64encode(combined).decode()

# ---------------- glTF ----------------
gltf={
"asset":{"version":"2.0"},
"buffers":[{
"uri":f"data:application/octet-stream;base64,{encoded}",
"byteLength":len(combined)
}],
"bufferViews":[
{"buffer":0,"byteOffset":0,"byteLength":len(vertex_bytes),"target":34962},
{"buffer":0,"byteOffset":len(vertex_bytes),"byteLength":len(normal_bytes),"target":34962},
{"buffer":0,"byteOffset":len(vertex_bytes)+len(normal_bytes),
 "byteLength":len(index_bytes),"target":34963}
],
"accessors":[
{"bufferView":0,"componentType":5126,"count":len(all_vertices),"type":"VEC3"},
{"bufferView":1,"componentType":5126,"count":len(normals),"type":"VEC3"},
{"bufferView":2,"componentType":5125,"count":len(all_indices),"type":"SCALAR"}
],
"materials":[{
"pbrMetallicRoughness":{
"baseColorFactor":[0.75,0.75,0.8,1],
"metallicFactor":0.05,
"roughnessFactor":0.9
}
}],
"meshes":[{
"primitives":[{
"attributes":{"POSITION":0,"NORMAL":1},
"indices":2,
"material":0
}]
}],
"nodes":[{"mesh":0}],
"scenes":[{"nodes":[0]}],
"scene":0
}

path=Path("./models_v2.gltf")
with open(path,"w") as f:
    json.dump(gltf,f)

path
