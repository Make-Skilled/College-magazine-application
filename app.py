from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os
import uuid
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# MongoDB configuration
client = MongoClient('mongodb://localhost:27017/')
db = client['college_magazine']
students_collection = db['students']
events_collection = db['events']
news_collection = db['news']
gallery_collection = db['gallery']
registrations_collection = db['registrations']

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'news'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'events'), exist_ok=True)
os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'gallery'), exist_ok=True)

# Admin credentials (hardcoded for simplicity)
ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'admin123'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            flash('Please login as admin to access this page.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('student_id'):
            flash('Please login first to access this page.', 'error')
            return redirect(url_for('student_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

# Admin Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials!', 'error')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    # Get counts for dashboard
    news_count = news_collection.count_documents({})
    events_count = events_collection.count_documents({})
    gallery_count = gallery_collection.count_documents({})
    students_count = students_collection.count_documents({})
    
    return render_template('admin_dashboard.html', 
                         news_count=news_count,
                         events_count=events_count,
                         gallery_count=gallery_count,
                         students_count=students_count)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

# News Management
@app.route('/admin/news')
@admin_required
def admin_news():
    news = list(news_collection.find().sort('date', -1))
    return render_template('admin_news.html', news=news)

@app.route('/admin/news/add', methods=['GET', 'POST'])
@admin_required
def admin_add_news():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image = request.files['image']
        
        news_data = {
            'title': title,
            'content': content,
            'date': datetime.now(),
            'image': None
        }
        
        if image and allowed_file(image.filename):
            filename = str(uuid.uuid4()) + '.' + image.filename.rsplit('.', 1)[1].lower()
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], 'news', filename))
            news_data['image'] = filename
        
        news_collection.insert_one(news_data)
        flash('News added successfully!', 'success')
        return redirect(url_for('admin_news'))
    
    return render_template('admin_add_news.html')

@app.route('/admin/news/edit/<news_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_news(news_id):
    news = news_collection.find_one({'_id': ObjectId(news_id)})
    if not news:
        flash('News not found!', 'error')
        return redirect(url_for('admin_news'))
    
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        image = request.files['image']
        
        update_data = {
            'title': title,
            'content': content,
            'date': news['date']  # Keep original date
        }
        
        if image and allowed_file(image.filename):
            filename = str(uuid.uuid4()) + '.' + image.filename.rsplit('.', 1)[1].lower()
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], 'news', filename))
            update_data['image'] = filename
        else:
            update_data['image'] = news.get('image')
        
        news_collection.update_one({'_id': ObjectId(news_id)}, {'$set': update_data})
        flash('News updated successfully!', 'success')
        return redirect(url_for('admin_news'))
    
    return render_template('admin_edit_news.html', news=news)

@app.route('/admin/news/delete/<news_id>')
@admin_required
def admin_delete_news(news_id):
    news_collection.delete_one({'_id': ObjectId(news_id)})
    flash('News deleted successfully!', 'success')
    return redirect(url_for('admin_news'))

# Events Management
@app.route('/admin/events')
@admin_required
def admin_events():
    events = list(events_collection.find().sort('date', -1))
    return render_template('admin_events.html', events=events)

@app.route('/admin/events/add', methods=['GET', 'POST'])
@admin_required
def admin_add_event():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        date = request.form['date']
        location = request.form['location']
        image = request.files['image']
        
        event_data = {
            'title': title,
            'description': description,
            'date': datetime.strptime(date, '%Y-%m-%d'),
            'location': location,
            'created_at': datetime.now(),
            'image': None
        }
        
        if image and allowed_file(image.filename):
            filename = str(uuid.uuid4()) + '.' + image.filename.rsplit('.', 1)[1].lower()
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], 'events', filename))
            event_data['image'] = filename
        
        events_collection.insert_one(event_data)
        flash('Event added successfully!', 'success')
        return redirect(url_for('admin_events'))
    
    return render_template('admin_add_event.html')

@app.route('/admin/events/edit/<event_id>', methods=['GET', 'POST'])
@admin_required
def admin_edit_event(event_id):
    event = events_collection.find_one({'_id': ObjectId(event_id)})
    if not event:
        flash('Event not found!', 'error')
        return redirect(url_for('admin_events'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        date = request.form['date']
        location = request.form['location']
        image = request.files['image']
        
        update_data = {
            'title': title,
            'description': description,
            'date': datetime.strptime(date, '%Y-%m-%d'),
            'location': location,
            'created_at': event['created_at']
        }
        
        if image and allowed_file(image.filename):
            filename = str(uuid.uuid4()) + '.' + image.filename.rsplit('.', 1)[1].lower()
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], 'events', filename))
            update_data['image'] = filename
        else:
            update_data['image'] = event.get('image')
        
        events_collection.update_one({'_id': ObjectId(event_id)}, {'$set': update_data})
        flash('Event updated successfully!', 'success')
        return redirect(url_for('admin_events'))
    
    return render_template('admin_edit_event.html', event=event)

@app.route('/admin/events/delete/<event_id>')
@admin_required
def admin_delete_event(event_id):
    events_collection.delete_one({'_id': ObjectId(event_id)})
    flash('Event deleted successfully!', 'success')
    return redirect(url_for('admin_events'))

@app.route('/admin/events/registrations/<event_id>')
@admin_required
def admin_event_registrations(event_id):
    event = events_collection.find_one({'_id': ObjectId(event_id)})
    if not event:
        flash('Event not found!', 'error')
        return redirect(url_for('admin_events'))
    
    # Get all registrations for this event
    registrations = list(registrations_collection.find({'event_id': event_id}))
    
    # Get student details for each registration
    registered_students = []
    for reg in registrations:
        student = students_collection.find_one({'_id': ObjectId(reg['student_id'])})
        if student:
            registered_students.append({
                'name': student['name'],
                'roll_no': student['roll_no'],
                'email': student['email'],
                'registered_at': reg['registered_at']
            })
    
    return render_template('admin_event_registrations.html', 
                         event=event, 
                         registrations=registered_students)

# Gallery Management
@app.route('/admin/gallery')
@admin_required
def admin_gallery():
    images = list(gallery_collection.find().sort('date', -1))
    return render_template('admin_gallery.html', images=images)

@app.route('/admin/gallery/add', methods=['GET', 'POST'])
@admin_required
def admin_add_image():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        image = request.files['image']
        
        if image and allowed_file(image.filename):
            filename = str(uuid.uuid4()) + '.' + image.filename.rsplit('.', 1)[1].lower()
            image.save(os.path.join(app.config['UPLOAD_FOLDER'], 'gallery', filename))
            
            image_data = {
                'title': title,
                'description': description,
                'filename': filename,
                'date': datetime.now()
            }
            
            gallery_collection.insert_one(image_data)
            flash('Image added successfully!', 'success')
            return redirect(url_for('admin_gallery'))
        else:
            flash('Please select a valid image file!', 'error')
    
    return render_template('admin_add_image.html')

@app.route('/admin/gallery/delete/<image_id>')
@admin_required
def admin_delete_image(image_id):
    gallery_collection.delete_one({'_id': ObjectId(image_id)})
    flash('Image deleted successfully!', 'success')
    return redirect(url_for('admin_gallery'))

# Student Routes
@app.route('/student/register', methods=['GET', 'POST'])
def student_register():
    if request.method == 'POST':
        roll_no = request.form['roll_no']
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        
        # Check if student already exists
        if students_collection.find_one({'roll_no': roll_no}):
            flash('Student with this roll number already exists!', 'error')
            return render_template('student_register.html')
        
        if students_collection.find_one({'email': email}):
            flash('Student with this email already exists!', 'error')
            return render_template('student_register.html')
        
        student_data = {
            'roll_no': roll_no,
            'email': email,
            'name': name,
            'password': generate_password_hash(password),
            'created_at': datetime.now()
        }
        
        students_collection.insert_one(student_data)
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('student_login'))
    
    return render_template('student_register.html')

@app.route('/student/login', methods=['GET', 'POST'])
def student_login():
    if request.method == 'POST':
        roll_no = request.form['roll_no']
        password = request.form['password']
        
        student = students_collection.find_one({'roll_no': roll_no})
        
        if student and check_password_hash(student['password'], password):
            session['student_id'] = str(student['_id'])
            session['student_name'] = student['name']
            flash('Login successful!', 'success')
            return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid credentials!', 'error')
    
    return render_template('student_login.html')

@app.route('/student/dashboard')
@student_required
def student_dashboard():
    # Get recent data for dashboard
    recent_news = list(news_collection.find().sort('date', -1).limit(3))
    upcoming_events = list(events_collection.find({'date': {'$gte': datetime.now()}}).sort('date', 1).limit(3))
    recent_images = list(gallery_collection.find().sort('date', -1).limit(6))
    
    return render_template('student_dashboard.html', 
                         recent_news=recent_news,
                         upcoming_events=upcoming_events,
                         recent_images=recent_images)

@app.route('/student/logout')
def student_logout():
    session.pop('student_id', None)
    session.pop('student_name', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/student/my-events')
@student_required
def student_my_events():
    student_id = session.get('student_id')
    
    # Get all registrations for this student
    registrations = list(registrations_collection.find({'student_id': student_id}))
    
    # Get event details for each registration
    registered_events = []
    for reg in registrations:
        event = events_collection.find_one({'_id': ObjectId(reg['event_id'])})
        if event:
            event['registered_at'] = reg['registered_at']
            registered_events.append(event)
    
    return render_template('student_my_events.html', events=registered_events)

# Public Pages
@app.route('/news')
def news():
    news_list = list(news_collection.find().sort('date', -1))
    return render_template('news.html', news=news_list)

@app.route('/events')
def events():
    events_list = list(events_collection.find().sort('date', -1))
    return render_template('events.html', events=events_list)

@app.route('/gallery')
def gallery():
    images = list(gallery_collection.find().sort('date', -1))
    return render_template('gallery.html', images=images)

@app.route('/event/register/<event_id>', methods=['POST'])
def register_for_event(event_id):
    if not session.get('student_id'):
        return jsonify({'success': False, 'message': 'Please login first'})
    
    student_id = session.get('student_id')
    
    # Check if already registered
    existing_registration = registrations_collection.find_one({
        'student_id': student_id,
        'event_id': event_id
    })
    
    if existing_registration:
        return jsonify({'success': False, 'message': 'Already registered for this event'})
    
    registration_data = {
        'student_id': student_id,
        'event_id': event_id,
        'registered_at': datetime.now()
    }
    
    registrations_collection.insert_one(registration_data)
    return jsonify({'success': True, 'message': 'Successfully registered for the event'})

if __name__ == '__main__':
    app.run(debug=True)