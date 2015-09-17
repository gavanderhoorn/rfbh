# rfbh

ROS-Fanuc-Blender helper script


## Overview

Simple Blender Python script that imports STL meshes into an empty scene, applies translations and / or rotations, then exports them again to STL, Collada and a Blender file.

This is useful when dealing with robot 3D models that have the origins of all meshes at the 'global origin' of the robot (ie: the `[0, 0, 0]` coordinate).


## Dependencies

 - Blender
 - configparser (should already be included with Blender Python)


## Typical usage

 1. Convert SolidWorks assembly to STLs (eDrawings, single STL *per part*). Filenames may be anything, but already using ROS standard `base_link`, `link_1`, etc would be good. Make note of orientation wrt global coordinate origin
 1. Use robot 'basic specifications' to figure out translations needed
 1. Define 'ops' in `ini` file (see `example.ini`). Be sure to use filenames of STLs when specifying the `chain` and under `ops`
 1. run script:

  ```
  blender -b -P \path\to\mesh_processor.py \path\to\base\dir \path\to\your\file.ini
  ```

If successful, the script should have placed the meshes in the `stl`, `dae` and `blend` subdirs of `\path\to\base\dir`.
