from numpy import zeros_like


def apply_mask_on_data(in_data, in_mask):
    out_data = zeros_like(in_data)
    out_data[in_mask] = in_data[in_mask]
    return out_data
