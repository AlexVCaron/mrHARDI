from subprocess import Popen, PIPE, STDOUT


def init_gpu_logger(log_file_name):
    cuda_log_file = "{}_cuda_trace.{}".format(*(log_file_name.split(".")))
    with open(cuda_log_file, "w+") as f:
        f.write("Logging cuda activity for {}".format(log_file_name.split("/")[-1].split(".")[0]))


def log_gpu_usage_callback(log_file_name):
    process = Popen(
        "nvidia-smi",
        stdout=PIPE,
        stderr=STDOUT
    )

    cuda_log_file = "{}_cuda_trace.{}".format(*(log_file_name.split(".")))

    stdout, stderr = process.communicate()

    line_of_interest = stdout.decode("ascii").split("\n")[8].split("|")
    ram_usage = line_of_interest[2].strip(" ")
    gpu_usage = line_of_interest[3].strip(" ").strip("Default").strip(" ")
    with open(cuda_log_file, "a+") as log_file:
        log_file.write("===> GPU USAGE : [VRAM] {} [VPROC] {}\n".format(ram_usage, gpu_usage))
