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
4. Create a `.env` file with your API keys (see `.env.example` for required variables):
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   SECRET_KEY=your_secret_key_here
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

## Project Structure

- `app.py`: Flask web application
- `meal_planner.py`: Core meal planning functionality
- `ai_recipe_generator.py`: AI-based recipe generation
- `recipe_fetcher.py`: Recipe fetching and processing
- `recipe_remixer.py`: Creative meal remixing
- `shopping_list.py`: Shopping list generation and Tesco integration
- `preferences.py`: User preferences management
- `templates/`: HTML templates for the web interface

## Requirements

- Python 3.8+
- OpenAI API key
- Flask web framework
- Internet connection for AI features
