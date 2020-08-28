from importlib import import_module
from os import getcwd
from os.path import join

from traitlets import Bool

from magic_monkey.base.application import MagicMonkeyBaseApplication


_flags = dict(
    document=(
        {'MagicMonkeyBaseApplication': {'document': True}},
        "Generate documentation for the project in the current directory"
    )
)


class MagicMonkeyApplication(MagicMonkeyBaseApplication):
    flags = _flags

    document = Bool(False, help='Generate projects documentation').tag(
        config=True, ignore_write=True, hidden=True
    )

    def start(self):
        if self.document:
            self.document_config_options()
        else:
            super().start()

    def document_config_options(self):
        cwd = getcwd()
        with open(join(cwd, "{}.rst".format(self.name)), "w+") as f:
            f.write(super().document_config_options())

        for name, command in self.subcommands.items():
            self.initialize_subcommand(name, ["--safe"])
            with open(join(cwd, "{}.rst".format(self.subapp.name)), "w+") as f:
                f.write(self.subapp.document_config_options())
            self.subapp.__class__.clear_instance()

    def _start(self):
        if self.subapp:
            self.subapp.start()

    def _example_command(self, *args):
        return "magic_monkey command <args> <flags>"

    subcommands = dict(
        ants_registration=(
            "magic_monkey.apps.AntsRegistration", 'Register images via ants'
        ),
        ants_transform=(
            "magic_monkey.apps.AntsTransform", 'Apply a registration transform'
        ),
        apply_mask=("magic_monkey.apps.ApplyMask", 'Apply mask to image'),
        apply_topup=(
            "magic_monkey.apps.ApplyTopup",
            'Apply Topup correction to a set of images'
        ),
        b0=(
            "magic_monkey.apps.B0Utils",
            'Basic processing on B0 slices of dwi volumes'
        ),
        concatenate=(
            "magic_monkey.apps.Concatenate", 'Concatenates images together'
        ),
        csd=(
            "magic_monkey.apps.CSD",
            'Perform constrained spherical deconvolution'
        ),
        diamond=(
            "magic_monkey.apps.Diamond", 'Perform diamond reconstruction'
        ),
        diamond_metrics=(
            "magic_monkey.apps.DiamondMetrics", 'Compute DTI metrics'
        ),
        dti=("magic_monkey.apps.DTI", 'Perform dti reconstruction'),
        dti_metrics=("magic_monkey.apps.TensorMetrics", 'Compute DTI metrics'),
        eddy=("magic_monkey.apps.Eddy", 'Execute eddy correction'),
        pft=(
            "magic_monkey.apps.PftTracking",
            'Execute particle filtering tracking'
        ),
        response=(
            "magic_monkey.apps.FiberResponse",
            'Compute single fiber response (and gm and csf if msmt)'
        ),
        topup=("magic_monkey.apps.Topup", 'Execute topup correction')
    )


launch_new_instance = MagicMonkeyApplication.launch_instance


def console_entry_point():
    launch_new_instance()


if __name__ == '__main__':
    console_entry_point()



