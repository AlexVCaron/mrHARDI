import time
import sys
import traceback
from io import UnsupportedOperation
from multiprocessing import Queue
from queue import Empty, Full
from subprocess import CalledProcessError, PIPE, Popen
from threading import Thread


def _threaded_enqueue_pipe(process, pipe, queue):
    try:
        while process.poll() is None:
            ln = pipe.read1()
            if ln:
                queue.put(ln)
            else:
                time.sleep(1)
    except Full:
        time.sleep(1)
        _threaded_enqueue_pipe(process, pipe, queue)


def _dequeue_pipe(log_file, queue, tag, sys_stream, stream_end_eol=True):
    ln = None
    try:
        while not queue.empty():
            ln = queue.get_nowait().decode("ascii").split("\n")
            if ln:
                wr = "\n".join(
                    "[{}] {}".format(tag, l) if l else "" for l in ln
                )
                if not stream_end_eol:
                    wr = wr[3 + len(tag):]
                stream_end_eol = (ln[-1] == '')
                sys_stream.write(wr)
                sys_stream.flush()
                log_file.write(wr)
                log_file.flush()
    except Empty:
        time.sleep(1)
        _dequeue_pipe(log_file, queue, tag, sys_stream, stream_end_eol)
    except BlockingIOError:
        print("Cannot output log to file :\n{}".format(ln))
    except UnsupportedOperation:
        print("Unsupported operation on {}".format(log_file))
        print("Cannot output log to file :\n{}".format(ln))

    return stream_end_eol

def process_pipes_to_log_file(
    process, log_file_path, poll_timer=4, logging_callback=lambda a: None
):
    stdout_queue = Queue()
    stderr_queue = Queue()

    t1 = Thread(
        target=_threaded_enqueue_pipe,
        args=(process, process.stdout, stdout_queue)
    )
    t1.daemon = True
    t1.start()

    t2 = Thread(
        target=_threaded_enqueue_pipe,
        args=(process, process.stderr, stderr_queue)
    )
    t2.daemon = True
    t2.start()

    std_eol, err_eol = True, True

    with open(log_file_path, "a+") as log_file:
        while process.poll() is None:
            std_eol = _dequeue_pipe(
                log_file, stdout_queue, "STD", sys.stdout, std_eol
            )
            err_eol = _dequeue_pipe(
                log_file, stderr_queue, "ERR", sys.stderr, err_eol
            )

            logging_callback(log_file_path)
            time.sleep(poll_timer)

        _dequeue_pipe(log_file, stdout_queue, "STD", sys.stdout, std_eol)
        _dequeue_pipe(log_file, stderr_queue, "ERR", sys.stderr, err_eol)

        logging_callback(log_file_path)


def basic_error_manager(process):
    raise CalledProcessError(
        process.returncode, process.args, stderr=process.stderr
    )


def launch_shell_process(
    command, log_file_path, overwrite=False, sleep=4, logging_callback=None,
    init_logger=None, error_manager=basic_error_manager, **_
):
    with open(log_file_path, "w+" if overwrite else "a+") as log_file:
        log_file.write("Running command {}\n".format(command))

    process = None

    try:
        try:
            process = Popen(
                command.split(" "),
                stdout=PIPE,
                stderr=PIPE
            )
        except FileNotFoundError as e:
            e.filename = command
            raise e

        if init_logger:
            init_logger(log_file_path)

        logging_args = (process, log_file_path, sleep)
        if logging_callback:
            logging_args += (logging_callback,)

        log_thread = Thread(
            target=process_pipes_to_log_file, args=logging_args
        )
        log_thread.daemon = True
        log_thread.start()
        log_thread.join()

        if process.returncode != 0:
            with open(log_file_path, "a+") as log_file:
                log_file.write(
                    "[ERR] Process ended in error. Return code : {}\n".format(
                        process.returncode
                    )
                )
                log_file.write("[ERR] Traceback :\n")
                log_file.write("\n".join([
                    "[ERR]    {}".format(t)
                    for t in traceback.format_exc().split("\n")
                ]))
                log_file.flush()

            error_manager(process)

        process.stdout.close()
        process.stderr.close()

    except CalledProcessError as e:
        with open(log_file_path, "a+") as log_file:
            log_file.write("Error : Code {}\n".format(e))
            log_file.flush()

        if process:
            process.stdout.close()
            process.stderr.close()

        raise e


def test_process_launcher(command, *args, **kwargs):
    print("Command {} :".format(command))
    print("   - Arguments : {}".format(args))
    print("   - Special arguments : {}".format(kwargs))
