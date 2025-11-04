from jinja2 import Template
from pathlib import Path

class PromptBuilder:
    def __init__(self, state):
        self.state = state
        base = Path(__file__).resolve().parents[1] / "prompts"
        self.system_tpl = (base / "system_prompt.txt").read_text(encoding="utf-8")
        self.character_tpl = Template((base / "character_prompt.j2").read_text(encoding="utf-8"))
        self.scenario_tpl = Template((base / "scenario_prompt.j2").read_text(encoding="utf-8"))
        self.guard_tpl = Template((base / "guardrails_prompt.j2").read_text(encoding="utf-8"))

    def build_prompt(self, character: str, user_question: str) -> str:
        ch_data = self.state.characters["characters"][character]
        scen_data = self.state.get_scenario()

        character_block = self.character_tpl.render(
            name=character,
            data=ch_data
        )
        scenario_block = self.scenario_tpl.render(
            scenario=scen_data,
            relations=self.state.relations
        )
        guard_block = self.guard_tpl.render()

        # Ensamble final
        prompt = (
            self.system_tpl
            + "\n\n"
            + scenario_block
            + "\n\n"
            + character_block
            + "\n\n"
            + "## USER QUESTION\n"
            + user_question.strip()
            + "\n\n"
            + guard_block
        )
        return prompt
