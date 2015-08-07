#!/usr/bin/env python
'''
Get the latest gimp_spine.py script:
https://github.com/clofresh/gimp-spine

Copyright (c) 2014, Carlo Cabanilla <carlo.cabanilla@gmail.com>
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright
notice, this list of conditions and the following disclaimer in the
documentation and/or other materials provided with the distribution.

* Neither the name of the author nor the names of its contributors may be
used to endorse or promote products derived from this software without
specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS ''AS IS''
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

'''

'''
Exports layers to images and outputs a Spine JSON file
http://esotericsoftware.com/spine-json-format

Run from the GIMP menu option: File -> Export to Spine

'''

import json
import math
import os.path

import gimpfu
from gimp import pdb

def spine_export(img, active_layer, compression, dir_name, json_filename, export_visible_only, reverse_draw_order, autocrop_layers):
    ''' Plugin entry point
    '''

    orig_img = img
    orig_active_layer = pdb.gimp_image_get_active_layer(orig_img)
    img = pdb.gimp_image_duplicate(orig_img)

    # Set up the initial JSON format
    output = {
        'bones': [{'name': 'root'}],
        'slots': [],
        'skins': {'default': {}},
        'animations': {}
    }
    slots = output['slots']
    attachments = output['skins']['default']

    # Iterate through the layers, extracting their info into the JSON output
    # and saving the layers as individual images
    for layer in img.layers:
       if (layer.visible or not(export_visible_only)):
               to_save = process_layer(img, layer, slots, attachments, reverse_draw_order, autocrop_layers)
               save_layers(img, to_save, compression, dir_name)

    # Write the JSON output
    if not json_filename:
        json_filename = os.path.splitext(os.path.basename(orig_img.filename))[0]

    with open(os.path.join(dir_name, '%s.json' % json_filename), 'w') as json_file:
        json.dump(output, json_file)

    pdb.gimp_image_delete(img)
    pdb.gimp_image_set_active_layer(orig_img, orig_active_layer)

def process_layer(img, layer, slots, attachments, reverse_draw_order, autocrop_layers):
    ''' Extracts the Spine info from each layer, recursing as necessary on
        layer groups. Returns all the layers it processed in a flat list.
    '''
    processed = []

    # If this layer is a layer has sublayers, recurse into them
    if hasattr(layer, 'layers'):
        for sublayer in layer.layers:
            processed.extend(process_layer(img, sublayer, slots, attachments, reverse_draw_order, autocrop_layers))
    else:
        if autocrop_layers:
            pdb.gimp_image_set_active_layer(img, layer) # note: for some reason we need to do this before autocropping the layer.
            pdb.plug_in_autocrop_layer(img, layer)

        layer_name = layer.name

        if reverse_draw_order:
            slots.append({
                'name': layer_name,
                'bone': 'root',
                'attachment': layer_name,
            })
        else:
            slots.insert(0, {
                'name': layer_name,
                'bone': 'root',
                'attachment': layer_name,
            })
        x, y = layer.offsets

        # Compensate for GIMP using the top left as the origin, vs Spine
        # using the center.
        x += math.floor(layer.width / 2)
        y += math.floor(layer.height / 2)

        # Center the image on Spine's x origin,
        x -= math.floor(img.width / 2)

        # Compensate for GIMP's y axis going from top to bottom, vs Spine
        # going bottom to top
        y = img.height - y

        attachments[layer_name] = {layer_name: {
            'x': x,
            'y': y,
            'rotation': 0,
            'width': layer.width,
            'height': layer.height,
        }}
        processed.append(layer)

    return processed

def save_layers(img, layers, compression, dir_name):
    ''' Takes a list of layers and saves them in `dir_name` as PNGs,
        naming the files after their layer names.
    '''

    for layer in layers:
        tmp_img = pdb.gimp_image_new(img.width, img.height, img.base_type)
        tmp_layer = pdb.gimp_layer_new_from_drawable(layer, tmp_img)
        tmp_layer.name = layer.name
        tmp_img.add_layer(tmp_layer, 0)
        filename = '%s.png' % layer.name
        fullpath = os.path.join(dir_name, filename)
        tmp_img.resize_to_layers()
        pdb.file_png_save(
            tmp_img,
            tmp_img.layers[0],
            fullpath,
            filename,
            0, # interlace
            compression, # compression
            1, # bkgd
            1, # gama
            1, # offs
            1, # phys
            1 # time
        )

gimpfu.register(
    # name
    "spine-export",
    # blurb
    "Spine export",
    # help
    "Exports layers to images and outputs a Spine JSON file",
    # author
    "Carlo Cabanilla",
    # copyright
    "Carlo Cabanilla",
    # date
    "2014",
    # menupath
    "<Image>/File/Export/Export to Spine",
    # imagetypes
    "*",
    # params
    [   
        (gimpfu.PF_ADJUSTMENT, "compression", "PNG Compression level:", 0, (0, 9, 1)),
        (gimpfu.PF_DIRNAME, "dir", "Directory", "/tmp"),
        (gimpfu.PF_STRING, "json_filename", "JSON filename", ""),
        (gimpfu.PF_TOGGLE,   "export_visible_only", "Export visible layers only", True),
        (gimpfu.PF_TOGGLE,   "reverse_draw_order", "Reverse draw order", False),
        (gimpfu.PF_TOGGLE,   "autocrop_layers", "Autocrop layers", False)
    ],
    # results
    [],
    # function
    spine_export
)

gimpfu.main()
