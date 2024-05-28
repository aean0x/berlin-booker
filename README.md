# Berlin.de Appointment Booker
Reserve Bürgeramt appointments on berlin.de using pyppeteer. No dependency on API calls- uses a browser frame from your install of Chrome so it's resistant to bot detection.

It will monitor for an appointment availability until it finds one that fits the parameters, and notify you once it's waiting for you to finish the booking.

Install Python 3.8 or greater, and then edit parameters in booker.py, then run commands:
```
pip install pyppeteer
python booker.py
```

Limitations:
- Web frame must not be minimised- must be visible on-screen. Otherwise it will stall out.
- It will not finish the booking process, only get you to the point where it's no longer time-critical.