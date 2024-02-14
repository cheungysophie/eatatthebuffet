from config import secrets

tickers = ['AAPL', 'NVDA', 'ENPH', 'ALB', 'AMD', 'META', 'SEDG', 'CCJ', 'FCX', 'VEOEY']

users = [
    {
        "email": secrets.admin_email,
        "name": "sophie",
        "watchlist": {
            "AAPL": {
                "triggers": {
                    "daily_below_last_month": True,
                    "daily_below_ninety": True,
                    "daily_below_365": True,
                    "rsi": {"lte": 30} # notify if RSI is <= 30
                }
            },
            "NVDA": {
                "triggers": {
                    "daily_below_last_month": True,
                    "daily_below_ninety": True,
                    "daily_below_365": True,
                    "rsi": {"lte": 30, "gte": 70}, # lte = less than or equal to, gte = greater than or equal to,
                    "stock_price": {"lte": 150}
                }
            },
            "ALB": {
                "triggers": {
                    "daily_report": False,
                    "daily_below_last_month": True,
                    "daily_below_ninety": True,
                    "daily_below_365": True,
                }
            },
            "AMD": {
                "triggers": {
                    "daily_below_last_month": True,
                    "daily_below_ninety": True,
                    "daily_below_365": True,
                    "stock_price": {"lte": 80},
                }
            },
            "ENPH": {
                "triggers": {
                    "stock_price": {"lte": 101},
                    "daily_below_last_month": False,
                    "rsi": {"lte": 30} # notify if RSI is <= 30
                }
            },
            "META": {
                "triggers": {
                    "stock_price": {"lte": 150},
                    "daily_below_last_month": True,
                    "daily_below_ninety": True,
                    "daily_below_365": True,
                    "rsi": {"lte": 30} # notify if RSI is <= 30
                }
            },
            "SEDG": {
                "triggers": {
                    "stock_price": {"lte": 100},
                    "daily_below_last_month": True,
                    "daily_below_ninety": True,
                    "daily_below_365": True,
                    "rsi": {"lte": 30} # notify if RSI is <= 30
                }
            },
            "CCJ": {
                "triggers": {
                    "stock_price": {"lte": 30},
                    "daily_below_last_month": True,
                    "daily_below_ninety": True,
                    "daily_below_365": True,
                    "rsi": {"lte": 30} # notify if RSI is <= 30
                }
            },
            "FCX": {
                "triggers": {
                    "stock_price": {"lte": 25},
                    "daily_below_last_month": True,
                    "daily_below_ninety": True,
                    "daily_below_365": True,
                    "rsi": {"lte": 30} # notify if RSI is <= 30
                }
            },
        }
    },
    {
        "email": "so@sophie.vision",
        "name": "so",
        "watchlist": {
            "NVDA": {
                "triggers": {
                    "daily_below_last_month": True,
                    "rsi": {"lte": 30}
                }
            }
        }
    }
]
