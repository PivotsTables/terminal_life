# Terminal Life

Terminal Life is a terminal-based game that simulates interactions in a convenience store. Players can explore the store, interact with characters, and experience dynamic dialogues powered by an AI model.

## Project Structure

```
Terminal-Life
├── src
│   ├── main.py               # Entry point of the game
│   ├── store
│   │   └── __init__.py       # Store class definition
│   ├── characters
│   │   └── __init__.py       # Character and Bob class definitions
│   ├── graphics
│   │   └── __init__.py       # Terminal graphics rendering
│   ├── lm_integration
│   │   └── __init__.py       # Integration with LM Studio
│   └── memory
│       └── __init__.py       # Memory management for characters
├── requirements.txt           # Project dependencies
└── README.md                  # Project documentation
```

## Setup Instructions

1. Clone the repository:
   ```
   git clone <repository-url>
   cd Terminal-Life
   ```

2. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Run the game:
   ```
   python src/main.py
   ```

## Gameplay Mechanics

- Explore the convenience store layout, which includes aisles and checkout areas.
- Interact with various characters, each with unique dialogues and actions.
- Experience dynamic conversations powered by the openai/gpt-oss-20b model, allowing for rich character interactions.

## Character Descriptions

- **Bob**: The store owner who interacts with players and provides information about the store. Bob has specific dialogues and actions that enhance the gameplay experience.

## Contributing

Contributions are welcome! Please submit a pull request or open an issue for any suggestions or improvements.

## License

This project is licensed under the MIT License. See the LICENSE file for details.