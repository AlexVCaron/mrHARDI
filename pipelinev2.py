import json
import os
import shutil

from piper.comm import Channel, ChannelFilter, Gatherer, Subscriber
from piper.executor.executor import Executor
from piper.pipeline import SequenceLayer, Pipeline, Unit

from blocks import registration_sequence, topup_sequence, eddy_sequence
from magic_monkey.b0_process import B0PostProcess
from monkey_io.dataloader import Dataloader
from monkey_io.dirdataset import DirDataset
from processes.preprocess.denoise import DenoiseProcess
from processes.preprocess.preprocess import ExtractB0Process
from processes.preprocess.register import ants_rigid_step, \
    ants_affine_step, \
    ants_global_params

root_directory = os.getcwd()
data_directory = os.path.join(root_directory, "data")
output_directory = os.path.join(root_directory, "output")

if os.path.exists(output_directory) and len(os.listdir(output_directory)) > 0:
    shutil.rmtree(output_directory)

os.makedirs(output_directory, exist_ok=True)

config = {
    "diff_mask": os.path.join(output_directory, "mask_to_diff"),
    "dwi_denoise": os.path.join(output_directory, "dwi_denoise")
}

for k, v in config.items():
    os.makedirs(v, exist_ok=True)

dwell_time = 1234


def load_repetition_fn(subject, repetition, repetition_path):
    base_name = os.path.join(
        repetition_path, "{}_".format(repetition) + "{}.{}"
    )
    rep_config = json.load(
        open(os.path.join(repetition_path, "rep_config.json"))
    )
    data = {
        "img": base_name.format("dwi", "nii.gz"),
        "bvals": base_name.format("dwi", "bvals"),
        "bvecs": base_name.format("dwi", "bvecs"),
        "dir": rep_config["acq_direction"]
    }

    if os.path.exists(base_name.format("mask", "nii.gz")):
        data["mask"] = base_name.format("mask", "nii.gz")
    if os.path.exists(base_name.format("anat", "nii.gz")):
        data["anat"] = base_name.format("anat", "nii.gz")

    return data


dataset = DirDataset(
    data_directory, 3, load_repetition_fn, None,
    lambda subject, sub_dir: os.path.join(
        sub_dir, "{}_anat.nii.gz".format(subject)
    ),
    lambda subject, sub_dir: os.path.join(
        sub_dir, "{}_mask.nii.gz".format(subject)
    )
)

dataloader = Dataloader([dataset], ["img", "mask", "bvals", "bvecs"])

# Get T1 mask to diffusion
b0_extract = ExtractB0Process(
    os.path.join(config["diff_mask"], "b0"), mean_post_proc=B0PostProcess.whole
)

t1_to_b0 = registration_sequence(
    Gatherer(
        lambda data: all(
            k in data for k in b0_extract.required_output_keys
        ),
        lambda data: {
            **{"img_from": data.pop("anat"), "img_to": data.pop("img")},
            **data
        },
        name="t1_to_b0_registration_input"
    ),
    os.path.join(config["diff_mask"], "reg"),
    [ants_rigid_step(), ants_affine_step()],
    ants_params=ants_global_params(),
    interpolation="NearestNeighbor",
    trans_img_key="mask"
)

# Initial denoising of data via Mrtrix dwidenoise
dwi_denoise = DenoiseProcess(os.path.join(config["dwi_denoise"], "dwidenoise"))

# Extract B0 hyper-volume by averaging over contiguous b0 volumes
b0_4D_extract = ExtractB0Process(
    os.path.join(config["dwi_denoise"], "b0"),
    mean_post_proc=B0PostProcess.batch
)

# Topup sequence on b0 volumes
b0_topup = topup_sequence(
    Gatherer(
        lambda data: len(data["dwi"]) == data["n_rep"][0],
        name="dwi_topup_input"
    ),
    os.path.join(config["dwi_denoise"], "topup"), dwell_time
)

# Eddy sequence on dwi volumes
dwi_eddy = eddy_sequence(
    Gatherer(
        lambda data: len(data["dwi"]) == data["n_rep"][0],
        name="dwi_eddy_input"
    ),
    b0_topup.output,
    os.path.join(config["dwi_denoise"], "eddy")
)


# Create preprocessing layer
preproc_layer = SequenceLayer(
    Channel(dataloader.package_keys, True, name="preproc_chan_in"),
    Channel(dataloader.package_keys, name="preproc_chan_out"),
    name="preproc_layer"
)

preproc_layer.add_unit(
    Unit(b0_extract, config["diff_mask"], name="b0_extract_unit")
)
preproc_layer.add_unit(t1_to_b0, [ChannelFilter(
    preproc_layer.input, excludes=b0_extract.required_output_keys
)])
preproc_layer.add_unit(
    Unit(dwi_denoise, config["dwi_denoise"], name="dwi_denoise_unit"),
    [ChannelFilter(preproc_layer.input, excludes=t1_to_b0.package_keys)]
)
preproc_layer.add_unit(
    Unit(b0_4D_extract, config["dwi_denoise"], name="b0_extract_4d")
)
preproc_layer.add_unit(b0_topup)
preproc_layer.add_unit(dwi_eddy)

output_collector = Channel(dwi_eddy.package_keys, name="pipe_out")
subscriber = Subscriber("output_subscriber")
output_collector.add_subscriber(subscriber, Channel.Sub.OUT)

pipeline = Pipeline(dataloader, output_collector)
pipeline.add_item(preproc_layer)

executor = Executor(pipeline, name="test_executor")
# executor.profile()
executor.execute_pipeline()


# with StatsManager(pipeline) as stm:
#     print(stm)

# pipeline.test_run(quiet=False)
# pipeline.run()
# items = loop.run_until_complete(collect_outputs(subscriber))
# loop.run_forever()
# pipeline.wait_for_completion()
# loop.stop()
# loop.close()
