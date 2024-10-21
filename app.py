from flask import Flask
from flask import render_template, redirect, url_for
from flask import request
from flask import session
from flask import flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash , check_password_hash
from datetime import datetime , timedelta
from flask_migrate import Migrate

import re
app = Flask(__name__)

app.permanent_session_lifetime = timedelta(minutes=30)

app.secret_key = 'SECRET_KEY'

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://razabaqir:raza@localhost/smart_underage_driver_detector'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

migrate = Migrate(app, db)

# Define the User model
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable = False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    password = db.Column(db.String(200), nullable=False)

# Define the Location model
class Location(db.Model):
    __tablename__ = 'locations'
    id = db.Column(db.Integer, primary_key=True)
    location_name = db.Column(db.String(200), nullable=False)

# Define the Result model
class Result(db.Model):
    __tablename__ = 'results'
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    date_time = db.Column(db.DateTime, nullable=False)
    image_path = db.Column(db.String(200), nullable=False)
    underage_status = db.Column(db.Boolean, nullable=False)

    location = db.relationship('Location', backref=db.backref('results', lazy=True))

# Create the database tables
with app.app_context():
    db.create_all()

# Home route
@app.route('/')
def home():
    return render_template("index.html")

# Error handlers for better UX
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500


# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():

    if request.method == 'POST':
        email = request.form.get('email').strip()
        password = request.form.get('password')

        # Basic email validation
        if not email or not password:
            flash('Please provide both email and password.', 'error')
            return redirect(url_for('login'))

        # Fetch the user from the database
        user = User.query.filter_by(email=email).first()

        # Check if the user exists and password matches
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['email'] = user.email
            session['logged_in'] = True 
            session.permanent = True  # Set session timeout
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials! Please try again.', 'error')
            return redirect(url_for('login')) 

    return render_template('login.html')

# Signup route 
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']

        phone_regex = r'^\d{11}$'  # 11 digit phone number
        password_regex = r'^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{8,}$'

        # Check if the user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('User already exists!', 'error')
            return render_template('signup.html', name=name, email=email, phone=phone)

        # Phone validation
        if not re.match(phone_regex, phone):
            flash('Invalid phone number! It should be 11 digits long.', 'error')
            return render_template('signup.html',name=name, email=email, phone=phone)

        # Password validation
        if not re.match(password_regex, password):
            flash('Password must be at least 8 characters long and include both letters and numbers.', 'error')
            return render_template('signup.html', name=name, email=email, phone=phone)

        # Create a new user if validation pass
        new_user = User(name = name, email=email, phone=phone, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()

        session['user_id'] = new_user.id
        session['logged_in'] = True

        flash('Account created successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('signup.html')


# Update Profile route
@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
    if 'email' not in session:
        return redirect(url_for('login'))

    user = User.query.filter_by(email=session['email']).first()

    if request.method == 'POST':
        # Get updated information from the form
        user.name = request.form['name']
        user.email = request.form['email']
        user.phone = request.form['phone']

        # Optionally, update password
        if request.form['password']:
            user.password = generate_password_hash(request.form['password'])

        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('dashboard'))

    return render_template('update_profile.html', user=user)


# Dashboard route
@app.route('/dashboard')
def dashboard():
    # Check if the user is logged in by verifying session
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Query the user based on the stored user_id in session
    user = User.query.filter_by(id=session['user_id']).first()
    
    if not user:
        flash('User not found. Please log in again.', 'error')
        return redirect(url_for('login'))

    # Pass the user's name to the dashboard template
    return render_template('dashboard.html', name=user.name)


# Add Location route
@app.route('/add_location', methods=['GET', 'POST'])
def add_location():
    if 'email' not in session:
        return redirect(url_for('login'))

    session.pop('_flashes',None)

    if request.method == 'POST':
        location_name = request.form['location']

        # Check if the location already exists
        existing_location = Location.query.filter_by(location_name=location_name).first()
        if existing_location:
            flash('Location already exists!', 'error')
            return render_template('add_location.html')

        try:
            new_location = Location(location_name=location_name)
            db.session.add(new_location)
            db.session.commit()

            flash('Location added successfully!', 'success')
            return redirect(url_for('dashboard'))

        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
            return render_template('add_location.html')

    return render_template('add_location.html')

# Delete location route
@app.route('/delete_location', methods=['GET', 'POST'])
def delete_location():
    if 'email' not in session:
        return redirect(url_for('login'))

    session.pop('_flashes', None)

    locations = Location.query.all()

    if request.method == 'POST':
        location_id = request.form['location_id']
        location_to_delete = Location.query.get(location_id)

        if location_to_delete:
            db.session.delete(location_to_delete)
            db.session.commit()
            flash('Location deleted successfully!', 'success')
        else:
            flash('Location not found!', 'error')

        return redirect(url_for('dashboard'))

    return render_template('delete_location.html', locations=locations)

# Start Capturing route
@app.route('/start_capturing')
def start_capturing():
    return render_template('start_capturing.html')

# Show Results route
@app.route('/show_results', methods=['GET', 'POST'])
def show_results():

    session.pop('_flashes',None)
    if 'email' not in session:
        return redirect(url_for('login'))
    locations = Location.query.all()
    location_filter = request.args.get('location', None)
    underage_filter = request.args.get('underage_status', None)
    start_date = request.args.get('start_date', None)
    end_date = request.args.get('end_date', None)

    query = Result.query.join(Location).add_columns(
        Result.id, Result.date_time, Result.image_path, Result.underage_status, Location.location_name
    )

    if location_filter:
        query = query.filter(Location.location_name == location_filter)

    if underage_filter:
        underage_bool = True if underage_filter == "Yes" else False
        query = query.filter(Result.underage_status == underage_bool)

    if start_date and end_date:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        query = query.filter(Result.date_time >= start, Result.date_time <= end)

    page = request.args.get('page', 1, type=int)
    per_page = 10
    pagination = query.paginate(page=page, per_page=per_page)

    # Check if any filters have been applied
    filters_applied = any([location_filter, underage_filter, start_date, end_date])

    return render_template(
        'show_results.html', 
        results=pagination.items, 
        pagination=pagination, 
        location_filter=location_filter, 
        underage_filter=underage_filter, 
        start_date=start_date, 
        end_date=end_date , 
        locations = locations , 
        filters_applied = filters_applied
        )

# Logout route
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Main entry point
if __name__ == "__main__":
    app.run(debug=True)
