import shutil
import sys
import os
from typing import List, Optional, Tuple
import numpy as np
import open3d as o3d

def mesh_ply_file(ply_file, output_dir, depth: int = 8) -> Optional[Tuple[str, int]]:
    # Check if file exists
    if not os.path.isfile(ply_file):
        raise FileNotFoundError(f"File {ply_file} does not exist.")
    
    # Read point cloud
    pcd = o3d.io.read_point_cloud(ply_file)
    if pcd.is_empty():
        print(f"Point cloud {ply_file} is empty.")
        return None
    
    normals = np.zeros((len(pcd.points), 3))
    normals[:, 2] = 1.0
    pcd.normals = o3d.utility.Vector3dVector(normals)
    
    
    # Perform Poisson reconstruction
    mesh, densities = o3d.geometry.TriangleMesh.create_from_point_cloud_poisson(pcd, depth=depth)
    
    # Remove low-density vertices to clean up the mesh
    densities = np.asarray(densities)
    density_threshold = np.percentile(densities, 5)  # Remove the lowest 5% densities
    vertices_to_keep = densities > density_threshold
    mesh = mesh.select_by_index(np.where(vertices_to_keep)[0])
    mesh.remove_unreferenced_vertices()
    
    # Save the mesh
    output_file = os.path.join(output_dir, os.path.basename(ply_file))
    o3d.io.write_triangle_mesh(output_file, mesh)
    return output_file, len(mesh.triangles)

def decimate_mesh(mesh_file, target_polycount):
    mesh = o3d.io.read_triangle_mesh(mesh_file)
    mesh.simplify_quadric_decimation(target_polycount)
    o3d.io.write_triangle_mesh(mesh_file, mesh)


def mesh_point_clouds(ply_files, output_dir, max_total_polycount: int, meshing_depth:int = 7) -> List[Optional[str]]:
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)
    os.makedirs(output_dir)
    results = []
    total_polycount = 0
    for ply_file in ply_files:
        results.append(mesh_ply_file(ply_file, output_dir, depth=meshing_depth))
    
    total_polycount = sum([r[1] for r in results if r is not None])
    if total_polycount > max_total_polycount:
        print(f"Total polycount {total_polycount} exceeds maximum {max_total_polycount}. Decimating meshes.")
        for i, (mesh_file, polycount) in enumerate(results):
            if mesh_file is not None:
                contribution = polycount / total_polycount
                target_polycount = int(max_total_polycount * contribution)
                decimate_mesh(mesh_file, target_polycount)
                results[i] = (mesh_file, target_polycount)

    return [r[0] for r in results]

if __name__ == "__main__":
    plys_dir = "./tiles_output"
    output_dir = "./meshes_output"
    ply_files = [os.path.join(plys_dir, f) for f in os.listdir(plys_dir) if f.endswith('.ply')]
    results = mesh_point_clouds(ply_files, output_dir, max_total_polycount=1_000_000, meshing_depth=6)
    print(results)