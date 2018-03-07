#!/usr/bin/env python
# coding: utf-8

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
LIB = os.path.join(ROOT, "HTC_lib")

if ROOT not in sys.path:
    sys.path.append(ROOT)
if LIB not in sys.path:
    sys.path.append(LIB)

from HTC_lib.Parse_calculation_workflow import parse_calculation_workflow

if __name__ == "__main__":
    workflow = parse_calculation_workflow("HTC_calculation_setup_example")
    print workflow
