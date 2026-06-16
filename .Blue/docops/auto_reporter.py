#!/usr/bin/env python3
"""
BlueHub DocOps - Automatic Session Reporter
============================================

This script automatically generates project status reports every 6 hours
by analyzing project files and tracking progress.

Features:
- Parses tasks.md to calculate completion percentage
- Tracks completed vs pending tasks
- Generates snapshots in .kiro/docops/snapshots/
- Updates STATUS.md with latest project state
- Integrates with Celery Beat for scheduling

Usage:
    python auto_reporter.py                    # Run once
    celery -A services.celery_app beat        # Schedule with Celery
"""

import re
from datetime import datetime
from pathlib import Path


class DocOpsReporter:
    """Automated documentation and operations reporter for BlueHub project."""

    def __init__(self, project_root: str = ".") -> None:
        self.project_root = Path(project_root)
        self.docops_dir = self.project_root / ".kiro" / "docops"
        self.snapshots_dir = self.docops_dir / "snapshots"
        self.sessions_dir = self.docops_dir / "sessions"

        # Ensure directories exist
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Spec files
        self.specs_dir = self.project_root / ".kiro" / "specs" / "bluehub-platform"
        self.tasks_file = self.specs_dir / "tasks.md"
        self.design_file = self.specs_dir / "design.md"
        self.requirements_file = self.specs_dir / "requirements.md"

    def parse_tasks_progress(self) -> dict:
        """Parse tasks.md to calculate completion percentage."""
        if not self.tasks_file.exists():
            return {"total": 0, "completed": 0, "in_progress": 0, "percentage": 0}

        content = self.tasks_file.read_text(encoding='utf-8')

        # Count task statuses
        total_tasks = len(re.findall(r'\*\*ID:\*\* TASK-\d+', content))
        completed_tasks = len(re.findall(r'\*\*Status:\*\* ✅ complete', content, re.IGNORECASE))
        in_progress_tasks = len(re.findall(r'\*\*Status:\*\* 🔄 in[_-]?progress', content, re.IGNORECASE))

        percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        return {
            "total": total_tasks,
            "completed": completed_tasks,
            "in_progress": in_progress_tasks,
            "blocked": total_tasks - completed_tasks - in_progress_tasks,
            "percentage": round(percentage, 1)
        }

    def parse_recent_decisions(self) -> list[str]:
        """Extract recent architectural decisions from design.md."""
        if not self.design_file.exists():
            return []

        content = self.design_file.read_text(encoding='utf-8')
        decisions = []

        # Look for decision patterns (simple heuristic)
        lines = content.split('\n')
        for _i, line in enumerate(lines):
            if any(keyword in line.lower() for keyword in ['decision:', 'chosen:', 'selected:', 'recommendation:']):
                decisions.append(line.strip())
                if len(decisions) >= 5:  # Last 5 decisions
                    break

        return decisions

    def count_requirements(self) -> dict:
        """Count total and completed requirements from requirements.md."""
        if not self.requirements_file.exists():
            return {"total": 0, "completed": 0}

        content = self.requirements_file.read_text(encoding='utf-8')

        # Count REQ- patterns
        total_reqs = len(re.findall(r'\*\*REQ-\d+:\*\*', content))

        # Heuristic: if requirement has acceptance criteria checked, it's done
        completed_reqs = len(re.findall(r'- \[x\].*(?:implemented|complete|done)', content, re.IGNORECASE))

        return {
            "total": total_reqs,
            "completed": completed_reqs,
            "percentage": round(completed_reqs / total_reqs * 100, 1) if total_reqs > 0 else 0
        }

    def identify_blockers(self) -> list[str]:
        """Identify current blockers from tasks.md."""
        if not self.tasks_file.exists():
            return []

        content = self.tasks_file.read_text(encoding='utf-8')
        blockers = []

        # Find blocked tasks
        blocked_pattern = r'\*\*Status:\*\* (?:blocked|⛔)\s*\n.*?\*\*Description:\*\*\s*(.*?)(?:\n\n|\Z)'
        matches = re.findall(blocked_pattern, content, re.DOTALL | re.IGNORECASE)

        for match in matches[:3]:  # Top 3 blockers
            # Clean up the description (first line only)
            desc = match.split('\n')[0].strip()
            if desc:
                blockers.append(desc)

        return blockers

    def generate_snapshot(self) -> str:
        """Generate a snapshot report and save to file."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        snapshot_file = self.snapshots_dir / f"{timestamp}.md"

        # Gather data
        tasks_data = self.parse_tasks_progress()
        reqs_data = self.count_requirements()
        decisions = self.parse_recent_decisions()
        blockers = self.identify_blockers()

        # Generate report
        report = f"""# 📸 BlueHub Snapshot - {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 Project Metrics

| Metric | Value |
|--------|-------|
| **Tasks Progress** | {tasks_data['completed']}/{tasks_data['total']} ({tasks_data['percentage']}%) |
| **Tasks In Progress** | {tasks_data['in_progress']} |
| **Tasks Blocked** | {tasks_data['blocked']} |
| **Requirements** | {reqs_data['completed']}/{reqs_data['total']} ({reqs_data['percentage']}%) |

## ✅ Completion Status

```
Progress Bar: {'█' * int(tasks_data['percentage'] / 5)}{'░' * (20 - int(tasks_data['percentage'] / 5))} {tasks_data['percentage']}%
```

## 🚫 Current Blockers

"""

        if blockers:
            for i, blocker in enumerate(blockers, 1):
                report += f"{i}. {blocker}\n"
        else:
            report += "✅ No active blockers\n"

        report += "\n## 🗂️ Recent Decisions\n\n"

        if decisions:
            for decision in decisions:
                report += f"- {decision}\n"
        else:
            report += "No recent decisions recorded.\n"

        report += f"""
## 🔄 Next Actions

Based on current progress:
- Continue Phase {self._estimate_current_phase(tasks_data['percentage'])}
- Focus on unblocking {tasks_data['blocked']} blocked tasks
- Review {reqs_data['total'] - reqs_data['completed']} pending requirements

---

**Generated by:** DocOps Auto-Reporter
**Next snapshot:** {self._next_snapshot_time()}
"""

        # Write to file
        snapshot_file.write_text(report, encoding='utf-8')

        return str(snapshot_file)

    def update_status_file(self) -> None:
        """Update the main STATUS.md file with latest project state."""
        status_file = self.docops_dir / "STATUS.md"

        # Gather latest data
        tasks_data = self.parse_tasks_progress()
        reqs_data = self.count_requirements()
        blockers = self.identify_blockers()

        # Get last session info
        last_session = self._get_last_session_info()

        # Generate status
        status = f"""# 📊 BlueHub Project Status

**Last Updated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Overall Status:** {self._get_status_emoji(tasks_data['percentage'])}

---

## 🎯 Quick Overview

| Metric | Current | Target |
|--------|---------|--------|
| **Overall Progress** | {tasks_data['percentage']}% | 100% |
| **Completed Tasks** | {tasks_data['completed']} | {tasks_data['total']} |
| **In Progress** | {tasks_data['in_progress']} | - |
| **Blocked Tasks** | {tasks_data['blocked']} | 0 |
| **Requirements** | {reqs_data['completed']}/{reqs_data['total']} | {reqs_data['total']}/{reqs_data['total']} |

## 📈 Progress Visualization

```
{self._generate_progress_bar(tasks_data['percentage'])}
```

## 🚧 Active Blockers ({len(blockers)})

"""

        if blockers:
            for i, blocker in enumerate(blockers, 1):
                status += f"{i}. {blocker}\n"
        else:
            status += "✅ No active blockers - Clear path ahead!\n"

        status += f"""
## 📅 Session Information

- **Last Session:** {last_session['date']} (Session #{last_session['number']})
- **Sessions This Week:** {self._count_sessions_this_week()}
- **Average Session Duration:** {last_session.get('duration', 'N/A')}

## 🔄 Next Steps

**Immediate Actions:**
1. {self._suggest_next_action(tasks_data)}
2. Review blocked tasks and remove blockers
3. Continue Phase {self._estimate_current_phase(tasks_data['percentage'])} development

**Current Phase:** Phase {self._estimate_current_phase(tasks_data['percentage'])} - {self._get_phase_name(tasks_data['percentage'])}

---

## 📂 Quick Links

- [Tasks](../.kiro/specs/bluehub-platform/tasks.md)
- [Requirements](../.kiro/specs/bluehub-platform/requirements.md)
- [Design](../.kiro/specs/bluehub-platform/design.md)
- [Latest Snapshot]({self._get_latest_snapshot()})
- [Session Reports](./sessions/)

---

*Generated automatically by DocOps Reporter*
*Next update: {self._next_snapshot_time()}*
"""

        status_file.write_text(status, encoding='utf-8')
        print("✅ STATUS.md updated successfully")

    def _get_status_emoji(self, percentage: float) -> str:
        """Get status emoji based on progress."""
        if percentage >= 80:
            return "🟢 On Track"
        if percentage >= 50:
            return "🟡 In Progress"
        if percentage >= 20:
            return "🟠 Early Stage"
        return "🔴 Just Started"

    def _generate_progress_bar(self, percentage: float) -> str:
        """Generate ASCII progress bar."""
        filled = int(percentage / 5)
        empty = 20 - filled
        return f"[{'█' * filled}{'░' * empty}] {percentage}%"

    def _estimate_current_phase(self, percentage: float) -> int:
        """Estimate current phase based on percentage."""
        if percentage < 10:
            return 0
        if percentage < 30:
            return 1
        if percentage < 50:
            return 2
        if percentage < 65:
            return 3
        if percentage < 80:
            return 4
        if percentage < 90:
            return 5
        return 6

    def _get_phase_name(self, percentage: float) -> str:
        """Get phase name."""
        phases = {
            0: "Setup & Foundation",
            1: "Core System",
            2: "VPN Module",
            3: "Admin Panel",
            4: "VPS Module",
            5: "Additional Modules",
            6: "Production Ready"
        }
        return phases.get(self._estimate_current_phase(percentage), "Unknown")

    def _suggest_next_action(self, tasks_data: dict) -> str:
        """Suggest next action based on project state."""
        if tasks_data['blocked'] > 0:
            return "Unblock tasks to maintain momentum"
        if tasks_data['in_progress'] > 3:
            return "Focus on completing in-progress tasks before starting new ones"
        if tasks_data['percentage'] < 10:
            return "Complete Phase 0 setup tasks"
        return "Continue with current phase development"

    def _get_last_session_info(self) -> dict:
        """Get info about last session."""
        sessions = list(self.sessions_dir.glob("*.md"))
        if not sessions:
            return {"date": "N/A", "number": 0, "duration": "N/A"}

        latest = max(sessions, key=lambda p: p.stat().st_mtime)

        # Parse session number from filename
        match = re.search(r'session-(\d+)', latest.name)
        session_num = int(match.group(1)) if match else 0

        # Get date from filename
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', latest.name)
        date = date_match.group(1) if date_match else "N/A"

        return {
            "date": date,
            "number": session_num,
            "duration": "N/A"  # Could be parsed from file content
        }

    def _count_sessions_this_week(self) -> int:
        """Count sessions in the current week."""
        sessions = list(self.sessions_dir.glob("*.md"))
        today = datetime.now()
        week_start = today - datetime.timedelta(days=today.weekday())

        count = 0
        for session in sessions:
            mtime = datetime.fromtimestamp(session.stat().st_mtime)
            if mtime >= week_start:
                count += 1

        return count

    def _get_latest_snapshot(self) -> str:
        """Get path to latest snapshot."""
        snapshots = list(self.snapshots_dir.glob("*.md"))
        if not snapshots:
            return "No snapshots yet"

        latest = max(snapshots, key=lambda p: p.stat().st_mtime)
        return f"./snapshots/{latest.name}"

    def _next_snapshot_time(self) -> str:
        """Calculate next snapshot time (6 hours from now)."""
        next_time = datetime.now() + datetime.timedelta(hours=6)
        return next_time.strftime("%Y-%m-%d %H:%M")

    def run(self) -> None:
        """Main execution method."""
        print("🚀 BlueHub DocOps Reporter Starting...")
        print("=" * 50)

        # Generate snapshot
        print("📸 Generating project snapshot...")
        snapshot_path = self.generate_snapshot()
        print(f"✅ Snapshot saved: {snapshot_path}")

        # Update status
        print("📊 Updating STATUS.md...")
        self.update_status_file()

        print("=" * 50)
        print("✅ DocOps report generation complete!")
        print(f"📅 Next run: {self._next_snapshot_time()}")


# Celery task integration
def setup_celery_task(celery_app):
    """Setup Celery periodic task for auto-reporting."""

    @celery_app.task(name='docops.generate_report')
    def generate_docops_report() -> str:
        """Celery task to generate DocOps report."""
        reporter = DocOpsReporter()
        reporter.run()
        return "DocOps report generated successfully"

    # Add to Celery Beat schedule
    celery_app.conf.beat_schedule = celery_app.conf.beat_schedule or {}
    celery_app.conf.beat_schedule['docops-auto-report'] = {
        'task': 'docops.generate_report',
        'schedule': 6 * 60 * 60,  # Every 6 hours (in seconds)
        'options': {'queue': 'background'}
    }

    return generate_docops_report


if __name__ == "__main__":
    # Run standalone
    reporter = DocOpsReporter()
    reporter.run()
