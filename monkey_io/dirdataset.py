import os

from monkey_io.dataset import Dataset
from piper.exceptions import NotImplementedException


class DirDataset(Dataset):
    def __init__(
        self, root_dir, cache_len, load_subject_fn, add_subject_info_fn=None,
        single_anat_fn=None, single_mask_fn=None
    ):
        self._single_fn = [single_anat_fn, single_mask_fn]
        self._load_repetition = load_subject_fn
        self._root = root_dir

        super().__init__(
            cache_len, None, add_subject_info_fn,
            single_anat_fn is not None, single_mask_fn is not None,
            "{}_dataset".format(os.path.split(root_dir)[-1])
        )

    def _initialize(self):
        for subject in filter(
            lambda d: os.path.isdir(os.path.join(self._root, d)),
            os.listdir(self._root)
        ):
            sdir = os.path.join(self._root, subject)
            single_data_kwargs = {
                "single_anat":
                    self._single_fn[0](subject, sdir)
                    if self._single_anat else None,
                "single_mask":
                    self._single_fn[1](subject, sdir)
                    if self._single_mask else None
            }
            subject_root = os.path.join(self._root, subject)
            self._add_subject_info(
                subject,
                list(filter(
                    lambda d: os.path.isdir(os.path.join(subject_root, d)),
                    os.listdir(subject_root)
                )),
                lambda rep_id: self._load_repetition(
                    subject, rep_id,
                    os.path.join(self._root, subject, rep_id)
                ),
                **single_data_kwargs
            )

    def _load_repetition(self, subject, rep, rep_path):
        raise NotImplementedException(
            "A function must be supplied to load the dataset's repetitions"
        )

    def _load_into_cache(self, id, subject, rep, **kwargs):
        data = self._load_repetition(
            subject, rep,
            os.path.join(self._root, subject, rep)
        )
        self._add_to_cache(id, data)
