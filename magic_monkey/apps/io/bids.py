import json
import numpy as np
from os import makedirs
from os.path import basename, join
from shutil import copyfile, rmtree

from bids import BIDSLayout
from bids.layout import Query
from bids.layout.writing import build_path

from traitlets import Unicode, Dict, Float, Enum, Integer, Bool

from magic_monkey.base.application import MagicMonkeyBaseApplication, \
    required_arg, MultipleArguments, ChoiceList


_aliases = {
    "in": "ConvertBidsToMMY.projects",
    "out": "ConvertBidsToMMY.output_folder",
    "mod": "ConvertBidsToMMY.modalities",
    "default_readout": "ConvertBidsToMMY.default_readout",
    "default_phase_dir": "ConvertBidsToMMY.default_phase_direction",
    "default_mb_factor": "ConvertBidsToMMY.default_multiband_factor"
}

_flags = dict(
    default_interleaved=(
        {"ConvertBidsToMMY": {'default_interleaved': True}},
        "States files missing information on "
        "slice ordering as acquired interleaved"
    ),
    default_sequential=(
        {"ConvertBidsToMMY": {'default_interleaved': False}},
        "States files missing information on "
        "slice ordering as acquired sequentially"
    )
)


class ConvertBidsToMMY(MagicMonkeyBaseApplication):
    projects = required_arg(
        MultipleArguments, traits_args=(Unicode(),),
        description="Input bids projects to convert to magic-monkey input tree"
    )

    output_folder = required_arg(
        Unicode,
        description="Output directory for the magic-monkey input tree"
    )

    modalities = ChoiceList(
        ["t1", "t2", "dwi"], Unicode(), ["t1", "dwi"],
        help="Modalities to try to convert for magic-monkey"
    ).tag(config=True)

    default_readout = Float(
        None, allow_none=True,
        help="Default acquisition readout to put on files missing it"
    ).tag(config=True)

    default_phase_direction = Enum(
        ['AP', 'PA', 'LR', 'RL', 'IS', 'SI'], None, allow_none=True,
        help="Default phase encoding direction to put on files missing it"
    ).tag(config=True)

    default_multiband_factor = Integer(
        None, allow_none=True,
        help="Default multiband factor to put on files missing it"
    ).tag(config=True)

    default_interleaved = Bool(
        None, allow_none=True, help="Declare the acquisition containing "
                                    "interleaved slices if file is missing it"
    ).tag(config=True)

    aliases = Dict(default_value=_aliases)
    flags = Dict(default_value=_flags)

    _dataloader = {
        "t1": lambda l, f, o, _: ConvertBidsToMMY.save_files(
            ConvertBidsToMMY.load_anat_dataset(l, 'T1w', f, 't1', o),
            o, "t1"
        ),
        "t2": lambda l, f, o, _: ConvertBidsToMMY.save_files(
            ConvertBidsToMMY.load_anat_dataset(l, 'T2w', f, 't1', o),
            o, "t2"
        ),
        "dwi": lambda l, f, o, d: ConvertBidsToMMY.load_dwi_dataset(l, f, o, d)
    }

    @classmethod
    def save_files(cls, files, folder, tag):
        for f in files:
            file = build_path(
                f.entities,
                "sub-{subject}_ses-{session}[-{run}]_" + tag + ".{extension}"
            )
            copyfile(f.path, join(folder, file))

    @classmethod
    def load_anat_dataset(cls, layout, suffix, filtering, tag, folder):
        anat = layout.get(
            datatype='anat', extension="nii.gz", suffix=suffix, **filtering
        )

        if len(anat) == 0:
            if 'run' in filtering:
                anat = layout.get(
                    datatype='anat', extension="nii.gz", suffix=suffix,
                    **{k: v for k, v in filtering.items() if not k == "run"}
                )

                if len(anat) == 0:
                    raise ValueError("No {} image found".format(suffix))

                file_path = "sub-{subject}_ses-{session}"
                if 'run' in filtering:
                    file_path += "-" + str(filtering['run'])

                file = build_path(
                    anat[0].entities, file_path + "_" + tag + ".{extension}"
                )
                copyfile(anat[0].path, join(folder, file))

                return []
            else:
                raise ValueError("No {} image found".format(suffix))

        return anat

    @classmethod
    def save_metadata(cls, dwi, output_folder, tag, defaults):
        output_metadata = {
            'readout': defaults['readout'],
            'direction': defaults['direction'],
            'slice_direction': 'IS',
            'interleaved': defaults['interleaved'],
            'multiband_factor': defaults['multiband_factor']
        }
        conversion = {
            "i": "LR", "i-": "RL", "j": "PA", "j-": "AP", "k": "IS", "k-": "SI"
        }

        if tag == 'rev' and output_metadata['direction'] != 'todo':
            output_metadata['direction'] = output_metadata['direction'][::-1]

        if output_metadata['direction'] in ['IS', 'SI']:
            output_metadata['slice_direction'] = 'AP'

        with open(dwi.path.replace('.nii.gz', '.json'), 'r') as handle:
            metadata = json.load(handle)
            if 'TotalReadoutTime' in metadata:
                output_metadata['readout'] = metadata['TotalReadoutTime']
            if 'PhaseEncodingDirection' in metadata:
                output_metadata['direction'] = conversion[metadata[
                    'PhaseEncodingDirection'
                ]]
            if 'SliceTiming' in metadata:
                times = np.array(metadata['SliceTiming'])
                sort_idxs = np.argsort(times)
                sorted_times = times[sort_idxs]
                diff1d = np.concatenate((
                    [True], np.logical_not(np.isclose(
                        sorted_times[1:], sorted_times[:-1]
                    ))
                ))
                cgroups = np.split(
                    sort_idxs,
                    np.cumsum(np.diff(np.concatenate(
                        np.nonzero(diff1d) + ([times.size],)
                    )))[:-1]
                )
                output_metadata['slice_indexes'] = list(
                    g.tolist() for g in cgroups
                )

                output_metadata.pop('interleaved')
                output_metadata.pop('multiband_factor')

        if any([
            isinstance(val, str) and val == 'todo'
            for val in output_metadata.values()
        ]):
            print(
                "Missing metadata fields for dwi {}. Check the "
                "output metadata file and replace the fields "
                "containing \'todo\' as value".format(dwi.path)
            )

        file = build_path(
            dwi.entities,
            "sub-{subject}_ses-{session}[-{run}]_" + tag + ".json"
        )

        with open(join(output_folder, file), 'w+') as handle:
            json.dump(output_metadata, handle)

    @classmethod
    def load_dwi_dataset(cls, layout, filtering, output_folder, defaults):
        dwi = layout.get(
            datatype="dwi", extension='nii.gz', suffix="dwi",
            acquisition=Query.NONE, regex_search=True, **filtering
        )

        direction = Query.NONE
        if 'direction' in dwi[0].tags:
            direction = dwi[0].tags['direction'].value
            dwi = [dwi[0]]

        dwi += layout.get(
            datatype="dwi", extension='bval', suffix="dwi",
            acquisition=Query.NONE, direction=direction,
            regex_search=True, **filtering
        )
        dwi += layout.get(
            datatype="dwi", extension='bvec', suffix="dwi",
            acquisition=Query.NONE, direction=direction,
            regex_search=True, **filtering
        )

        cls.save_files(dwi, output_folder, "dwi")
        cls.save_metadata(dwi[0], output_folder, "dwi", defaults)

        rev = layout.get(
            datatype="dwi", extension='nii.gz', suffix="dwi",
            acquisition="RevPol", regex_search=True, **filtering
        )

        if len(rev) == 0:
            if direction is not Query.NONE:
                rev = layout.get(
                    datatype="dwi", extension='nii.gz', suffix="dwi",
                    direction=direction[::-1], regex_search=True, **filtering
                )
                rev += layout.get(
                    datatype="dwi", extension='bval', suffix="dwi",
                    direction=direction[::-1], regex_search=True, **filtering
                )
                rev += layout.get(
                    datatype="dwi", extension='bvec', suffix="dwi",
                    direction=direction[::-1], regex_search=True, **filtering
                )

            if len(rev) == 0:
                rev = layout.get(
                    datatype="fmap", extension='nii.gz', suffix="epi",
                    **filtering
                )
        else:
            rev += layout.get(
                datatype="dwi", extension='bval', suffix="dwi",
                acquisition="RevPol", regex_search=True, **filtering
            )
            rev += layout.get(
                datatype="dwi", extension='bvec', suffix="dwi",
                acquisition="RevPol", regex_search=True, **filtering
            )

        if len(rev) > 0:
            cls.save_files(rev, output_folder, "rev")
            cls.save_metadata(rev[0], output_folder, "rev", defaults)

    def _convert_entity(self, layout, filtering, output_folder, defaults):
        for mod in self.modalities:
            self._dataloader[mod](layout, filtering, output_folder, defaults)

    def execute(self):
        for project in self.projects:
            layout = BIDSLayout(project, index_metadata=False)
            project_name = basename(project)
            project_folder = join(self.output_folder, project_name)
            makedirs(project_folder, exist_ok=True)
            runs = layout.get_runs()
            sessions = layout.get_sessions()

            defaults = {
                'readout': self.default_readout,
                'direction': self.default_phase_direction,
                'interleaved': self.default_interleaved,
                'multiband_factor': self.default_multiband_factor
            }

            defaults = {k: v if v else 'todo' for k, v in defaults.items()}

            for subject in layout.get_subjects():
                for session in sessions:
                    filtering = {
                        "subject": subject, "session": session
                    }
                    subject_folder = join(
                        project_folder, "sub-{}".format(subject)
                    )
                    makedirs(subject_folder, exist_ok=True)

                    if runs:
                        for run in runs:
                            filtering["run"] = run
                            session_folder = join(
                                subject_folder, "ses-{}-{}".format(session, run)
                            )
                            makedirs(session_folder, exist_ok=True)
                            try:
                                self._convert_entity(
                                    layout, filtering, session_folder, defaults
                                )
                            except BaseException as e:
                                print(
                                    "| {} | Error converting subject {} "
                                    "- session {} - run {}".format(
                                        project, subject, session, run
                                    )
                                )
                                rmtree(session_folder)
                    else:
                        session_folder = join(
                            subject_folder, "ses-{}".format(session)
                        )
                        try:
                            self._convert_entity(
                                layout, filtering, session_folder, defaults
                            )
                        except BaseException:
                            print(
                                "Error converting subject {} "
                                "- session {}".format(
                                    subject, session
                                )
                            )
                            rmtree(session_folder)
