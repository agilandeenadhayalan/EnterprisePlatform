"""
Game Days — structured chaos engineering exercises with teams.

WHY THIS MATTERS:
A game day is a scheduled chaos engineering event where the team
deliberately breaks production (or a staging environment) to test
resilience and practice incident response. Unlike automated chaos
experiments, game days involve humans: engineers observe the system,
make decisions, and practice their runbooks.

The structure ensures safety (pre-planned steps with rollbacks),
learning (observations and debriefing), and follow-through (action
items tracked to completion).

Key concepts:
  - Phases: planning -> briefing -> execution -> observation ->
    debriefing -> followup. Each phase has specific goals.
  - Runbooks: step-by-step procedures with expected outcomes and
    rollback actions. If a step fails, you know exactly how to undo it.
  - Observations: real-time notes during the game day that become
    the raw material for the debrief.
  - Reports: structured output with pass rates, observations, and
    action items for post-game-day improvement.
"""

import time
from enum import Enum
from dataclasses import dataclass, field


class GameDayPhase(Enum):
    """Ordered phases of a game day exercise."""
    planning = "planning"
    briefing = "briefing"
    execution = "execution"
    observation = "observation"
    debriefing = "debriefing"
    followup = "followup"


_PHASE_ORDER = [
    GameDayPhase.planning,
    GameDayPhase.briefing,
    GameDayPhase.execution,
    GameDayPhase.observation,
    GameDayPhase.debriefing,
    GameDayPhase.followup,
]


@dataclass
class RunbookStep:
    """A single step in a game day runbook.

    Attributes:
        step_number: sequential step number
        action: description of what to do
        expected_outcome: what should happen if the system is resilient
        rollback_action: how to undo this step if needed
        actual_outcome: filled in after execution
        passed: whether the step matched expectations
    """
    step_number: int
    action: str
    expected_outcome: str
    rollback_action: str
    actual_outcome: str = ""
    passed: bool | None = None


class GameDayRunbook:
    """Step-by-step runbook for a game day exercise.

    Each step has an action, expected outcome, and rollback. Steps are
    executed in order, and progress is tracked for the final report.
    """

    def __init__(self):
        self._steps: list[RunbookStep] = []

    def add_step(
        self,
        action: str,
        expected_outcome: str,
        rollback_action: str,
    ) -> RunbookStep:
        """Append a step to the runbook. Returns the created step."""
        step = RunbookStep(
            step_number=len(self._steps) + 1,
            action=action,
            expected_outcome=expected_outcome,
            rollback_action=rollback_action,
        )
        self._steps.append(step)
        return step

    def execute_step(
        self,
        step_number: int,
        actual_outcome: str,
        passed: bool,
    ) -> bool:
        """Record the outcome of a step execution.

        Args:
            step_number: which step was executed (1-indexed)
            actual_outcome: what actually happened
            passed: True if the outcome matched expectations

        Returns:
            True if the step was found and updated.
        """
        for step in self._steps:
            if step.step_number == step_number:
                step.actual_outcome = actual_outcome
                step.passed = passed
                return True
        return False

    def get_progress(self) -> float:
        """Return completion ratio: steps executed / total steps."""
        if not self._steps:
            return 0.0
        executed = sum(1 for s in self._steps if s.passed is not None)
        return executed / len(self._steps)

    def needs_rollback(self) -> bool:
        """Check if any executed step failed (needs rollback)."""
        return any(s.passed is False for s in self._steps)

    @property
    def steps(self) -> list[RunbookStep]:
        return list(self._steps)

    def __len__(self) -> int:
        return len(self._steps)


@dataclass
class GameDayReport:
    """Summary report of a game day exercise.

    Attributes:
        name: game day name
        date: when the game day was held
        phases_completed: list of phases that were completed
        steps: dict of step_number -> RunbookStep details
        observations: notes captured during the exercise
        pass_rate: fraction of steps that passed
        action_items: follow-up tasks identified during debrief
    """
    name: str
    date: str
    phases_completed: list[str]
    steps: dict[int, dict]
    observations: list[str]
    pass_rate: float
    action_items: list[str]


class GameDayRunner:
    """Orchestrate a game day exercise through its phases.

    Manages the phase progression, observation collection, and final
    report generation.
    """

    def __init__(
        self,
        name: str,
        runbook: GameDayRunbook,
        participants: list[str] | None = None,
    ):
        self.name = name
        self.runbook = runbook
        self.participants = participants or []
        self._current_phase_idx: int = -1
        self._phases_completed: list[GameDayPhase] = []
        self._observations: list[str] = []
        self._action_items: list[str] = []
        self._started = False

    def start(self) -> GameDayPhase:
        """Begin the game day. Enters the planning phase."""
        self._started = True
        self._current_phase_idx = 0
        return _PHASE_ORDER[0]

    def advance_phase(self) -> GameDayPhase | None:
        """Move to the next phase. Returns None if all phases are complete."""
        if not self._started:
            return self.start()

        # Complete current phase
        if 0 <= self._current_phase_idx < len(_PHASE_ORDER):
            self._phases_completed.append(_PHASE_ORDER[self._current_phase_idx])

        self._current_phase_idx += 1
        if self._current_phase_idx >= len(_PHASE_ORDER):
            return None

        return _PHASE_ORDER[self._current_phase_idx]

    def get_current_phase(self) -> GameDayPhase | None:
        """Return the current phase, or None if not started or finished."""
        if not self._started or self._current_phase_idx >= len(_PHASE_ORDER):
            return None
        if self._current_phase_idx < 0:
            return None
        return _PHASE_ORDER[self._current_phase_idx]

    def add_observation(self, text: str) -> None:
        """Record an observation during the game day."""
        self._observations.append(text)

    def add_action_item(self, text: str) -> None:
        """Record an action item identified during the game day."""
        self._action_items.append(text)

    def generate_report(self) -> GameDayReport:
        """Generate the final game day report.

        Includes pass rate, observations, action items, and step details.
        """
        steps_dict = {}
        total = 0
        passed = 0
        for step in self.runbook.steps:
            steps_dict[step.step_number] = {
                "action": step.action,
                "expected_outcome": step.expected_outcome,
                "actual_outcome": step.actual_outcome,
                "passed": step.passed,
            }
            if step.passed is not None:
                total += 1
                if step.passed:
                    passed += 1

        pass_rate = passed / total if total > 0 else 0.0

        return GameDayReport(
            name=self.name,
            date=time.strftime("%Y-%m-%d"),
            phases_completed=[p.value for p in self._phases_completed],
            steps=steps_dict,
            observations=list(self._observations),
            pass_rate=pass_rate,
            action_items=list(self._action_items),
        )
