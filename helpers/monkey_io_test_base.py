from functools import partial

from helpers.data import create_pipeline_input_subject, \
    create_pipeline_input_rep_h5, \
    create_hdf5_dataset


class MonkeyIOTestBase:
    def generate_hdf5_dataset(
        self, n_subs, n_reps, shape, prefix=None,
        init_val=None, single_anat=True, single_mask=True
    ):
        sub_fn = partial(
            create_pipeline_input_subject,
            shape=shape, init_val=init_val,
            single_anat=single_anat,
            single_mask=single_mask
        )

        rep_fn = partial(
            create_pipeline_input_rep_h5,
            shape=shape, init_val=init_val,
            mask=not single_mask, anat=not single_anat
        )

        return create_hdf5_dataset(
            n_subs, n_reps, prefix, rep_fn, sub_fn
        )
