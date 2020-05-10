from multiprocessing import Queue
from subprocess import Popen, PIPE, CalledProcessError, SubprocessError
import time
import traceback
from threading import Thread


def enqueue_thread_output(process, pipe, queue):
    while process.poll() is None:
        ln = pipe.readline()
        queue.put(ln)


def dequeue_output(log_file, queue, tag):
    try:
        while not queue.empty():
            ln = queue.get_nowait()
            log_file.write("\n".join(["[{}] {}".format(tag, l) for l in ln.decode("ascii").strip().split("\n")]) + "\n")
            log_file.flush()
    except:
        pass


def read_output(process, log_file_path, poll_timer=4, logging_callback=lambda a: None):
    stdout_queue = Queue()
    stderr_queue = Queue()
    t1 = Thread(target=enqueue_thread_output, args=(process, process.stdout, stdout_queue))
    t1.daemon = True
    t1.start()
    t2 = Thread(target=enqueue_thread_output, args=(process, process.stderr, stderr_queue))
    t2.daemon = True
    t2.start()

    with open(log_file_path, "a+") as log_file:
        while process.poll() is None:
            dequeue_output(log_file, stdout_queue, "STD")
            dequeue_output(log_file, stderr_queue, "ERR")

            logging_callback(log_file_path)
            time.sleep(poll_timer)


def basic_error_manager(process):
    raise CalledProcessError(process.returncode, process.args, stderr=process.stderr)


def launch_shell_process(command, log_file_path, keep_log=False, poll_timer=4, logging_callback=None, init_logger=None, error_manager=basic_error_manager):
    with open(log_file_path, "a+" if keep_log else "w+") as log_file:
        log_file.write("Running command {}\n".format(command))

    process = None

    try:
        process = Popen(
            command.split(" "),
            stdout=PIPE,
            stderr=PIPE
        )

        if init_logger:
            init_logger(log_file_path)

        logging_args = (process, log_file_path, poll_timer)
        if logging_callback:
            logging_args += (logging_callback,)

        log_thread = Thread(target=read_output, args=logging_args)
        log_thread.daemon = True
        log_thread.start()
        log_thread.join()

        if process.returncode != 0:
            with open(log_file_path, "a+") as log_file:
                log_file.write("[ERR] Process ended in error. Return code : {}\n".format(process.returncode))
                log_file.write("[ERR] Traceback :\n")
                log_file.write(
                    "\n".join(["[ERR]    {}".format(t) for t in traceback.format_exc().split("\n")])
                )

            error_manager(process)

        process.stdout.close()
        process.stderr.close()

    except SubprocessError as e:
        with open(log_file_path, "a+") as log_file:
            log_file.write("Error : {}\n".format(e))

        if process:
            process.stdout.close()
            process.stderr.close()

        raise e


def launch_singularity_process(command, log_file_path, keep_log=False, poll_timer=4, logging_callback=None, init_logger=None, error_manager=basic_error_manager, container=None, bind_paths=None):
    command = "singularity exec -B {} {} {}".format(",".join(bind_paths), container, command)
    launch_shell_process(command, log_file_path, keep_log, poll_timer, logging_callback, init_logger, error_manager)


def launch_python_process(method, *args, **kwargs):
    return method(*args, **kwargs)
