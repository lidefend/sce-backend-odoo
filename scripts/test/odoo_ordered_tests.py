#!/usr/bin/env python3
"""Keep Odoo's test lifecycle; vary unittest method order deterministically."""
import os
import random
import sys
import unittest

order = os.environ['SC_TEST_ORDER']
seed = int(os.environ['SC_TEST_ORDER_SEED'])
original = unittest.TestLoader.getTestCaseNames


def names(loader, test_case):
    methods = original(loader, test_case)
    if order == 'reverse':
        methods.reverse()
    elif order == 'random':
        random.Random(str(seed) + ':' + test_case.__module__ + '.' + test_case.__name__).shuffle(methods)
    elif order != 'forward':
        raise ValueError('unknown governed test order')
    return methods


unittest.TestLoader.getTestCaseNames = names
import odoo.cli
print(f'LOCAL_TEST_ORDER={order} seed={seed}', flush=True)
odoo.cli.main()
