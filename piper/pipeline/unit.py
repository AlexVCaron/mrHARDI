import asyncio
import logging
from os.path import join

from piper.comm import Channel, Subscriber
from piper.drivers.shell import test_process_launcher
from piper.exceptions import UnexpectedUnitException, TransmitClosedException, \
    YieldClosedException
from .pipeline_item import PipelineItem


class Unit(PipelineItem):
    def __init__(self, process, log_file_root, name="unit", timeout=5):
        super().__init__(
            Subscriber("{}_sub_in".format(name)),
            Subscriber("{}_sub_out".format(name)),
            name
        )

        self._proc = process
        self._log = join(log_file_root, "{}.log".format(self._name))
        self._timeout = timeout
        self._cache = {}

    @property
    def serialize(self):
        return {**super().serialize, **{
            'log_file': self._log,
            'process': self._proc.serialize
        }}

    def get_process(self):
        return self._proc

    def set_test(self, on=True):
        if on and not self._test_mode:
            self._cache["launcher"] = self._proc.launcher
            self._proc.set_process_launcher(test_process_launcher)
        elif not on and self._test_mode:
            self._proc.set_process_launcher(self._cache["launcher"])
            self._cache["launcher"] = None

        super().set_test(on)

    def connect_input(self, channel, *args, **kwargs):
        channel.add_subscriber(self.input, Channel.Sub.OUT)
        return super().connect_input(channel)

    def connect_output(self, channel, *args, **kwargs):
        channel.add_subscriber(self.output, Channel.Sub.IN)
        return super().connect_input(channel)

    @property
    def package_keys(self):
        return self._proc.get_input_keys()

    def get_required_output_keys(self):
        return self._proc.get_required_output_keys()

    async def process(self):
        while self.input.promise_data():
            try:
                logger.error("{} awaiting data".format(self._name))
                id_tag, in_package = await self.input.yield_data()
                outputs = self._digest(in_package)
                logger.error("{} transmitting data".format(self._name))
                await self.output.transmit(id_tag, outputs)
                logger.error("{} transmitted data".format(self._name))
            except TransmitClosedException as e:
                logger.error(
                    "{} output closed before end, killing unit".format(
                        self._name
                    )
                )
                raise e
            except YieldClosedException:
                logger.error("{} input flow shutdown".format(self._name))
                break
            except asyncio.CancelledError:
                logger.error(
                    "{} process task cancelled".format(self._name)
                )
                break
            except BaseException as e:
                logger.error("Unit {} received unexpected error\n{}".format(
                    self._name, str(e)
                ))
                await self.output.shutdown(True)
                raise UnexpectedUnitException(self, e)

        logger.error("{} shutting down outputs".format(self._name))
        await self.output.shutdown()
        logger.info("{} processing complete".format(self._name))

    async def wait_for_shutdown(self):
        if not self.output.done():
            await self.output.wait_for_completion()
        logger.error(
            "{} done waiting on output subscriber".format(self.name)
        )

    def _digest(self, in_package):
        logger.debug("{} received data".format(self._name))
        self._proc.set_inputs(in_package)
        logger.info("{} executing process".format(self._name))
        self._proc.execute(self._log)
        return self._proc.get_outputs()


logger = logging.getLogger(Unit.__name__)


def create_unit(process, log_file_path, channel_in, channel_out):
    return Unit(process, log_file_path).connect_input(channel_in) \
                                       .connect_output(channel_out)
