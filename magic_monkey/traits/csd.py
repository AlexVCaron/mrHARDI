from abc import abstractmethod

from traitlets import Float, Integer
from traitlets.config import Bool, Enum, List, Unicode, default

from magic_monkey.base.application import MagicMonkeyConfigurable


def _format_response_names(responses):
    return ["{}_response".format(r) for r in responses]


class SphericalDeconvAlgorithm(MagicMonkeyConfigurable):
    def _validate(self):
        pass

    cli_name = Unicode()
    responses = List(Unicode)
    non_neg_lambda = Float(1.).tag(config=True)
    norm_lambda = Float(1.).tag(config=True)

    def serialize(self):
        return " ".join([
            "-neg_lambda {}".format(self.non_neg_lambda),
            "-norm_lambda {}".format(self.norm_lambda)
        ])


class CSDAlgorithm(SphericalDeconvAlgorithm):
    threshold = Float(0.).tag(config=True)
    max_iter = Integer(50).tag(config=True)
    responses = List(Unicode, ["wm"])
    multishell = False

    @default('cli_name')
    def _cli_name_default(self):
        return "csd"

    def serialize(self):
        return " ".join([
            super().serialize(),
            "-threshold {}".format(self.threshold),
            "-niter {}".format(self.max_iter)
        ])


class MSMTCSDAlgorithm(SphericalDeconvAlgorithm):
    predicted_signal = Bool(False).tag(config=True)
    responses = List(Unicode, ["wm", "gm", "csf"])
    multishell = True

    @default('cli_name')
    def _cli_name_default(self):
        return "msmt_csd"

    @default('non_neg_lambda')
    def _non_neg_lambda_default(self):
        return 1E-10

    @default('norm_lambda')
    def _non_neg_lambda_default(self):
        return 1E-10


class ResponseAlgorithm(MagicMonkeyConfigurable):
    cli_name = Unicode()
    responses = List(Unicode)
    multishell = False

    def _validate(self):
        pass

    @abstractmethod
    def serialize(self):
        pass


class DhollanderResponseAlgorithm(ResponseAlgorithm):
    erode_iters = Integer(3).tag(config=True)
    fa_threshold = Float(0.2).tag(config=True)
    p_sf_wm_voxels = Float(0.5).tag(config=True)
    p_gm_voxels = Float(2).tag(config=True)
    p_csf_voxels = Float(10).tag(config=True)
    wm_alg = Enum(
        ["fa", "tax", "tournier", None], None, allow_none=True
    ).tag(config=True)

    multishell = True

    @default('cli_name')
    def _cli_name_default(self):
        return "dhollander"

    @default('responses')
    def _responses_default(self):
        return ["wm", "gm", "csf"]

    def serialize(self):
        optionals = []

        if self.wm_alg:
            optionals.append("-wm_algo {}".format(self.wm_alg))

        return [
            "-erode {}".format(self.erode_iters),
            "-fa {}".format(self.fa_threshold),
            "-sfwm {}".format(self.p_sf_wm_voxels),
            "-gm {}".format(self.p_gm_voxels),
            "-csf {}".format(self.p_csf_voxels)
        ] + optionals


class FAResponseAlgorithm(ResponseAlgorithm):
    erode_iters = Integer().tag(config=True)
    n_voxels = Integer().tag(config=True)
    fa_threshold = Float().tag(config=True)

    @default('cli_name')
    def _cli_name_default(self):
        return "fa"

    @default('responses')
    def _responses_default(self):
        return ["wm"]

    def serialize(self):
        return [
            "-erode {}".format(self.erode_iters),
            "-number {}".format(self.n_voxels),
            "-threshold {}".format(self.fa_threshold)
        ]


class MSMT5TTResponseAlgorithm(ResponseAlgorithm):
    fa_threshold = Float(0.2).tag(config=True)
    pvf_threshold = Float(0.95).tag(config=True)
    wm_alg = Enum(["fa", "tax", "tournier"], "tournier").tag(config=True)
    sfwm_fa_threshold = Float().tag(config=True)

    multishell = True

    @default('cli_name')
    def _cli_name_default(self):
        return "msmt_5tt"

    @default('responses')
    def _responses_default(self):
        return ["wm", "gm", "csf"]

    def serialize(self):
        optionals = []

        if self.sfwm_fa_threshold:
            optionals.append(
                "-sfwm_fa_threshold {}".format(self.sfwm_fa_threshold)
            )

        return [
            "-fa {}".format(self.fa_threshold),
            "-pvf {}".format(self.pvf_threshold),
            "-wm_algo {}".format(self.wm_alg)
        ] + optionals


class TaxResponseAlgorithm(ResponseAlgorithm):
    peak_ratio_thr = Float().tag(config=True)
    max_iters = Integer().tag(config=True)
    convergence = Float().tag(config=True)

    @default('cli_name')
    def _cli_name_default(self):
        return "tax"

    @default('responses')
    def _responses_default(self):
        return ["wm"]

    def serialize(self):
        optionals = []

        if self.peak_ratio_thr:
            optionals.append("-peak_ratio {}".format(self.peak_ratio_thr))
        if self.max_iters:
            optionals.append("-max_iters {}".format(self.max_iters))
        if self.convergence:
            optionals.append("-convergence {}".format(self.convergence))

        return optionals


class TournierResponseAlgorithm(ResponseAlgorithm):
    n_voxels = Integer().tag(config=True)
    iter_n_voxels = Integer().tag(config=True)
    dilate_iters = Integer().tag(config=True)
    max_iter = Integer().tag(config=True)

    @default('cli_name')
    def _cli_name_default(self):
        return "tournier"

    @default('responses')
    def _responses_default(self):
        return ["wm"]

    def serialize(self):
        optionals = []

        if self.n_voxels:
            optionals.append("-number {}".format(self.n_voxels))
        if self.iter_n_voxels:
            optionals.append("-iter_voxels {}".format(self.iter_n_voxels))
        if self.dilate_iters:
            optionals.append("-dilate {}".format(self.dilate_iters))
        if self.max_iter:
            optionals.append("-max_iters {}".format(self.max_iter))

        return optionals
