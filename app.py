from flask import Flask,render_template,g,request,session,redirect,url_for
from database import get_db
from werkzeug.security import generate_password_hash, check_password_hash
import os

count_dict = dict()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(42)

@app.teardown_appcontext
def close_db(error):
      if hasattr(g,'sqlite_db'):
             g.sqlite_db.close()

def get_curr_user():
   result = None
   if 'user' in session:
      user = session['user']
      db = get_db()
      result = db.execute('select id, name, password, expert,  admin from users where name=?',[user])
      result = result.fetchone()
   return result

@app.route("/")
def index():
   user = get_curr_user()
   db = get_db()
   res = db.execute('select questions.id as id, questions.question_text, questions.answer_text,  askers.name as askers_name, experts.name as expert_name from questions join users as askers on askers.id = questions.asked_by_id join users as experts on experts.id = questions.expert_id where questions.answer_text is not null')
   question_res = res.fetchall()
   return render_template('home.html',user=user,questions= question_res);

@app.route('/register',methods=['POST','GET'])
def register():
   user = get_curr_user()
   if request.method == 'POST':
         db = get_db()
         existing_usr = db.execute('select id from users where name=?',
                                   [request.form["Name"]])
         # print(existing_usr)
         if existing_usr.fetchone():
               return render_template('register.html',user=user,error="This User already exits")
         hashed_pass = generate_password_hash(request.form["Password"], method="sha256")
         db.execute('Insert into users (name, password, expert, admin) values (?, ?, ?, ?)',
                    [request.form["Name"],
                     hashed_pass, '0', '0'])
         db.commit()
         session['user'] = request.form["Name"]
         return redirect(url_for('index'))
   return render_template('register.html', user=user)

@app.route('/login',methods=['GET','POST'])
def login():
      user = get_curr_user()
      if request.method == 'POST':
         db = get_db()
         name = request.form["Name"]
         passwd = request.form["Password"]
         res = db.execute('select id, name, password from users where name=?',[name])
         user_res = res.fetchone()
         if user_res:
            if check_password_hash(user_res['password'], passwd):
               session['user'] = user_res['name']
               return redirect(url_for('index'))
            else:
               return render_template('login.html',err="Password or Username is Incorrect")
         else:
            return render_template('login.html',err="Password or Username is Incorrect")
      return render_template('login.html',user=user)

@app.route('/question/<question_id>')
def question(question_id):
   user = get_curr_user()
   db = get_db()
   res = db.execute('select questions.question_text, questions.answer_text,  askers.name as askers_name, experts.name as expert_name from questions join users as askers on askers.id = questions.asked_by_id join users as experts on experts.id = questions.expert_id where questions.id=?',[question_id])
   res = res.fetchone()
   return render_template('question.html', user=user, question=res)

@app.route('/answer/<question_id>',methods=['GET','POST'])
def answer(question_id):
   user = get_curr_user()
   db = get_db()
   if request.method == 'POST':
          db.execute('Update questions set answer_text=? where id=?',[request.form['Answer'], question_id])
          db.commit()
          return redirect(url_for('unanswered'))
   result = db.execute('select id from users where name=? and (admin=1 or expert = 1)',[user["name"]])
   if result.fetchone():
         res = db.execute('select question_text, id from questions where id=?',[question_id])
         question = res.fetchone()
         return render_template('answer.html',user=user,question=question)
   else:
         return redirect(url_for('index'))

@app.route('/ask',methods=['GET','POST'])
def ask():
   user = get_curr_user()
   if request.method == 'POST':
         if not request.form['question'] or ' ' in request.form['question'][0]:
               return redirect(url_for('ask'))
         db = get_db()
         db.execute('Insert into questions (question_text, asked_by_id, expert_id) values (?, ?, ?)',
                    [request.form['question'],
                     user['id'],
                     request.form['expert']])
         db.commit()
         return redirect(url_for('index'))
   db = get_db()
   exps = db.execute('select * from users where expert = 1')
   exps = exps.fetchall()
   return render_template('ask.html',user=user,experts=exps)

@app.route('/unanswered')
def unanswered():
   user = get_curr_user()
   db = get_db()
   fetch = db.execute('select * from questions where answer_text is NULL')
   fetch = fetch.fetchall()
   for_exp = []
   for question in fetch:
          if question['expert_id'] == user['id']:
            f = db.execute('select name from users where id= ?',[question['asked_by_id']])
            f = f.fetchone()
            for_exp.append((question,f['name']))
   return render_template('unanswered.html',user=user,questions=for_exp)

@app.route('/users')
def users():
   user = get_curr_user()
   db = get_db()
   if not user:
         return redirect(url_for('login'))
   es = db.execute('select name from users where id=? and admin=1',[user['id']])
   es = es.fetchone()
   if es:
      all_users = db.execute('select id, name, expert, admin from users')
      all_users = all_users.fetchall()
      return render_template('users.html',user=user,users=all_users)
   else:
      return redirect(url_for('index'))

@app.route("/promote/<user_id>")
def promote(user_id):
      user = get_curr_user()
      if not user:
         return redirect(url_for('login'))
      db = get_db()
      ek = db.execute('select id, name from users where id=? and expert=1',[user['id']])
      ek = ek.fetchone()
      if ek:
         res = db.execute('select expert from users where id=?',[user_id])
         res = res.fetchone()
         if res['expert']:
            db.execute('Update users set expert = 0 where id = ?',[user_id])
            db.commit()
         else:
            db.execute('Update users set expert= 1 where id = ?',[user_id])
            db.commit()
         return redirect(url_for('users'))
      else:
         return redirect(url_for('index'))

@app.route("/logout")
def logout():
   session.pop('user',None)
   return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)