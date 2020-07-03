import h5py

from monkey_io.dataset import Dataset


class H5Dataset(Dataset):
    def __init__(
        self, h5_archive, cache_len=3, prepare_data_fn=None,
        single_anat=True, single_mask=True, name="h5dataset"
    ):
        self._archive = h5_archive

        super().__init__(
            cache_len, prepare_data_fn, None, single_anat, single_mask, name
        )

    def _load_into_cache(self, id, subject, rep, **kwargs):
        with h5py.File(self._archive, "r") as archive:
            data = archive[subject][rep]
            self._add_to_cache(id, data)

    def _initialize(self):
        with h5py.File(self._archive, "r") as archive:
            for subject, group in archive.items():
                gp = dict(group)

                single_data_kwargs = {
                    "single_anat":
                        gp.pop("anat")[()] if self._single_anat else None,
                    "single_mask":
                        gp.pop("mask")[()] if self._single_mask else None
                }

                self._add_subject_info(
                    subject, list(gp.keys()), lambda k: gp[k],
                    **single_data_kwargs
                )

    def _data_to_dict(self, data):
        return {
            k: v[()] for k, v in data.items()
        }
