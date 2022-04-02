#!/usr/bin/env python3
# Copyright 2019-2022 Alibaba Group Holding Limited.
# SPDX-License-Identifier: GPL-2.0 OR BSD-3-Clause

"""test.py - A test tool for plugsched

Usage:
  ./test.py --host=<host> [--port=<port>] --test=<test>
  ./test.py --ecs=<ecs> --test=<test>
  ./test.py --help

Options:
  --help     Show help.
"""

import sh
import os
import json
import coloredlogs
from docopt import docopt
from runner import RemoteRunner
from instance import AlibabaInstance, PhysicalInstance
coloredlogs.install(level='INFO')
sh.ErrorReturnCode.truncate_cap = 10**1000

if __name__ == '__main__':
    arguments = docopt(__doc__)
    configs = {}

    if arguments['--host']:
        Instance = PhysicalInstance
        configs = {
            'host': arguments['--host'],
            'port': arguments['--port'] or '22',
            'passwd': os.environ.get('HOST_PASSWD', '')
        }
    else:
        Instance = AlibabaInstance
        with open(arguments['--ecs']) as f:
            profile = json.load(f)
        configs = {
            'profile': profile,
            'akid': os.environ['ALICLOUD_ACCESS_KEY'],
            'aksecret': os.environ['ALICLOUD_SECRET_KEY']
        }

    test = RemoteRunner(arguments['--test'])
    Instance.run_test(test=test, **configs)
