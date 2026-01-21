#!/usr/bin/env python3
"""
Analyze existing backtest results.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.backtest_synergy_comparison import SynergyBacktester

if __name__ == "__main__":
    bt = SynergyBacktester()
    bt.compare_results(
        'backtest_results/synergy_baseline_60d.csv',
        'backtest_results/synergy_enhanced_60d.csv'
    )
