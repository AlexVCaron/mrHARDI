import asyncio
import logging

from os.path import join
from tempfile import TemporaryDirectory
from unittest import TestCase

from piper.comm import Subscriber, Channel, CloseCondition
from piper.pipeline import Unit

from helpers.data import load_dwi_repetition, DATA_KEYS
from monkey_io import DirDataset, Dataloader
from monkey_io.io_process import PythonIOProcess

from scripts.generate_fake_dir_dataset import generate_fake_dir_dataset


logging.basicConfig(level="DEBUG")


class CreateAndAssertProcess(PythonIOProcess):
    def __init__(
        self, output_prefix, metadata_check_fn, name="create_assert_process"
    ):
        super().__init__(name, output_prefix, DATA_KEYS)
        self._meta_check = metadata_check_fn

    @property
    def required_output_keys(self):
        return DATA_KEYS

    def _execute(self, *args, **kwargs):
        assert self.metadata, "Process must have metadata"
        self._output_package.update(dict(zip(DATA_KEYS, self._input)))
        self._meta_check(self.metadata, self)


class TestIOProcess(TestCase):
    def setUp(self):
        self.test_data_dir = TemporaryDirectory()
        self.test_res_dir = TemporaryDirectory()
        self.loop = asyncio.new_event_loop()

    def tearDown(self):
        self.test_data_dir.cleanup()
        self.test_res_dir.cleanup()
        self.loop.close()

    def test_subject_meta_passed(self):
        def check_meta(meta, proc):
            base_prefix = self.test_res_dir.name
            awaited_prefix = join(base_prefix, proc.prefix_unpacker(meta))
            output_prefix = proc.get_outputs()["prefix"]
            assert output_prefix == awaited_prefix
            assert proc.path_prefix == awaited_prefix

        generate_fake_dir_dataset(
            self.test_data_dir.name, 10, 10, (10, 10, 10, 5), int
        )

        dataset = DirDataset(
            self.test_data_dir.name, 3, load_dwi_repetition, None,
            lambda subject, sub_dir: join(
                sub_dir, "{}_anat.nii.gz".format(subject)
            ),
            lambda subject, sub_dir: join(
                sub_dir, "{}_mask.nii.gz".format(subject)
            )
        )

        end_cnd = CloseCondition()
        dataloader = Dataloader([dataset], DATA_KEYS)
        output = Channel(DATA_KEYS, name="output_channel")
        out_sub = Subscriber(name="output_subscriber")
        output.add_subscriber(out_sub, Channel.Sub.OUT)

        process = CreateAndAssertProcess(self.test_res_dir.name, check_meta)

        unit = Unit(process, self.test_res_dir.name)
        unit.connect_input(dataloader)
        unit.connect_output(output)

        proc_task = self.loop.create_task(unit.process())
        dequeue_task = self.loop.create_task(self._dequeue_output(out_sub))

        dataloader.start(lambda: end_cnd)
        output.start()

        self.loop.run_until_complete(proc_task)
        end_cnd.set()
        self.loop.run_until_complete(dequeue_task)

    async def _dequeue_output(self, sub):
        while sub.promise_data():
            try:
                await sub.yield_data()
            except asyncio.CancelledError:
                pass
