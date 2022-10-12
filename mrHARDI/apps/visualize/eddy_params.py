from itertools import product
from os.path import exists

import numpy as np
import plotly.graph_objects as go

from plotly.subplots import make_subplots
from traitlets import Dict

from mrHARDI.base.application import (mrHARDIBaseApplication,
                                           prefix_argument)


_aliases = {
    "in": "VisualizeEddyParameters.input_prefix"
}


class VisualizeEddyParameters(mrHARDIBaseApplication):
    input_prefix = prefix_argument("Prefix of eddy outputs")

    aliases = Dict(default_value=_aliases)

    def execute(self):
        dwi_parameters, dwi_mss = self._load_parameters("dwi")
        b0_parameters, b0_mss = self._load_parameters("b0")

        shapes = [dwi_parameters.shape[0], b0_parameters.shape[0]]
        packages = [
            [dwi_parameters, dwi_mss],
            [b0_parameters, b0_mss]
        ]
        titles = [
            "Eddy parameters for dwi registration",
            "Eddy parameters for B0 registration"
        ]

        if exists(
            "{}.eddy_slice_to_vol_dwi_mss_history".format(self.input_prefix)
        ):
            sls_dwi_parameters, sls_dwi_mss = self._load_parameters(
                "slice_to_vol_dwi"
            )
            sls_b0_parameters, sls_b0_mss = self._load_parameters(
                "slice_to_vol_b0"
            )
            shapes += [sls_dwi_parameters.shape[0], sls_b0_parameters.shape[0]]
            packages += [
                [sls_dwi_parameters, sls_dwi_mss],
                [sls_b0_parameters, sls_b0_mss]
            ]
            titles += [
                "Eddy s2v parameters for dwi registration",
                "Eddy s2v parameters for B0 registration"
            ]

        figure, plot_params = self._configure_plot(
            nrows=int(sum(np.array(shapes) > 0)),
            titles=titles
        )

        for i, params in enumerate(plot_params):
            row, col = params
            pms, mss = packages[i]
            for data_pt in pms.T:
                figure.add_trace(
                    go.Scatter(
                        x=np.arange(0, len(data_pt)), y=data_pt, mode="lines"
                    ),
                    row=row, col=col
                )
            # figure.add_trace(go.Bar(x=x_mss, y=mss), row=row, col=col)

        figure.show()

    def _configure_plot(self, ncols=1, nrows=1, titles=()):
        if np.any(np.array([ncols, nrows]) > 1):
            return make_subplots(nrows, ncols, subplot_titles=titles), \
                   product(range(1, nrows + 1), range(1, ncols + 1))

        fig = go.Figure()
        fig.update_layout(title=titles[0])

        return fig, ((1, 1),)

    def _load_parameters(self, param_type):
        return np.loadtxt(
            "{}.eddy_{}_parameter_history".format(
                self.input_prefix, param_type
            )
        ), np.loadtxt(
            "{}.eddy_{}_mss_history".format(self.input_prefix, param_type)
        )
