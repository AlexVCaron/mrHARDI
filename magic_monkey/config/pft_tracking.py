from traitlets import  Integer

from magic_monkey.base.application import MagicMonkeyConfigurable


class ParticleFilteringConfiguration(MagicMonkeyConfigurable):
    def _validate(self):
        pass

    def serialize(self, *args, **kwargs):
        pass

    max_crossing = Integer(
        None, allow_none=True,
        help="Maximum number of possible tracks in voxels containing crossings"
    ).tag(config=True)

    back_tracking_dist = Integer(
        2, help="Back-tracking distance (mm) before PFT iteration"
    ).tag(config=True)

    front_tracking_dist = Integer(
        1, help="PFT tracking iteration distance (mm)"
    ).tag(config=True)

    max_trials = Integer(
        20, help="Maximum number of trial tracks when "
                 "iteration ends in partial volume"
    ).tag(config=True)

    particle_count = Integer(
        15, help="Number of particles for the particle filtering algorithm"
    ).tag(config=True)
