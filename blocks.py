from piper.comm import Channel
from piper.comm import Collector
from piper.comm.channel_filter import ChannelFilter
from piper.pipeline import SequenceLayer, ParallelLayer
from piper.pipeline.unit import Unit
from processes.compute_mask_process import ComputeMaskProcess
from processes.preprocess.denoise import *
from processes.preprocess.preprocess import *
from processes.preprocess.register import *


###################################################
# Concatenate block :
#  - Input : {partial_datapoint}, {partial_datapoint}, ..., {partial_datapoint}
#      - Data can come from multiple channels, it will be gathered
#        respecting the data_ready_fn argument
#  - Steps :
#     Gather all inputs from the channels and test them, when a
#     package is ready, it is submitted to the concatenation process
###################################################
# def concatenate_input_block(
#     main_loop, input_channels, output_prefix, data_ready_fn,
#     base_name="cat_block", img_key_deriv="img", log_prefix=None,
#     pre_connect_unit=False
# ):
#     log_prefix = log_prefix if log_prefix else output_prefix
#
#     gatherer = Gatherer(
#         main_loop, data_ready_fn,
#         lambda datapoints: ConcatenateDatasets.prepare_input(datapoints),
#         name="{}_input".format(base_name)
#     )
#
#     for in_channel in input_channels:
#         subscriber = Subscriber(
#             "sub_{}_to_{}".format(in_channel.name, gatherer.name)
#         )
#         in_channel.add_subscriber(subscriber, Channel.Sub.OUT)
#         gatherer.add_subscriber(subscriber)
#
#     cat_unit = Unit(
#         ConcatenateDatasets(output_prefix, img_key_deriv),
#         log_prefix, "{}_cat_process".format(base_name)
#     )
#
#     if pre_connect_unit:
#         cat_unit.connect_input(gatherer)
#
#     return gatherer, cat_unit


###################################################
# Eddy sequence :
#  - Input : {dwi,bvals,bvecs}, {dwi,bvals,bvecs}, ..., {dwi,bvals,bvecs}
#      - (Optional) : mask
#  - Steps :
#     1. Concatenate datasets => {dwi_cat,bvals_cat,bvecs_cat}
#     2. (Optional) Average contiguous b0 volumes
#                             => {dwi_avg,bvals_avg,bvecs_avg}
#     3. Prepare eddy script => {eddy_script,eddy_params}
#     4. Run eddy process => {dwi_eddy,bvals_eddy,bvecs_eddy}
###################################################
def eddy_sequence(
    input_channel, input_topup, output_prefix,
    compute_high_res_mask=True, base_name="eddy_sequence",
    log_prefix=None, img_key_deriv="img", avg_contiguous_b0=True,
    dtype=np.float
):
    log_prefix = log_prefix if log_prefix else output_prefix

    cat_unit = Unit(
        ConcatenateDatasets("{}_cat".format(output_prefix), img_key_deriv),
        log_prefix, "{}_cat_process".format(base_name)
    )

    prep_eddy_unit = Unit(
        PrepareEddyProcess("{}_prep".format(output_prefix)),
        log_prefix, "{}_prep_eddy_process".format(base_name)
    )

    eddy_unit = Unit(
        EddyProcess(output_prefix, img_key_deriv),
        log_prefix, "{}_run_eddy_process".format(base_name)
    )

    output_channel = Channel(
        eddy_unit.package_keys,
        name="{}_out_chan".format(base_name)
    )

    topup_filter = ChannelFilter(
        input_topup, includes=input_topup.package_keys
    )

    layer = SequenceLayer(input_channel, output_channel, base_name)

    eddy_input_units = []
    if compute_high_res_mask:
        mask_unit = Unit(
            ComputeMaskProcess("{}_mask".format(output_prefix), img_key_deriv),
            log_prefix, name="{}_high_res_mask_process".format(base_name)
        )

        sub_par_layer = ParallelLayer(
            Channel(
                input_channel.package_keys, True,
                "{}_sub_layer_chan_in".format(base_name)
            ),
            Collector(
                np.unique(
                    mask_unit.package_keys + cat_unit.package_keys
                ).tolist(),
                name="{}_cat_mask_sub_layer_out_chan".format(base_name)
            ),
            "{}_cat_mask_sub_layer".format(base_name)
        )

        sub_par_layer.add_unit(cat_unit)
        sub_par_layer.add_unit(mask_unit, [topup_filter])

        layer.add_unit(sub_par_layer)
        eddy_input_units.append(sub_par_layer)
    else:
        layer.add_unit(cat_unit)
        eddy_input_units.append(cat_unit)

    if avg_contiguous_b0:
        avg_unit = Unit(SquashB0Process(
            "{}_squashed".format(output_prefix),
            dtype, img_key_deriv=img_key_deriv
        ), log_prefix, "{}_avg_process".format(base_name))
        layer.add_unit(avg_unit)
        eddy_input_units.append(avg_unit)

    layer.add_unit(prep_eddy_unit, [topup_filter])
    layer.add_unit(eddy_unit, eddy_input_units)

    return layer


###################################################
# Topup sequence :
#  - Input : {b0_vol}, {b0_vol}, ..., {b0_vol}
#  - Steps :
#     1. Concatenate datasets => {b0_vol_cat}
#     2. Prepare topup script => {topup_script,topup_params}
#     3. Run topup process => {b0_vol_topup,topup_field_params}
###################################################
def topup_sequence(
    input_channel, output_prefix, dwell_time,
    base_name="topup_sequence", log_prefix=None, img_key_deriv="img",
    base_topup_config="b02b0.cnf", extra_topup_params=None
):
    log_prefix = log_prefix if log_prefix else output_prefix

    cat_unit = Unit(
        ConcatenateDatasets(
            "{}_cat".format(output_prefix), img_key_deriv, False
        ), log_prefix, "{}_cat_process".format(base_name)
    )

    prep_topup_unit = Unit(
        PrepareTopupProcess(
            "{}_prep".format(output_prefix), dwell_time, base_topup_config,
            extra_topup_params, img_key_deriv
        ), log_prefix, "{}_prep_topup_process".format(base_name)
    )

    topup_unit = Unit(
        TopupProcess(output_prefix, img_key_deriv),
        log_prefix, "{}_run_topup_process".format(base_name)
    )

    output_channel = Channel(
        topup_unit.package_keys,
        name="{}_out_chan".format(base_name)
    )

    layer = SequenceLayer(input_channel, output_channel, base_name)
    layer.add_unit(cat_unit)
    layer.add_unit(prep_topup_unit)
    layer.add_unit(topup_unit, [cat_unit])

    return layer


###################################################
# Registration sequence :
#  - Input : {img0,...,imgN}, {img0,...,imgN}, ..., {img0,...,imgN}
#  - Steps :
#     1. Register using ants and the provided steps => {ref,affine}
#     2. Apply ants transformation => {img}
#
#    NOTICE : Ants requires its inputs to be named "img_from" and "img_to"
#             be sure to use the required channels or modify your package
#             namings before this step !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
###################################################
def registration_sequence(
    input_channel, output_prefix, ants_steps,
    base_name="registration_sequence", log_prefix=None, trans_img_key="img",
    ants_params=ants_global_params(), ants_do_init_moving_reg=True,
    ants_input_type=0, img_dim=3, fill_value=0, interpolation="Linear"
):
    log_prefix = log_prefix if log_prefix else output_prefix

    reg_unit = Unit(
        AntsRegisterProcess(
            "{}_compute".format(output_prefix), ants_steps,
            ants_params, ants_do_init_moving_reg
        ), log_prefix, "{}_ants_reg_process".format(base_name)
    )

    trans_unit = Unit(
        AntsApplyTransformProcess(
            output_prefix, img_dim, ants_input_type, interpolation,
            fill_value, img_key_deriv=trans_img_key
        ), log_prefix, "{}_apply_reg_process".format(base_name)
    )

    output_channel = Channel(
        trans_unit.package_keys,
        name="{}_out_chan".format(base_name)
    )

    layer = SequenceLayer(
        input_channel, output_channel, base_name
    )

    layer.add_unit(reg_unit)
    layer.add_unit(trans_unit, [input_channel])

    return layer
