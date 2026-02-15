"""Lightweight smoke tests to verify imports and basic calls after Phase 3 migration."""
import sys
import traceback
from pathlib import Path

# Ensure repo root is on sys.path so imports of top-level modules succeed
ROOT = str(Path(__file__).resolve().parents[1])
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

def run():
    errors = []
    try:
        from module_e import LudiCalibrator
        print('Imported LudiCalibrator')
        try:
            cal = LudiCalibrator()
            print('Instantiated LudiCalibrator')
            # Try a safe call
            try:
                r = cal._get_tracking_stats('LeBron James', days=30)
                print('LudiCalibrator._get_tracking_stats OK, result type:', type(r))
            except Exception as e:
                errors.append(('LudiCalibrator._get_tracking_stats', repr(e)))
        except Exception as e:
            errors.append(('LudiCalibrator init', repr(e)))
    except Exception as e:
        errors.append(('import module_e', repr(e)))

    try:
        from module_h_historian import LudiHistorian
        print('Imported LudiHistorian')
        try:
            h = LudiHistorian()
            print('Instantiated LudiHistorian')
            try:
                # call a lightweight method if present
                if hasattr(h, 'update_database'):
                    print('LudiHistorian.update_database exists (skipping full run)')
            except Exception as e:
                errors.append(('LudiHistorian call', repr(e)))
        except Exception as e:
            errors.append(('LudiHistorian init', repr(e)))
    except Exception as e:
        errors.append(('import module_h_historian', repr(e)))

    if errors:
        print('\nSMOKE ERRORS:')
        for name, err in errors:
            print('-', name, err)
        return 2
    print('\nSmoke checks passed')
    return 0

if __name__ == '__main__':
    sys.exit(run())
