import random
from typing import List

def choose_killer(suspects: List[str], seed=None) -> str:
    rnd = random.Random(seed)
    return rnd.choice(suspects)
