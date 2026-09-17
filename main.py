from playwright.sync_api import sync_playwright
from urllib.parse import quote
import os, re, json, traceback, pandas as pd
from collections import defaultdict
from datetime import datetime


# =====================================================
# TEXT PARSERS
# =====================================================

def extract_title(page):

    try:

        title = page.title()

        title = title.replace(
            " - Airbnb",
            ""
        )

        return title.strip()

    except:

        return ""
    
def extract_rating_reviews(text):

    rating = ""
    reviews = ""

    try:

        rating_match = re.search(
            r"Rated\s+([0-9.]+)\s+out\s+of\s+5",
            text
        )

        if rating_match:

            rating = rating_match.group(1)

        reviews_match = re.search(
            r"([0-9]+)\s+reviews",
            text
        )

        if reviews_match:

            reviews = reviews_match.group(1)

    except:
        pass

    return rating, reviews

def extract_room_info(text):


    match = re.search(
        r"(\d+\s+guests.*?\d+\s+bath)",
        text,
        re.IGNORECASE
    )

    if match:

        return match.group(1)

    return ""



def extract_price(text):

    patterns = [

        r"\$[0-9,]+\s+for\s+\d+\s+nights",

        r"\$[0-9,]+\s+total",

        r"\$[0-9,]+"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:

            return match.group(0)

    return ""

def calculate_price_per_night(price_text):

    try:

        # Case 1:
        # "$221 for 3 nights"

        match = re.search(
            r"\$([0-9,]+)\s+for\s+(\d+)\s+nights",
            price_text
        )

        if match:

            total_price = float(
                match.group(1).replace(",", "")
            )

            nights = int(
                match.group(2)
            )

            return round(
                total_price / nights,
                2
            )

        # Case 2:
        # "$128"

        single_price = re.search(
            r"\$([0-9,]+)",
            price_text
        )

        if single_price:

            return float(
                single_price.group(1)
                .replace(",", "")
            )

    except Exception:
        pass

    return ""


def extract_amenities(text):

    try:

        start = text.find(
            "What this place offers"
        )

        if start == -1:
            return ""

        section = text[start:]

        end_markers = [
            "Select check-in date",
            "Add your travel dates",
            "Show all",
            "Check availability"
        ]

        end = len(section)

        for marker in end_markers:

            pos = section.find(marker)

            if pos > 0:

                end = min(end, pos)

        section = section[:end]

        lines = [
            x.strip()
            for x in section.splitlines()
            if x.strip()
        ]

        amenities = []

        skip = {
            "What this place offers"
        }

        for line in lines:

            if line in skip:
                continue

            if len(line) < 3:
                continue

            amenities.append(line)

        return ", ".join(
            amenities[:15]
        )

    except:

        return ""

def extract_location_from_title(page):

    try:

        title = page.title()

        patterns = [

            r"for\s+Rent\s+in\s+(.+?)(?:\s*-\s*Airbnb|$)",

            r"\bin\s+(.+?)(?:\s*-\s*Airbnb|$)"
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                title,
                re.IGNORECASE
            )

            if match:

                location = match.group(1).strip()

                if "|" not in location:

                    return location

    except Exception:
        pass

    return ""

def split_location(location):

    try:

        parts = [
            x.strip()
            for x in location.split(",")
        ]

        city = parts[0] if len(parts) > 0 else ""

        country = parts[-1] if len(parts) > 1 else ""

        return city, country

    except:

        return "", ""
    

def extract_highlights(text):

    try:

        start = text.find(
            "Listing highlights"
        )

        if start == -1:
            return ""

        section = text[start:start+1000]

        lines = [
            x.strip()
            for x in section.splitlines()
            if x.strip()
        ]

        highlights = []

        for line in lines:

            if line == "Listing highlights":
                continue

            if len(line) > 5:
                highlights.append(line)

            if len(highlights) >= 6:
                break

        return ", ".join(highlights)

    except:
        return ""
    

def extract_description(text):

    try:

        start = text.find(
            "The space"
        )

        if start == -1:
            return ""

        section = text[start:]

        stop_markers = [

            "Guest access",
            "Other things to note",
            "Where you'll sleep",
            "Where you’ll sleep",
            "What this place offers",
            "Show all amenities",
            "Show all reviews",
            "Where you'll be",
            "Where you’ll be",
            "Meet your host",
            "Things to know",
            "House rules",
            "Cancellation policy"
        ]

        end = len(section)

        for marker in stop_markers:

            pos = section.find(marker)

            if pos > 0:

                end = min(
                    end,
                    pos
                )

        description = section[:end].strip()

        description = description.replace(
            "The space",
            ""
        ).strip()

        return description

    except Exception:

        return ""
    


def extract_description_fallback(text):

    try:

        markers = [

            "About this place",
            "Description",
            "Summary"
        ]

        for marker in markers:

            start = text.find(marker)

            if start != -1:

                return text[
                    start:
                    start + 2000
                ]

    except:
        pass

    return ""


def extract_location_description(text):

    try:

        start = text.find(
            "Where you'll be"
        )

        if start == -1:
            return ""

        section = text[start:start+500]

        return section

    except:
        return ""
    
def extract_coordinates(html):

    try:

        lat_match = re.search(
            r'"lat"\s*:\s*([-0-9.]+)',
            html
        )

        lng_match = re.search(
            r'"lng"\s*:\s*([-0-9.]+)',
            html
        )

        lat = (
            lat_match.group(1)
            if lat_match
            else ""
        )

        lng = (
            lng_match.group(1)
            if lng_match
            else ""
        )

        return lat, lng

    except:

        return "", ""
    
def extract_calendar_range(page):

    try:

        locator = page.locator(
            "[data-testid='availability-calendar-date-range']"
        )

        if locator.count() > 0:

            text = locator.first.inner_text().strip()

            return text

    except Exception as e:

        print(
            f"Calendar Range Error: {e}"
        )

    return ""

def extract_availability(page):

    available_dates = []
    unavailable_dates = []

    try:

        days = page.locator(
            "[data-testid^='calendar-day-']"
        )

        count = days.count()

        print(
            f"[CALENDAR] Found {count} day cells"
        )

        for i in range(count):

            try:

                day = days.nth(i)

                date_value = day.get_attribute(
                    "data-testid"
                )

                blocked = day.get_attribute(
                    "data-is-day-blocked"
                )

                if not date_value:
                    continue

                date_value = (
                    date_value
                    .replace(
                        "calendar-day-",
                        ""
                    )
                )

                if blocked == "true":

                    unavailable_dates.append(
                        date_value
                    )

                else:

                    available_dates.append(
                        date_value
                    )

            except Exception:
                pass

    except Exception as e:

        print(
            f"[CALENDAR ERROR] {e}"
        )

    print(
        f"[CALENDAR DEBUG] Available={len(available_dates)}"
    )

    print(
        f"[CALENDAR DEBUG] Unavailable={len(unavailable_dates)}"
    )

    return (
        available_dates,
        unavailable_dates
    )    

def format_dates_by_month(date_list):

    grouped = defaultdict(list)

    for date_str in date_list:

        try:

            dt = datetime.strptime(
                date_str,
                "%m/%d/%Y"
            )

            month_key = dt.strftime(
                "%b-%Y"
            )

            grouped[month_key].append(
                str(dt.day)
            )

        except:
            pass

    output = []

    for month, days in grouped.items():

        output.append(
            f"{month}: {','.join(days)}"
        )

    return "\n".join(output)


def extract_amenity_categories(page):

    categories = {}

    try:

        # Click Show all amenities button

        show_btn = page.get_by_text(
            "Show all amenities",
            exact=False
        )

        if show_btn.count() > 0:
        
            print(
                "[INFO] Opening amenities modal..."
            )

            show_btn.first.click()

            page.wait_for_timeout(3000)

            with open(
                "amenities_modal.html",
                "w",
                encoding="utf-8"
            ) as f:

                f.write(page.content())
        else:

            print(
                "[INFO] Show all amenities button not found"
            )

            return categories

        modal_text = page.locator(
            "[role='dialog']"
        ).inner_text()

        lines = [
            x.strip()
            for x in modal_text.splitlines()
            if x.strip()
        ]

        current_category = None

        known_categories = [

            "Bathroom",
            "Bedroom and laundry",
            "Entertainment",
            "Family",
            "Heating and cooling",
            "Home safety",
            "Internet and office",
            "Kitchen and dining",
            "Location features",
            "Outdoor",
            "Parking and facilities",
            "Services"
        ]

        for line in lines:

            if line in known_categories:

                current_category = line

                categories[current_category] = []

                continue

            if current_category:

                categories[current_category].append(
                    line
                )

        # Close modal

        try:

            page.keyboard.press(
                "Escape"
            )

        except:
            pass

    except Exception as e:

        print(
            f"[Amenities Modal Error] {e}"
        )

    return categories
    
def classify_amenities(
    amenities_text,
    description_text
):

    text = (
        amenities_text +
        " " +
        description_text
    ).lower()

    text = text.replace("-", " ")
    text = text.replace("wi-fi", "wifi")
    text = text.replace("wi fi", "wifi")
    text = text.replace("self check in", "self check-in")
    text = text.replace("air-conditioning", "air conditioning")

    data = {

        "Bathroom": [],
        "Bedroom and laundry": [],
        "Entertainment": [],
        "Family": [],
        "Heating and cooling": [],
        "Home safety": [],
        "Internet and office": [],
        "Kitchen and dining": [],
        "Location features": [],
        "Outdoor": [],
        "Parking and facilities": [],
        "Services": []
    }

    # Bathroom

    bathroom_keywords = [
        "bathroom",
        "hot water",
        "shampoo",
        "towels",
        "bathtub"
    ]

    # Laundry

    laundry_keywords = [
        "washer",
        "dryer",
        "iron"
    ]

    # Entertainment

    entertainment_keywords = [
        "tv",
        "netflix",
        "amazon prime",
        "youtube"
    ]

    # Internet

    internet_keywords = [
        "wifi",
        "workspace"
    ]

    # Kitchen

    kitchen_keywords = [
        "kitchen",
        "microwave",
        "oven",
        "cookware",
        "refrigerator",
        "fridge",
        "freezer"
    ]

    # Cooling

    cooling_keywords = [
        "air conditioning",
        "heating",
        "ac"
    ]

    # Parking

    parking_keywords = [
        "parking",
        "garage",
        "elevator"
    ]

    # Services

    services_keywords = [

            "cleaning service",
            "laundry service",
            "maid service",
            "housekeeping",
            "self check-in",
            "self check in",
            "lockbox",
            "smart lock",
            "concierge",
            "host",
            "24/7 support",
            "check in"
        ]

    family_keywords = [

    "family",
    "families",
    "kids",
    "children",
    "crib",
    "baby",
    "high chair"
    ]
    
    home_safety_keywords = [

        "security",
        "security camera",
        "security cameras",
        "armed guard",
        "guard",
        "guards",
        "watchman",
        "watchmen",
        "safe",
        "safety",
        "emergency",
        "medical assistance",
        "smoke alarm",
        "carbon monoxide alarm",
        "first aid",
        "fire extinguisher"
    ]
    
    location_keywords = [
        
        # Food
    
        "restaurant",
        "restaurants",
        "cafe",
        "cafes",
        "food court",
        "food chains",
    
        # Shopping
    
        "shopping",
        "shopping center",
        "shopping mall",
        "mall",
        "market",
        "commercial market",
        "supermarket",
        "supermarkets",
        "grocery",
        "grocery store",
    
        # Transport
    
        "airport",
        "metro",
        "bus stop",
        "public transportation",
        "walking distance",
        "ring road",
    
        # Tourist / lifestyle
    
        "beach",
        "park",
        "parks",
        "lake",
        "city center",
        "downtown",
    
        # Business districts
    
        "business district",
        "financial district",
    
        # Common Pakistan examples
    
        "dha",
        "gulberg",
        "bahria town",
        "clifton",
        "phase"
    ]
    
    outdoor_keywords = [

        "balcony",
        "terrace",
        "patio",
        "garden",
        "beach access",
        "sea view",
        "outdoor",
        "courtyard",
        "park",
        "park facing",
        "pool",
        "rooftop",
        "bbq"
    ]
    
    mapping = {

        "Bathroom":
            bathroom_keywords,

        "Bedroom and laundry":
            laundry_keywords,

        "Entertainment":
            entertainment_keywords,

        "Family":
            family_keywords,

        "Heating and cooling":
            cooling_keywords,

        "Home safety":
            home_safety_keywords,

        "Internet and office":
            internet_keywords,

        "Kitchen and dining":
            kitchen_keywords,

        "Location features":
            location_keywords,

        "Outdoor":
            outdoor_keywords,

        "Parking and facilities":
            parking_keywords,

        "Services":
            services_keywords
    }

    for category, keywords in mapping.items():

        for keyword in keywords:

            if keyword in text:

                data[category].append(
                    keyword
                )

    return data

def extract_location_and_transport(description):

    location_info = []

    transport_info = []

    location_keywords = [

        "mall",
        "market",
        "shopping",
        "restaurant",
        "restaurants",
        "food",
        "cafe",
        "cafes",
        "airport",
        "park",
        "beach"
    ]

    transport_keywords = [

        "minutes",
        "minute",
        "drive",
        "walking distance",
        "ring road",
        "transport",
        "uber",
        "careem"
    ]

    lines = description.splitlines()

    for line in lines:

        line_lower = line.lower()

        review_words = [

            "stayed",
            "airbnb",
            "host",
            "recommended",
            "great stay",
            "rating",
            "show more",
            "reviews"
        ]

        if any(
            word in line_lower
            for word in review_words
        ):
            continue
        if any(
            k in line_lower
            for k in location_keywords
        ):

            location_info.append(
                line.strip()
            )

        if any(
            k in line_lower
            for k in transport_keywords
        ):

            transport_info.append(
                line.strip()
            )

    return (

        " | ".join(
            location_info
        ),

        " | ".join(
            transport_info
        )
    )


AIRBNB_URL = "https://www.airbnb.com"

SCREENSHOT_DIR = "screenshots"
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


# =====================================================
# Utilities
# =====================================================

def log(msg):
    print(f"[INFO] {msg}")


def take_screenshot(page, name):
    path = os.path.join(SCREENSHOT_DIR, name)
    page.screenshot(path=path, full_page=True)
    log(f"Screenshot saved: {path}")

# =====================================================
# Popup Handler
# =====================================================

def close_popups(page):

    log("Checking for popups...")

    popup_selectors = [

    # Generic close buttons
    "button[aria-label='Close']",
    "button[aria-label='close']",

    # Airbnb modal close buttons
    "[role='dialog'] button",

    # Cookie banners
    "button:has-text('Accept')",
    "button:has-text('Accept all')",
    "button:has-text('OK')",

    # Login popups
    "button:has-text('Not now')",
    "button:has-text('Maybe later')",
    "button:has-text('Dismiss')",

    # Wishlist / sign in prompts
    "button:has-text('Continue without signing in')",
    "button:has-text('No thanks')",
    "button:has-text('Skip')"
    ]

    for selector in popup_selectors:

        try:

            locator = page.locator(selector)

            if locator.count() > 0:

                print(
                    f"[POPUP FOUND] {selector}"
                )

                locator.first.click(
                    timeout=2000
                )

                page.wait_for_timeout(
                    1000
                )
        except Exception:
            pass

    try:
        page.keyboard.press("Escape")
        page.wait_for_timeout(1000)
    except:
        pass

    log("Popup handling complete")


# =====================================================
# Open Airbnb
# =====================================================

def open_airbnb(playwright):

    log("Launching browser")

    browser = playwright.chromium.launch(
        headless=False,
        slow_mo=500
    )

    context = browser.new_context()

    page = context.new_page()
    page.on(
        "framenavigated",
        lambda frame: print(
            f"\nNAVIGATION DETECTED: {frame.url}"
        )
    )

    log("Opening Airbnb")

    page.goto(
        AIRBNB_URL,
        wait_until="domcontentloaded",
        timeout=60000
    )

    page.wait_for_timeout(5000)
    

    log(f"URL: {page.url}")

    try:
        log(f"Title: {page.title()}")
    except:
        pass

    close_popups(page)

    dialogs = page.locator("[role='dialog']").count()

    log(f"Dialogs Found: {dialogs}")

    take_screenshot(page, "homepage.png")

    return browser, page


# =====================================================
# Inputs
# =====================================================

def collect_user_inputs():

    destination = input("Destination: ")

    checkin = input(
        "Check-in (YYYY-MM-DD): "
    )

    checkout = input(
        "Check-out (YYYY-MM-DD): "
    )

    max_pages = int(
        input(
         "How many result pages to scrape? " )
    )

    adults = int(
        input("Adults: ")
    )

    children = int(
        input("Children: ")
    )

    infants = int(
        input("Infants: ")
    )

    pets = int(
        input("Pets: ")
    )
    
    return {
        "destination": destination,
        "checkin": checkin,
        "checkout": checkout,
        "max_pages": max_pages,
        "adults": adults,
        "children": children,
        "infants": infants,
        "pets": pets
    }

# =====================================================
# URL Builder
# =====================================================

def build_airbnb_url(user_data):

    destination = quote(
        user_data["destination"]
    )

    url = (
        f"https://www.airbnb.com/s/"
        f"{destination}/homes"
        f"?checkin={user_data['checkin']}"
        f"&checkout={user_data['checkout']}"
        f"&date_picker_type=calendar"
        f"&adults={user_data['adults']}"
        f"&children={user_data['children']}"
        f"&infants={user_data['infants']}"
        f"&pets={user_data['pets']}"
    )

    return url

def scrape_listing(page, url):

    data = {}

    try:
        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(5000)

        print(
            f"\nOpened Listing: {page.title()}"
        )

        # Close any popup that appears
        close_popups(page)

        # ====================================
        # RAW PAGE TEXT FOR ANALYSIS
        # ====================================
        body_text = page.locator("body").inner_text()

        html = page.content()

        try:

            title = page.locator(
                "h1"
            ).first.inner_text()

        except:
        
            title = page.title()

            title = title.replace(
                " - Airbnb",
                ""
            )

        rating, reviews = extract_rating_reviews(body_text)
        room = extract_room_info(body_text)
        price = extract_price(body_text)
        price_per_night = (
            calculate_price_per_night(
                price
            )
        )
        amenities = extract_amenities(body_text)
        amenity_categories = (
            extract_amenity_categories(
                page
            )
        )

        print("\n========== AMENITY MODAL ==========")

        for key, value in amenity_categories.items():
        
            print(f"\n{key}")

            for item in value[:5]:
                print(f"  - {item}")

        location = extract_location_from_title(page)
        print(
            f"\nTITLE: {page.title()}"
        )

        print(
            f"LOCATION FOUND: {location}"
        )

        city, country = split_location(
            location
        )
        
        highlights = extract_highlights(
            body_text
        )
        
        description = extract_description(
            body_text
        )

        if not description:
        
            description = (
                extract_description_fallback(
                    body_text
                )
            )

        if not description:

            safe_title = (
                title
                .replace("/", "_")
                .replace("\\", "_")
            )
        
            with open(
                f"failed_{safe_title[:30]}.txt",
                "w",
                encoding="utf-8"
            ) as f:
        
                f.write(body_text)
        
            print(
                f"[FAILED DESCRIPTION] "
                f"{safe_title}"
            )

        if not description:
        
            filename = (
                f"failed_page_"
                f"{title[:30]}.txt"
            )

            with open(
                filename,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(body_text)

            print(
                f"[FAILED PAGE SAVED] {filename}"
            )
        location_desc, getting_around = (
            extract_location_and_transport(
                description
            )
        )
        print(
            f"\nDescription Length: "
            f"{len(description)}"
        )

        categorized = classify_amenities(
            amenities,
            description + " " + highlights
        )

        location_description = (
            extract_location_description(
                body_text
            )
        )
        
        latitude, longitude = (
            extract_coordinates(html)
        )

        # ==========================
        # OPEN AIRBNB CALENDAR
        # ==========================

        calendar_selectors = [
        
            "[data-testid='change-dates-checkIn']",

            "button:has-text('Check availability')",

            "button:has-text('Select check-in date')",

            "[data-testid='structured-search-input-field-split-dates-0']"
        ]

        opened = False

        for selector in calendar_selectors:
        
            try:
            
                btn = page.locator(selector)

                if btn.count() > 0:
                
                    print(
                        f"[CALENDAR] Opening with: {selector}"
                    )

                    btn.first.click()

                    page.wait_for_timeout(3000)

                    opened = True

                    break
                
            except:
                pass
            
        if not opened:
        
            print(
                "[CALENDAR] Could not find calendar button"
            )

        # ==========================
        # SCRAPE AVAILABILITY
        # ==========================

        available_dates, unavailable_dates = (
            extract_availability(page)
        )
        
        available_dates_formatted = (
            format_dates_by_month(
                available_dates
            )
        )       

        unavailable_dates_formatted = (
            format_dates_by_month(
                unavailable_dates
            )
        )
        print(
            "[CALENDAR DEBUG] Starting availability extraction..."
        )

        print(
            f"Available: {len(available_dates_formatted)}"
        )

        print(
            f"Unavailable: {len(unavailable_dates_formatted)}"
        )

        data["Hotel Name"] = title
        data["Rating"] = rating
        data["Reviews"] = reviews
        data["Room Details"] = room
        data["Amenities"] = amenities
        data["Displayed Price"] = price
        data["City"] = city
        data["Location"] = location
        data["Country"] = country
        data["Highlights"] = highlights
        data["Description"] = description
        data["Displayed Price"] = price

        data["Available Dates"] = available_dates_formatted

        data["Unavailable Dates"] = unavailable_dates_formatted
        
        data["Price Per Night"] = (
            price_per_night
        )
        data["Bathroom"] = ", ".join(
            categorized["Bathroom"]
        )
        
        data["Bedroom and laundry"] = ", ".join(
            categorized["Bedroom and laundry"]
        )
        
        data["Entertainment"] = ", ".join(
            categorized["Entertainment"]
        )
        
        data["Heating and cooling"] = ", ".join(
            categorized["Heating and cooling"]
        )
        
        data["Internet and office"] = ", ".join(
            categorized["Internet and office"]
        )
        
        data["Kitchen and dining"] = ", ".join(
            categorized["Kitchen and dining"]
        )
        
        data["Parking and facilities"] = ", ".join(
            categorized["Parking and facilities"]
        )
        
        data["Services"] = ", ".join(
            categorized["Services"]
        )
        data["Home safety"] = ", ".join(
            amenity_categories.get(
                "Home safety",
                []
            )
        )

        data["Location features"] = ", ".join(
            amenity_categories.get(
                "Location features",
                []
            )
        )

        data["Outdoor"] = ", ".join(
            amenity_categories.get(
                "Outdoor",
                []
            )
        )    
        data["Family"] = ", ".join(
            categorized["Family"]
        )

        data["Home safety"] = ", ".join(
            categorized["Home safety"]
        )

        data["Location features"] = ", ".join(
            categorized["Location features"]
        )

        data["Outdoor"] = ", ".join(
            categorized["Outdoor"]
        )   
        data["Latitude"] = latitude
        data["Longitude"] = longitude
        data["Location Description"] = (
            location_desc
        )
        
        data["Getting Around"] = (
            getting_around
        )
        data["URL"] = url

        return data
    except Exception as e:
        print(f"scrape_listing failed: {e}")
        return {}
    
def collect_listing_urls(
    page,
    max_pages
):

    unique_rooms = {}

    for current_page in range(max_pages):

        print(
            f"\n========== PAGE {current_page + 1} =========="
        )

        page.wait_for_timeout(5000)

        room_links = page.locator(
            "a[href*='/rooms/']"
        )

        for i in range(room_links.count()):

            try:

                href = room_links.nth(i).get_attribute(
                    "href"
                )

                if not href:
                    continue

                if href.startswith("/"):

                    href = AIRBNB_URL + href

                room_id = (
                    href
                    .split("/rooms/")[1]
                    .split("?")[0]
                )

                if room_id not in unique_rooms:

                    unique_rooms[room_id] = href

            except:
                pass

        print(
            f"Unique URLs so far: "
            f"{len(unique_rooms)}"
        )

        try:

            next_button = page.locator(
                "a[aria-label='Next']"
            )

            if next_button.count() == 0:

                print(
                    "No more pages found."
                )

                break

            next_button.first.click()

            page.wait_for_load_state(
                "domcontentloaded"
            )

            page.wait_for_timeout(
                5000
            )

        except Exception as e:

            print(
                f"Pagination stopped: {e}"
            )

            break

    return list(
        unique_rooms.values()
    )


# =====================================================
# Main
# =====================================================

def main():

    user_data = collect_user_inputs()

    print("\n==========================")
    print("USER INPUTS")
    print("==========================")
    print(user_data)

    with sync_playwright() as p:

        browser = None

    
        results = []

        try:

            browser, page = open_airbnb(p)

            search_url = build_airbnb_url(
                user_data
            )
            
            print("\nGenerated URL:")
            print(search_url)
            
            page.goto(
                search_url,
                wait_until="domcontentloaded",
                timeout=60000
            )

            page.wait_for_timeout(10000)
            with open(
                "search_page.html",
                "w",
                encoding="utf-8"
            ) as f:
                f.write(page.content())
            
            print("\nHTML saved to search_page.html")

            room_links = page.locator(
                "a[href*='/rooms/']"
            )

            print(
                f"\nRoom Links Found: {room_links.count()}"
            )

            for i in range(
                min(10, room_links.count())
            ):
                try:
                    href = room_links.nth(i).get_attribute(
                        "href"
                    )
                    print(href)
                except Exception as e:
                    print(e)
            page.wait_for_timeout(5000)

            take_screenshot(
                page,
                "search_results.png"
            )

            print("\nSEARCH PAGE LOADED")

            # ====================================
            # COLLECT URLS FROM MULTIPLE PAGES
            # ====================================
            
            urls = collect_listing_urls(
                page,
                user_data["max_pages"]
            )
            
            print(
                f"\nTOTAL UNIQUE LISTINGS: "
                f"{len(urls)}"
            )
            
            if urls:
            
                print(
                    "\nFirst URL:"
                )
            
                print(urls[0])
            # ====================================
            # SCRAPE FIRST 10 LISTINGS
            # ====================================

            results = []

            for idx, listing_url in enumerate(
                urls,
                start=1
            ):
                print(
                    f"\n[{idx}/{len(urls)}] "
                    f"Scraping: {listing_url}"
                )

                try:
                
                    listing = scrape_listing(
                        page,
                        listing_url
                    )

                    if listing:
                    
                        results.append(
                            listing
                        )

                        print(
                            f"Hotel: {listing.get('Hotel Name')}"
                        )

                except Exception as e:
                
                    print(
                        f"Failed: {e}"
                    )

            # ====================================
            # RESULTS
            # ====================================

            print("\n")
            print("=" * 70)
            print("FINAL RESULTS")
            print("=" * 70)

            for item in results:
            
                print("\n")

                for k, v in item.items():
                
                    print(
                        f"{k}: {v}"
                    )

            # ====================================
            # SAVE JSON
            # ====================================

            with open(
                "airbnb_results.json",
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    results,
                    f,
                    indent=4,
                    ensure_ascii=False
                )

            print(
                "\nJSON saved: airbnb_results.json"
            )        

            # ====================================
            # SAVE CSV
            # ====================================
            
            df = pd.DataFrame(results)
            
            df.to_csv(
                "airbnb_results.csv",
                index=False,
                encoding="utf-8-sig"
            )
            
            print(
                "CSV saved: airbnb_results.csv"
            )


            print(
                f"\nTotal Listings Scraped: "
                f"{len(results)}"
            )

            input(
                "\nPress ENTER to close browser..."
            )
        except Exception as e:

            print("\nERROR:")
            print(e)

            print("\nTRACEBACK:")
            traceback.print_exc()
        finally:

            if browser:
                browser.close()


if __name__ == "__main__":
    main()

    
