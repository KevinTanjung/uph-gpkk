# =========================================================
# SEMANTIC BIM-STYLE BUILDING GENERATOR
# - Separate Mesh Nodes (Slabs, Columns, Beams, Core, Walls, Spatial Zones)
# - Semantic Tagging via node.extras
# - 2 LOD Levels (LOD0 full grid 5x5, LOD1 reduced grid 3x3)
# - Structure vs Spatial separation ready
# =========================================================

import json, base64, struct, math
from pathlib import Path

# ---------------- PARAMETERS ----------------
floors = 5
floor_height = 3.5
building_width = 20
grid_L0 = 5
grid_L1 = 3

column_size = 0.4
beam_height = 0.5
beam_width = 0.4
slab_thickness = 0.3
core_size = 4
wall_thickness = 0.3

# ---------------- GEOMETRY HELPERS ----------------
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

# ---------------- MESH BUILDER ----------------
def build_structure(grid_size):
    spacing = building_width/(grid_size-1)
    slabs_v, slabs_i = [], []
    cols_v, cols_i = [], []
    beams_v, beams_i = [], []
    spatial_v, spatial_i = [], []
    core_v, core_i = [], []
    walls_v, walls_i = [], []

    def add(v,i,store_v,store_i):
        offset=len(store_v)
        store_v.extend(v)
        store_i.extend([idx+offset for idx in i])

    for f in range(floors):
        y=f*floor_height

        # Slab
        v,i=create_box(building_width,slab_thickness,building_width,0,y,0)
        add(v,i,slabs_v,slabs_i)

        # Spatial Zone (transparent volume per floor)
        v,i=create_box(building_width*0.9,floor_height*0.8,
                       building_width*0.9,0,y+floor_height/2,0)
        add(v,i,spatial_v,spatial_i)

        if f < floors-1:
            # Columns
            for gx in range(grid_size):
                for gz in range(grid_size):
                    x=-building_width/2+gx*spacing
                    z=-building_width/2+gz*spacing
                    v,i=create_box(column_size,floor_height,column_size,
                                   x,y+floor_height/2,z)
                    add(v,i,cols_v,cols_i)

            # Beams
            for gz in range(grid_size):
                z=-building_width/2+gz*spacing
                for gx in range(grid_size-1):
                    xs=-building_width/2+gx*spacing
                    xe=xs+spacing
                    mx=(xs+xe)/2
                    v,i=create_box(spacing,beam_height,beam_width,
                                   mx,y+floor_height-beam_height/2,z)
                    add(v,i,beams_v,beams_i)

    # Core
    for f in range(floors-1):
        y=f*floor_height+floor_height/2
        v,i=create_box(core_size,floor_height,core_size,0,y,0)
        add(v,i,core_v,core_i)

    # Shear Wall
    for f in range(floors-1):
        y=f*floor_height+floor_height/2
        v,i=create_box(wall_thickness,floor_height,building_width,
                       -building_width/2,y,0)
        add(v,i,walls_v,walls_i)

    return {
        "Slabs":(slabs_v,slabs_i,"structure"),
        "Columns":(cols_v,cols_i,"structure"),
        "Beams":(beams_v,beams_i,"structure"),
        "Core":(core_v,core_i,"structure"),
        "Walls":(walls_v,walls_i,"structure"),
        "SpatialZones":(spatial_v,spatial_i,"spatial")
    }

# ---------------- BUILD LOD0 + LOD1 ----------------
lod0 = build_structure(grid_L0)
lod1 = build_structure(grid_L1)

# ---------------- GLTF CONSTRUCTION ----------------
all_buffer = b""
bufferViews=[]
accessors=[]
meshes=[]
nodes=[]
node_index=0

def append_mesh(name,data,lod_level):
    global all_buffer,node_index
    verts,inds,semantic=data
    normals=compute_normals(verts,inds)

    v_bytes=b''.join([struct.pack('<3f',*v) for v in verts])
    n_bytes=b''.join([struct.pack('<3f',*n) for n in normals])
    i_bytes=b''.join([struct.pack('<I',i) for i in inds])

    offset_v=len(all_buffer)
    all_buffer+=v_bytes
    offset_n=len(all_buffer)
    all_buffer+=n_bytes
    offset_i=len(all_buffer)
    all_buffer+=i_bytes

    bv_v=len(bufferViews); bufferViews.append({"buffer":0,"byteOffset":offset_v,"byteLength":len(v_bytes)})
    bv_n=len(bufferViews); bufferViews.append({"buffer":0,"byteOffset":offset_n,"byteLength":len(n_bytes)})
    bv_i=len(bufferViews); bufferViews.append({"buffer":0,"byteOffset":offset_i,"byteLength":len(i_bytes)})

    acc_v=len(accessors); accessors.append({"bufferView":bv_v,"componentType":5126,"count":len(verts),"type":"VEC3"})
    acc_n=len(accessors); accessors.append({"bufferView":bv_n,"componentType":5126,"count":len(normals),"type":"VEC3"})
    acc_i=len(accessors); accessors.append({"bufferView":bv_i,"componentType":5125,"count":len(inds),"type":"SCALAR"})

    meshes.append({"primitives":[{"attributes":{"POSITION":acc_v,"NORMAL":acc_n},"indices":acc_i}]})
    nodes.append({
        "mesh":len(meshes)-1,
        "name":f"{name}_LOD{lod_level}",
        "extras":{"semantic":semantic,"lod":lod_level}
    })

for name,data in lod0.items():
    append_mesh(name,data,0)

for name,data in lod1.items():
    append_mesh(name,data,1)

encoded=base64.b64encode(all_buffer).decode()

gltf={
"asset":{"version":"2.0"},
"buffers":[{"uri":f"data:application/octet-stream;base64,{encoded}","byteLength":len(all_buffer)}],
"bufferViews":bufferViews,
"accessors":accessors,
"meshes":meshes,
"nodes":nodes,
"scenes":[{"nodes":list(range(len(nodes)))}],
"scene":0
}

path=Path("./model_v3.gltf")
with open(path,"w") as f:
    json.dump(gltf,f)

path
