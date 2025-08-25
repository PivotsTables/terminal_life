class Character:
    def __init__(self, name):
        self.name = name
        self.memory = []

    def interact(self, other_character):
        pass

    def remember(self, interaction):
        if len(self.memory) >= 100:
            self.memory.pop(0)
        self.memory.append(interaction)


class Bob(Character):
    def __init__(self):
        super().__init__("Bob")

    def greet(self):
        return "Welcome to my store! How can I help you today?"

    def provide_info(self):
        return "We have a great selection of snacks and drinks!"