from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from src import db

class Products(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String)
    price = db.Column(db.Integer)
    description = db.Column(db.String)
    image_url = db.Column(db.String)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

    def __repr__(self):
        return f"<Product {self.name}>"
    
class Orders(db.Model):
    id = db.Column(db.String, primary_key=True)
    product_id = db.Column(db.String, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer)
    total_price = db.Column(db.Integer)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

    product = db.relationship('Products', backref=db.backref('order_item', uselist=False))
    def __repr__(self):
        return f"<Order {self.product_id}-{self.quantity}-{self.total_price}>"
    
class Inventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False, unique=True)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    low_stock_threshold = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    updated_at = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())

    product = db.relationship('Products', backref=db.backref('inventory_item', uselist=False))
    def __repr__(self):
        return f"<Inventory product_id={self.product_id} quantity={self.quantity}>"
