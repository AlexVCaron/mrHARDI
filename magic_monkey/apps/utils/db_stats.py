import json
import glob
import nibabel as nib
import os
import sqlite3
from os import makedirs
from os.path import join, basename

import numpy as np
import pandas as pd
from traitlets import Unicode, Dict

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    required_arg, MultipleArguments


_aliases = {
    'in': "DBStats.projects",
    'out': "DBStats.output_folder"
}


class DBStats(MagicMonkeyBaseApplication):
    projects = required_arg(
        MultipleArguments, traits_args=(Unicode(),),
        description="Input magic-monkey projects to analyse"
    )

    output_folder = required_arg(
        Unicode, description="Output root for the db and stats dashboard"
    )

    aliases = Dict(default_value=_aliases)

    _subject_columns = [
        'subject', 'session', 'run', 'project'
    ]
    _dwi_columns = [
        'subject_session_run', 'space_attrs', 'diffusion_attrs'
    ]
    _space_columns = ['voxel_size', 'volume_size', 'image_id']
    _diffusion_columns = [
        'phase', 'n_directions', 'shells', 'n_per_shell',
        'directions', 'b_values', 'image_id'
    ]

    def create_db(self):
        makedirs(join(self.output_folder, "db"), exist_ok=True)
        connection = sqlite3.connect(join(self.output_folder, "db", "stats.db"))
        cursor = connection.cursor()
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS PROJECTS ('
            'id integer PRIMARY KEY, '
            'name text NOT NULL)'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS SUBJECTS ('
            'id integer PRIMARY KEY, '
            'subject text NOT NULL, '
            'session text, '
            'run text, '
            'project integer NOT NULL, '
            'FOREIGN KEY (project) REFERENCES PROJECTS (id) '
            ')'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS DWI ('
            'id integer PRIMARY KEY, '
            'subject_session_run integer NOT NULL, '
            'space_attrs integer NOT NULL, '
            'diffusion_attrs integer NOT NULL, '
            'FOREIGN KEY (subject_session_run) REFERENCES SUBJECTS (id), '
            'FOREIGN KEY (space_attrs) REFERENCES SPACE_ATTRS (id), '
            'FOREIGN KEY (diffusion_attrs) REFERENCES DIFFUSION_ATTRS (id))'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS SPACE_ATTRS ('
            'id integer PRIMARY KEY, '
            'voxel_size blob NOT NULL, '
            'volume_size blob NOT NULL, '
            'image_id integer NOT NULL, '
            'FOREIGN KEY (image_id) REFERENCES DWI (id))'
        )
        cursor.execute(
            'CREATE TABLE IF NOT EXISTS DWI_ATTRIBUTES ('
            'id integer PRIMARY KEY, '
            'phase text NOT NULL, '
            'n_directions integer NOT NULL, '
            'shells blob NOT NULL, '
            'n_per_shell blob NOT NULL, '
            'directions blob, '
            'b_values blob NOT NULL, '
            'image_id integer NOT NULL, '
            'FOREIGN KEY (image_id) REFERENCES DWI (id))'
        )
        connection.commit()

        return connection

    def _prepare_subject_frame(self, init_data=None):
        return pd.DataFrame(data=init_data, columns=self._subject_columns)

    def _prepare_dwi_frame(self, init_data=None):
        return pd.DataFrame(data=init_data, columns=self._dwi_columns)

    def _prepare_space_frame(self, init_data=None):
        return pd.DataFrame(data=init_data, columns=self._space_columns)

    def _prepare_diffusion_frame(self, init_data=None):
        return pd.DataFrame(data=init_data, columns=self._diffusion_columns)

    def _load_subjects(self, project_idx, project_root, init_idxs):
        init_sub_idx, init_dwi_idx, init_spc_idx, init_dif_idx = init_idxs

        subject_data = {k: [] for k in self._subject_columns}
        dwi_data = {k: [] for k in self._dwi_columns}
        space_data = {k: [] for k in self._space_columns}
        diffusion_data = {k: [] for k in self._diffusion_columns}

        for subject in [
            it for it in os.listdir(project_root)
            if os.path.isdir(join(project_root, it))
        ]:
            subject_root = join(project_root, subject)
            for session in [
                it for it in os.listdir(subject_root)
                if os.path.isdir(join(subject_root, it))
            ]:
                session_root = join(subject_root, session)
                session_split = session.split("-")
                if len(session_split) > 2:
                    ses, run = "-".join(session_split[:-1]), session_split[-1]
                else:
                    ses, run = session, None

                subject_data['subject'].append(subject)
                subject_data['project'].append(project_idx)
                subject_data['session'].append(ses)
                subject_data['run'].append(run)

                tag = "{}_{}".format(subject, session)

                for dataset in (
                    glob.glob1(session_root, tag + "_dwi.nii.gz") +
                    glob.glob1(session_root, tag + "_rev.nii.gz")
                ):
                    name = join(session_root, dataset.split(".")[0])
                    img = nib.load(join(session_root, dataset))
                    with open("{}.json".format(name), 'r') as handle:
                        metadata = json.load(handle)

                    space_data['volume_size'].append(str(img.shape[:3]))
                    zooms = img.header.get_zooms()
                    space_data['voxel_size'].append(str(zooms[:3]))

                    diffusion_data['n_directions'].append(
                        img.shape[-1] if len(img.shape) > 3 else 1
                    )
                    diffusion_data['phase'].append(metadata['direction'])

                    try:
                        bvals = np.loadtxt("{}.bval".format(name))
                        bvecs = np.loadtxt("{}.bvec".format(name))
                        shells, counts = np.unique(bvals, return_counts=True)
                        diffusion_data['shells'].append(str(shells))
                        diffusion_data['n_per_shell'].append(str(counts))
                        diffusion_data['directions'].append(bvecs.tostring())
                        diffusion_data['b_values'].append(bvals.tostring())
                    except FileNotFoundError:
                        diffusion_data['shells'].append("[0]")
                        diffusion_data['n_per_shell'].append("[1]")
                        diffusion_data['directions'].append(None)
                        diffusion_data['b_values'].append("[0]")

                    diffusion_data['image_id'].append(init_dwi_idx)
                    space_data['image_id'].append(init_dwi_idx)

                    dwi_data['subject_session_run'].append(init_sub_idx)
                    dwi_data['space_attrs'].append(init_spc_idx)
                    dwi_data['diffusion_attrs'].append(init_dif_idx)

                    init_dwi_idx += 1
                    init_spc_idx += 1
                    init_dif_idx += 1

                init_sub_idx += 1

        subject_frame = self._prepare_subject_frame(subject_data)
        dwi_frame = self._prepare_dwi_frame(dwi_data)
        space_frame = self._prepare_space_frame(space_data)
        diffusion_frame = self._prepare_diffusion_frame(diffusion_data)

        return subject_frame, dwi_frame, space_frame, diffusion_frame

    def execute(self):
        connection = self.create_db()

        project_frame = pd.DataFrame(
            {'name': [basename(p) for p in self.projects]}, columns=['name']
        )
        project_frame.to_sql(
            'PROJECTS', connection, if_exists='append', index_label='id'
        )

        subject_frame = self._prepare_subject_frame()
        dwi_frame = self._prepare_dwi_frame()
        space_frame = self._prepare_space_frame()
        diffusion_frame = self._prepare_diffusion_frame()

        for i, project in enumerate(self.projects):
            sub, dwi, spc, dif = self._load_subjects(
                i, project, (len(subject_frame.index),
                             len(dwi_frame.index),
                             len(space_frame.index),
                             len(diffusion_frame.index))
            )
            subject_frame = subject_frame.append(sub, ignore_index=True)
            dwi_frame = dwi_frame.append(dwi, ignore_index=True)
            space_frame = space_frame.append(spc, ignore_index=True)
            diffusion_frame = diffusion_frame.append(dif, ignore_index=True)

        subject_frame.to_sql(
            'SUBJECTS', connection, if_exists='append', index_label='id'
        )
        dwi_frame.to_sql(
            'DWI', connection, if_exists='append', index_label='id'
        )
        space_frame.to_sql(
            'SPACE_ATTRS', connection, if_exists='append', index_label='id'
        )
        diffusion_frame.to_sql(
            'DWI_ATTRIBUTES', connection, if_exists='append', index_label='id'
        )

        connection.close()
