"""
职工信息管理系统 - Flask Web版
功能：登录权限、增删改查、多条件检索、数据排序、考勤统计、数据持久化、报表导出
"""

from flask import Flask, render_template, request, redirect, url_for, Response
import json
import os
from collections import defaultdict
from datetime import datetime
import csv
from io import StringIO

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ============================================================
# 数据文件路径
# ============================================================
EMPLOYEE_FILE = 'employees.json'
USER_FILE = 'users.json'

# 当前登录用户
current_user = {'username': None, 'role': None}


# ============================================================
# 职工数据管理类
# ============================================================
class EmployeeManager:
    def __init__(self):
        self.employees = []
        self.load_data()

    def load_data(self):
        """加载数据"""
        if os.path.exists(EMPLOYEE_FILE):
            try:
                with open(EMPLOYEE_FILE, 'r', encoding='utf-8') as f:
                    self.employees = json.load(f)
            except:
                self.employees = []
        else:
            self.employees = []

    def save_data(self):
        """保存数据"""
        try:
            with open(EMPLOYEE_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.employees, f, ensure_ascii=False, indent=2)
            return True
        except:
            return False

    # ---------- 增删改查 ----------
    def add(self, emp):
        """添加职工"""
        for e in self.employees:
            if e.get('emp_id') == emp.get('emp_id'):
                return False, f"工号 {emp.get('emp_id')} 已存在"
        self.employees.insert(0, emp)
        self.save_data()
        return True, "添加成功"

    def delete(self, emp_id):
        """删除职工"""
        for i, e in enumerate(self.employees):
            if e.get('emp_id') == emp_id:
                del self.employees[i]
                self.save_data()
                return True, f"工号 {emp_id} 删除成功"
        return False, f"未找到工号 {emp_id}"

    def update(self, emp_id, data):
        """修改职工"""
        for e in self.employees:
            if e.get('emp_id') == emp_id:
                e.update(data)
                self.save_data()
                return True, "修改成功"
        return False, f"未找到工号 {emp_id}"

    # ---------- 多条件查询 ----------
    def find_by_id(self, emp_id):
        """按工号精确查询"""
        for e in self.employees:
            if e.get('emp_id') == emp_id:
                return e
        return None

    def find_by_name(self, name):
        """按姓名模糊查询"""
        return [e for e in self.employees if name in e.get('name', '')]

    def find_by_department(self, department):
        """按部门查询"""
        return [e for e in self.employees if e.get('department') == department]

    def get_all(self):
        """获取全部"""
        return self.employees

    # ---------- 数据排序 ----------
    def sort_by_date(self, reverse=False):
        """按出勤日期排序"""
        return sorted(self.employees, key=lambda e: e.get('attendance_date', ''), reverse=reverse)

    def sort_by_days(self, reverse=False):
        """按出勤天数排序"""
        return sorted(self.employees, key=lambda e: int(e.get('days_present', 0)), reverse=reverse)

    # ---------- 考勤统计 ----------
    def get_statistics(self):
        """获取统计信息"""
        if not self.employees:
            return {'total': 0, 'dept_stats': {}, 'avg_days': 0, 'max_days': 0, 'min_days': 0, 'max_emp': None, 'min_emp': None}

        total = len(self.employees)
        dept_stats = defaultdict(int)
        days_list = []

        for e in self.employees:
            dept_stats[e.get('department', '未知')] += 1
            days_list.append(e.get('days_present', 0))

        max_days = max(days_list) if days_list else 0
        min_days = min(days_list) if days_list else 0

        # 找到极值人员
        max_emp = next((e for e in self.employees if e.get('days_present', 0) == max_days), None)
        min_emp = next((e for e in self.employees if e.get('days_present', 0) == min_days), None)

        return {
            'total': total,
            'dept_stats': dict(dept_stats),
            'avg_days': round(sum(days_list) / total, 1) if total > 0 else 0,
            'max_days': max_days,
            'min_days': min_days,
            'max_emp': max_emp,
            'min_emp': min_emp
        }

    def monthly_stats(self, year_month):
        """按月统计出勤"""
        total_days = 0
        count = 0
        for e in self.employees:
            date = e.get('attendance_date', '')
            if date.startswith(year_month):
                total_days += e.get('days_present', 0)
                count += 1
        return {
            'total_days': total_days,
            'count': count,
            'avg_days': round(total_days / count, 1) if count > 0 else 0
        }

    # ---------- 报表导出 ----------
    def export_csv(self, employees=None):
        """导出CSV"""
        if employees is None:
            employees = self.employees
        if not employees:
            return None

        si = StringIO()
        writer = csv.writer(si)
        writer.writerow(['工号', '姓名', '部门', '出勤日期', '当月出勤天数'])
        for e in employees:
            writer.writerow([
                e.get('emp_id', ''),
                e.get('name', ''),
                e.get('department', ''),
                e.get('attendance_date', ''),
                e.get('days_present', 0)
            ])
        return si.getvalue()


# ============================================================
# 用户认证类
# ============================================================
class AuthSystem:
    def __init__(self):
        self.users = {}
        self.load_users()

    def load_users(self):
        if os.path.exists(USER_FILE):
            try:
                with open(USER_FILE, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
            except:
                self.init_default()
        else:
            self.init_default()
            self.save_users()

    def init_default(self):
        self.users = {
            'admin': {'password': 'admin123', 'role': 'admin'},
            'user': {'password': 'user123', 'role': 'employee'}
        }

    def save_users(self):
        try:
            with open(USER_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, ensure_ascii=False, indent=2)
        except:
            pass

    def login(self, username, password):
        if username in self.users and self.users[username]['password'] == password:
            return self.users[username]['role']
        return None


# ============================================================
# 初始化
# ============================================================
manager = EmployeeManager()
auth = AuthSystem()


# ============================================================
# Flask路由
# ============================================================

# ---------- 登录 ----------
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')
    role = auth.login(username, password)
    if role:
        current_user['username'] = username
        current_user['role'] = role
        return redirect(url_for('home'))
    return render_template('index.html', error='账号或密码错误')


@app.route('/home')
def home():
    if not current_user['username']:
        return redirect(url_for('index'))
    employees = manager.get_all()
    is_admin = current_user['role'] == 'admin'
    template = 'admin.html' if is_admin else 'employee.html'
    return render_template(template,
                          employees=employees,
                          username=current_user['username'],
                          is_admin=is_admin)


# ---------- 添加 ----------
@app.route('/add')
def add_page():
    if current_user['role'] != 'admin':
        return redirect(url_for('home'))
    return render_template('add.html')


@app.route('/add2', methods=['POST'])
def add_employee():
    if current_user['role'] != 'admin':
        return redirect(url_for('home'))

    emp_id = request.form.get('emp_id')
    name = request.form.get('name')
    department = request.form.get('department')
    attendance_date = request.form.get('attendance_date')

    try:
        days_present = int(request.form.get('days_present', 0))
        if days_present < 0 or days_present > 31:
            return render_template('add.html', error='出勤天数必须在0-31之间')
    except:
        return render_template('add.html', error='出勤天数请输入数字')

    emp = {
        'emp_id': emp_id,
        'name': name,
        'department': department,
        'attendance_date': attendance_date,
        'days_present': days_present
    }

    success, msg = manager.add(emp)
    if success:
        return redirect(url_for('home'))
    return render_template('add.html', error=msg)


# ---------- 删除 ----------
@app.route('/delete/<emp_id>')
def delete_employee(emp_id):
    if current_user['role'] != 'admin':
        return redirect(url_for('home'))
    manager.delete(emp_id)
    return redirect(url_for('home'))


# ---------- 修改 ----------
@app.route('/change/<emp_id>')
def change_page(emp_id):
    if current_user['role'] != 'admin':
        return redirect(url_for('home'))
    emp = manager.find_by_id(emp_id)
    if emp:
        return render_template('change.html', user=emp)
    return redirect(url_for('home'))


@app.route('/changed/<emp_id>', methods=['POST'])
def change_employee(emp_id):
    if current_user['role'] != 'admin':
        return redirect(url_for('home'))

    data = {
        'name': request.form.get('name'),
        'department': request.form.get('department'),
        'attendance_date': request.form.get('attendance_date'),
        'days_present': int(request.form.get('days_present', 0))
    }
    manager.update(emp_id, data)
    return redirect(url_for('home'))


# ---------- 多条件检索 ----------
@app.route('/search', methods=['POST'])
def search():
    if not current_user['username']:
        return redirect(url_for('index'))

    keyword = request.form.get('keyword', '').strip()
    search_type = request.form.get('search_type')

    if not keyword:
        employees = manager.get_all()
    elif search_type == 'id':
        result = manager.find_by_id(keyword)
        employees = [result] if result else []
    elif search_type == 'name':
        employees = manager.find_by_name(keyword)
    elif search_type == 'department':
        employees = manager.find_by_department(keyword)
    else:
        employees = manager.get_all()

    template = 'admin.html' if current_user['role'] == 'admin' else 'employee.html'
    return render_template(template,
                          employees=employees,
                          username=current_user['username'],
                          is_admin=current_user['role'] == 'admin',
                          keyword=keyword)


# ---------- 数据排序 ----------
@app.route('/sort/<field>/<order>')
def sort_employees(field, order):
    if not current_user['username']:
        return redirect(url_for('index'))

    reverse = order == 'desc'
    if field == 'date':
        employees = manager.sort_by_date(reverse=reverse)
    elif field == 'days':
        employees = manager.sort_by_days(reverse=reverse)
    else:
        employees = manager.get_all()

    template = 'admin.html' if current_user['role'] == 'admin' else 'employee.html'
    return render_template(template,
                          employees=employees,
                          username=current_user['username'],
                          is_admin=current_user['role'] == 'admin',
                          sort_field=field,
                          sort_order=order)


# ---------- 考勤统计 ----------
@app.route('/statistics')
def statistics():
    if not current_user['username']:
        return redirect(url_for('index'))

    stats = manager.get_statistics()

    # 月度统计
    month_stats = None
    month = request.args.get('month')
    if month:
        month_stats = manager.monthly_stats(month)

    return render_template('statistics.html',
                          stats=stats,
                          month_stats=month_stats,
                          username=current_user['username'],
                          is_admin=current_user['role'] == 'admin')


# ---------- 报表导出 ----------
@app.route('/export')
def export():
    if not current_user['username']:
        return redirect(url_for('index'))

    # 检查是否有筛选条件
    keyword = request.args.get('keyword', '').strip()
    search_type = request.args.get('search_type')

    if keyword and search_type:
        if search_type == 'id':
            result = manager.find_by_id(keyword)
            employees = [result] if result else []
        elif search_type == 'name':
            employees = manager.find_by_name(keyword)
        elif search_type == 'department':
            employees = manager.find_by_department(keyword)
        else:
            employees = manager.get_all()
    else:
        employees = manager.get_all()

    csv_data = manager.export_csv(employees)
    if csv_data is None:
        return redirect(url_for('home'))

    response = Response(csv_data, mimetype='text/csv')
    filename = f'职工数据_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    response.headers['Content-Disposition'] = f'attachment; filename={filename}'
    return response


# ---------- 退出 ----------
@app.route('/logout')
def logout():
    current_user['username'] = None
    current_user['role'] = None
    return redirect(url_for('index'))


# ============================================================
# 启动
# ============================================================
if __name__ == '__main__':
    app.run(debug=True, port=5000)