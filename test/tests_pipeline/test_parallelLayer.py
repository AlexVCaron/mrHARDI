# from os.path import join
# from unittest import TestCase
#
# from multiprocess.pipeline.block import ParallelLayer
# from test.tests_pipeline.helpers.process import AssertPythonProcess
# from test.tests_pipeline.helpers.process_test_base import ProcessTestBase
#
#
# class TestParallelLayer(ProcessTestBase, TestCase):
#     def __init__(self, *args, **kwargs):
#         ProcessTestBase.__init__(self)
#         TestCase.__init__(self, *args, **kwargs)
#
#     def test_process(self):
#         processes = [AssertPythonProcess(
#             join(self.test_dir.name, "test_python_proc{}".format(i)),
#             self.payload[1]
#         ) for i in range(3)]
#
#         layer = ParallelLayer(processes)
#         layer.process()
