# AIXN P2P Exchange - Frontend

A complete, production-ready web frontend for the AIXN peer-to-peer cryptocurrency exchange.

## Features

### Authentication
- User registration with validation
- Secure login/logout
- Session persistence using localStorage
- JWT token-based authentication

### Trading Interface
- **Buy/Sell AIXN**: Place market orders with real-time price calculation
- **Order Book**: Live order book display with bids and asks
- **Price Ticker**: Real-time price updates with 24h change, high, and low
- **Wallet Balance**: Display user's AIXN and USD balances
- **Recent Trades**: Live feed of recent trades with timestamps

### Real-time Updates
- WebSocket connection for live data
- Automatic reconnection with exponential backoff
- Live price ticker updates
- Order book updates
- Trade notifications

### UI/UX
- Modern, responsive design using Tailwind CSS
- Dark theme optimized for extended use
- Toast notifications for user actions
- Loading states and error handling
- Form validation

## File Structure

```
exchange/frontend/
├── index.html  - Main HTML file with complete UI structure
├── app.js      - JavaScript application logic and API integration
└── README.md   - This file
```

## Testing Instructions

### Prerequisites
1. Backend server must be running at `http://localhost:5000`
2. WebSocket server must be available at `ws://localhost:5000`

### Step 1: Open the Application
Simply open `index.html` in a modern web browser:
```bash
# Option 1: Direct file open
open exchange/frontend/index.html

# Option 2: Using Python HTTP server
cd exchange/frontend
python -m http.server 8080
# Then open http://localhost:8080 in your browser

# Option 3: Using Node.js http-server
cd exchange/frontend
npx http-server -p 8080
# Then open http://localhost:8080 in your browser
```

### Step 2: Register a New Account
1. Click on the "Register" tab
2. Enter a username (min 3 characters)
3. Enter a password (min 6 characters)
4. Confirm password
5. Click "Register"
6. Upon success, you'll be redirected to the login form

### Step 3: Login
1. Enter your username and password
2. Click "Login"
3. You'll be redirected to the trading dashboard

### Step 4: Check Your Balance
- Your wallet balances (AIXN and USD) are displayed at the top
- New accounts typically start with some test balance

### Step 5: Place a Buy Order
1. Click the "Buy" tab (should be selected by default)
2. Enter the price per AIXN in USD
3. Enter the amount of AIXN you want to buy
4. The total cost will be calculated automatically
5. Click "Buy AIXN"
6. Check for success message and balance update

### Step 6: Place a Sell Order
1. Click the "Sell" tab
2. Enter the price per AIXN in USD
3. Enter the amount of AIXN you want to sell
4. The total amount you'll receive is calculated automatically
5. Click "Sell AIXN"
6. Check for success message and balance update

### Step 7: Monitor Real-time Updates
- Watch the **Order Book** update as new orders are placed
- See **Recent Trades** appear when orders are matched
- Monitor **Price Ticker** for current price and 24h statistics
- Check **WebSocket Status** indicator at the bottom right (should be green when connected)

### Step 8: Test WebSocket Reconnection
1. Stop the backend server
2. Watch the WebSocket status turn red
3. Restart the backend server
4. The application should automatically reconnect within a few seconds

## API Endpoints Used

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user

### Trading
- `POST /api/orders/create` - Create buy/sell order
- `GET /api/orders/book` - Get current order book

### Wallet
- `GET /api/wallet/balance` - Get user balance

### Market Data
- `GET /api/trades/recent` - Get recent trades

## WebSocket Events

### Subscriptions
- `price` - Real-time price updates
- `orderbook` - Order book updates
- `trades` - New trade notifications

### Message Types
- `price_update` - Price ticker data
- `orderbook_update` - Updated order book
- `new_trade` - New trade executed
- `trade_executed` - Your order was matched

## Browser Compatibility

Tested and working on:
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Security Features

- JWT token authentication
- Secure token storage in localStorage
- Authorization headers on all protected endpoints
- Input validation and sanitization
- CORS handling
- XSS protection through proper escaping

## Troubleshooting

### "Network error. Please check if the server is running."
- Ensure the backend server is running at `http://localhost:5000`
- Check browser console for CORS errors
- Verify API endpoints are accessible

### WebSocket not connecting
- Ensure WebSocket server is running at `ws://localhost:5000`
- Check firewall settings
- Look for WebSocket errors in browser console

### Orders not appearing
- Refresh the page to reload order book
- Check that you have sufficient balance
- Verify backend is processing orders correctly

### Balance not updating
- The balance auto-refreshes every 10 seconds
- Manual refresh: logout and login again
- Check API response in browser network tab

## Development Notes

### Technology Stack
- **HTML5** - Semantic markup
- **Tailwind CSS** - Utility-first styling via CDN
- **Vanilla JavaScript** - No frameworks, pure ES6+
- **WebSocket API** - Real-time communication
- **Fetch API** - HTTP requests

### Code Organization
- `app.js` is organized into sections:
  - Configuration
  - Global State Management
  - Authentication Functions
  - Trading Functions
  - Data Loading Functions
  - WebSocket Functions
  - UI Helper Functions

### Best Practices
- Separation of concerns
- Error handling at all levels
- Loading states for better UX
- Automatic data refresh
- Responsive design principles
- Accessibility considerations

## Future Enhancements

Potential improvements:
- Advanced charting (TradingView integration)
- Order history page
- Cancel open orders functionality
- Trade history with filters
- Multiple trading pairs
- Dark/Light theme toggle
- Mobile app version
- Price alerts
- Portfolio tracking

## License

This frontend is part of the AIXN P2P Exchange project.

## Support

For issues or questions:
1. Check browser console for errors
2. Verify backend server is running
3. Check network tab for failed requests
4. Review this README for common solutions
