import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

import io
import os
import uuid
import json


def get_bezels_metadata(force_refresh=False):
    """
    Opens JSON of bezel metadata, if it exists, and returns dict of bezel metadata.
    Scans bezels folder and creates JSON if it doesn't exist.
    :return: dict of bezel metadata.
    """
    bezels_folder = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../static/bezels/devices")
    bezel_metadata_fp = os.path.join(bezels_folder, "device_bezels.json")

    if force_refresh:
        print("forced bezel metadata refresh")
        try:
            os.remove(bezel_metadata_fp)
        except:
            print("error attempting to delete JSON")

    bezels_metadata = None
    try:
        bezels_metadata = json.load(open(bezel_metadata_fp, ))
    except:
        print("error attempting to load JSON")

    if bezels_metadata is not None:
        return bezels_metadata

    bezels_metadata = {}

    for root, dirs, files in os.walk(bezels_folder):
        for name in files:
            if name.startswith("."):
                continue
            fk, _ = os.path.splitext(name)
            if fk in bezels_metadata:
                continue

            fp = os.path.join(root, name)
            bim = None
            try:
                bim = Image.open(fp)
            except UnidentifiedImageError:
                print("UnidentifiedImageError: " + fp)

            if bim is not None:
                bezel_metadata = get_bezel_metadata(fp)
                if bezel_metadata is not None:
                    bezels_metadata[fk] = bezel_metadata

    print("saving bezels metadata file")
    print(os.path.join(bezels_folder, "device_bezels.json"))
    bezel_metadata_json = json.dumps(bezels_metadata)
    with open(bezel_metadata_fp, 'w') as json_file:
        json.dump(bezels_metadata, json_file)

    return bezels_metadata


def get_bezel_metadata(filepath):
    """
    Opens bezel file, finds transparent screen section, creates and returns bezel metadata.
    :param filepath: path to bezel file
    :return: dict of bezel metadata or None
        {
        bezel name: {
            file: filepath
            size: size
            name: filename without extension
            top_left, top_right, bottom_left, bottom_right: coordinates of screen corners
            screen_width, screen_height: pixel widths and height of screen
        }
    }
    """
    print(filepath)
    bim = None
    try:
        bim = Image.open(filepath)
    except UnidentifiedImageError:
        print("UnidentifiedImageError: " + filepath)
        return None

    bezel_metadata = {"file": filepath, "size": bim.size}

    _, filename = os.path.split(filepath)
    bezel_metadata["name"], _ = os.path.splitext(filename)

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
        return None
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
    # All done, except that some phones have notches in the top of their screens
    # to make space for the cameras. To find the true min_y start from half_width
    # and min_y, then x++. IF pixel above alpha != 255 THEN min_y-- and continue.
    # ELSE IF pixel to right alpha is not 100% transparent THEN stop.
    temp_x = half_width
    while im_data[min_y][temp_x + 1][3] < 255:
        if im_data[min_y - 1][temp_x][3] != 0:
            temp_x = temp_x + 1
        else:
            min_y = min_y - 1

    bezel_metadata["screen_top_left"] = (min_x, min_y)
    bezel_metadata["screen_width"] = max_x - min_x + 1
    bezel_metadata["screen_height"] = max_y - min_y + 1
    bezel_metadata["portrait"] = bezel_metadata["screen_height"] > \
                                 bezel_metadata["screen_width"]
    print(bezel_metadata)

    return bezel_metadata


def add_bezel(fp, bezel_id, stretch=False, crop=False, preview=False):
    im_src = Image.open(fp)
    # rotate if landscape
    landscape = im_src.size[0] > im_src.size[1]
    if landscape:
        # rotate source image to portrait and then back again at the end
        im_src = im_src.rotate(270, expand=True)

    if bezel_id.lower() == "auto":
        matching_bezels = find_matching_device_bezels(im_src.size)
        if len(matching_bezels) == 0:
            print("no matching bezels")
            return None
        b = matching_bezels[0]
    else:
        bezel_metadata = get_bezels_metadata()
        if bezel_id not in bezel_metadata:
            print("bezel has no matching metadata")
            return None
        b = bezel_metadata[bezel_id]

    if stretch:
        print(b)
        print(im_src.size)
        im_src = im_src.resize((b['screen_width'], b['screen_height']))
    elif crop:
        w, h = im_src.size
        im_src = ImageOps.fit(im_src, (b['screen_width'], b['screen_height']), centering=(0.0, 0.0))
        w_ratio = b['screen_width'] / w
        h_ratio = b['screen_height'] / h
        """
        if w_ratio > h_ratio:
            im_src = im_src.resize((w, (h * h_ratio) + 1))
        else:
            im_src = im_src.resize(((w * w_ratio) + 1, h))
        im_src = im_src.crop
        """

    im_bez = Image.open(b["file"])
    im_tgt = Image.new('RGBA', im_bez.size)
    im_tgt.paste(im_src, b["screen_top_left"])
    im_tgt.alpha_composite(im_bez)
    im_tgt.crop(im_tgt.getbbox())

    if preview:
        w, h = im_tgt.size
        im_tgt = im_tgt.reduce(3)

    if landscape:
        im_tgt = im_tgt.rotate(90, expand=True)

    tgt_folder, _ = os.path.split(fp)
    tgt_fn = str(uuid.uuid4()) + '.png'
    tgt_fp = os.path.join(tgt_folder, tgt_fn)
    im_tgt.save(tgt_fp)

    return tgt_fp


def find_matching_device_bezels(im_size):
    bezel_metadata = get_bezels_metadata()
    portrait = im_size[0] < im_size[1]
    matching_bezels = []

    for k in bezel_metadata:
        bw = bezel_metadata[k]["screen_width"]
        bh = bezel_metadata[k]["screen_height"]
        if not portrait:
            t = bw
            bw = bh
            bh = t
        if im_size[0] == bw and im_size[1] == bh:
            matching_bezels.append(bezel_metadata[k])

    return matching_bezels
