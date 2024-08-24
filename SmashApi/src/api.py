from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import os

app = Flask(__name__)
DB_URL = f"postgresql://{os.getenv('DATABASE_USER')}:{os.getenv('DATABASE_PASSWORD')}@{os.getenv('DATABASE_HOST')}:{os.getenv('DATABASE_PORT')}/{os.getenv('DATABASE_NAME')}?sslmode=require"
app.config['SQLALCHEMY_DATABASE_URI'] = "postgresql://postgres:PoZtqe1@localhost:5432/markdb"
db = SQLAlchemy(app)

# Models
class Customer(db.Model):
    id = db.Column(db.String(10), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    group = db.Column(db.String(50))
    balance = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.now)

class Group(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    acronym = db.Column(db.String(3), unique=True, nullable=False)

    def __init__(self, name, acronym):
        self.name = name
        self.acronym = acronym.upper()[:3]

class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.String(10), db.ForeignKey('customer.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'deposit'/'credit' or 'withdraw'/'debit'
    timestamp = db.Column(db.DateTime, default=datetime.now)

# Helper functions
def generate_customer_id(group):
    prefix = group.acronym if group else 'DM'
    last_customer = Customer.query.filter(Customer.id.like(f'{prefix}%')).order_by(Customer.id.desc()).first()

    if last_customer:
        last_id = int(last_customer.id[len(prefix):])
        new_id = f"{prefix}{(last_id + 1):0{4 - len(prefix)}d}"
    else:
        new_id = f"{prefix}{'0' * (4 - len(prefix))}1"

    return new_id

# Index route
@app.route('/')
def index():
    return 'Hello, World!'

# Route to get all customers
@app.route('/customers', methods=['GET'])
def get_customers():
    customers = Customer.query.all()
    return jsonify([{"id": c.id, "name": c.name, "email": c.email, "group": c.group, "balance": c.balance} for c in customers])

# Route to get a customer
@app.route('/customer/<customer_id>', methods=['GET'])
def get_customer(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    return jsonify({"id": customer.id, "name": customer.name, "email": customer.email, "group": customer.group, "balance": customer.balance})

# Route to create customer
@app.route('/customer', methods=['POST'])
def create_customer():
    data = request.json
    group = Group.query.filter_by(acronym=data.get('group', 'DM')).first()
    new_customer = Customer(
        id=generate_customer_id(group),
        name=data['name'],
        email=data['email'],
        group=group.acronym if group else 'DM'
    )
    db.session.add(new_customer)
    db.session.commit()
    return jsonify({"message": "Customer created successfully", "customer_id": new_customer.id}), 201

# Route to create group
@app.route('/group', methods=['GET', 'POST'])
def create_group():
    if request.method == 'POST':
        if request.is_json:
            data = request.json
            name = data.get('name')
            acronym = data.get('acronym')
        else:
            return jsonify({"error": "Request must be JSON"}), 415
    else:
        name = request.args.get('name')
        acronym = request.args.get('acronym')

    if not name or not acronym or len(acronym) < 2 or len(acronym) > 3:
        return jsonify({"error": "Name and a 2 or 3 letter acronym are required"}), 400

    existing_group = Group.query.filter_by(acronym=acronym.upper()).first()
    if existing_group:
        return jsonify({"error": "A group with this acronym already exists"}), 400

    new_group = Group(name=name, acronym=acronym)
    db.session.add(new_group)
    db.session.commit()

    return jsonify({"message": "Group created", "group_id": new_group.id, "acronym": new_group.acronym}), 201

# Route to get a group
@app.route('/group/<group_id>', methods=['GET'])
def get_group(group_id):
    group = Group.query.get(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404
    return jsonify({"id": group.id, "name": group.name, "acronym": group.acronym})

# Route to get all groups
@app.route('/groups', methods=['GET'])
def get_groups():
    groups = Group.query.all()
    return jsonify([{"id": g.id, "name": g.name, "acronym": g.acronym} for g in groups])

# Route to deposit
@app.route('/deposit', methods=['POST'])
def deposit():
    data = request.json
    customer = Customer.query.get(data["customer_id"])
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    amount = data['amount']
    customer.balance += amount

    transaction = Transaction(customer_id=customer.id, amount=amount, type='deposit')
    db.session.add(transaction)
    db.session.commit()

    return jsonify({"message": "Deposit successful", "new_balance": customer.balance}), 200

# Route to withdraw
@app.route('/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    customer = Customer.query.get(data['customer_id'])
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    amount = data['amount']
    if customer.balance < amount:
        return jsonify({"error": "Insufficient balance"}), 400

    customer.balance -= amount

    transaction = Transaction(customer_id=customer.id, amount=amount, type='withdraw')
    db.session.add(transaction)
    db.session.commit()

    return jsonify({"message": "Withdrawal successful", "new_balance": customer.balance}), 200

# Route to get balance
@app.route('/balance/<customer_id>', methods=['GET'])
def get_balance(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    return jsonify({"customer_id": customer.id, "balance": customer.balance}), 200

def pay_interest():
    customers = Customer.query.all()
    for customer in customers:
        interest = customer.balance * 0.025  # 2.5% interest
        customer.balance += interest
        transaction = Transaction(customer_id=customer.id, amount=interest, type='interest')
        db.session.add(transaction)
    db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True)
