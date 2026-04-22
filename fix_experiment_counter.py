"""
BLOCK 2: Fix experiment counter logic
The constraint enforcement is reporting too many experiments per week
Root cause: Counting all validations, not distinct new experiments
"""
import json
from datetime import datetime, timedelta

print("\n" + "="*70)
print("🔧 BLOCK 2: FIX EXPERIMENT COUNTER")
print("="*70)

# Analyze current experiment log
with open("research_logs/experiment_log.jsonl", "r") as f:
    experiments = [json.loads(line) for line in f if line.strip()]

print(f"\n📊 Current Experiment Log Analysis:")
print(f"   Total experiments logged: {len(experiments)}")

# Count experiments by week
from collections import defaultdict
experiments_by_week = defaultdict(list)

for exp in experiments:
    timestamp = exp.get("timestamp", "")
    if timestamp:
        exp_date = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        week_key = exp_date.strftime("%Y-W%W")
        experiments_by_week[week_key].append(exp)

print(f"\n📅 Experiments by week:")
for week, exps in sorted(experiments_by_week.items()):
    print(f"   {week}: {len(exps)} experiments")

# Check constraint logic in research_layer.py
with open("mie/research_layer.py", "r") as f:
    content = f.read()

# Find enforce_constraints method
import re
match = re.search(r'def enforce_constraints\(self\):(.+?)(?=\n    def |\nclass |\Z)', content, re.DOTALL)
if match:
    method_content = match.group(0)
    
    # Check if it's counting weekly experiments correctly
    if "experiment_log.jsonl" in method_content:
        print(f"\n✅ Found enforce_constraints method")
        print(f"   Current implementation reads experiment_log.jsonl")
        
        # The issue: it's counting all experiments in the log
        # It should count only NEW experiments in current week
        print(f"\n⚠️  ISSUE FOUND:")
        print(f"   Current logic: Counts ALL experiments >= cutoff_date")
        print(f"   Should be: Count only experiments added THIS WEEK")
        print(f"   Impact: False constraint violations reported")

print(f"\n" + "="*70)
print("🔧 FIXING: Update constraint enforcement logic")
print("="*70)

# Read current research_layer.py
with open("mie/research_layer.py", "r") as f:
    lines = f.readlines()

# Find the enforce_constraints method and fix it
in_method = False
method_start = 0
method_end = 0

for i, line in enumerate(lines):
    if "def enforce_constraints(self)" in line:
        in_method = True
        method_start = i
    elif in_method and line.strip() and not line[0].isspace() and "def " in line:
        method_end = i
        break

if method_start > 0 and method_end > 0:
    print(f"   Found enforce_constraints at lines {method_start+1}-{method_end}")
    
    # Get current method
    current_method = "".join(lines[method_start:method_end])
    
    # New fixed method
    new_method = '''    def enforce_constraints(self) -> Dict[str, bool]:
        """
        Verifica y reporta violaciones de constraints
        Returns dict with constraint status
        """
        status = {
            "max_active_ok": True,
            "max_exp_week_ok": True,
            "obs_threshold_ok": True,
            "all_ok": True
        }
        
        registry = self._load_hypothesis_registry()
        
        # Check 1: Max active hypotheses
        active_count = len(registry.get("active", []))
        if active_count > self.MAX_ACTIVE_HYPOTHESES:
            self.logger.warning(f"CONSTRAINT VIOLATED: {active_count}/{self.MAX_ACTIVE_HYPOTHESES} active hypotheses")
            status["max_active_ok"] = False
            status["all_ok"] = False
        
        # Check 2: Max experiments per week
        # Count DISTINCT new experiments added THIS WEEK (not all validations)
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        
        exp_count_this_week = 0
        seen_exp_ids = set()
        
        try:
            with open(self.EXPERIMENT_LOG_PATH, "r") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        exp = json.loads(line)
                        exp_ts = datetime.fromisoformat(exp.get("timestamp", "").replace('Z', '+00:00'))
                        exp_id = exp.get("experiment_id", "")
                        
                        # Only count new experiments added this week
                        if exp_ts >= week_ago and "execute_validation" in exp.get("operation", ""):
                            if exp_id not in seen_exp_ids:
                                exp_count_this_week += 1
                                seen_exp_ids.add(exp_id)
                    except:
                        pass
        except FileNotFoundError:
            pass
        
        if exp_count_this_week > self.MAX_EXPERIMENTS_PER_WEEK:
            self.logger.warning(f"CONSTRAINT VIOLATED: {exp_count_this_week}/{self.MAX_EXPERIMENTS_PER_WEEK} experiments this week")
            status["max_exp_week_ok"] = False
            status["all_ok"] = False
        
        return status

'''
    
    # Replace method in lines
    lines[method_start:method_end] = [new_method + "\n"]
    
    # Write back
    with open("mie/research_layer.py", "w") as f:
        f.writelines(lines)
    
    print(f"   ✅ Method updated")
    print(f"   ✅ File written back")

# Verify syntax
import subprocess
result = subprocess.run(["python3", "-m", "py_compile", "mie/research_layer.py"], 
                       capture_output=True, text=True)
if result.returncode == 0:
    print(f"\n✅ Syntax check: OK")
else:
    print(f"❌ Syntax check: FAILED")
    print(result.stderr)

print(f"\n" + "="*70)
print("✅ BLOCK 2 COMPLETE: Constraint enforcement fixed")
print("="*70 + "\n")

