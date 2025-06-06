from flask import Blueprint
from src.Shop.views import ShopViews
from src.Shop.orderviews import OrderViews


# Create the shop blueprint
shop_bp = Blueprint('shop', __name__, template_folder='templates')

# Initialize the view class
shop_views = ShopViews()
order_views = OrderViews()

# Define routes
@shop_bp.route('/')
def home():
    return shop_views.home()

@shop_bp.route('/products/create', methods=['GET', 'POST'])
def create_product():
    return shop_views.create_product()

@shop_bp.route('/products')
def list_products():
    return shop_views.list_products()

@shop_bp.route('/products/<string:product_id>')
def get_product(product_id):
    return shop_views.get_product(product_id)

@shop_bp.route('/products/<product_id>/update', methods=['POST', 'GET'])
def update_product(product_id):
    return shop_views.update_product(product_id)

@shop_bp.route('/products/<product_id>/delete', methods=['POST'])
def delete_product(product_id):
    return shop_views.delete_product(product_id)

@shop_bp.route('/product/create-order/<string:product_id>/<price>', methods=['GET', 'POST'])
def create_order(product_id, price):
    print(product_id)
    print(price)
    return order_views.create_order(product_id, price)

@shop_bp.route('/orders')
def list_orders():
    return order_views.list_orders()

@shop_bp.route('/orders/<string:order_id>')
def get_order(order_id):
    return order_views.get_order(order_id)

@shop_bp.route('/orders/<string:order_id>/delete', methods=['POST'])
def delete_order(order_id):
    return order_views.delete_order(order_id)
    