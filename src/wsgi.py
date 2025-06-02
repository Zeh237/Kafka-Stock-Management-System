from src import create_app
from src.config import ProductionConfig

application = create_app(ProductionConfig)

if __name__ == '__main__':
    application.run(debug=False) 