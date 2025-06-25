import os
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Initialize CSV files with headers if they don't exist
def init_csv(file_path, headers):
    if not os.path.exists(file_path):
        with open(file_path, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers)

init_csv('data/users.csv', ['id', 'username', 'password', 'email', 'phone'])
init_csv('data/admins.csv', ['id', 'username', 'password'])
init_csv('data/services.csv', ['id', 'name', 'description', 'price', 'duration'])
init_csv('data/reservations.csv', ['id', 'user_id', 'service_id', 'date', 'time', 'barber', 'status'])
init_csv('data/reviews.csv', ['id', 'user_id', 'rating', 'comment', 'date'])

# Helper functions for CSV operations
def read_csv(file_path):
    with open(file_path, 'r') as file:
        return list(csv.DictReader(file))

def write_csv(file_path, data, headers):
    with open(file_path, 'w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writeheader()
        writer.writerows(data)

def append_csv(file_path, row, headers):
    with open(file_path, 'a', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=headers)
        writer.writerow(row)

def get_next_id(file_path):
    data = read_csv(file_path)
    if not data:
        return 1
    return max(int(row['id']) for row in data) + 1

# Authentication functions
def authenticate_user(username, password):
    users = read_csv('data/users.csv')
    for user in users:
        if user['username'] == username and user['password'] == password:
            return user
    return None

def authenticate_admin(username, password):
    admins = read_csv('data/admins.csv')
    for admin in admins:
        if admin['username'] == username and admin['password'] == password:
            return admin
    return None

def username_exists(username):
    users = read_csv('data/users.csv')
    admins = read_csv('data/admins.csv')
    return any(u['username'] == username for u in users + admins)

# Routes
@app.route('/')
def home():
    services = read_csv('data/services.csv')[:4]  # Show only 4 services on home page
    reviews = read_csv('data/reviews.csv')[-3:]   # Show 3 most recent reviews
    return render_template('home.html', services=services, reviews=reviews)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_type = request.form.get('user_type', 'user')
        
        if user_type == 'admin':
            admin = authenticate_admin(username, password)
            if admin:
                session['user_id'] = admin['id']
                session['username'] = admin['username']
                session['is_admin'] = True
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid admin credentials', 'danger')
        else:
            user = authenticate_user(username, password)
            if user:
                session['user_id'] = user['id']
                session['username'] = user['username']
                session['is_admin'] = False
                return redirect(url_for('home'))
            else:
                flash('Invalid user credentials', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        phone = request.form['phone']
        
        if username_exists(username):
            flash('Username already exists', 'danger')
        else:
            user_id = get_next_id('data/users.csv')
            new_user = {
                'id': user_id,
                'username': username,
                'password': password,
                'email': email,
                'phone': phone
            }
            append_csv('data/users.csv', new_user, ['id', 'username', 'password', 'email', 'phone'])
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/services')
def services():
    services = read_csv('data/services.csv')
    return render_template('services.html', services=services)

@app.route('/reservations')
def reservations():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    all_reservations = read_csv('data/reservations.csv')
    services = {s['id']: s for s in read_csv('data/services.csv')}
    
    user_reservations = [
        {**res, 'service_name': services.get(res['service_id'], {}).get('name', 'Unknown')}
        for res in all_reservations if res['user_id'] == user_id
    ]
    
    return render_template('reservations.html', reservations=user_reservations)

@app.route('/make_reservation', methods=['GET', 'POST'])
def make_reservation():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        service_id = request.form['service_id']
        date = request.form['date']
        time = request.form['time']
        barber = request.form['barber']
        
        reservation_id = get_next_id('data/reservations.csv')
        new_reservation = {
            'id': reservation_id,
            'user_id': session['user_id'],
            'service_id': service_id,
            'date': date,
            'time': time,
            'barber': barber,
            'status': 'confirmed'
        }
        append_csv('data/reservations.csv', new_reservation, 
                  ['id', 'user_id', 'service_id', 'date', 'time', 'barber', 'status'])
        flash('Reservation made successfully!', 'success')
        return redirect(url_for('reservations'))
    
    services = read_csv('data/services.csv')
    barbers = ['John', 'Mike', 'Sarah', 'David']  # Example barbers
    return render_template('make_reservation.html', services=services, barbers=barbers)

@app.route('/cancel_reservation/<reservation_id>', methods=['GET', 'POST'])
def cancel_reservation(reservation_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    reservations = read_csv('data/reservations.csv')
    reservation = next((r for r in reservations if r['id'] == reservation_id), None)
    
    if not reservation or reservation['user_id'] != session['user_id']:
        flash('Reservation not found or not authorized', 'danger')
        return redirect(url_for('reservations'))
    
    if request.method == 'POST':
        updated_reservations = [r for r in reservations if r['id'] != reservation_id]
        write_csv('data/reservations.csv', updated_reservations, 
                 ['id', 'user_id', 'service_id', 'date', 'time', 'barber', 'status'])
        flash('Reservation cancelled successfully', 'success')
        return redirect(url_for('reservations'))
    
    services = {s['id']: s for s in read_csv('data/services.csv')}
    reservation['service_name'] = services.get(reservation['service_id'], {}).get('name', 'Unknown')
    return render_template('cancel_reservation.html', reservation=reservation)

@app.route('/reviews', methods=['GET', 'POST'])
def reviews():
    if request.method == 'POST':
        if 'user_id' not in session:
            return redirect(url_for('login'))
        
        rating = request.form['rating']
        comment = request.form['comment']
        
        review_id = get_next_id('data/reviews.csv')
        new_review = {
            'id': review_id,
            'user_id': session['user_id'],
            'rating': rating,
            'comment': comment,
            'date': datetime.now().strftime('%Y-%m-%d')
        }
        append_csv('data/reviews.csv', new_review, ['id', 'user_id', 'rating', 'comment', 'date'])
        flash('Thank you for your review!', 'success')
        return redirect(url_for('reviews'))
    
    reviews = read_csv('data/reviews.csv')
    users = {u['id']: u['username'] for u in read_csv('data/users.csv')}
    
    for review in reviews:
        review['username'] = users.get(review['user_id'], 'Anonymous')
    
    return render_template('reviews.html', reviews=reviews)

@app.route('/contact')
def contact():
    branches = [
        {'location': 'Jakarta', 'address': 'Jl. Kembang Raya, Jakarta Pusat', 'phone': '(123) 456-7890'},
        {'location': 'Bali', 'address': 'Jl. Kenari No.61, Kota Denpasar', 'phone': '(123) 456-7891'},
        {'location': 'Yogyakarta', 'address': 'Jl. Sisingamangaraja No.65, Kota Denpasar', 'phone': '(123) 456-7892'}
    ]
    return render_template('contact.html', branches=branches)

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    reservations = read_csv('data/reservations.csv')
    services = {s['id']: s for s in read_csv('data/services.csv')}
    users = {u['id']: u for u in read_csv('data/users.csv')}
    
    # Enhance reservation data with service and user info
    enhanced_reservations = []
    for res in reservations:
        enhanced = res.copy()
        enhanced['service_name'] = services.get(res['service_id'], {}).get('name', 'Unknown')
        enhanced['username'] = users.get(res['user_id'], {}).get('username', 'Unknown')
        enhanced_reservations.append(enhanced)
    
    stats = {
        'total_reservations': len(reservations),
        'confirmed_reservations': sum(1 for r in reservations if r['status'] == 'confirmed'),
        'cancelled_reservations': sum(1 for r in reservations if r['status'] == 'cancelled'),
        'total_users': len(users),
        'total_services': len(services)
    }
    
    return render_template('admin_dashboard.html', 
                         reservations=enhanced_reservations, 
                         stats=stats)

@app.route('/admin/delete/<dataset>')
def admin_delete(dataset):
    if 'user_id' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    
    file_map = {
        'users': 'data/users.csv',
        'admins': 'data/admins.csv',
        'services': 'data/services.csv',
        'reservations': 'data/reservations.csv',
        'reviews': 'data/reviews.csv'
    }
    
    if dataset in file_map:
        headers = {
            'users': ['id', 'username', 'password', 'email', 'phone'],
            'admins': ['id', 'username', 'password'],
            'services': ['id', 'name', 'description', 'price', 'duration'],
            'reservations': ['id', 'user_id', 'service_id', 'date', 'time', 'barber', 'status'],
            'reviews': ['id', 'user_id', 'rating', 'comment', 'date']
        }
        
        # Write empty file with headers
        with open(file_map[dataset], 'w', newline='') as file: 
            writer = csv.DictWriter(file, fieldnames=headers[dataset])
            writer.writeheader()
        
        flash(f'All {dataset} data has been cleared', 'success')
    else:
        flash('Invalid dataset', 'danger')
    
    return redirect(url_for('admin_dashboard'))

if __name__ == '__main__':
    # Create a default admin if none exists
    admins = read_csv('data/admins.csv')
    if not admins:
        with open('data/admins.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['1', 'admin', 'admin123'])
    
    # Create some sample services if none exist
    services = read_csv('data/services.csv')
    if not services:
        sample_services = [
            ['1', 'Haircut', 'Basic haircut with styling', '25', '30'],
            ['2', 'Beard Trim', 'Beard shaping and trimming', '15', '20'],
            ['3', 'Haircut + Beard', 'Combination package', '35', '45'],
            ['4', 'Hair Coloring', 'Full hair coloring service', '50', '60']
        ]
        with open('data/services.csv', 'a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(sample_services)
    
    app.run(debug=True)