# class TestPythonProcess(ProcessTestBase, TestCase):
#     def setUp(self):
#         self.process = AssertPythonProcess(
#             join(self.test_dir.name, "test_python_proc"),
#             self.payload[1]
#         )
#
#
# class TestShellProcess(ShellProcessTestBase, TestCase):
#     def __init__(self, *args, **kwargs):
#         ShellProcessTestBase.__init__(self)
#         TestCase.__init__(self, *args, **kwargs)
#
#     def setUp(self):
#         script, output = self._get_script()
#
#         self.process = AssertShellProcess(
#             script, join(self.test_dir.name, "test_python_proc"),
#             self.payload[1], output, self._assert_shell
#         )
#
#     def test_execute(self):
#         self._execute()
#         self._assert_shell()


# class TestProcess(TestCase):
#     def test_set_process_launcher(self):
#         self.fail()
#
#     def test_set_inputs(self):
#         self.fail()
#
#     def test_get_outputs(self):
#         self.fail()
#
#     def test_name(self):
#         self.fail()
#
#     def test_n_cores(self):
#         self.fail()
#
#     def test_execute(self):
#         self.fail()
