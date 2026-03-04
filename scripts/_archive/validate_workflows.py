# ARCHIVED: 2026-03-03 — YAML validation — not scheduled
#!/usr/bin/env python3
"""
Workflow Validation Script

Validates all GitHub Actions workflows for correctness.
Checks file existence, YAML validity, and script references.

Usage:
    python scripts/validate_workflows.py [--trigger]
"""

import argparse
import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Tuple

WORKFLOWS_DIR = Path(__file__).parent.parent / '.github' / 'workflows'
SCRIPTS_DIR = Path(__file__).parent.parent / 'scripts'


def validate_workflows() -> Dict[str, Tuple[bool, str]]:
    """Validate all workflow YAML files."""
    results = {}
    
    if not WORKFLOWS_DIR.exists():
        return {'ERROR': (False, "Workflows directory not found")}
    
    workflow_files = list(WORKFLOWS_DIR.glob('*.yml')) + list(WORKFLOWS_DIR.glob('*.yaml'))
    workflow_files.sort()
    
    print(f"Found {len(workflow_files)} workflow files\n")
    print("=" * 70)
    
    for wf_path in workflow_files:
        wf_name = wf_path.name
        checks = []
        
        # Check 1: Valid YAML
        try:
            with open(wf_path, 'r') as f:
                content = yaml.safe_load(f)
            if content is None:
                checks.append(("YAML Valid", False, "Empty YAML"))
            else:
                checks.append(("YAML Valid", True, ""))
        except yaml.YAMLError as e:
            checks.append(("YAML Valid", False, f"YAML error: {e}"))
            results[wf_name] = (False, checks)
            continue
        except Exception as e:
            checks.append(("YAML Valid", False, f"Error: {e}"))
            results[wf_name] = (False, checks)
            continue
        
        # Check 2: Has name
        name = content.get('name', '')
        if name:
            checks.append(("Has Name", True, name))
        else:
            checks.append(("Has Name", False, "Missing 'name' field"))
        
        # Check 3: Has on trigger
        triggers = content.get('on', {})
        if triggers:
            trigger_str = ', '.join(triggers.keys()) if isinstance(triggers, dict) else str(triggers)
            checks.append(("Has Trigger", True, trigger_str))
        else:
            checks.append(("Has Trigger", False, "Missing 'on' trigger"))
        
        # Check 4: Has jobs
        jobs = content.get('jobs', {})
        if jobs:
            checks.append(("Has Jobs", True, f"{len(jobs)} job(s)"))
        else:
            checks.append(("Has Jobs", False, "No jobs defined"))
        
        # Check 5: Referenced scripts exist
        script_refs = []
        if 'jobs' in content:
            for job_name, job_data in jobs.items():
                steps = job_data.get('steps', [])
                for step in steps:
                    run = step.get('run', '')
                    if 'python' in run.lower() and 'scripts/' in run:
                        import re
                        matches = re.findall(r'scripts/[\w_]+\.py', run)
                        script_refs.extend(matches)
        
        if script_refs:
            missing_scripts = []
            for script_ref in script_refs:
                script_name = script_ref.replace('scripts/', '')
                script_path = SCRIPTS_DIR / script_name
                if not script_path.exists():
                    missing_scripts.append(script_name)
            
            if missing_scripts:
                checks.append(("Scripts Exist", False, f"Missing: {', '.join(missing_scripts)}"))
            else:
                checks.append(("Scripts Exist", True, f"{len(script_refs)} script(s)"))
        
        # Determine overall pass/fail
        all_passed = all(check[1] for check in checks)
        results[wf_name] = (all_passed, checks)
    
    return results


def print_results(results: Dict[str, Tuple[bool, str]]):
    """Print validation results."""
    pass_count = sum(1 for v in results.values() if isinstance(v[0], bool) and v[0])
    fail_count = len(results) - pass_count
    
    for wf_name, (overall, details) in results.items():
        if isinstance(details, str):
            print(f"\n❌ {wf_name}: {details}")
            continue
        
        status = "✅ PASS" if overall else "❌ FAIL"
        print(f"\n{status} | {wf_name}")
        
        if isinstance(details, list):
            for check_name, passed, info in details:
                icon = "✓" if passed else "✗"
                if info:
                    print(f"    {icon} {check_name}: {info}")
                else:
                    print(f"    {icon} {check_name}")
    
    print("\n" + "=" * 70)
    print(f"SUMMARY: {pass_count} passed, {fail_count} failed")
    print("=" * 70)


def print_manual_trigger_list():
    """Print list of workflows to manually test on Feb 19."""
    print("\n" + "=" * 70)
    print("MANUAL TRIGGER LIST - Feb 19 Game Day")
    print("=" * 70)
    print("""
The following workflows should be manually triggered on Feb 19
(first game day back from All-Star Break):

1. daily_simulation_pipeline.yml
   - Run: 11 AM EST to generate recommendations
   
2. daily_briefing.yml  
   - Run: 11:30 AM EST after pipeline completes
   
3. evening_slate_lock.yml
   - Run: 6:30 PM EST before games start
   
4. capture_closing_lines.yml
   - Run: 7:30 PM EST (30 min before tipoff)
   - Run: 8:00 PM EST, 9:00 PM EST, etc.
   
5. nightly_debrief.yml
   - Run: 11 PM EST after games complete

To trigger manually:
  gh workflow run <workflow-name> --repo LudiInformatio/Ludi-Bot

Or use GitHub Web UI: Actions > Workflow > Run workflow
""")
    print("=" * 70)


def trigger_workflows():
    """Trigger workflows using gh CLI."""
    print("\nAttempting to trigger workflows with gh CLI...\n")
    
    # Check if gh is available
    import subprocess
    try:
        subprocess.run(['gh', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ gh CLI not found. Install from: https://cli.github.com/")
        print("   Or trigger manually from GitHub Web UI.")
        return
    
    # List of workflows to trigger
    workflows_to_trigger = [
        'daily_simulation_pipeline.yml',
        'capture_closing_lines.yml',
    ]
    
    for wf in workflows_to_trigger:
        wf_name = wf.replace('.yml', '').replace('_', ' ').title().replace(' ', '_')
        try:
            result = subprocess.run(
                ['gh', 'workflow', 'run', wf],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"✅ Triggered: {wf}")
            else:
                print(f"❌ Failed: {wf} - {result.stderr}")
        except Exception as e:
            print(f"❌ Error triggering {wf}: {e}")


def main():
    parser = argparse.ArgumentParser(description='Validate GitHub Actions workflows')
    parser.add_argument('--trigger', action='store_true', 
                        help='Trigger workflows after validation (requires gh CLI)')
    args = parser.parse_args()
    
    print("WORKFLOW VALIDATION")
    print()
    
    results = validate_workflows()
    print_results(results)
    
    print_manual_trigger_list()
    
    if args.trigger:
        response = input("\nTrigger workflows? (y/N): ")
        if response.lower() == 'y':
            trigger_workflows()
    
    # Exit with error if any failed
    failed = sum(1 for v in results.values() if isinstance(v[0], bool) and not v[0])
    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
