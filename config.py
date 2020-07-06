IMG_EXT = None
PROCESS_PATHS = None


def get_img_extension():
    global IMG_EXT
    if "IMG_EXT" not in globals() or IMG_EXT is None:
        import json
        config = json.load(open("piper_config.json"))

        IMG_EXT = config["image_extension"] \
            if "image_extension" in config else ".nii.gz"

    return IMG_EXT


def append_image_extension(prefix):
    return "{}{}".format(prefix, get_img_extension())


def get_root(name):
    _load_process_paths()
    return PROCESS_PATHS[name]


def _load_process_paths():
    global PROCESS_PATHS
    if "PROCESS_PATHS" not in globals() or PROCESS_PATHS is None:
        import json
        config = json.load(open("piper_config.json"))

        PROCESS_PATHS = config["process_paths"]

    return PROCESS_PATHS
