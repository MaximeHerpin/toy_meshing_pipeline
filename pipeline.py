import sys
import argparse
import os
import shutil
from steps.tilling import tile_las_into_plys
from steps.meshing import mesh_point_clouds
from steps.texturing import texture_meshes
from time import time

def process_las_file(las_filepath: str, output_directory: str, tile_size_in_meters: float = 100, points_buffer_size = 10_000_000, max_total_polycount: int = 1_000_000, meshing_depth: int = 6, texture_resolution: int = 512):
    t0 = time()
    
    tilling_output_dir = os.path.join(output_directory, "step1_tilling")
    meshes_output_dir = os.path.join(output_directory, "step2_meshing")
    textures_output_dir = os.path.join(output_directory, "step3_texturing")
    
    tiles = tile_las_into_plys(las_filepath, tile_size_in_meters, points_buffer_size, tilling_output_dir)
    tiles = [t for t in tiles if t is not None]
    print(f"split las file into {len(tiles)} tiles")

    meshes = mesh_point_clouds(tiles, meshes_output_dir, max_total_polycount, meshing_depth)
    print(f"generated {len(meshes)} meshes")

    out_glbs = texture_meshes(tiles, meshes, textures_output_dir, texture_resolution)
    print(f"textured {len(out_glbs)} meshes")
    print(f"total time: {time() - t0} seconds")
    return out_glbs

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process a LAS file into a textured mesh')
    parser.add_argument('las_file', type=str, help='The input LAS file')
    parser.add_argument('--output_dir', type=str, default="./output", help='The output directory')
    parser.add_argument('--tile_size', type=float, default=100, help='The size of the tiles to split the LAS file into')
    parser.add_argument('--points_buffer_size', type=int, default=10_000_000, help='The number of points to buffer before writing to disk')
    parser.add_argument('--max_total_polycount', type=int, default=1_000_000, help='The maximum total polycount of the output meshes')
    parser.add_argument('--meshing_depth', type=int, default=6, help='The depth of the Poisson meshing algorithm, higher values result in more detailed meshes')
    parser.add_argument('--texture_resolution', type=int, default=512, help='The resolution of the texture maps')
    args = parser.parse_args()

    results = process_las_file(args.las_file, args.output_dir, args.tile_size, args.points_buffer_size, args.max_total_polycount, args.meshing_depth, args.texture_resolution)
