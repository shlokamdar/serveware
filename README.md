# ServeWare

ServeWare is a comprehensive restaurant management system built using Django. It simplifies restaurant operations, enhances customer experiences, and streamlines tasks. The platform includes features for managing customers, orders, and restaurant tables, all through an intuitive interface. 🍴


## Features

### 1. **Accounts Management** 🔒
   - Role-based authentication for Restaurant Admin and Customer.
   - OTP verification via email for sign-up and password reset. 📧

### 2. **Customer App** 🛒
   - QR code-based menu access for specific tables. 📱
   - Add items to the cart, update quantities, and place orders. ✅
   - View order details 🍽️

### 3. **Restaurant App** 🏢
   - Manage menus with CRUD operations for menu items. 📋
   - Dashboard to monitor orders, table statuses, and order progress. 📊
   - Add and view restaurant tables and track their availability. 🪑

## User Flows

### Customer Flow 👤
1. Scan a table-specific QR code to view the menu.
2. Add items to the cart and place orders.
3. View order details and request additional items.

### Restaurant Admin Flow 👨‍💼
1. Set up the restaurant profile and details.
2. Add and manage menus and tables.
3. Monitor orders and table statuses on the dashboard.

## Tech Stack 🛠️
- **Frontend**: HTML, CSS, Bootstrap 🎨
- **Backend**: Django Framework 🐍
- **Database**: SQLite (can be replaced with PostgreSQL or MySQL) 💾
- **Other Tools**: QR Code generation, Email OTP authentication 📲

## Installation 🚀

1. Clone the repository:
   ```bash
   git clone https://github.com/shlokamdar/serveware.git
   ```

2. Navigate to the project directory:
   ```bash
   cd serveware
   ```

3. Create a virtual environment:
   ```bash
   python -m venv env
   source env/bin/activate # On Windows, use `env\Scripts\activate`
   ```

4. Apply migrations:
   ```bash
   python manage.py migrate
   ```

5. Run the server:
   ```bash
   python manage.py runserver
   ```

6. Access the application at [http://127.0.0.1:8000](http://127.0.0.1:8000).

## Future Enhancements ✨
- Real-time order tracking using Django Channels.
- Integration with payment gateways. 💳
- Analytics dashboard for restaurant performance. 📈




