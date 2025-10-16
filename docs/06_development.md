## 6. Development

### 6.1. Code Structure

The code is organized into modules as described in the Architecture section. Each module is designed to be as self-contained as possible.

### 6.2. Adding a New Agent

To add a new agent:

1.  Create a new agent class in the `agents/` directory that inherits from `BaseAgent`.
2.  Implement the `analyze` method.
3.  Integrate the new agent into the `PortfolioManager`'s workflow.

### 6.3. Contributing

Contributions are welcome. Please open an issue or submit a pull request on the GitHub repository.

