import nibabel as nib
import nrrd


valid_extensions = ["nii", "nii.gz", "nrrd"]


class NRRDImage:
    def __init__(self, data, header):
        self.data = data
        self.header = header

    def __getattr__(self, item):
        return getattr(self.data, item)

    def __setattr__(self, key, value):
        setattr(self.data, key, value)

    def __getitem__(self, item):
        return self.data[item]

    def __setitem__(self, key, value):
        self.data[key] = value


def convert_nii_to_nrrd_header(nifti_image):
    pass


def convert_nrrd_to_nii(nrrd_image):
    pass


class NiftiImageReader:
    @classmethod
    def read(cls, filename):
        return nib.load(filename)


class NiftiImageWriter:
    @classmethod
    def write(cls, filename, image):
        if isinstance(image, NRRDImage):
            image = convert_nrrd_to_nii(image)

        nib.save(image, filename)


class NrrdImageReader:
    @classmethod
    def read(cls, filename):
        return NRRDImage(
            *nrrd.read(filename)
        )


class NrrdImageWriter:
    @classmethod
    def write(cls, filename, image):
        if not isinstance(image, NRRDImage):
            image = convert_nii_to_nrrd_header(image)

        nrrd.write(filename, image.data, image.header)


image_reader = {
    "nii": NiftiImageReader,
    "nii.gz": NiftiImageReader,
    "nrrd": NrrdImageReader
}

image_writer = {
    "nii": NiftiImageWriter,
    "nii.gz": NiftiImageWriter,
    "nrrd": NiftiImageWriter
}
