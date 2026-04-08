from flask import Flask, render_template, request, session, flash, redirect, url_for
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

#accessing the .env
load_dotenv()

#keys
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

#secret-key
SECRET_KEY = os.getenv('SECRET_KEY')

#supabase build
supabase: Client = create_client(
    SUPABASE_URL, SUPABASE_KEY
)
print(SECRET_KEY)

#Flask Build
app = Flask(__name__)

#secret-key-build
app.secret_key=SECRET_KEY

# ROUTES
@app.route('/')
def landing_page():
    return render_template('landing_page.html')


@app.route('/login',methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        pwd = request.form.get('password')

        print(f'{email} {pwd} ')

        try:
            #login to the website
            data = supabase.auth.sign_in_with_password({
                'email':email,
                'password':pwd
            })
            #supabase session
            session['supabase_session'] = data.session.access_token
            #flask session
            session['user_id'] = data.user.id

            session['access_token'] = data.session.access_token

            print(f'{email} {pwd}   -->\n {session.get('supabase_session')}')

            return redirect(url_for('dashboard'))

        except Exception as e:
            return f"{e}"
            
    return render_template('Login.html')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        fname = request.form.get('first_name')
        lname = request.form.get('last_name')
        
        #data
        name = fname + lname
        email = request.form.get('email')
        pwd = request.form.get('password')
        c_pwd = request.form.get('confirm_password')

        try:
            if pwd != c_pwd:
                flash("Register Failed", "Check Password")
            
            else:
                response = supabase.auth.sign_up({
                    'email': email,
                    'password':pwd,
                    'options':{
                        'data':{
                            'name':name
                        }
                    }
                })

                return redirect(url_for('dashboard'))
            
        except Exception as e:
            return f"{e}"


    return render_template('register.html')

@app.route('/dash', methods=['GET', 'POST'])
def dashboard():
    token = session.get('supabase_session')

    try:
        if 'user_id' not in session:
            return redirect(url_for('login'))

        # ✅ Attach auth
        supabase.postgrest.auth(session['access_token'])

        # ✅ Get user info
        user_data = supabase.auth.get_user(token)
        user_name = 'Guest'
        user_email = 'Log in'

        if user_data:
            user_name = user_data.user.user_metadata.get('name', 'Guest')
            user_email = user_data.user.email

        # INSERT (only on POST)
        if request.method == 'POST':
            skill = request.form.get('skill')
            hrs = request.form.get('hours')
            descp = request.form.get('description')
            select_type = request.form.get('type-action')

            supabase.table('skill_logs').insert({
                'user_id': session['user_id'],
                'skill': skill,
                'time': hrs,
                'description': descp,
                'Type': select_type
            }).execute()


        # today's range (UTC)
        today = datetime.now(timezone.utc).date()
        start = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
        end = start + timedelta(days=1)

        # get today's entries (only this user)
        response = supabase.table('skill_logs') \
            .select('*') \
            .eq('user_id', session['user_id']) \
            .gte('created_at', start.isoformat()) \
            .lt('created_at', end.isoformat()) \
            .execute()

        sessions_log = response.data or []

        # total rows (today)
        total_rows = len(sessions_log)

        # total hours 🔥
        tot_hours = round(sum(float(row.get('time', 0) or 0) for row in sessions_log), 2)

        # unique skills
        uniq_skills = len(set(row['skill'] for row in sessions_log))

    except Exception as e:
        return f"Something went wrong: {e}"

    return render_template(
        'dashboard.html',
        email=user_email,
        total_sessions=total_rows,
        unique_skills=uniq_skills,
        entries = sessions_log,
        total_hours = tot_hours
    )


if __name__ == '__main__':
    app.run()
    
