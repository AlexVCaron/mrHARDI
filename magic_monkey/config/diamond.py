from os import cpu_count

from traitlets import Float, Integer
from traitlets.config import Bool, Enum, default
from traitlets.config.loader import ConfigError

from magic_monkey.base.application import MagicMonkeyConfigurable
from magic_monkey.traits.diamond import BoundingBox, Stick

_flags = {
    "mose-tensor": (
        {'DiamondConfiguration': {'mose_tensor': True}},
        "Use tensor distribution to compute model selection"
    ),
    "iso-null": (
        {'DiamondConfiguration': {'iso_if_no_fascicle': True}},
        "Compute an isotropic compartment in voxels without a fascicle"
    ),
    "iso-tensor": (
        {'DiamondConfiguration': {'water_tensor': True}},
        "Use tensor distribution to estimate isotropic compartment"
    ),
    "restricted": (
        {'DiamondConfiguration': {'estimate_restriction': True}},
        "Estimate isotropic restricted compartment"
    ),
    "res-tensor": (
        {'DiamondConfiguration': {'restriction_tensor': True}},
        "Use tensor distribution to estimate restricted compartment"
    ),
    "b0": (
        {'DiamondConfiguration': {'estimate_b0': True}},
        "Estimate b0 volume from diffusion data"
    ),
    "nosum-fractions": (
        {'DiamondConfiguration': {'sum_fractions_to_1': False}},
        "Disable check on unitary compartment "
        "fractions vector inside each voxels"
    ),
    "lenient-n-tensors": (
        {'DiamondConfiguration': {'strict_n_tensors': False}},
        "Compute the number of parameters (tensors) that can "
        "be estimated from the input DWI volume (up to n)"
    )
}

_aliases = dict(
    n="DiamondConfiguration.n_tensors",
    mose="DiamondConfiguration.mose_model",
    noise="DiamondConfiguration.noise_model",
    f="DiamondConfiguration.fascicle",
    box="DiamondConfiguration.bounding_box",
    opt="DiamondConfiguration.optimizer"
)


class DiamondConfiguration(MagicMonkeyConfigurable):
    @default('app_flags')
    def _app_flags_default(self):
        return _flags

    @default('app_aliases')
    def _app_aliases_default(self):
        return _aliases

    n_tensors = Integer(3).tag(config=True)

    estimate_mose = Bool(True)
    mose_model = Enum(
        ["none", "mcv", "aic", "aicc", "aicu", "bic"], "aicu"
    ).tag(config=True)
    mose_iter = Integer(30).tag(config=True)
    mose_tensor = Bool(False).tag(config=True)
    mose_min_fraction = Float(0).tag(config=True)

    noise_model = Enum(
        ["gaussian", "gaussianML", "rician", "ricianBeta"], "gaussian"
    ).tag(config=True)

    fascicle = Enum(
        ["tensorcyl", "diamondcyl", "diamondNC", "diamondNCcyl"],
        "diamondNCcyl"
    ).tag(config=True)

    estimate_water = Bool(True).tag(config=True)
    water_tensor = Bool(False).tag(config=True)
    water_diff = Float(3E-3).tag(config=True)
    estimate_restriction = Bool(False).tag(config=True)
    restriction_tensor = Bool(False).tag(config=True)

    max_evals = Integer(600).tag(config=True)
    max_passes = Integer(10).tag(config=True)
    multi_restart = Bool(False).tag(config=True)

    gen_error_iters = Integer(0).tag(config=True)
    regularization = Float(1.0).tag(config=True)
    estimate_b0 = Bool(False).tag(config=True)
    iso_no_fascicle = Bool(False).tag(config=True)
    bounding_box = BoundingBox(allow_none=True).tag(config=True)

    initial_stick = Stick(allow_none=True).tag(config=True)
    md_higher_bound = Float(1E-4).tag(config=True)
    fa_lower_bound = Float(0.7).tag(config=True)
    fw_md_higher_bound = Float(3E-3).tag(config=True)

    sum_fractions_to_1 = Bool(True).tag(config=True)

    splits = Integer(cpu_count()).tag(config=True)

    optimizer = Enum(
        ["powell", "newuoa", "bobyqa", "cobyla", "directl"], "bobyqa"
    ).tag(config=True)

    little_angles = Bool(False).tag(config=True)

    strict_n_tensors = Bool(True).tag(config=True)

    def _validate(self):
        pass

    def optimize_n_params(self, max_n_params):
        n_fascicle_params = 8 if "NC" in self.fascicle else 6

        n_add_params = 0
        if self.estimate_water:
            n_fw_params = 2 if not self.water_tensor else 6
            n_add_params += n_fw_params

        if self.estimate_restriction:
            n_res_params = 2 if not self.restriction_tensor else 6
            n_add_params += n_res_params

        n_params = n_fascicle_params * self.n_tensors + n_add_params
        while n_params > max_n_params:
            if self.n_tensors > 4:
                self.n_tensors -= 1
            elif self.estimate_restriction and self.restriction_tensor:
                self.restriction_tensor = False
                n_add_params -= 4
            elif self.estimate_water and self.water_tensor:
                self.water_tensor = False
                n_add_params -= 4
            elif self.estimate_restriction:
                self.estimate_restriction = False
                n_add_params -= 2
            elif self.estimate_water:
                self.estimate_water = False
                n_add_params -= 2
            elif self.n_tensors > 1:
                self.n_tensors -= 1
            else:
                raise ConfigError(
                    "Impossible to fit the number of parameters to the max "
                    "required. Either supply a DWI volume with more directions "
                    "or consider changing the fascicle model."    
                )

            n_params = n_fascicle_params * self.n_tensors + n_add_params


    def serialize(self, *args, **kwargs):
        optionals = []

        if self.bounding_box:
            optionals.append("--bbox {}".format(self.bounding_box))

        if self.gen_error_iters > 0:
            optionals.append(
                "--generalizationerror {}".format(self.gen_error_iters)
            )

        if self.little_angles:
            optionals.append("--littleAngles")

        if self.initial_stick:
            optionals.append("--initstick {}".format(self.initial_stick))

        if self.multi_restart:
            optionals.append("--multirestart")

        if self.estimate_mose:
            optionals.extend([
                "--automose {}".format(self.mose_model),
                "--moseminfraction {}".format(self.mose_min_fraction),
                "--moseiter {}".format(self.mose_iter),
                "--mosefulltensor".format(int(self.mose_tensor))
            ])

        return " ".join([
            "-n {} -r {}".format(self.n_tensors, self.regularization),
            "-s {}".format(self.splits),
            "--estimb0 {}".format(int(self.estimate_b0)),
            "--noisemodel {}".format(self.noise_model),
            "--fascicle {}".format(self.fascicle),
            "--waterfraction {}".format(int(self.estimate_water)),
            "--waterDiamond {}".format(int(self.water_tensor)),
            "--waterDiff {}".format(self.water_diff),
            "--isorfraction {}".format(int(self.estimate_restriction)),
            "--isorDiamond {}".format(int(self.restriction_tensor)),
            "--maxevals {}".format(self.max_evals),
            "--maxpasses {}".format(self.max_passes),
            "--initMD {}".format(self.md_higher_bound),
            "--initFA {}".format(self.fa_lower_bound),
            "--freediffbound {}".format(self.fw_md_higher_bound),
            "--fractions_sumto1 {}".format(int(self.sum_fractions_to_1)),
            "--estimateDisoIfNoFascicle {}".format(int(self.iso_no_fascicle)),
            "-a {}".format(self.optimizer)
        ] + optionals)
