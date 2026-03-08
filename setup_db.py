import sqlite3

def init_db():
    conn = sqlite3.connect("ecommerce.db")
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        signup_date DATE NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        price REAL NOT NULL
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_id INTEGER,
        quantity INTEGER NOT NULL,
        order_date DATE NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (product_id) REFERENCES products(id)
    )
    ''')

    # Insert sample data
    cursor.execute("DELETE FROM users")
    cursor.execute("DELETE FROM products")
    cursor.execute("DELETE FROM orders")

    users = [
        ('Alice Smith', 'alice@example.com', '2023-01-15'),
        ('Bob Jones', 'bob@example.com', '2023-02-20'),
        ('Charlie Brown', 'charlie@example.com', '2023-03-10')
    ]
    cursor.executemany("INSERT INTO users (name, email, signup_date) VALUES (?, ?, ?)", users)

    products = [
        ('Laptop', 'Electronics', 999.99),
        ('Smartphone', 'Electronics', 599.99),
        ('Desk Chair', 'Furniture', 149.50),
        ('Coffee Mug', 'Home', 12.99)
    ]
    cursor.executemany("INSERT INTO products (name, category, price) VALUES (?, ?, ?)", products)

    orders = [
        (1, 1, 1, '2023-04-01'), # Alice bought Laptop
        (1, 4, 2, '2023-04-02'), # Alice bought 2 Coffee Mugs
        (2, 2, 1, '2023-04-05'), # Bob bought Smartphone
        (3, 3, 1, '2023-04-10')  # Charlie bought Desk Chair
    ]
    cursor.executemany("INSERT INTO orders (user_id, product_id, quantity, order_date) VALUES (?, ?, ?, ?)", orders)

    conn.commit()
    conn.close()
    print("Database 'ecommerce.db' initialized with sample data.")

if __name__ == "__main__":
    init_db()
