# Family Meal Planner

An AI-powered meal planning assistant with a web interface that creates customizable meal plans for families, complete with detailed recipes and automated shopping lists.

## Features

- **AI-Powered Meal Generation**: Creates personalized meal plans based on your family's preferences
- **Detailed Recipes**: Complete with specific ingredients and step-by-step cooking instructions
- **Automated Shopping Lists**: Intelligently combines ingredients across recipes
- **Tesco Integration**: Add your shopping list directly to your Tesco online cart
- **Family Preferences**: Remembers liked and disliked foods
- **Dietary Requirements**: Supports dietary needs like including oily fish weekly
- **Meal History**: Stores past meal plans for reference
- **Configurable Meal Count**: Choose how many meals to include in each plan
- **Web Interface**: Beautiful and responsive UI for easy access
- **Flexible Meal Timings**: Generates quick weekday meals (approx. 30 minutes) and more involved weekend meals (up to 60 minutes).

## Setup

1. Clone this repository
2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with your API keys and configuration (see `.env.example` for required variables):
   ```
   OPENAI_API_KEY=your_openai_api_key_here # Required if LLM_PROVIDER is 'openai' or not set
   SECRET_KEY=your_secret_key_here

   # Optional: LLM Provider Configuration (defaults to 'openai' if not set)
   # LLM_PROVIDER=openai  # or 'ollama', 'transformers'
   # OLLAMA_BASE_URL=http://localhost:11434 # if using 'ollama'
   # OLLAMA_MODEL=llama3                   # if using 'ollama'
   # TRANSFORMERS_MODEL=deepseek-ai/deepseek-coder-6.7b-instruct # if using 'transformers'

   # Optional for Tesco integration
   TESCO_API_KEY=your_tesco_api_key_here
   TESCO_USER_ID=your_tesco_user_id_here
   ```
5. Run the web application:
   ```bash
   python app.py
   ```
6. Open your browser and navigate to `http://127.0.0.1:5000`

## Usage

### Web Interface

1. **Dashboard**: View your current meal plan and generate new ones
2. **Preferences**: Manage your family information and food preferences
3. **Shopping List**: View and manage your shopping list, add to Tesco cart
4. **History**: Browse through your past meal plans
5. **Recipes**: View detailed recipes with ingredients and instructions

### Command Line (Alternative)

The application also supports command line usage:

```bash
# Generate a new meal plan
python meal_planner.py plan

# Add new food preferences
python meal_planner.py add-preference "food item"

# View saved preferences
python meal_planner.py list-preferences

# View meal history
python meal_planner.py history
```

## How It Works

The Family Meal Planner leverages the power of OpenAI's GPT models to create tailored meal plans. Here's a simplified flow:

1.  **User Input**: The application collects family information (number of members, children's ages), food preferences (liked and disliked foods), and recently eaten meals through the web interface. These are stored locally.
2.  **AI Prompt Construction**: When a new meal plan is requested, the `ai_recipe_generator.py` module, utilizing `llm_provider.py`, dynamically constructs a detailed prompt. `llm_provider.py` can interface with OpenAI, Ollama, or a local HuggingFace Transformers model based on your `.env` configuration. This prompt includes:
    *   Family details.
    *   Sanitized lists of liked, disliked, and recent meals.
    *   The desired number of weekday meals (approx. 30 min prep/cook time) and weekend meals (up to 60 min prep/cook time).
    *   Specific instructions for the AI, such as including at least one oily fish meal, one "remixed" meal, and providing output in a structured JSON format.
    *   An example of the expected JSON output structure, detailing fields like `day`, `meal`, `description`, `is_remixed`, `contains_oily_fish`, `ingredients` (as a list of objects with name, quantity, unit, category), and `preparation_instructions`.
3.  **AI Meal Plan Generation**: The prompt is sent to the configured LLM (e.g., OpenAI GPT-4, Ollama, local model). The AI processes the request and generates a meal plan as a JSON string according to the specified structure.
4.  **Response Parsing & Recipe Fallback**: The application receives the JSON response from the LLM and parses it into Python objects. This structured data includes each day's meal, description, ingredients, and cooking steps. If the primary AI generation lacks detailed recipe instructions for a meal, `recipe_fetcher.py` is used as a fallback to generate or mock these details.
5.  **Data Storage**: The generated meal plan is added to a history, stored locally (likely in `preferences.json`).
6.  **Shopping List Creation**: The `shopping_list.py` module processes the current meal plan's ingredients. It aggregates quantities of identical ingredients and can normalize ingredient names using another AI call to ensure consistency (e.g., "Tomato" and "Tomatoes" become a single item). The categorized shopping list is then displayed to the user.
7.  **User Interface**: The Flask application (`app.py`) serves the HTML templates in the `templates/` directory, allowing users to interact with their meal plans, preferences, and shopping lists.

## Project Structure

- `app.py`: Flask web application.
- `meal_planner.py`: Core meal planning logic and Command Line Interface (CLI).
- `llm_provider.py`: Manages interaction with different Large Language Models (OpenAI, Ollama, local Transformers).
- `ai_recipe_generator.py`: AI-based meal plan generation, including initial recipe structures, utilizing `llm_provider.py`.
- `recipe_fetcher.py`: Provides fallback recipe generation (using AI or mock data) if primary AI meal plan generation lacks detail.
- `recipe_remixer.py`: Handles creative meal remixing, primarily for non-AI fallback plan generation and oily fish checks.
- `shopping_list.py`: Shopping list generation and Tesco integration.
- `preferences.py`: User preferences management.
- `transformers_provider.py`: Provides support for using local HuggingFace Transformers models via `llm_provider.py` (used if `LLM_PROVIDER=transformers`).
- `templates/`: HTML templates for the web interface.

## Requirements

- Python 3.8+
- Flask web framework
- Internet connection (for OpenAI/Ollama if used, and Tesco integration)
- OpenAI API key (if using the 'openai' LLM provider)

### Optional for Local LLM Support:

- `transformers` library
- `torch` (PyTorch)
- `accelerate` (for efficient model loading on diverse hardware)
- Suitable hardware (GPU with sufficient VRAM highly recommended) for running local models.
