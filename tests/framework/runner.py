# Copyright 2019-2022 Alibaba Group Holding Limited.
# SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause

import os
from typing import Union, Tuple
from sh import grep, scp, ssh, rsync, ErrorReturnCode, RunningCommand
from lib import retry
import logging

class Runner:
    def __init__(self, script: str):
        self.script = script
        self.desc = '[ Script #%s ]' % script
        self.assert_panic = grep('# Expect: Panic', self.script, _ok_code=[0,1]).exit_code==0

    def _assert(self, result: Union[ErrorReturnCode, RunningCommand]) -> None:
        logging.info('Test %s stdout:\n%s', self.desc, result.stdout.strip())
        logging.info('Test %s stderr:\n%s', self.desc, result.stderr.strip())
        if result.exit_code:
            raise Exception("Test failed %s" % self.desc)

class RemoteRunner(Runner):
    def run_on_instance(self, host: str, port: str) -> None:
        old_boot_id = retry(ssh, 30, 'Connection refused',
            '-p', port, host, 'cat /proc/sys/kernel/random/boot_id').strip()
        logging.info("Reading original boot_id = %s", old_boot_id)

        root_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../')
        logging.info("Uploading plugsched to /tmp/plugsched/")
        retry(rsync, 30, 'Connection refused',
             '-e', 'ssh -p %s' % port, '-a', '--delete', root_path, '%s:/tmp/plugsched/' % host)

        logging.info("Uploading test %s", self.desc)
        retry(scp, 30, 'Connection refused',
            '-P', port, self.script, '%s:~/test.sh' % host)

        logging.info("Running test %s", self.desc)
        try:
            result = retry(ssh, 30, 'Connection refused',
                '-o', 'ServerAliveInterval=60', '-p', port, host, '~/test.sh',
                finish='Connection to localhost closed by remote host')
        except Exception as e:
            result = e

        new_boot_id = retry(ssh, 30, 'Connection refused',
            '-p', port, host, 'cat /proc/sys/kernel/random/boot_id').strip()
        logging.info("Reading new boot_id = %s", new_boot_id)

        logging.info("Assert test result")
        self._assert(boot_id=(old_boot_id, new_boot_id), result=result)

    def _assert(self, boot_id: Tuple[str], result: Union[ErrorReturnCode, RunningCommand]) -> None:
        old_boot_id, new_boot_id = boot_id
        paniked = (old_boot_id != new_boot_id)

        if paniked and not self.assert_panic:
            raise Exception("Boot id not matched %s!=%s, because kernel has been crashed by test %s" % (old_boot_id, new_boot_id, self.desc))
        elif not paniked and self.assert_panic:
            raise Exception("Kernel didn't crash as expected by test %s" % self.desc)

        super()._assert(result)
