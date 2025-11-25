
from typing import List, Tuple

EMOTIONS = [
    "alegría","calma","motivación","gratitud","esperanza",
    "tristeza","ansiedad","enojo","estrés","frustración","soledad","cansancio"
]

DAY_TAGS = [
    "buen día","mal día","peleé con mi pareja","problemas en el trabajo/escuela",
    "tráfico","poco tiempo","logré una meta","hice ejercicio","salí con amigos",
    "tiempo en familia","muchas tareas","otro"
]

def compute_score_and_diagnosis(mood: int, emotions: List[str], sleep_hours: int) -> Tuple[int, str]:
    base = (mood - 1) * 25  # 1..5 -> 0..100

    positives = {"alegría","calma","motivación","gratitud","esperanza"}
    negatives = {"tristeza","ansiedad","enojo","estrés","frustración","soledad","cansancio"}

    adj = 0
    for e in emotions:
        if e in positives: adj += 6
        elif e in negatives: adj -= 6
    adj = max(-18, min(18, adj))

    if 7 <= sleep_hours <= 9:      adj_sleep = 8
    elif (5 <= sleep_hours <= 6) or (10 <= sleep_hours <= 11): adj_sleep = 2
    elif sleep_hours <= 4 or sleep_hours >= 12: adj_sleep = -8
    else: adj_sleep = 0

    score = max(0, min(100, base + adj + adj_sleep))

    if score <= 24:       diagnosis = "Muy bajo"
    elif score <= 44:     diagnosis = "Bajo"
    elif score <= 59:     diagnosis = "Neutral"
    elif score <= 79:     diagnosis = "Positivo"
    else:                 diagnosis = "Muy positivo"

    return score, diagnosis
