from dataclasses import dataclass

@dataclass
class Evidence:
    text: str
    visible: bool = True
