import numpy as np
import exiftool
from PIL import Image, UnidentifiedImageError

import os
import shutil
import uuid
import json
import zipfile

import zipfile

exiftool_location = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'exiftool',
                                 'exiftool')
print("Exiftool location: " + exiftool_location)
bezels_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../static/bezels/devices")
bezel_metadata_fp = os.path.join(bezels_folder, "device_bezels.json")


def create_new_folder(local_dir):
    newpath = local_dir
    if not os.path.exists(newpath):
        os.makedirs(newpath)
    return newpath


def delete_bezel_metadata():
    if os.path.exists(bezel_metadata_fp):
        os.remove(bezel_metadata_fp)
    metadata = get_bezel_metadata()


def get_bezel_metadata():
    bezel_metadata = None
    try:
        bezel_metadata = json.load(open(bezel_metadata_fp, ))
    except:
        print("error attempting to load JSON")

    if bezel_metadata is None:
        bezel_metadata = {}

        for root, dirs, files in os.walk(bezels_folder):
            for name in files:
                if name.startswith("."):
                    continue
                fk = str(uuid.uuid1())
                fp = os.path.join(root, name)
                if fk not in bezel_metadata:
                    bim = None
                    try:
                        bim = Image.open(fp)
                    except UnidentifiedImageError:
                        print("UnidentifiedImageError: " + fp)
                    if bim is not None:
                        bezel_metadata[fk] = {}
                        bezel_metadata[fk]["file"] = fp
                        bezel_metadata[fk]["size"] = bim.size
                        im_data = np.asarray(bim)
                        # To find the four corners of the screen area, to start with
                        # let's assume it's a rectangle, and that the middle pixel
                        # in the image is going to be screen. That means...
                        half_width = round(bim.size[0] / 2)
                        half_height = round(bim.size[1] / 2)
                        # ...the pixel array[half_height, half_width] should have alpha=0
                        # and if it DOESN'T we've messed up and the process needs to fail.
                        if im_data[half_height, half_width][3] != 0:
                            print("Alpha of middle pixel isn't 0. Moving on...")
                            continue
                        # From the middle pixel, we can check in each direction until we
                        # hit a pixel with alpha = 255. This will give us the min and max
                        # in each direction, from which we can get the x, y of each corner
                        # of the screen.
                        # 1. The MIN x value
                        min_x = half_width
                        while im_data[half_height][min_x - 1][3] != 255:
                            min_x = min_x - 1
                        # 2. The MAX x value
                        max_x = half_width
                        while im_data[half_height][max_x + 1][3] != 255:
                            max_x = max_x + 1
                        # 3. The MIN y value
                        min_y = half_height
                        while im_data[min_y - 1][half_width][3] != 255:
                            min_y = min_y - 1
                        # 4. The MAX y value
                        max_y = half_height
                        while im_data[max_y + 1][half_width][3] != 255:
                            max_y = max_y + 1
                        bezel_metadata[fk]["top_left"] = (min_x, min_y)
                        bezel_metadata[fk]["top_right"] = (max_x, min_y)
                        bezel_metadata[fk]["bottom_left"] = (min_x, max_y)
                        bezel_metadata[fk]["bottom_right"] = (max_x, max_y)
                        bezel_metadata[fk]["screen_width"] = max_x - min_x + 1
                        bezel_metadata[fk]["screen_height"] = max_y - min_y + 1
                        bezel_metadata[fk]["portrait"] = bezel_metadata[fk]["screen_height"] > \
                                                         bezel_metadata[fk]["screen_width"]
                        """
                        print((max_x - min_x, max_y - min_y))
                        print(bezel_metadata[fn]["top_left"])
                        print(bezel_metadata[fn]["top_right"])
                        print(bezel_metadata[fn]["bottom_left"])
                        print(bezel_metadata[fn]["bottom_right"])
                        """

        print("saving bezels metadata file")
        print(os.path.join(bezels_folder, "device_bezels.json"))
        bezel_metadata_json = json.dumps(bezel_metadata)
        with open(bezel_metadata_fp, 'w') as json_file:
            json.dump(bezel_metadata, json_file)

    return bezel_metadata


def find_matching_device_bezels(im_size):
    bezel_metadata = get_bezel_metadata()
    portrait = im_size[0] < im_size[1]
    matching_bezels = []

    for k in bezel_metadata:
        bw = bezel_metadata[k]["screen_width"]
        bh = bezel_metadata[k]["screen_height"]
        if not portrait:
            t = bw
            bw = bh
            bh = t
        if im_size[0] == bw:
            if im_size[1] == bh:
                matching_bezels.append(bezel_metadata[k])
    return matching_bezels


def add_bezels(fp, temp_working_folder):
    print("Adding bezels...")
    im_src = Image.open(fp)
    # rotate if landscape
    landscape = im_src.size[0] > im_src.size[1]
    if landscape:
        # rotate source image to portrait and then back again at the end
        im_src = im_src.rotate(270, expand=True)

    matching_bezels = find_matching_device_bezels(im_src.size)
    created_files = []
    for b in matching_bezels:
        im_bez = Image.open(b["file"])
        im_tgt = Image.new('RGBA', im_bez.size)
        im_tgt.paste(im_src, b["top_left"])
        im_tgt.alpha_composite(im_bez)
        if landscape:
            im_tgt = im_tgt.rotate(90, expand=True)

        tgt_fn = os.path.splitext(os.path.basename(fp))[0] + "_" + \
                    os.path.splitext(os.path.basename(b["file"]))[0] + ".png"
        tgt_fp = os.path.join(temp_working_folder, tgt_fn)
        im_tgt.save(tgt_fp)
        created_files.append(tgt_fp)

    return created_files


def create_zip_file(fs, temp_working_folder):
    zfp = os.path.join(temp_working_folder, "file.zip")
    zf = zipfile.ZipFile(zfp, 'w')
    for f in fs:
        arcname = os.path.basename(f)
        zf.write(f, arcname)
    return zf.filename


def unzip_file(zfp, temp_working_folder):
    try:
        with zipfile.ZipFile(zfp, 'r') as zipObj:
            # Extract all the contents of zip file in current directory
            zextp = os.path.join(temp_working_folder, "extracted_zip")
            zipObj.extractall(zextp)
            fs = []
            for root, dirs, files in os.walk(zextp):
                for name in files:
                    if not name.startswith("."):
                        fs.append(os.path.join(root, name))
            return fs
    except zipfile.BadZipfile:
        print("Exception: BadZipFile")
        return None


if __name__ == "__main__":
    pass
