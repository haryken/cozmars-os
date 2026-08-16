#!/usr/bin/env python3
"""In thư viện thiếu — chạy trên laptop hoặc Pi."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cozmars.bootcheck import main

raise SystemExit(main())
