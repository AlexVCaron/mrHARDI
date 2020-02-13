from multiprocessing import cpu_count, Process
import time
import tqdm


class Scheduler:
    def __init__(self):
        self._phases = {}
        self._num_phases = 0
        self._n_cores = cpu_count()

    def add_phase(self, name, processes, sequential=False):
        self._num_phases += 1
        self._phases[self._num_phases] = {
            "name": name,
            "processes": processes,
            "concurrent": not sequential
        }

    def execute(self):
        phases = sorted(self._phases.keys())
        for phase in phases:
            self._execute_phase(phase)

    def _execute_phase(self, key):
        phase = self._phases[key]

        print("Executing {} phase".format(phase["name"]))

        if phase["concurrent"]:
            self._execute_concurrent(phase)
        else:
            for process in phase["processes"]:
                print("  - Running process {}".format(process.name))
                process.execute()
                process.wait()

        print("Phase completed")

    def _execute_concurrent(self, phase):
        jobs = []
        processes = sorted(phase["processes"], key=lambda p: p.n_cores)
        n_cores = 0
        n_to_run = len(phase["processes"])
        with tqdm.tqdm(total=n_to_run) as pbar:
            while n_to_run > 0:
                if len(processes) > 0 and processes[0].n_cores + n_cores <= self._n_cores:
                    n_cores += processes[0].n_cores
                    jobs.append([Process(target=processes[0].execute), len(jobs), True, processes[0].n_cores])
                    jobs[-1][0].start()
                    processes = processes[1:]
                else:
                    while True:
                        ended = [job for job in jobs if not job[0].is_alive() and job[2]]
                        if len(ended) == 0:
                            time.sleep(1)
                        else:
                            for job in ended:
                                if jobs[job[1]][2]:
                                    n_cores -= job[-1]
                                    n_to_run -= 1
                                    jobs[job[1]][2] = False
                                    pbar.update(1)
                            break
