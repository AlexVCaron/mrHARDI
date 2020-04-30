IMG_EXT = None


def get_img_extension():
    global IMG_EXT
    if "IMG_EXT" not in globals() or IMG_EXT is None:
        import json
        config = json.load(open("config.json"))

        IMG_EXT = config["image_extension"] \
            if "image_extension" in config else ".nii.gz"

    return IMG_EXT


def append_image_extension(prefix):
    return "{}{}".format(prefix, get_img_extension())
