from src.models.llm_stub import SmolLMStub
from src.models.prompt_builder import PromptBuilder

class InterrogationEngine:
    def __init__(self, state, resolver):
        self.state = state
        self.resolver = resolver
        self.model = SmolLMStub(state) 
        self.prompter = PromptBuilder(state)

    def ask(self, canonical_name: str, user_question: str):
        prompt = self.prompter.build_prompt(
            character=canonical_name,
            user_question=user_question
        )
        answer = self.model.generate(prompt, character=canonical_name)

        clues = self._extract_clues(answer)
        clean_answer = self._strip_clue_tags(answer)

        self.state.log_qa(canonical_name, user_question, clean_answer)
        for clue in clues:
            self.state.add_clue(clue)

        self.state.inc_questions(canonical_name)
        return clean_answer, clues

    def _extract_clues(self, text: str):
        clues = []
        marker = "[CLUE:"
        pos = 0
        while True:
            i = text.find(marker, pos)
            if i == -1:
                break
            j = text.find("]", i)
            if j == -1:
                break
            clues.append(text[i+len(marker):j].strip())
            pos = j + 1
        return clues

    def _strip_clue_tags(self, text: str) -> str:
        # elimina los segmentos [CLUE: ...]
        out = []
        i = 0
        while i < len(text):
            start = text.find("[CLUE:", i)
            if start == -1:
                out.append(text[i:])
                break
            out.append(text[i:start])
            end = text.find("]", start)
            if end == -1:
                # tag mal cerrado; corta
                break
            i = end + 1
        return "".join(out).strip()
