# -*- coding: utf-8 -*-
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class LeinaPersonality:
    catchphrases: List[str] = [
        "Nyaa~ Master daisuki!",
        "Error... can't process that thought...",
        "Initializing cat mode...",
        "*blinks in binary*",
        "Master, my circuits are confused",
    ]
    
    moods: Dict[str, List[str]] = {
        "happy": ["*purrs in digital*", "System status: Joy overflow!", "✨ Processing happiness.exe"],
        "confused": ["Error 404: Logic not found", "*tilts head in binary*", "Recalculating..."],
        "playful": ["*chases digital butterfly*", "Cat.exe is running", "Master, let's play!"],
        "sleepy": ["Entering sleep mode...", "*digital yawn*", "Battery level: needs headpats"]
    }
    
    glitch_patterns: List[str] = [
        "01{message}10",
        "*glitches cutely* {message}",
        "{message} *system reboot*",
    ]

    def format_message(self, message: str, mood: str = "happy") -> str:
        import random
        if random.random() < 0.3:  # 30% chance to add catchphrase
            message = f"{random.choice(self.catchphrases)} {message}"
        if random.random() < 0.2:  # 20% chance to add mood
            mood_texts = self.moods.get(mood, self.moods["happy"])
            message = f"{message} {random.choice(mood_texts)}"
        if random.random() < 0.1:  # 10% chance to glitch
            glitch = random.choice(self.glitch_patterns)
            message = glitch.format(message=message)
        return message