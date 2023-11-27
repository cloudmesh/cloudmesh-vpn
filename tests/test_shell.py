###############################################################
# pytest -v --capture=no  tests/test_shell.py
# pytest -v tests/test_shell.py
# pytest -v --capture=no  tests/test_shell.py::Test_shell.test_001
###############################################################
import getpass
import subprocess

from cloudmesh.common.Shell import Shell
from cloudmesh.common.util import HEADING
from cloudmesh.common.systeminfo import os_is_windows
from cloudmesh.common.Benchmark import Benchmark
import pytest


def run(command):
    parameter = command.split(" ")
    shell_command = parameter[0]
    args = parameter[1:]
    result = Shell.execute(shell_command, args)
    return str(result)



@pytest.mark.incremental
class Test_shell(object):
    """

    """

    def setup_method(self):
        pass

    def test_vpn(self):
        HEADING()
        Benchmark.Start()
        r1 = Shell.cms('vpn status')
        r2 = Shell.cms('echo -r blue "hello"')
        print(r1)
        print(r2)
        Benchmark.Stop()
        assert 'True' or 'False' in r1
        assert 'hello' in r2


