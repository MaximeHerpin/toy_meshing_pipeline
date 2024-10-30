# toy_meshing_pipeline

converts las point cloud files into textured 3D meshes

## Assumptions
- the input point cloud is a .las file
- the input point cloud has a somewhat uniform point density
- the input point cloud is mostly a height field on the x-y plane

Texturing is done by projecting the point into the normalized x-y plane of each tile, hence the third assumption.

## Usage
```
python3 pipeline.py <input_las_file>
```

run `python3 pipeline.py --help` for more information