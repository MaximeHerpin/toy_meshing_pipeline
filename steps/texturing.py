import shutil
from typing import List
import open3d as o3d
import numpy as np
import os
from PIL import Image
from tqdm import tqdm

# Replace these lists with your actual file paths
pointcloud_files = ['pointcloud1.ply', 'pointcloud2.ply']
mesh_files = ['mesh1.ply', 'mesh2.ply']

def texture_mesh_with_pcd(pcd_filepath, mesh_filepath, output_directory, texture_resolution) -> str:
    point_cloud = o3d.io.read_point_cloud(pcd_filepath)
    mesh = o3d.io.read_triangle_mesh(mesh_filepath)

    # Get mesh vertices and compute bounds
    vertices = np.asarray(mesh.vertices)
    x_min, y_min = vertices[:, 0].min(), vertices[:, 1].min()
    x_max, y_max = vertices[:, 0].max(), vertices[:, 1].max()
    
    # Compute UV coordinates based on normalized XY coordinates
    uvs = np.zeros((vertices.shape[0], 2))
    uvs[:, 0] = (vertices[:, 0] - x_min) / (x_max - x_min)  # U coordinate
    uvs[:, 1] = (vertices[:, 1] - y_min) / (y_max - y_min)  # V coordinate
    
    # Assign UVs to mesh
    triangles = np.asarray(mesh.triangles)
    triangle_uv_indices = triangles.flatten()
    triangle_uvs = uvs[triangle_uv_indices]
    mesh.triangle_uvs = o3d.utility.Vector2dVector(triangle_uvs)
    
    # Set triangle material IDs
    mesh.triangle_material_ids = o3d.utility.IntVector(np.zeros(len(mesh.triangles), dtype=np.int32))
    
    # Create an empty texture image
    texture_image = np.zeros((texture_resolution, texture_resolution, 3), dtype=np.uint8)
    
    # Get point cloud points and colors
    pc_points = np.asarray(point_cloud.points)
    if point_cloud.has_colors():
        pc_colors = np.asarray(point_cloud.colors)
    else:
        pc_colors = np.ones((pc_points.shape[0], 3))  # Default to white
    
    # Normalize point coordinates to UV space
    u_coords = (pc_points[:, 0] - x_min) / (x_max - x_min)
    v_coords = (pc_points[:, 1] - y_min) / (y_max - y_min)
    
    # Map UV coordinates to texture pixel indices
    pixel_x = (u_coords * (texture_resolution - 1)).astype(int)
    pixel_y = (v_coords * (texture_resolution - 1)).astype(int)
    pixel_x = np.clip(pixel_x, 0, texture_resolution - 1)
    pixel_y = np.clip(pixel_y, 0, texture_resolution - 1)
    
    # Color the texture image using the point cloud data with padding
    for x, y, color in zip(pixel_x, pixel_y, pc_colors):
        texture_image[y, x] = (color * 255).astype(np.uint8)
    
    texture_image = gaussian_padding(texture_image)
    
    # Assign the texture to the mesh
    texture_image_o3d = o3d.geometry.Image(texture_image)
    mesh.textures = [texture_image_o3d]
    
    # Generate output file names
    base_name = os.path.splitext(os.path.basename(mesh_filepath))[0]
    output_mesh_filepath = os.path.join(output_directory, f'{base_name}.obj')
    output_texture_filepath = os.path.join(output_directory, f'{base_name}.png')

    Image.fromarray(texture_image).save(output_texture_filepath)
    o3d.io.write_triangle_mesh(output_mesh_filepath, mesh, write_triangle_uvs=True)

    return output_mesh_filepath
    

def gaussian_padding(image):
    mip_chain = generate_mip_chain(image)
    for mip in mip_chain:
        resized_mip = np.asarray(Image.fromarray(mip).resize((image.shape[1], image.shape[0]), Image.Resampling.NEAREST))
        mask = np.max(image, axis=2) == 0
        if not np.any(mask):
            break
        mask = np.expand_dims(mask, axis=2)
        image = image * (1 - mask) + resized_mip * mask
    return np.astype(image, np.uint8)


def generate_mip_chain(image):
    mip_chain = [image]
    
    current_level = image
    
    while current_level.shape[0] > 1 or current_level.shape[1] > 1:
        h, w = current_level.shape[:2]
        
        if h % 2 != 0:
            h -= 1
        if w % 2 != 0:
            w -= 1
        
        reduced_level = current_level[:h, :w].reshape(h // 2, 2, w // 2, 2, -1).max(axis=(1, 3))
        mip_chain.append(reduced_level)
        current_level = reduced_level
    
    return mip_chain


def texture_meshes(pcds_filepaths, meshes_filepaths, output_directory, texture_resolution=128) -> List[str]:
    if (len(pcds_filepaths) != len(meshes_filepaths)):
        raise ValueError("pointclouds must match meshes in length")
    if os.path.exists(output_directory):
        shutil.rmtree(output_directory, ignore_errors=True)
    os.makedirs(output_directory)

    print("Texturing meshes")
    results = []
    for pcd_file, mesh_file in tqdm(zip(pcds_filepaths, meshes_filepaths), total=len(pcds_filepaths)):
        results.append(texture_mesh_with_pcd(pcd_file, mesh_file, output_directory, texture_resolution=texture_resolution))
    
    return results

    
if __name__ == "__main__":
    pcd_directory = "./tiles_output"
    meshes_directory = "./meshes_output"
    output_directory = "./textured_meshes_output"
    
    all_pcd_files = [os.path.join(pcd_directory, f) for f in os.listdir(pcd_directory) if f.endswith('.ply')]
    all_mesh_files = [os.path.join(meshes_directory, f) for f in os.listdir(meshes_directory) if f.endswith('.ply')]

    pcd_files_dict = {os.path.splitext(os.path.basename(f))[0]: f for f in all_pcd_files}

    couples = []
    for mesh_file in all_mesh_files:
        base_name = os.path.splitext(os.path.basename(mesh_file))[0]
        if base_name in pcd_files_dict:
            couples.append((pcd_files_dict[base_name], mesh_file))
    
    output = texture_meshes([c[0] for c in couples], [c[1] for c in couples], output_directory, texture_resolution=128)
    print(output)
