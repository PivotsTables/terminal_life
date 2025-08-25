class Store:
    def __init__(self):
        self.layout = self.create_layout()
        self.characters = []
    
    def create_layout(self):
        # Define the layout of the store, including aisles and checkout areas
        return {
            "aisles": ["Aisle 1", "Aisle 2", "Aisle 3"],
            "checkout": "Checkout Area"
        }
    
    def add_character(self, character):
        self.characters.append(character)
    
    def move_character(self, character, new_location):
        # Logic to move character within the store
        pass
    
    def display_layout(self):
        # Logic to display the store layout in the terminal
        pass