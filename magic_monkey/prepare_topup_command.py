

def prepare_topup_params(ap_b0_shapes, pa_b0_shapes, dwell):
    param_string = ""
    for ap_b0, pa_b0 in zip(ap_b0_shapes, pa_b0_shapes):
        for _ in range(ap_b0[-1]):
            param_string += "0.0 1.0 0.0 {:.8f}\n".format(dwell)
        for _ in range(pa_b0[-1]):
            param_string += "0.0 -1.0 0.0 {:.8f}\n".format(dwell)

    return param_string
