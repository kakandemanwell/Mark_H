from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import os

app = Flask(__name__)
# DB_URL = "postgresql://{os.getenv('DATABASE_USER')}:{os.getenv('DATABASE_PASSWORD')}@{os.getenv('DATABASE_HOST')}:{os.getenv('DATABASE_PORT')}/{os.getenv('DATABASE_NAME')}?sslmode=require"
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
    type = db.Column(db.String(10), nullable=False) # 'deposit'/'credit' or 'withdraw'/'debit'
    timestamp = db.Column(db.DateTime, default=datetime.now)

# Helper functions
def generate_customer_id(group):
    # while True:
    #     new_id = f"{group_prefix}{str(uuid.uuid4().int)[:5]}"
    #     if not Customer.query.filter_by(id=new_id).first():
    #         return new_id
    prefix = group.acronym if group else 'DM'
    last_customer = Customer.query.filter(Customer.id.like(f'{prefix}%'))

    if last_customer:
        # last_id = int(last_customer.order_by(Customer.id.desc()).first().id[len(prefix):])
        last_id = int(last_customer.id[len(prefix):])
        new_id = f"{prefix}{(last_id + 1):0{4 - len(prefix)}d}"
    else:
        new_id = f"{prefix}{'0' *  (4 - len(prefix))}1"

    return new_id
    
# index route
@app.route('/') 
def index():
    return 'Hello, World!'

# route to get all customers
@app.route('/customers', methods=['GET'])
def customers():
    customers = Customer.query.all()
    return customers

# route to get a customer
@app.route('/customer/<customer_id>', methods=['GET'])
def customer(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404
    return customer
        
# @app.route('/customer', methods=['POST'])
# def create_customer():
#     data = request.json
#     new_customer = Customer(
#         id = generate_customer_id(data['group']),
#         name=data['name'],
#         email=data['email'],
#         group=data['group']
#     )
#     db.session.add(new_customer)
#     db.session.commit()
#     return jsonify({"message": "Customer created successfully", "customer_id": new_customer.id}), 201

# route to create user
@app.route('/user', methods=['POST'])
def create_user():
    name = request.args.get('name')
    email = request.args.get('email')
    group = request.args.get('group', 'default')

    if not name or not email:
        return jsonify({"error": "Name and email are required"}), 400
    
    new_customer = Customer(
        id=generate_customer_id(group),
        name=name,
        email=email,
        group=group
    )
    db.session.add(new_customer)
    db.session.commit()
    return jsonify({"message": "Customer created", "customer_id": new_customer.id}), 201


# route to create group
@app.route('/group', methods=['GET', 'POST'])
def create_group():
    # data = request.json
    # name = data.get('name')
    # acronym = data.get('acronym')
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
        return jsonify({"error": "Name of a 2 or 3 letter acronym are required"}), 400
    
    existing_group = Group.query.filter_by(acronym=acronym.upper()).first()
    if existing_group:
        return jsonify({"error": "A group with this acronym already exists"}), 400

    new_group = Group(name=name, acronym=acronym)
    db.session.add(new_group)
    db.session.commit()

    return jsonify({"message": "Group created", "group_id": new_group.id, "acronym": new_group.acronym}), 201


# route to create default group
def create_default_group():
    default_group = Group.query.filter_by(acronym='DM').first()
    if not default_group:
        default_group = Group(name='Default', acronym='DM')
        db.session.add(default_group)
        db.session.commit()

# route to get a group
@app.route('/group/<group_id>', methods=['GET'])
def get_group(group_id):
    group = Group.query.get(group_id)
    if not group:
        return jsonify({"error": "Group not found"}), 404
    return group

# route to get all groups
@app.route('/groups', methods=['GET'])
def get_groups():
    groups = Group.query.all()
    return groups


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

@app.route('/balance/<customer_id>', methods=['GET'])
def get_balance(customer_id):
    customer = Customer.query.get(customer_id)
    if not customer:
        return jsonify({"error": "Customer not found"}), 404

    return jsonify({"customer_id": customer.id, "balance": customer.balance}), 200

def pay_interest():
    customers = Customer.query.all()
    for customer in customers:
        interest = customer.balance * 0.025 # 2.5% interest
        customer.balance += interest
        transaction = Transaction(customer_id=customer.id, amount=interest, type='interest')
        db.session.add(transaction)
    db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', debug=True)