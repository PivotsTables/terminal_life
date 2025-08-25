class Memory:
    def __init__(self):
        self.interactions = {}

    def remember(self, character_name, interaction):
        if character_name not in self.interactions:
            self.interactions[character_name] = []
        self.interactions[character_name].append(interaction)
        if len(self.interactions[character_name]) > 100:
            self.interactions[character_name].pop(0)

    def recall(self, character_name):
        return self.interactions.get(character_name, [])