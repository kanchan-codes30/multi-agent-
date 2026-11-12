"""
Multi-Agent AI Research Assistant - Main Flask Application
=============================================================
Modules implemented:
  1. User Login            -> /login, /signup, /logout
  2. Research Topic Input  -> /research (form + submit)
  3. Information Retrieval Agent  -> agents/retrieval_agent.py
  4. Summarization Agent          -> agents/summarization_agent.py
  5. Comparison & Analysis Agent  -> agents/comparison_agent.py
  6. Report Generation Agent      -> agents/report_agent.py
  7. Citation Management          -> agents/citation_agent.py
  8. Research History      -> /history
  9. Dashboard             -> /dashboard
  10. Export Reports       -> /export/<session_id>/<format>
  11. Admin Panel          -> /admin (platform-wide visibility for admins)
"""
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, jsonify
from functools import wraps

import database.db as db
from agents.orchestrator import ResearchOrchestrator
from utils.export_utils import export_to_docx, export_to_pdf

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

orchestrator = ResearchOrchestrator()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to continue.', 'warning')
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('You do not have permission to access the admin panel.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated


@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')

        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return redirect(url_for('signup'))

        success, message = db.create_user(username, email, password)
        if success:
            flash(message + ' Please log in.', 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'danger')
            return redirect(url_for('signup'))

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = db.verify_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user.get('is_admin'))
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@login_required
def dashboard():
    stats = db.get_dashboard_stats(session['user_id'])
    recent_sessions = db.get_user_sessions(session['user_id'])[:5]
    return render_template('dashboard.html', stats=stats, recent_sessions=recent_sessions)


@app.route('/research', methods=['GET', 'POST'])
@login_required
def research():
    if request.method == 'POST':
        topic = request.form.get('topic', '').strip()
        if not topic:
            flash('Please enter a research topic.', 'danger')
            return redirect(url_for('research'))

        session_id = db.create_session(session['user_id'], topic)
        return redirect(url_for('run_research', session_id=session_id))

    return render_template('research_input.html')


@app.route('/research/run/<int:session_id>')
@login_required
def run_research(session_id):
    research_session = db.get_session(session_id)
    if not research_session or research_session['user_id'] != session['user_id']:
        flash('Research session not found.', 'danger')
        return redirect(url_for('dashboard'))

    if research_session['status'] != 'completed':
        result = orchestrator.run_pipeline(session_id, research_session['topic'])
        return render_template('research_result.html', research_session=research_session, result=result)
    else:
        return redirect(url_for('view_report', session_id=session_id))


@app.route('/report/<int:session_id>')
@login_required
def view_report(session_id):
    research_session = db.get_session(session_id)
    if not research_session or research_session['user_id'] != session['user_id']:
        flash('Research session not found.', 'danger')
        return redirect(url_for('dashboard'))

    report = db.get_report_for_session(session_id)
    summaries = db.get_summaries_for_session(session_id)
    comparison = db.get_comparison_for_session(session_id)

    if not report:
        flash('This research session has not completed yet.', 'warning')
        return redirect(url_for('run_research', session_id=session_id))

    return render_template('report.html', research_session=research_session,
                            report=report, summaries=summaries, comparison=comparison)


@app.route('/history')
@login_required
def history():
    sessions = db.get_user_sessions(session['user_id'])
    return render_template('history.html', sessions=sessions)


@app.route('/export/<int:session_id>/<fmt>')
@login_required
def export_report(session_id, fmt):
    research_session = db.get_session(session_id)
    if not research_session or research_session['user_id'] != session['user_id']:
        flash('Research session not found.', 'danger')
        return redirect(url_for('dashboard'))

    report = db.get_report_for_session(session_id)
    if not report:
        flash('No report available to export.', 'warning')
        return redirect(url_for('history'))

    safe_topic = "".join(c if c.isalnum() or c in (' ', '_') else '' for c in research_session['topic']).strip().replace(' ', '_')

    if fmt == 'pdf':
        filename = f"{safe_topic}_report.pdf"
        filepath = export_to_pdf(report['title'], report['content'], filename)
        return send_file(filepath, as_attachment=True, download_name=filename)
    elif fmt == 'docx':
        filename = f"{safe_topic}_report.docx"
        filepath = export_to_docx(report['title'], report['content'], filename)
        return send_file(filepath, as_attachment=True, download_name=filename)
    elif fmt == 'txt':
        filename = f"{safe_topic}_report.txt"
        filepath = os.path.join(os.path.dirname(__file__), 'exports', filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report['content'])
        return send_file(filepath, as_attachment=True, download_name=filename)
    else:
        flash('Unsupported export format.', 'danger')
        return redirect(url_for('view_report', session_id=session_id))


@app.route('/history/delete/<int:session_id>', methods=['POST'])
@login_required
def delete_session(session_id):
    research_session = db.get_session(session_id)
    if research_session and research_session['user_id'] == session['user_id']:
        conn = db.get_connection()
        conn.execute("DELETE FROM research_sessions WHERE id = ?", (session_id,))
        conn.commit()
        conn.close()
        flash('Research session deleted.', 'info')
    return redirect(url_for('history'))


@app.route('/admin')
@admin_required
def admin_dashboard():
    stats = db.get_platform_stats()
    all_users = db.get_all_users()
    recent_sessions = db.get_all_sessions_admin()[:15]
    return render_template('admin_dashboard.html', stats=stats,
                            all_users=all_users, recent_sessions=recent_sessions)


@app.route('/admin/user/<int:user_id>')
@admin_required
def admin_view_user(user_id):
    target_user = db.get_user_by_id(user_id)
    if not target_user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_dashboard'))
    user_sessions = db.get_sessions_for_specific_user(user_id)
    return render_template('admin_user_detail.html', target_user=target_user, user_sessions=user_sessions)


@app.route('/admin/report/<int:session_id>')
@admin_required
def admin_view_report(session_id):
    research_session = db.get_session(session_id)
    if not research_session:
        flash('Research session not found.', 'danger')
        return redirect(url_for('admin_dashboard'))

    report = db.get_report_for_session(session_id)
    summaries = db.get_summaries_for_session(session_id)
    comparison = db.get_comparison_for_session(session_id)
    owner = db.get_user_by_id(research_session['user_id'])

    if not report:
        flash('This research session has not completed yet.', 'warning')
        return redirect(url_for('admin_view_user', user_id=research_session['user_id']))

    return render_template('report.html', research_session=research_session,
                            report=report, summaries=summaries, comparison=comparison,
                            admin_view=True, owner=owner)


if __name__ == '__main__':
    db.init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
