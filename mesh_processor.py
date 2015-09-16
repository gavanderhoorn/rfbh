# Copyright 2014-2015 G.A. vd. Hoorn
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys
import time
import math
import copy
import argparse


import bpy
import mathutils



# default values for arg parse: directory locations (all relative to base dir)
DEF_DIR_STL_IN='stl-orig'
DEF_DIR_STL_OUT='stl'
DEF_DIR_DAE_OUT='dae'
DEF_DIR_BLEND_OUT='blend'





class MeshOp(object):
    def __init__(self, axis, val):
        self.axis = axis
        self.val = val

    def apply(self, obj):
        return mathutils.Matrix()

class TranslateOp(MeshOp):
    def __init__(self, axis, val):
        super(TranslateOp, self).__init__(axis, val)

    def apply(self, obj):
        super(TranslateOp, self).apply(obj)
        vec = [0, 0, 0]
        # TODO: check
        vec[ord(self.axis) - ord('x')] = self.val
        mat = mathutils.Matrix.Translation(tuple(vec))
        trans, _, _ = mat.decompose()
        obj.location.xyz += trans
        return mat

    def __str__(self):
        return 't%c:%.4f' % (self.axis, self.val)

    def __repr__(self):
        return self.__str__()

class RotateOp(MeshOp):
    def __init__(self, axis, val):
        """
        Note: val must be an angle in degrees
        """
        super(RotateOp, self).__init__(axis, val)

    def apply(self, obj):
        super(RotateOp, self).apply(obj)
        mat = mathutils.Matrix.Rotation(
            math.radians(self.val), 4, self.axis.upper())
        old_mode = obj.rotation_mode
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion *= mat.to_quaternion()
        obj.rotation_mode = old_mode
        return mat

    def __str__(self):
        return 'r%c:%.4f' % (self.axis, self.val)

    def __repr__(self):
        return self.__str__()









def load_link_info_ini(fname):
    print("Loading info from '%s'" % fname)

    ops=[]

    import configparser
    cfg = configparser.ConfigParser()
    cfg.read(fname)

    if not cfg.has_section('model'):
        sys.stderr.write("No 'model' section in config file. Cannot continue\n")
        return ops

    if not cfg.has_section('ops'):
        sys.stderr.write("WARN: no 'ops' section, input meshes will only be converted\n")
        return ops

    model_links = cfg.get('model', 'chain').split(',')
    print("%d links in model" % len(model_links))

    for link in model_links:
        if cfg.has_option('ops', link):

            link_ops = []

            op_string = cfg.get('ops', link)
            if len(op_string) == 0:
                sys.stdout.write("No ops found for %s\n" % link)
                continue

            op_strs = op_string.split(';')
            print("%d op(s) for '%s'" % (len(op_strs), link))

            for op_str in op_strs:
                if len(op_str) < 3:
                    sys.stderr.write("op-spec too short, need at least 3 "
                        "chars, got %d. Ignoring op '%s'\n" % (len(op_str),
                            op_str))
                    continue

                # tx0.123
                opop = op_str[:2]
                opval = op_str[2:]

                # 'tx' / 'ry'
                opchar = opop[0]
                opaxis = opop[1]
                if opchar == 't':
                    op_class = TranslateOp
                elif opchar == 'r':
                    op_class = RotateOp

                op_inst = op_class(opaxis, float(opval))
                link_ops.append(op_inst)

            #print (link_ops)
            ops.append([link, link_ops])

    #[['link_1', [op1, op2, ]], ['link_2', [..]], ..]
    return ops


def select_named_object(name):
    bpy.data.objects[name].select = True


def remove_named_object(name):
    """
    Note: this will throw if the obj does not exist
    """
    # make sure we are in obj mode
    #oldMode = bpy.context.mode
    #bpy.ops.object.mode_set(mode='OBJECT')

    # remove
    select_named_object(name)
    bpy.ops.object.delete()

    # return to whatever mode we were in
    #bpy.ops.object.mode_set(mode=oldMode)


def blenderfy_name(name):
    # note: title() CamelCases things
    return name.replace('_', ' ').title()


def save_blend(filename, overwrite=True):
    if os.path.exists(filename) and overwrite:
        os.remove(filename)
    bpy.ops.wm.save_mainfile(filepath=filename, check_existing=False)

def export_collada(filename, overwrite=True):
    bpy.ops.wm.collada_export(filepath=filename)

def export_stl(filename, overwrite=True):
    bpy.ops.export_mesh.stl(filepath=filename)




def main():
    print ("")

    argv = sys.argv
    if "--" not in argv:
        argv = []
    else:
        argv = argv[argv.index("--") + 1:]

    usage_text = "Run blender in background mode with this script:" + os.linesep + os.linesep + \
    "  blender -b --factory-startup -P " + os.path.basename(__file__) + " -- [options]"

    parser = argparse.ArgumentParser(description=usage_text,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-v', '--verbose', action='store_true',
                        dest='verbose', help='Be verbose')
    parser.add_argument('--src-stl', type=str, metavar='PATH',
        dest='src_stl', default=DEF_DIR_STL_IN,
        help="Directory containing the source STLs "
             "(default: '<base_dir>\\%(default)s')")
    parser.add_argument('--dst-stl', type=str, metavar='PATH',
        dest='dst_stl', default=DEF_DIR_STL_OUT,
        help="Directory where output STLs should be written to "
             "(default: '<base_dir>\\%(default)s')")
    parser.add_argument('--dst-dae', type=str, metavar='PATH',
        dest='dst_dae', default=DEF_DIR_DAE_OUT,
        help="Directory where Collada files should be written to "
             "(default: '<base_dir>\\%(default)s')")
    parser.add_argument('--dst-blend', type=str, metavar='PATH',
        dest='dst_blend', default=DEF_DIR_BLEND_OUT,
        help="Directory where Blender files should be written to "
             "(default: '<base_dir>\\%(default)s')")
    parser.add_argument('base_dir', type=str, metavar='BASE_DIR',
        help="Base directory. All other (default) paths will be relative to this)")
    parser.add_argument('link_info', type=str, metavar='LINK_INFO',
        help="File (ini) defining chain and ops")

    args = parser.parse_args(argv)

    if not argv:
        parser.print_help()
        return


    dir_base       = os.path.normpath(os.path.realpath(args.base_dir))
    dir_stl_src    = os.path.normpath(os.path.join(dir_base, args.src_stl))
    dir_stl_dst    = os.path.normpath(os.path.join(dir_base, args.dst_stl))
    dir_dae_dst    = os.path.normpath(os.path.join(dir_base, args.dst_dae))
    dir_blend_dst  = os.path.normpath(os.path.join(dir_base, args.dst_blend))
    file_mesh_ops  = os.path.normpath(os.path.realpath(args.link_info))


    print("Run config:")
    print("  base dir     : %s" % dir_base)
    print("  stl input    : %s" % dir_stl_src)
    print("  stl output   : %s" % dir_stl_dst)
    print("  dae output   : %s" % dir_dae_dst)
    print("  Blend output : %s" % dir_blend_dst)
    print("")

    print("  mesh ops     : %s" % file_mesh_ops)
    print("")



    # remove cube if it's there
    # TODO: this will most likely crash everything if it isn't
    remove_named_object('Cube')


    links_ops = load_link_info_ini(file_mesh_ops)
    #print (links_ops)
    print("Loaded ops for %d links" % len(links_ops))


    # op accumulator
    ops_accum = []

    for link_ops in links_ops:
        # TODO: can we get this from blender somehow?
        imported_mesh_name = blenderfy_name(link_ops[0])
        print("Processing '%s' (as '%s')" % (link_ops[0], imported_mesh_name))


        # import STL with same name
        sys.stdout.write("Importing .. ")
        # py.ops.import_mesh.stl(filepath="", axis_forward='Y', axis_up='Z', filter_glob="*.stl", files=[], directory="", global_scale=1, use_scene_unit=True, use_facet_normal=False)
        mesh_stl_path = os.path.join(dir_stl_src, '%s.stl' % link_ops[0])
        bpy.ops.import_mesh.stl(filepath=mesh_stl_path)


        # make sure just imported object is selected
        select_named_object(imported_mesh_name)
        obj = bpy.context.active_object


        # transform mesh to fix origin
        print("Fixing up mesh pose")

        # apply all ops: from base to tip of chain
        ops_accum.extend(link_ops[1])
        for op in ops_accum:
            op.apply(obj)


        # set origin to 3d cursor
        print("Fixing up mesh origin")
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')


        # save as Blend
        output_name_blend = os.path.join(dir_blend_dst, '%s.blend' % link_ops[0])
        print("Saving blend file (%s)" % output_name_blend)
        save_blend(output_name_blend)


        # export mesh/scene to Collada
        #   bpy.ops.wm.collada_import(filepath="")
        #   http://www.blender.org/api/blender_python_api_2_64_release/bpy.ops.wm.html#bpy.ops.wm.collada_export
        output_name_dae = os.path.join(dir_dae_dst, '%s.dae' % link_ops[0])
        print("Export mesh to Collada (%s)" % output_name_dae)
        export_collada(output_name_dae)


        # export mesh/scene to STL
        #   bpy.ops.export_mesh.stl(filepath="", check_existing=True, axis_forward='Y', axis_up='Z', filter_glob="*.stl", global_scale=1, use_scene_unit=False, ascii=False, use_mesh_modifiers=True)
        #   https://www.blender.org/api/blender_python_api_2_75_release/bpy.ops.export_mesh.html
        output_name_stl = os.path.join(dir_stl_dst, '%s.stl' % link_ops[0])
        print("Export mesh to STL (%s)" % output_name_stl)
        export_stl(output_name_stl)


        # remove mesh
        print("Removing '%s' from scene" % imported_mesh_name)
        remove_named_object(imported_mesh_name)


        #time.sleep(1.0)
        print("\n\n")




if __name__ == "__main__":
    main()
