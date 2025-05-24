import os
import json
import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from dotenv import load_dotenv
from meal_planner import MealPlanner
from preferences import PreferenceManager
from shopping_list import ShoppingListManager

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev_secret_key")

# Initialize components
meal_planner = MealPlanner()
preference_manager = PreferenceManager()
shopping_list_manager = ShoppingListManager()

@app.context_processor
def inject_now():
    return {'now': datetime.datetime.now()}

@app.route('/generation_status')
def generation_status():
    """Check if meal plan generation is in progress."""
    return jsonify({
        'in_progress': session.get('generation_in_progress', False)
    })

@app.route('/')
def index():
    """Render the main dashboard."""
    # Ensure we have the latest data
    preference_manager.reload()
    
    # Get the current meal plan (most recent)
    meal_history = preference_manager.get_meal_history()
    current_plan = meal_history[-1] if meal_history else None
    
    # Get family preferences
    liked_foods = preference_manager.get_liked_foods()
    disliked_foods = preference_manager.get_disliked_foods()
    
    # Get family info
    family_info = preference_manager.data.get("family_info", {
        "members": 4,
        "children_ages": [6, 8]
    })
    
    # Check if generation is in progress
    generation_in_progress = session.get('generation_in_progress', False)
    
    return render_template(
        'index.html', 
        current_plan=current_plan,
        liked_foods=liked_foods,
        disliked_foods=disliked_foods,
        family_info=family_info,
        meal_history=meal_history,
        generation_in_progress=generation_in_progress
    )

@app.route('/history')
def history():
    """View meal planning history."""
    meal_history = preference_manager.get_meal_history()
    return render_template('history.html', meal_history=meal_history)

@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    """Manage family preferences."""
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_liked':
            food = request.form.get('food')
            if food:
                preference_manager.add_preference(food, liked=True)
                flash(f'Added {food} to liked foods!', 'success')
        
        elif action == 'add_disliked':
            food = request.form.get('food')
            if food:
                preference_manager.add_preference(food, liked=False)
                flash(f'Added {food} to disliked foods!', 'success')
        
        elif action == 'remove_liked':
            food = request.form.get('food')
            if food:
                if preference_manager.remove_preference(food, liked=True):
                    flash(f'Removed {food} from liked foods!', 'success')
                else:
                    flash(f'Could not find {food} in liked foods!', 'danger')
        
        elif action == 'remove_disliked':
            food = request.form.get('food')
            if food:
                if preference_manager.remove_preference(food, liked=False):
                    flash(f'Removed {food} from disliked foods!', 'success')
                else:
                    flash(f'Could not find {food} in disliked foods!', 'danger')
        
        elif action == 'update_family_info':
            members = request.form.get('members', type=int)
            child1_age = request.form.get('child1_age', type=int)
            child2_age = request.form.get('child2_age', type=int)
            meal_count = request.form.get('meal_count', type=int)
            
            if members and child1_age and child2_age and meal_count:
                preference_manager.data["family_info"] = {
                    "members": members,
                    "children_ages": [child1_age, child2_age]
                }
                preference_manager.set_meal_count(meal_count)
                flash('Family information updated!', 'success')
        
        return redirect(url_for('preferences'))
    
    # GET request
    liked_foods = preference_manager.get_liked_foods()
    disliked_foods = preference_manager.get_disliked_foods()
    family_info = preference_manager.data.get("family_info", {
        "members": 4,
        "children_ages": [6, 8]
    })
    
    # Get preferences including meal count
    preferences = {
        "meal_count": preference_manager.get_meal_count()
    }
    
    return render_template(
        'preferences.html', 
        liked_foods=liked_foods, 
        disliked_foods=disliked_foods,
        family_info=family_info,
        preferences=preferences
    )

@app.route('/generate_plan', methods=['POST'])
def generate_plan():
    """Generate a new meal plan with progress indication."""
    try:
        # Start the generation process and show progress
        session['generation_in_progress'] = True
        
        # Generate a new meal plan (this now also generates and caches the shopping list)
        plan = meal_planner.generate_meal_plan()
        
        # Ensure we're using the latest data
        preference_manager.reload()
        
        # Generation complete
        session['generation_in_progress'] = False
        
        flash('New meal plan and shopping list generated successfully!', 'success')
    except Exception as e:
        # Error occurred
        session['generation_in_progress'] = False
        flash(f'Error generating meal plan: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

@app.route('/recipe/<int:plan_index>/<int:day_index>')
def view_recipe(plan_index, day_index):
    """View a specific recipe."""
    meal_history = preference_manager.get_meal_history()
    
    if 0 <= plan_index < len(meal_history):
        plan = meal_history[plan_index]
        if 0 <= day_index < len(plan['days']):
            day = plan['days'][day_index]
            return render_template('recipe.html', day=day, plan_index=plan_index, day_index=day_index)
    
    flash('Recipe not found!', 'danger')
    return redirect(url_for('index'))

@app.route('/api/preferences', methods=['GET'])
def api_preferences():
    """API endpoint to get preferences as JSON."""
    return jsonify({
        "liked_foods": preference_manager.get_liked_foods(),
        "disliked_foods": preference_manager.get_disliked_foods(),
        "family_info": preference_manager.data.get("family_info", {})
    })

@app.route('/shopping_list')
def shopping_list():
    """Display shopping list from current meal plan using cached list."""
    # Get the current meal plan (most recent)
    meal_history = preference_manager.get_meal_history()
    current_plan = meal_history[-1] if meal_history else None
    
    if not current_plan:
        flash('No meal plan found. Please generate a meal plan first.', 'warning')
        return redirect(url_for('index'))
    
    # Get the meal plan ID
    meal_plan_id = current_plan.get("id")
    if not meal_plan_id:
        flash('Meal plan ID not found. Please generate a new meal plan.', 'warning')
        return redirect(url_for('index'))
    
    # Get cached shopping list
    shopping_list_items = meal_planner.get_shopping_list(meal_plan_id)
    
    # Format date range for display
    # Handle different date formats in the meal plan
    if 'start_date' in current_plan:
        start_date_str = current_plan['start_date']
    elif 'week_starting' in current_plan:
        start_date_str = current_plan['week_starting'].split('T')[0] if 'T' in current_plan['week_starting'] else current_plan['week_starting']
    else:
        # If no date is available, use today's date
        start_date_str = datetime.datetime.now().strftime('%Y-%m-%d')
        
    start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = start_date + datetime.timedelta(days=len(current_plan['days'])-1)
    meal_plan_dates = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
    
    # Get Tesco result from session if available
    tesco_result = session.pop('tesco_result', None)
    
    return render_template(
        'shopping_list.html',
        shopping_list=shopping_list_items,
        meal_plan=current_plan,
        meal_plan_dates=meal_plan_dates,
        tesco_result=tesco_result
    )

@app.route('/add_to_tesco', methods=['POST'])
def add_to_tesco():
    """Add shopping list items to Tesco cart."""
    # Get the current meal plan
    meal_history = preference_manager.get_meal_history()
    current_plan = meal_history[-1] if meal_history else None
    
    if not current_plan:
        flash('No meal plan found. Please generate a meal plan first.', 'warning')
        return redirect(url_for('index'))
    
    # Get the meal plan ID
    meal_plan_id = current_plan.get("id")
    if not meal_plan_id:
        flash('Meal plan ID not found. Please generate a new meal plan.', 'warning')
        return redirect(url_for('index'))
    
    # Get cached shopping list
    shopping_list_items = meal_planner.get_shopping_list(meal_plan_id)
    
    # Add to Tesco cart
    tesco_result = shopping_list_manager.add_to_tesco_cart(shopping_list_items)
    
    # Store result in session for display
    session['tesco_result'] = tesco_result
    
    if tesco_result['success']:
        flash(tesco_result['message'], 'success')
    else:
        flash(tesco_result['message'], 'warning')
    
    return redirect(url_for('shopping_list'))

if __name__ == '__main__':
    app.run(debug=True)
