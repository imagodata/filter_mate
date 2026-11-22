# -*- coding: utf-8 -*-
"""``python -m filter_mate.standalone``: the same as the ``filtermate`` command."""
import sys

from .cli import main

sys.exit(main())
