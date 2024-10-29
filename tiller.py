from typing import List
import laspy
import os
import numpy as np
import tempfile
import shutil
import laspy
import os
import numpy as np
import tempfile
import shutil
from plyfile import PlyData, PlyElement

def tile_las_into_plys(las_file_path, tile_size_in_meters = 100, chunk_size = 1_000_000, output_dir="tiles_output") -> List[str]:
    if os.path.exists(output_dir):
        shutil.rmtree(output_dir, ignore_errors=True)

    temp_dir = os.path.join(output_dir, "tmp")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with laspy.open(las_file_path) as f:
        header = f.header
        min_x, max_x = header.min[0], header.max[0]
        min_y, max_y = header.min[1], header.max[1]
        min_z, max_z = header.min[2], header.max[2]

        tile_chunk_files = {}  # Mapping from tile keys to list of temporary file paths
        chunk_counter = 0

        for points in f.chunk_iterator(chunk_size):
            xs = points.x - min_x
            ys = points.y - min_y
            zs = points.z - min_z

            has_color = 'red' in points.point_format.extra_dimension_names
            if has_color:
                reds = points.red
                greens = points.green
                blues = points.blue

                # Convert colors from 16-bit to 8-bit by shifting
                reds = (reds >> 8).astype(np.uint8)
                greens = (greens >> 8).astype(np.uint8)
                blues = (blues >> 8).astype(np.uint8)

            # Compute tile indices for all points in the chunk
            tile_xs = (xs / tile_size_in_meters).astype(int)
            tile_ys = (ys / tile_size_in_meters).astype(int)
            tile_keys = list(zip(tile_xs, tile_ys))

            # Group points by tile
            tile_point_indices = {}
            for idx, tile_key in enumerate(tile_keys):
                if tile_key not in tile_point_indices:
                    tile_point_indices[tile_key] = []
                tile_point_indices[tile_key].append(idx)

            # For each tile, write the points to a temporary PLY file
            for tile_key, indices in tile_point_indices.items():
                tile_x, tile_y = tile_key
                # Create a temporary PLY file for this tile and chunk
                temp_file_path = os.path.join(temp_dir, f"tile_{tile_x}_{tile_y}_chunk_{chunk_counter}.ply")
                if tile_key not in tile_chunk_files:
                    tile_chunk_files[tile_key] = []
                tile_chunk_files[tile_key].append(temp_file_path)

                # Get the points corresponding to these indices
                x_subset = xs[indices]
                y_subset = ys[indices]
                z_subset = zs[indices]


                if has_color:
                    reds_subset = reds[indices]
                    greens_subset = greens[indices]
                    blues_subset = blues[indices]
                else:
                    reds_subset = np.ones(len(x_subset), dtype=np.uint8)
                    greens_subset = np.zeros(len(x_subset), dtype=np.uint8)
                    blues_subset = np.zeros(len(x_subset), dtype=np.uint8)

                # Create numpy structured array for PLY data with colors
                vertex = np.array(
                    list(zip(x_subset, y_subset, z_subset, reds_subset, greens_subset, blues_subset)),
                    dtype=[('x', 'f4'), ('y', 'f4'), ('z', 'f4'),
                            ('red', 'u1'), ('green', 'u1'), ('blue', 'u1')]
                )
               
                # Create PLY element
                ply_el = PlyElement.describe(vertex, 'vertex')
                # Write PLY file in binary format

                with open(temp_file_path, 'wb') as f:
                    PlyData([ply_el], text=False).write(f)

            chunk_counter += 1

    result = []

    # Write final PLY files for each tile
    for tile_key, temp_file_paths in tile_chunk_files.items():
        tile_x, tile_y = tile_key
        all_vertex_data = []
        for temp_file_path in temp_file_paths:
            with open(temp_file_path, 'rb') as f:
                plydata = PlyData.read(f)
                vertex_data = plydata['vertex'].data
                all_vertex_data.append(vertex_data)

        # Concatenate all vertex data
        if all_vertex_data:
            all_vertex_data = np.concatenate(all_vertex_data)

            # Create PLY element
            ply_el = PlyElement.describe(all_vertex_data, 'vertex')

            # Output PLY file path
            output_file_path = os.path.join(output_dir, f"tile_{tile_x}_{tile_y}.ply")

            # Write PLY file
            with open(output_file_path, 'wb') as f:
                PlyData([ply_el], text=False).write(f)

            result.append(output_file_path)


    # Clean up temporary directory
    shutil.rmtree(temp_dir, ignore_errors=True)

    return result

if __name__ == "__main__":
    filepath = "./dataset.las"
    results = tile_las_into_plys(filepath)
    print("Results: ", results)
