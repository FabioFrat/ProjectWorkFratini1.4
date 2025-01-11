from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mysqldb import MySQL
from config.config import Config
from functools import wraps
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import calendar
import random
import string

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = 'chiave-segreta-qualsiasi'  

mysql = MySQL(app)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/rooms')
def rooms():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM rooms")
    rooms = cur.fetchall()
    cur.close()
    return render_template('rooms.html', rooms=rooms)

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form.get('email')
        if email == "admin@admin.it":
            session['admin_logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        flash('Email non valida')
    return render_template('admin/login.html')

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    cur = mysql.connection.cursor()
    
    stats = {}
    
    cur.execute("SELECT COUNT(*) FROM bookings WHERE status != 'cancelled'")
    stats['total_bookings'] = cur.fetchone()[0]
    
    cur.execute("""
        SELECT COUNT(*) FROM bookings 
        WHERE check_in > CURDATE()
        AND status = 'confirmed'
    """)
    stats['active_bookings'] = cur.fetchone()[0]
    
    
    cur.execute("""
        SELECT 
            COALESCE(SUM(CASE WHEN status = 'confirmed' THEN total_price ELSE 0 END), 0) as confirmed_revenue,
            COALESCE(SUM(CASE WHEN status = 'pending' AND check_in > CURDATE() THEN total_price ELSE 0 END), 0) as pending_revenue
        FROM bookings 
        WHERE status != 'cancelled'
    """)
    revenues = cur.fetchone()
    stats['total_revenue'] = float(revenues[0] + revenues[1])  
    
    cur.execute("""
        SELECT b.*, r.name as room_name,
               DATEDIFF(b.check_out, b.check_in) as nights,
               r.price_per_night
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        ORDER BY b.created_at DESC
        LIMIT 10
    """)
    columns = [column[0] for column in cur.description]
    bookings = []
    for row in cur.fetchall():
        booking = dict(zip(columns, row))
        if booking['total_price'] == 0:
            total_price = booking['nights'] * booking['price_per_night']
            cur.execute("""
                UPDATE bookings 
                SET total_price = %s 
                WHERE id = %s
            """, (total_price, booking['id']))
            booking['total_price'] = total_price
        bookings.append(booking)
    mysql.connection.commit()
    
    monthly_stats = {
        'labels': [],
        'revenue': [],
        'future_revenue': []
    }
    
    today = date.today()
    start_date = today - relativedelta(months=6)
    start_date = start_date.replace(day=1)
    
    for i in range(13):  
        current_date = start_date + relativedelta(months=i)
        next_month = current_date + relativedelta(months=1)
        month_name = current_date.strftime("%B %Y")
        monthly_stats['labels'].append(month_name)
        
        cur.execute("""
            SELECT COALESCE(SUM(total_price), 0) as total
            FROM bookings
            WHERE DATE(check_in) >= %s 
            AND DATE(check_in) < %s
            AND status = 'confirmed'
        """, (current_date, next_month))
        confirmed_revenue = float(cur.fetchone()[0])
        
        cur.execute("""
            SELECT COALESCE(SUM(total_price), 0) as total
            FROM bookings
            WHERE DATE(check_in) >= %s 
            AND DATE(check_in) < %s
            AND DATE(check_in) > CURDATE()
            AND status = 'pending'
        """, (current_date, next_month))
        pending_revenue = float(cur.fetchone()[0])
        
        monthly_stats['revenue'].append(confirmed_revenue)
        monthly_stats['future_revenue'].append(pending_revenue)
    
    cur.close()
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         bookings=bookings,
                         monthly_stats=monthly_stats)
    
@app.route('/admin/bookings')
@admin_required
def admin_bookings():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT 
            b.id,
            r.name as room_name,
            b.guest_name,
            b.guest_email,
            b.check_in,
            b.check_out,
            b.total_price,
            b.status
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        ORDER BY b.check_in DESC
    """)
    columns = [column[0] for column in cur.description]
    bookings = []
    for row in cur.fetchall():
        booking = dict(zip(columns, row))
        bookings.append(booking)
    cur.close()
    return render_template('admin/bookings.html', bookings=bookings)

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


@app.route('/admin/booking/<int:booking_id>/confirm')
@admin_required
def admin_confirm_booking(booking_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE bookings 
        SET status = 'confirmed' 
        WHERE id = %s
    """, (booking_id,))
    mysql.connection.commit()
    cur.close()
    flash('Prenotazione confermata con successo', 'success')
    return redirect(url_for('admin_bookings'))

@app.route('/admin/booking/<int:booking_id>/cancel')
@admin_required
def admin_cancel_booking(booking_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        UPDATE bookings 
        SET status = 'cancelled' 
        WHERE id = %s
    """, (booking_id,))
    mysql.connection.commit()
    cur.close()
    flash('Prenotazione cancellata con successo', 'success')
    return redirect(url_for('admin_bookings'))

@app.route('/admin/booking/<int:booking_id>')
@admin_required
def admin_booking_details(booking_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.*, r.name as room_name
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        WHERE b.id = %s
    """, (booking_id,))
    booking = cur.fetchone()
    cur.close()
    
    if not booking:
        flash('Prenotazione non trovata', 'error')
        return redirect(url_for('admin_bookings'))
        
    return render_template('admin/booking_details.html', booking=booking)

def generate_confirmation_code():
    """Genera un codice di conferma univoco"""
    characters = string.ascii_uppercase + string.digits
    while True:
        code = 'B&amp;B-' + ''.join(random.choices(characters, k=6))
        cur = mysql.connection.cursor()
        cur.execute("SELECT id FROM bookings WHERE confirmation_code = %s", (code,))
        if not cur.fetchone():
            cur.close()
            return code
        cur.close()
        
def is_room_available(room_id, check_in, check_out, exclude_booking_id=None):
    """
    Verifica se una camera è disponibile per le date specificate
    exclude_booking_id: esclude una prenotazione specifica (utile per le modifiche)
    """
    cur = mysql.connection.cursor()
    
    query = """
        SELECT COUNT(*) 
        FROM bookings 
        WHERE room_id = %s 
        AND status != 'cancelled'
        AND (
            (check_in <= %s AND check_out > %s)
            OR (check_in < %s AND check_out >= %s)
            OR (%s <= check_in AND %s > check_in)
        )
    """
    params = [room_id, check_in, check_in, check_out, check_out, check_in, check_out]
    
    if exclude_booking_id:
        query += " AND id != %s"
        params.append(exclude_booking_id)
        
    cur.execute(query, params)
    count = cur.fetchone()[0]
    cur.close()
    
    return count == 0

@app.route('/booking/<int:room_id>', methods=['GET', 'POST'])
def booking(room_id):
    if request.method == 'POST':
        guest_name = request.form['guest_name']
        guest_email = request.form['guest_email']
        check_in = datetime.strptime(request.form['check_in'], '%Y-%m-%d')
        check_out = datetime.strptime(request.form['check_out'], '%Y-%m-%d')
        
        if not is_room_available(room_id, check_in, check_out):
            flash('Camera non disponibile per le date selezionate. Scegli altre date.', 'error')
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM rooms WHERE id = %s", (room_id,))
            room = cur.fetchone()
            cur.close()
            return render_template('booking.html', room=room, today=date.today().isoformat())
        
        nights = (check_out - check_in).days
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT price_per_night, name FROM rooms WHERE id = %s", (room_id,))
        room_info = cur.fetchone()
        price_per_night = room_info[0]
        room_name = room_info[1]
        total_price = nights * price_per_night
        
        confirmation_code = generate_confirmation_code()
        
        cur.execute("""
            INSERT INTO bookings 
            (room_id, guest_name, guest_email, check_in, check_out, total_price, status, confirmation_code)
            VALUES (%s, %s, %s, %s, %s, %s, 'pending', %s)
        """, (room_id, guest_name, guest_email, check_in, check_out, total_price, confirmation_code))
        mysql.connection.commit()
        
        confirmation_message = f"""
        Prenotazione effettuata con successo!
        Camera: {room_name}
        Check-in: {check_in.strftime('%d/%m/%Y')}
        Check-out: {check_out.strftime('%d/%m/%Y')}
        Totale: €{total_price:.2f}
        Codice di conferma: {confirmation_code}
        """
        
        flash(confirmation_message, 'success')
        cur.close()
        return redirect(url_for('booking_confirmation', confirmation_code=confirmation_code))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM rooms WHERE id = %s", (room_id,))
    room = cur.fetchone()
    cur.close()
    
    today = date.today().isoformat()
    return render_template('booking.html', room=room, today=today)

@app.route('/booking/confirmation/<confirmation_code>')
def booking_confirmation(confirmation_code):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.*, r.name as room_name, r.price_per_night
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        WHERE b.confirmation_code = %s
    """, (confirmation_code,))
    
    columns = [desc[0] for desc in cur.description] 
    booking_data = cur.fetchone()
    cur.close()
    
    if not booking_data:
        flash('Prenotazione non trovata', 'error')
        return redirect(url_for('index'))
    
    booking = dict(zip(columns, booking_data))
    
    return render_template('booking_confirmation.html', booking=booking)

@app.route('/manage-booking', methods=['GET'])
def manage_booking():
    return render_template('manage_booking.html')

@app.route('/find-booking', methods=['POST'])
def find_booking():
    confirmation_code = request.form.get('confirmation_code')
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT b.*, r.name as room_name, r.price_per_night
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        WHERE b.confirmation_code = %s AND b.status != 'cancelled'
    """, (confirmation_code,))
    
    columns = [desc[0] for desc in cur.description]
    booking_data = cur.fetchone()
    cur.close()
    
    if not booking_data:
        flash('Prenotazione non trovata o cancellata', 'error')
        return redirect(url_for('manage_booking'))
    
    booking = dict(zip(columns, booking_data))
    today = date.today().isoformat()
    
    return render_template('edit_booking.html', booking=booking, today=today)

@app.route('/booking/<confirmation_code>/update', methods=['POST'])
def update_booking(confirmation_code):
    cur = mysql.connection.cursor()
    
    cur.execute("""
        SELECT b.*, r.price_per_night
        FROM bookings b
        JOIN rooms r ON b.room_id = r.id
        WHERE confirmation_code = %s
    """, (confirmation_code,))
    booking_data = cur.fetchone()
    
    if not booking_data:
        flash('Prenotazione non trovata', 'error')
        return redirect(url_for('manage_booking'))
    
    new_check_in = datetime.strptime(request.form['check_in'], '%Y-%m-%d')
    new_check_out = datetime.strptime(request.form['check_out'], '%Y-%m-%d')
    
    if not is_room_available(booking_data[1], new_check_in, new_check_out, booking_data[0]):
        flash('La camera non è disponibile per le date selezionate', 'error')
        return redirect(url_for('find_booking'), code=307)
    
    nights = (new_check_out - new_check_in).days
    new_total_price = nights * booking_data[-1]  
    
    cur.execute("""
        UPDATE bookings
        SET guest_name = %s,
            guest_email = %s,
            check_in = %s,
            check_out = %s,
            total_price = %s
        WHERE confirmation_code = %s
    """, (
        request.form['guest_name'],
        request.form['guest_email'],
        new_check_in,
        new_check_out,
        new_total_price,
        confirmation_code
    ))
    
    mysql.connection.commit()
    cur.close()
    
    flash('Prenotazione aggiornata con successo!', 'success')
    return redirect(url_for('booking_confirmation', confirmation_code=confirmation_code))

@app.route('/booking/<confirmation_code>/cancel')
def cancel_booking(confirmation_code):
    cur = mysql.connection.cursor()
    
    cur.execute("UPDATE bookings SET status = 'cancelled' WHERE confirmation_code = %s", (confirmation_code,))
    mysql.connection.commit()
    cur.close()
    
    flash('Prenotazione cancellata con successo', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)