from dipy.io.streamline import save_trk
from traitlets import Bool, Float, Instance, Unicode

import nibabel as nib
import numpy as np
from dipy.data import default_sphere
from dipy.direction import ProbabilisticDirectionGetter
from dipy.io.stateful_tractogram import Space, StatefulTractogram
from dipy.tracking.stopping_criterion import CmcStoppingCriterion
from dipy.tracking.local_tracking import ParticleFilteringTracking
from dipy.tracking.streamline import Streamlines
from dipy.tracking.utils import seeds_from_mask

from magic_monkey.base.application import (MagicMonkeyBaseApplication,
                                           affine_file,
                                           mask_arg,
                                           output_prefix_argument,
                                           required_file,
                                           required_number)
from magic_monkey.config.pft_tracking import ParticleFilteringConfiguration


class PftTracking(MagicMonkeyBaseApplication):
    name = u"PFT Local Tracking"
    configuration = Instance(ParticleFilteringConfiguration).tag(config=True)

    sh_coefficients = required_file(
        description="Spherical harmonics coefficient map"
    )

    pve_maps = required_file(
        description="Partial volume estimation maps (wm, gm, csf) "
                    "concatenated in that order on the last axis"
    )

    step = required_number(description="Iteration step (in world space units)")

    output_prefix = output_prefix_argument()

    white_matter_mask = Unicode(
        help="Mask encapsulating the brain's white matter"
    ).tag(config=True)

    mask = mask_arg()

    affine = affine_file()

    seed_list = Unicode(
        None, allow_none=True,
        description="List of seed points to start the tracking algorithm"
    ).tag(config=True, exclusive_group="seed", group_index=0)

    pve_threshold = Float(
        0.5, help="Maximum PVE map value for a white matter voxel "
                  "to be considered a valid seed location"
    ).tag(config=True, exclusive_group="seed", group_index=1)
    seed_density = Float(
        2, help="Density of seeds inside each valid white matted seed voxel"
    ).tag(config=True, exclusive_group="seed", group_index=1)

    sphere_vertices = Unicode(
        help="Sphere tessellation used by the algorithms, "
             "will be read by numpy.loadtxt"
    ).tag(config=True)

    save_seeds = Bool(
        False, help="Save the seeds of the tracks alongside them"
    ).tag(config=True)

    compute_seeds = Bool(False)

    def _validate(self):
        super()._validate()
        if not self.seed_list:
            self.compute_seeds = True

    def execute(self):
        coeffs = nib.load(self.sh_coefficients).get_data()
        affine = np.loadtxt(self.affine)

        pve_img = nib.load(self.pve_maps)
        voxel_size = np.average(pve_img.header['pixdim'][1:4])
        pve_map = pve_img.get_fdata()

        sphere = default_sphere
        if self.sphere_vertices:
            sphere = np.loadtxt(self.sphere_vertices)

        tracker = ProbabilisticDirectionGetter.from_shcoeff(
            coeffs, max_angle=self.configuration.max_angle, sphere=sphere
        )

        if self.compute_seeds:
            seeds = self._compute_seeds(pve_map, affine)
        else:
            seeds = np.loadtxt(self.seed_list)

        cmc_crit = CmcStoppingCriterion.from_pve(
            *np.moveaxis(pve_map, -1, 0),
            step_size=self.step,
            average_voxel_size=voxel_size
        )

        pft_gen = ParticleFilteringTracking(
            tracker, cmc_crit, seeds, affine, self.step,
            self.configuration.max_crossing, self.configuration.max_length,
            self.configuration.back_tracking_dist,
            self.configuration.front_tracking_dist,
            self.configuration.max_trials, self.configuration.particle_count,
            save_seeds=self.save_seeds
        )

        tracks = Streamlines(pft_gen)
        save_trk(
            StatefulTractogram(tracks, pve_img, Space.RASMM),
            "{}.trk".format(self.output_prefix)
        )

    def _compute_seeds(self, pve_map, affine):
        seed_mask = self._get_wm_mask(pve_map.shape[:-1])
        seed_mask[pve_map[..., 0] < self.pve_threshold] = 0
        return seeds_from_mask(seed_mask, affine, density=self.seed_density)

    def _get_mask(self, none_shape=None):
        if self.mask:
            return nib.load(self.mask).get_fdata().astype(bool)
        elif none_shape is not None:
            return np.ones(none_shape)

        return None

    def _get_wm_mask(self, none_shape):
        mask = self._get_mask(none_shape)
        if self.white_matter_mask:
            wm_mask = nib.load(self.white_matter_mask).get_fdata().astype(bool)
            return mask & wm_mask

        return mask
