import asyncio
from pyppeteer import launch
from datetime import datetime
import winsound

cutoff_date = "31.05.2024" # Latest date to book an appointment in the format "dd.mm.yyyy"
url = "https://service.berlin.de/terminvereinbarung/termin/all/327537/" # URL of the appointment booking page
path = "C:/Program Files/Google/Chrome/Application/chrome.exe" # path to your Chrome or Chromium executable

async def navigate_and_check(page, url):
    await page.goto(url)
    await page.waitForSelector('body', {'timeout': 60000})

async def page_type(page):
    # Check if the page is showing the button, calendar, or timeslot
    is_calendar_page = await page.evaluate('''() => {
        return document.querySelector('.calendar-month-table') !== null;
    }''')

    is_no_appointments_page = await page.evaluate('''() => {
        return document.querySelector('.herounit-article h1') !== null && 
               document.querySelector('.herounit-article h1').innerText.includes('Leider sind aktuell keine Termine für ihre Auswahl verfügbar.');
    }''')

    is_timeslot_page = await page.evaluate('''() => {
        return document.querySelector('.timetable') !== null;
    }''')

    is_form_page = await page.evaluate('''() => {
        return document.querySelector('#registerform') !== null;
    }''')

    is_error_page = await page.evaluate('''() => {
        return document.querySelector('.alert.alert-error p') !== null && 
            document.querySelector('.alert.alert-error p').innerText.includes('Leider konnte der ausgewählte Termin nicht reserviert werden.');
    }''')

    if is_calendar_page:
        return "calendar"
    elif is_no_appointments_page:
        return "no-appointments"
    elif is_timeslot_page:
        return "timeslot"
    elif is_form_page:
        return "form"
    elif is_error_page:
        return "error"
    else:
        return None

async def book_appointment(cutoff_date, url, path):
    # Convert cutoff_date to datetime object
    latest_date = datetime.strptime(cutoff_date, "%d.%m.%Y").date()
    timeout_seconds = 61

    browser = await launch(headless=False, executablePath=path)  # Specify the path to your Chromium or Chrome executable
    page = await browser.newPage()

    while True:
        try:
            # Step 1: Navigate to the initial page
            print("Navigating to the initial page...")
            await navigate_and_check(page, url)

            # Step 2: Check if the page is showing the calendar or the button directly
            current_page_type = await page_type(page)
            print(f"Current page type after navigating: {current_page_type}")

            if current_page_type == None:
                print(f"Wrong page detected. Starting over in {timeout_seconds}...")
                await asyncio.sleep(timeout_seconds)
                continue

            if current_page_type != "calendar":
                button_selector = 'button.btn'
                try:
                    button_disabled = await page.evaluate(f'document.querySelector("{button_selector}").disabled')
                    if button_disabled:
                        await asyncio.sleep(timeout_seconds)
                    
                    print("Button enabled. Clicking the button...")
                    await page.click(button_selector)
                    await page.waitForSelector('.calendar-month-table', {'timeout': 2000})  # Ensure calendar is loaded
                    current_page_type = await page_type(page)
                    break
                except Exception as e:
                    print(f"Calendar not found. Starting over in {timeout_seconds}...")
                    await asyncio.sleep(timeout_seconds)
                    await page.reload()
                    continue

            if current_page_type == "calendar":
                await page.waitForSelector('.calendar-month-table', {'timeout': 2000})  # Ensure calendar is loaded
                current_page_type = await page_type(page)
                print(f"Current page type after waiting for calendar: {current_page_type}")

                if current_page_type != "calendar":
                    print(f"Wrong page detected after waiting for calendar. Starting over in {timeout_seconds}...")
                    await asyncio.sleep(timeout_seconds)
                    continue

                available_date_url = await page.evaluate(r'''(cutoff_date) => {
                    const availableDates = document.querySelectorAll('.calendar-table .buchbar a');
                    if (availableDates.length > 0) {
                        for (let dateLink of availableDates) {
                            const dateText = dateLink.title.match(/(\d{2}\.\d{2}\.\d{4})/)[0];  // Extract date from title
                            const dateParts = dateText.split('.');
                            const date = new Date(`${dateParts[2]}-${dateParts[1]}-${dateParts[0]}`);
                            const latest_date = new Date(cutoff_date.split('.').reverse().join('-'));

                            if (date <= latest_date) {
                                return dateLink.href;
                            }
                        }
                    }
                    return null;
                }''', cutoff_date)

                if available_date_url:
                    print(f"Found available date URL: {available_date_url}")
                    await navigate_and_check(page, available_date_url)

                    # Step 4: Wait for the timetable to load and select the first available slot
                    print("Waiting for the timetable to load...")
                    await page.waitForSelector('.timetable', {'timeout': 2000})  # Ensure timetable is loaded

                    current_page_type = await page_type(page)
                    print(f"Current page type after waiting for timetable: {current_page_type}")

                    if current_page_type != "timeslot":
                        print(f"Wrong page detected after waiting for timetable. Starting over in {timeout_seconds}...")
                        await asyncio.sleep(timeout_seconds)
                        continue

                    # Find and click the first available slot
                    first_slot_href = await page.evaluate('''() => {
                        const firstSlot = document.querySelector('.timetable .frei a');
                        return firstSlot ? firstSlot.href : null;
                    }''')

                    if first_slot_href:
                        print(f"Found first slot URL: {first_slot_href}")
                        await navigate_and_check(page, first_slot_href)

                        current_page_type = await page_type(page)
                        print(f"Current page type after selecting timeslot: {current_page_type}")

                        if current_page_type == None:
                            print(f"Unexpected page type after selecting timeslot. Starting over in {timeout_seconds}...")
                            await asyncio.sleep(timeout_seconds)
                            continue
                        
                        if current_page_type != "form":
                            print("Somebody else was faster. Starting over...")
                            try:
                                await page.click('a[href="/terminvereinbarung/termin/day/"]')
                                continue
                            except:
                                await asyncio.sleep(timeout_seconds)
                                continue

                        # Play notification sound
                        print("Appointment booked successfully! Playing notification sound.")
                        winsound.MessageBeep(winsound.MB_ICONHAND)

                        exit(0)
                    else:
                        print(f"No appointment slots available at the moment. Retrying in {timeout_seconds} seconds...")
                        await asyncio.sleep(timeout_seconds)  # Wait before retrying
                else:
                    print(f"No dates available within the specified range. Retrying in {timeout_seconds} seconds...")
                    await asyncio.sleep(timeout_seconds)  # Wait before retrying
        except Exception as e:
            print(f"An error occurred: {e}. Retrying in {timeout_seconds} seconds...")
            await asyncio.sleep(timeout_seconds)  # Wait before retrying

# This part ensures compatibility with different Python versions and environments
if __name__ == '__main__':
    try:
        asyncio.run(book_appointment(cutoff_date, url, path))
    except AttributeError:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(book_appointment(cutoff_date, url, path))
