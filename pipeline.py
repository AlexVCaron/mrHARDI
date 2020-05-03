import json
from os import getcwd, makedirs
from os.path import join
from functools import partial
import numpy as np

from magic_monkey.dataloader import Dataloader
from multiprocess.gpu.cuda_logger import log_gpu_usage_callback
from multiprocess.scheduler import Scheduler
from multiprocess.shell.shell_process import launch_shell_process, launch_python_process, launch_singularity_process
from processes.apply_mask_process import ApplyMaskProcess
from processes.compute_mask_process import ComputeMaskProcess
from processes.preprocess.preprocess import ExtractB0Process, B0PostProcess, \
    ConcatenateDatasets, SquashB0Process
from processes.preprocess.denoise import DenoiseProcess, PrepareTopupProcess, \
    TopupProcess, PrepareEddyProcess, EddyProcess
from processes.preprocess.register import AntsApplyTransformProcess, AntsRegisterProcess, ants_rigid_step, ants_affine_step, ants_syn_step, ants_global_params
from processes.reconstruction.dti import DTIProcess, ComputeFAProcess
from processes.utils.copy_files_process import CopyFilesProcess

config = json.load(open(join(getcwd(), "config.json")))

singularity_process_launcher = partial(
    launch_singularity_process,
    container=config["singularity"],
    bind_paths=config["base_paths"]
)


class StepsLibrary:
    eddy = singularity_process_launcher
    topup = singularity_process_launcher
    mrtrix_denoise = launch_shell_process
    extract_b0 = launch_python_process
    ants_register = launch_shell_process
    concatenation = launch_python_process
    bet = launch_shell_process
    squash = launch_python_process
    prepare_scripts = launch_python_process
    copy = launch_python_process


dataloader = Dataloader(config["datasets"])
dataloader.load_mask(config)

datasets = dataloader.get_data("DWI")
t1_data = dataloader.get_data("T1")[0]
mask_data = dataloader.get_mask()[0]

scheduler = Scheduler()

for path in config["process_paths"].values():
    makedirs(path, exist_ok=True)

# Extract mean B0 of each dataset
mean_b0_datasets = [{
    "path": config["process_paths"]["b0_extract"],
    "name": "{}_mean_b0.{}".format(d["name"].split(".")[0], ".".join(d["name"].split(".")[1:])),
    "direction": d["direction"] if "direction" in d else None
} for d in datasets]

mean_b0_processes = [
    ExtractB0Process(
        join(in_data["path"], in_data["name"]), join(in_data["path"], in_data["bvals"]),
        join(out_data["path"], out_data["name"]), mean_post_proc=B0PostProcess.whole
    ).set_process_launcher(
        partial(
            StepsLibrary.extract_b0,
            log_file_path=join(out_data["path"], out_data["name"]).split(".")[0] + ".log"
        ))
    for in_data, out_data in zip(datasets, mean_b0_datasets)
]

# Pre-register T1 to b0 for each dataset (Rigid + Affine)
t1_registered = [{
    "path": config["process_paths"]["t1_register"],
    "name": "{}_t1".format(d["name"].split(".")[0])
} for d in datasets]

rigid_step, affine_step = ants_rigid_step(), ants_affine_step()
global_params = ants_global_params()

t1_register_processes = [
    AntsRegisterProcess(
        join(b0_img["path"], b0_img["name"]), join(t1_data["path"], t1_data["name"]),
        join(out_data["path"], out_data["name"]), [rigid_step, affine_step], global_params, verbose=True
    ).set_process_launcher(
        partial(
            StepsLibrary.ants_register,
            log_file_path=join(out_data["path"], out_data["name"]).split(".")[0] + ".log"
        ))
    for b0_img, out_data in zip(mean_b0_datasets, t1_registered)
]

# Register T1 brain mask to diffusion (Rigid + Affine)
mask_registered = [{
    "path": config["process_paths"]["mask_register"],
    "name": "{}_brain_mask.{}".format(d["name"].split(".")[0], ".".join(d["name"].split(".")[1:]))
} for d in datasets]

mask_register_processes = [
    AntsApplyTransformProcess(
        mask_data,
        (join(t1_transform["path"], "{}0GenericAffine.mat".format(t1_transform["name"])), False),
        join(t1_transform["path"], "{}Warped.nii.gz".format(t1_transform["name"])),
        join(out_mask["path"], out_mask["name"]),
        interpolation="NearestNeighbor",
        verbose=True
    ).set_process_launcher(
        partial(
            StepsLibrary.ants_register,
            log_file_path=join(out_mask["path"], out_mask["name"]).split(".")[0] + ".log"
        ))
    for t1_transform, out_mask in zip(t1_registered, mask_registered)
]

# Denoising processing
denoise_datasets = [{
    "path": config["process_paths"]["denoise"],
    "name": "{}_denoised.{}".format(d["name"].split(".")[0], ".".join(d["name"].split(".")[1:])),
    "direction": d["direction"] if "direction" in d else None,
    "bvals": "{}_denoised.bvals".format(d["name"].split(".")[0]),
    "bvecs": "{}_denoised.bvecs".format(d["name"].split(".")[0])
} for d in datasets]

files_in, files_out = [], []

for dt, den_dt in zip(datasets, denoise_datasets):
    files_in.append(join(dt["path"], dt["bvals"]))
    files_out.append(join(den_dt["path"], den_dt["bvals"]))
    files_in.append(join(dt["path"], dt["bvecs"]))
    files_out.append(join(den_dt["path"], den_dt["bvecs"]))

copy_for_denoise_process = [
    CopyFilesProcess(files_in, files_out).set_process_launcher(
        partial(
            StepsLibrary.copy,
            log_file_path=join(config["process_paths"]["denoise"], "copy_for_denoise.log")
        ))
]

denoise_processes = [
    DenoiseProcess(
        join(in_data["path"], in_data["name"]),
        join(out_data["path"], out_data["name"]),
        join(mask_data["path"], mask_data["name"])
    ).set_process_launcher(
        partial(
            StepsLibrary.mrtrix_denoise,
            log_file_path=join(out_data["path"], out_data["name"]).split(".")[0] + ".log"
        ))
    for in_data, out_data, mask_data in zip(datasets, denoise_datasets, mask_registered)
]

# Extract mean b0 clusters
mean_b0_clusters_datasets = [{
    "path": config["process_paths"]["topup"],
    "name": "{}_b0_clusters.{}".format(d["name"].split(".")[0], ".".join(d["name"].split(".")[1:])),
    "direction": d["direction"] if "direction" in d else None
} for d in datasets]

mean_b0_clusters_processes = [
    ExtractB0Process(
        join(in_data["path"], in_data["name"]), join(in_data["path"], in_data["bvals"]),
        join(out_data["path"], out_data["name"]), mean_post_proc=B0PostProcess.batch
    ).set_process_launcher(
        partial(
            StepsLibrary.extract_b0,
            log_file_path=join(out_data["path"], out_data["name"]).split(".")[0] + ".log"
        ))
    for in_data, out_data in zip(denoise_datasets, mean_b0_clusters_datasets)
]

# Prepare Topup command
AP_b0_datasets = list(filter(lambda dt: dt["direction"] == "AP", mean_b0_clusters_datasets))
PA_b0_datasets = list(filter(lambda dt: dt["direction"] == "PA", mean_b0_clusters_datasets))

topup_dataset = {
    "path": config["process_paths"]["topup"],
    "name": "clustered_b0"
}

prepare_topup_process = [
    PrepareTopupProcess(
        [join(dt["path"], dt["name"]) for dt in AP_b0_datasets],
        [join(dt["path"], dt["name"]) for dt in PA_b0_datasets],
        join(topup_dataset["path"], topup_dataset["name"]), 0.06248
    ).set_process_launcher(
        partial(
            StepsLibrary.prepare_scripts,
            log_file_path=join(topup_dataset["path"], "prepare_topup_{}".format(topup_dataset["name"])) + ".log"
        ))
]

# Concatenate all b0s together interleaved
interleaved_b0_datasets = [dt for pair in zip(AP_b0_datasets, PA_b0_datasets) for dt in pair]

concatenate_process = [
    ConcatenateDatasets(
        [join(dt["path"], dt["name"]) for dt in interleaved_b0_datasets],
        join(topup_dataset["path"], topup_dataset["name"])
    ).set_process_launcher(
        partial(
            launch_python_process,
            log_file_path=join(topup_dataset["path"], "concatenate_{}".format(topup_dataset["name"])) + ".log"
        ))
]

# Run topup process
topup_process = [
    TopupProcess(
        join(topup_dataset["path"], "{}_topup_command.sh".format(topup_dataset["name"])),
        join(topup_dataset["path"], "{}.nii.gz".format(topup_dataset["name"]))
    ).set_process_launcher(
        partial(
            StepsLibrary.topup,
            log_file_path=join(topup_dataset["path"], "run_topup_{}".format(topup_dataset["name"])) + ".log"
        ))
]

# Compute high-res b0 mask for diffusion
high_res_b0_mask_process = [
    ComputeMaskProcess(
        join(topup_dataset["path"], "{}_topup_unwarped.nii.gz".format(topup_dataset["name"])),
        join(topup_dataset["path"], topup_dataset["name"])
    ).set_process_launcher(
        partial(
            StepsLibrary.bet,
            log_file_path=join(topup_dataset["path"], "extract_high_res_mask_{}".format(topup_dataset["name"])) + ".log"
        ))
]

# Concatenate interleaved AP PA datasets ((len(AP) + len(PA)) / 2 output)
AP_datasets = list(filter(lambda dt: dt["direction"] == "AP", datasets))
PA_datasets = list(filter(lambda dt: dt["direction"] == "PA", datasets))

concatenated_for_eddy_datasets = [{
    "path": config["process_paths"]["eddy"],
    "name": "{}_CAT_{}.{}".format(dt_ap["name"].split(".")[0], dt_pa["name"].split(".")[0], ".".join(dt_ap["name"].split(".")[1:])),
    "bvals": "{}_CAT_{}.bvals".format(dt_ap["name"].split(".")[0], dt_pa["name"].split(".")[0]),
    "bvecs": "{}_CAT_{}.bvecs".format(dt_ap["name"].split(".")[0], dt_pa["name"].split(".")[0])
} for dt_ap, dt_pa in zip(AP_datasets, PA_datasets)]

concatenate_dwi_process = [
    ConcatenateDatasets(
        [join(dt["path"], dt["name"]) for dt in dts],
        join(output["path"], output["name"]),
        [join(dt["path"], dt["bvals"]) for dt in dts],
        [join(dt["path"], dt["bvecs"]) for dt in dts]
    ).set_process_launcher(
        partial(
            StepsLibrary.concatenation,
            log_file_path=join(output["path"], "concatenate_datasets_for_{}".format(output["name"])) + ".log"
        ))
    for dts, output in zip(zip(AP_datasets, PA_datasets), concatenated_for_eddy_datasets)
]

squash_b0_for_eddy_datasets = [{
    "path": config["process_paths"]["eddy"],
    "name": "squashed_b0_{}.{}".format(dataset["name"].split(".")[0], ".".join(dataset["name"].split(".")[1:])),
    "bvals": "squashed_b0_{}.bvals".format(dataset["name"].split(".")[0]),
    "bvecs": "squashed_b0_{}.bvecs".format(dataset["name"].split(".")[0])
} for dataset in concatenated_for_eddy_datasets]

squash_dwi_process = [
    SquashB0Process(
        join(dt["path"], dt["name"]),
        join(dt["path"], dt["bvals"]),
        join(dt["path"], dt["bvecs"]),
        join(output["path"], output["name"]),
        dtype=np.float32
    ).set_process_launcher(
        partial(
            StepsLibrary.squash,
            log_file_path=join(output["path"], "squash_b0_for_{}".format(dt["name"])) + ".log"
        ))
    for dt, output in zip(concatenated_for_eddy_datasets, squash_b0_for_eddy_datasets)
]

# Prepare eddy parameters and scrips
eddy_script_prefix = join(config["process_paths"]["eddy"], "splitted_compute_gpu")

prepare_eddy_process = [
    PrepareEddyProcess(
        [join(dt["path"], dt["bvals"]) for dt in squash_b0_for_eddy_datasets],
        join(topup_dataset["path"], "{}_topup_params.txt".format(topup_dataset["name"])),
        eddy_script_prefix,
        use_cuda=True
    ).set_process_launcher(
        partial(
            StepsLibrary.prepare_scripts,
            log_file_path=join(config["process_paths"]["eddy"], "prepare_eddy_command.log")
        ))
]

# Run eddy on concatenated APPA
eddy_datasets = [{
    "path": config["process_paths"]["eddy"],
    "name": "{}_eddy_corrected.{}".format(dt["name"].split(".")[0], ".".join(dt["name"].split(".")[1:]))
} for dt in concatenated_for_eddy_datasets]

run_eddy_process = [
    EddyProcess(
        "{}_eddy_command.sh".format(eddy_script_prefix),
        join(in_eddy["path"], in_eddy["name"]),
        join(in_eddy["path"], in_eddy["bvals"]),
        join(in_eddy["path"], in_eddy["bvecs"]),
        join(topup_dataset["path"], "{}_mask.nii.gz".format(topup_dataset["name"])),
        join(out_eddy["path"], "{}_index.txt".format(in_eddy["bvals"].split("/")[-1].split(".")[0])),
        join(topup_dataset["path"], topup_dataset["name"]),
        join(out_eddy["path"], out_eddy["name"])
    ).set_process_launcher(
        partial(
            StepsLibrary.eddy,
            log_file_path=join(out_eddy["path"], "run_eddy_on_{}".format(in_eddy["name"].split(".")[0])) + ".log",
            poll_timer=1,
            logging_callback=log_gpu_usage_callback
        ))
    for in_eddy, out_eddy in zip(squash_b0_for_eddy_datasets, eddy_datasets)
]

# Concatenate all DWI datasets interleaved
# interleaved_datasets = [dt for pair in zip(AP_datasets, PA_datasets) for dt in pair]
#
# concatenate_dwi_process = [
#     ConcatenateDatasets(
#         [join(dt["path"], dt["name"]) for dt in interleaved_datasets],
#         join(eddy_dataset["path"], "cat_APPA_for_{}".format(eddy_dataset["name"])),
#         [join(dt["path"], dt["bvals"]) for dt in interleaved_datasets],
#         [join(dt["path"], dt["bvecs"]) for dt in interleaved_datasets]
#     ).set_process_launcher(
#         partial(
#             launch_python_process,
#             log_file_path=join(eddy_dataset["path"], "concatenate_datasets_for_{}".format(eddy_dataset["name"])) + ".log"
#         ))
# ]

# Apply DTI reconstruction to datasets for SyN registration
reg_dti_datasets = [{
    "path": config["process_paths"]["t1_register_syn"],
    "name": "{}_dti.{}".format(d["name"].split(".")[0], ".".join(d["name"].split(".")[1:]))
} for d in datasets]

reg_dti_processes = [
    DTIProcess(
        join(dwi["path"], dwi["name"]),
        join(dwi["path"], dwi["bvals"]),
        join(dwi["path"], dwi["bvecs"]),
        join(dti["path"], dti["name"]),
        mask=join(mask["path"], mask["name"])
    ).set_process_launcher(
        partial(
            launch_shell_process,
            log_file_path=join(dti["path"], dti["name"]).split(".")[0] + ".log"
        ))
    for dwi, mask, dti in zip(denoise_datasets, mask_registered, reg_dti_datasets)
]

# Compute FA on DTI reconstructions
reg_fa_datasets = [{
    "path": config["process_paths"]["t1_register_syn"],
    "name": "{}_fa.{}".format(d["name"].split(".")[0], ".".join(d["name"].split(".")[1:]))
} for d in datasets]

reg_fa_processes = [
    ComputeFAProcess(
        join(in_dt["path"], in_dt["name"]),
        join(out_fa["path"], out_fa["name"]),
        mask=join(mask["path"], mask["name"])
    ).set_process_launcher(
        partial(
            launch_python_process,
            log_file_path=join(out_fa["path"], out_fa["name"]).split(".")[0] + ".log"
        ))
    for in_dt, mask, out_fa in zip(reg_dti_datasets, mask_registered, reg_fa_datasets)
]

# Extract T1 brain for syn
masked_t1_registered = [{
    "path": config["process_paths"]["t1_register_syn"],
    "name": "{}_masked_t1.{}".format(d["name"].split(".")[0], ".".join(d["name"].split(".")[1:]))
} for d in datasets]

masked_t1_registered_processes = [
    ApplyMaskProcess(
        join(in_t1["path"], "{}Warped.nii.gz".format(in_t1["name"])),
        join(in_mask["path"], in_mask["name"]),
        join(out_t1["path"], out_t1["name"])
    ).set_process_launcher(
        partial(
            launch_python_process,
            log_file_path=join(out_t1["path"], out_t1["name"]).split(".")[0] + ".log"
    ))
    for in_t1, in_mask, out_t1 in zip(t1_registered, mask_registered, masked_t1_registered)
]

# Extract B0 brain for SyN
masked_b0_registered = [{
    "path": config["process_paths"]["t1_register_syn"],
    "name": "{}_masked_b0.{}".format(d["name"].split(".")[0], ".".join(d["name"].split(".")[1:]))
} for d in datasets]

masked_b0_registered_processes = [
    ApplyMaskProcess(
        join(in_b0["path"], in_b0["name"]),
        join(in_mask["path"], in_mask["name"]),
        join(out_b0["path"], out_b0["name"])
    ).set_process_launcher(
        partial(
            launch_python_process,
            log_file_path=join(out_b0["path"], out_b0["name"]).split(".")[0] + ".log"
    ))
    for in_b0, in_mask, out_b0 in zip(mean_b0_datasets, mask_registered, masked_b0_registered)
]

# Register T1 to b0/FA SyN
t1_syn_registered = [{
    "path": config["process_paths"]["t1_register_syn"],
    "name": "{}_syn_t1".format(d["name"].split(".")[0])
} for d in datasets]

ants_syn = ants_syn_step(n_in_for_metric=2)

t1_syn_register_process = [
    AntsRegisterProcess(
        [join(in_b0["path"], in_b0["name"]), join(in_fa["path"], in_fa["name"])],
        [join(in_t1["path"], in_t1["name"]), join(in_t1["path"], in_t1["name"])],
        join(out_t1["path"], out_t1["name"]),
        ants_syn, global_params, verbose=True
    ).set_process_launcher(
        partial(
            launch_shell_process,
            log_file_path=join(out_t1["path"], out_t1["name"]).split(".")[0] + ".log"
        ))
    for in_t1, in_b0, in_fa, out_t1 in zip(masked_t1_registered, masked_b0_registered, reg_fa_datasets, t1_syn_registered)
]

# Apply SyN to mask
mask_syn_registered = [{
    "path": config["process_paths"]["mask_register"],
    "name": "{}_syn_brain_mask.{}".format(d["name"].split(".")[0], ".".join(d["name"].split(".")[1:]))
} for d in datasets]

# mask_syn_register_process = [
#     AntsApplyTransformProcess(
#
#     )
#     from in_mask, in_affine, in_ref, out_mask in zip(mask_registered, )
# ]

# scheduler.add_phase("Mean B0 extraction", mean_b0_processes)
# scheduler.add_phase("T1 registration (Rigid + Affine)", t1_register_processes)
# scheduler.add_phase("Mask registration to DWI (Rigid + Affine)", mask_register_processes)
# scheduler.add_phase("Denoising", copy_for_denoise_process + denoise_processes)
# scheduler.add_phase("Compute DTI for SyN registration", reg_dti_processes)
# scheduler.add_phase("Compute FA on DTI for SyN registration", reg_fa_processes)
# scheduler.add_phase("Apply mask to registered T1 and mean B0", masked_b0_registered_processes + masked_t1_registered_processes)
# scheduler.add_phase("Mean B0 cluster extraction", mean_b0_clusters_processes)
# scheduler.add_phase("Prepare topup and concatenate Mean B0 clusters", prepare_topup_process + concatenate_process)
scheduler.add_phase("Run topup", topup_process)
scheduler.add_phase("Concatenate dwi and compute bet mask for eddy", high_res_b0_mask_process + concatenate_dwi_process)
scheduler.add_phase("Squash b0 inside datasets for eddy", squash_dwi_process)
scheduler.add_phase("Prepare eddy command", prepare_eddy_process)
scheduler.add_phase("Run eddy", run_eddy_process)
# scheduler.add_phase("T1 registration (SyN)", t1_syn_register_process)

scheduler.execute()
