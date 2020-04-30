from os.path import join

from multiprocess.pipeline.block import Block
from multiprocess.pipeline.channel import Channel, create_connection
from multiprocess.pipeline.unit import create_unit

from processes.preprocess.preprocess import *
from processes.preprocess.denoise import *
from processes.preprocess.register import *


def eddy_block(channel_in, topup_in, config, output_root, output_prefix="data", reduce_b0=True, vebose=True):
    cat_ap_pa = ConcatenateDatasets(join(output_root, "eddy", output_prefix))
    out_cat_ap_pa_c = Channel(["img", "bvals", "bvecs"])

    unit_list = [create_unit(cat_ap_pa, channel_in, out_cat_ap_pa_c)]
    channel_list = [out_cat_ap_pa_c]

    if reduce_b0:
        squash_b0 = SquashB0Process(join(output_root, "eddy", output_prefix))
        out_squash_b0_c = Channel(["img", "bvals", "bvecs"])

        channel_list.append(out_squash_b0_c)
        unit_list.append(create_unit(squash_b0, out_cat_ap_pa_c, out_squash_b0_c))

        in_prepare_eddy_c = out_squash_b0_c
    else:
        in_prepare_eddy_c = out_cat_ap_pa_c

    in_prepare_eddy_c = create_connection([topup_in, in_prepare_eddy_c], ["bvals", "param_topup"])
    prepare_eddy = PrepareEddyProcess(
        join(output_root, "eddy", output_prefix), **config["prepare_eddy"]
    )
    out_prepare_eddy_c = Channel(["script_eddy", "param_eddy"])

    in_run_eddy_c = create_connection(
        [channel_in, in_prepare_eddy_c, out_prepare_eddy_c],
        ["script_eddy", "img", "mask", "bvals", "bvecs", "param_eddy", "param_topup"]
    )
    run_eddy = EddyProcess(join(output_root, "eddy", output_prefix))
    out_run_eddy_c = Channel(["img", "bvals", "bvecs"])

    unit_list += [
        create_unit(prepare_eddy, in_prepare_eddy_c, out_prepare_eddy_c),
        create_unit(run_eddy, in_run_eddy_c, out_run_eddy_c)
    ]

    channel_list += [
        in_prepare_eddy_c, out_prepare_eddy_c,
        in_run_eddy_c, out_run_eddy_c
    ]

    return Block(unit_list), channel_list


def topup_block(channel_in, config, output_root, output_prefix="data", verbose=True):
    prepare_topup = PrepareTopupProcess(
        join(output_root, "topup", output_prefix), **config["prepare_topup"]
    )
    out_prepare_topup_c = Channel(["param_topup", "config_topup", "script_topup"])

    cat_ap_pa = ConcatenateDatasets(join(output_root, "topup", output_prefix))
    out_cat_ap_pa_c = Channel(["img"])

    in_run_topup_c = create_connection([out_prepare_topup_c, out_cat_ap_pa_c], ["script_topup", "img"])
    run_topup = TopupProcess(join(output_root, "topup", output_prefix))
    out_run_topup_c = Channel(["param_topup", "img"])

    return Block([
        create_unit(prepare_topup, channel_in, out_prepare_topup_c),
        create_unit(cat_ap_pa, channel_in, out_cat_ap_pa_c),
        create_unit(run_topup, in_run_topup_c, out_run_topup_c)
    ]), [out_prepare_topup_c, out_cat_ap_pa_c, in_run_topup_c, out_run_topup_c]


def denoised_b0_block(channel_in, output_root, output_prefix="data", masked_data=True, verbose=True):
    init_mean_B0 = ExtractB0Process(
        join(output_root, "init_mean_B0", output_prefix),
        mean_post_proc=B0PostProcess.whole
    )
    out_init_mean_b0_c = Channel(["img"])

    unit_list = [create_unit(init_mean_B0, channel_in, out_init_mean_b0_c)]
    channel_list = [out_init_mean_b0_c]

    if masked_data:
        rigid_step, affine_step = ants_rigid_step(), ants_affine_step()
        global_params = ants_global_params()

        in_reg_t1_b0_c = create_connection([channel_in, out_init_mean_b0_c], ["img", "anat"])
        reg_t1_b0 = AntsRegisterProcess(
            join(output_root, "reg_t1_b0", output_prefix),
            [rigid_step, affine_step], global_params, verbose=verbose
        )
        out_reg_t1_b0_c = Channel(["ref", "affine"])

        in_reg_mask_c = create_connection([channel_in, out_reg_t1_b0_c], ["img", "ref", "affine"])
        reg_mask = AntsApplyTransformProcess(
            join(output_root, "reg_t1_b0", output_prefix),
            interpolation="NearestNeighbor",
            verbose=verbose
        )
        out_reg_mask_c = Channel(["img"])

        unit_list += [
            create_unit(reg_t1_b0, in_reg_t1_b0_c, out_reg_t1_b0_c),
            create_unit(reg_mask, in_reg_mask_c, out_reg_mask_c)
        ]

        in_denoise_b0_c = create_connection([channel_in, out_reg_mask_c], ["img", "mask"])

        channel_list += [
            in_reg_t1_b0_c, out_reg_t1_b0_c, in_reg_mask_c, out_reg_mask_c
        ]
    else:
        in_denoise_b0_c = out_init_mean_b0_c

    denoise_b0 = DenoiseProcess(join(output_root, "b0_denoised", output_prefix))
    out_denoise_b0_c = Channel(["img"])

    unit_list.append(create_unit(denoise_b0, in_denoise_b0_c, out_denoise_b0_c))
    channel_list.append(out_denoise_b0_c)

    return Block(unit_list), channel_list
