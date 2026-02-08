"""Allow running sfcs-mdp as ``python -m sfcs_mdp``."""

from __future__ import annotations

import sys

from sfcs_mdp.cli import main

sys.exit(main())
