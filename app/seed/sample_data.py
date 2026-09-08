import asyncio
import logging
from datetime import datetime, timezone, date, timedelta
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.core.mongodb import get_database, close_mongo_connection

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed")

SAMPLE_DESTINATIONS = [
    {
        "name": "Amritsar",
        "country": "India",
        "state": "Punjab",
        "city": "Amritsar",
        "description": "Spiritual and cultural hub home to the iconic Golden Temple and vibrant culinary scene.",
        "image_url": "https://images.unsplash.com/photo-amritsar",
        "latitude": 31.6340,
        "longitude": 74.8723,
        "tags": ["Spiritual", "History", "Food", "Heritage"],
        "best_time_to_visit": "October to March"
    },
    {
        "name": "Jaipur",
        "country": "India",
        "state": "Rajasthan",
        "city": "Jaipur",
        "description": "The historic Pink City renowned for magnificent forts, royal palaces, and artisanal textiles.",
        "image_url": "https://images.unsplash.com/photo-jaipur",
        "latitude": 26.9124,
        "longitude": 75.7873,
        "tags": ["Heritage", "Architecture", "Palaces", "Culture"],
        "best_time_to_visit": "October to March"
    },
    {
        "name": "Goa",
        "country": "India",
        "state": "Goa",
        "city": "Panaji",
        "description": "Coastal tropical paradise famed for palm-fringed beaches, Portuguese villas, and vibrant nightlife.",
        "image_url": "https://images.unsplash.com/photo-goa",
        "latitude": 15.4989,
        "longitude": 73.8278,
        "tags": ["Beach", "Nightlife", "Water Sports", "Relaxation"],
        "best_time_to_visit": "November to February"
    },
    {
        "name": "Manali",
        "country": "India",
        "state": "Himachal Pradesh",
        "city": "Manali",
        "description": "High-altitude Himalayan resort town known for snowy peaks, cedar forests, and adventure sports.",
        "image_url": "https://images.unsplash.com/photo-manali",
        "latitude": 32.2432,
        "longitude": 77.1892,
        "tags": ["Mountains", "Adventure", "Snow", "Trekking"],
        "best_time_to_visit": "October to June"
    },
    {
        "name": "Varanasi",
        "country": "India",
        "state": "Uttar Pradesh",
        "city": "Varanasi",
        "description": "Ancient sacred city along the holy Ganges, known for historic ghats, silk weaving, and evening aartis.",
        "image_url": "https://images.unsplash.com/photo-varanasi",
        "latitude": 25.3176,
        "longitude": 82.9739,
        "tags": ["Spiritual", "Ghats", "Culture", "Sacred"],
        "best_time_to_visit": "November to February"
    },
    {
        "name": "Udaipur",
        "country": "India",
        "state": "Rajasthan",
        "city": "Udaipur",
        "description": "The City of Lakes, featuring fairytale marble palaces rising above serene blue waters.",
        "image_url": "https://images.unsplash.com/photo-udaipur",
        "latitude": 24.5854,
        "longitude": 73.7125,
        "tags": ["Lakes", "Romance", "Palaces", "Heritage"],
        "best_time_to_visit": "September to March"
    },
    {
        "name": "Kochi",
        "country": "India",
        "state": "Kerala",
        "city": "Kochi",
        "description": "Port town where Portuguese architecture meets serene backwaters and Chinese fishing nets.",
        "image_url": "https://images.unsplash.com/photo-kochi",
        "latitude": 9.9312,
        "longitude": 76.2673,
        "tags": ["Backwaters", "Coastal", "Art", "Spices"],
        "best_time_to_visit": "October to April"
    },
    {
        "name": "Shillong",
        "country": "India",
        "state": "Meghalaya",
        "city": "Shillong",
        "description": "The Scotland of the East, surrounded by pine hills, roaring waterfalls, and living root bridges.",
        "image_url": "https://images.unsplash.com/photo-shillong",
        "latitude": 25.5788,
        "longitude": 91.8933,
        "tags": ["Nature", "Waterfalls", "Hills", "Music"],
        "best_time_to_visit": "September to May"
    },
    {
        "name": "Rishikesh",
        "country": "India",
        "state": "Uttarakhand",
        "city": "Rishikesh",
        "description": "World Capital of Yoga set along the emerald Ganges, famed for meditation and white-water rafting.",
        "image_url": "https://images.unsplash.com/photo-rishikesh",
        "latitude": 30.0869,
        "longitude": 78.2676,
        "tags": ["Yoga", "Rafting", "Spiritual", "Wellness"],
        "best_time_to_visit": "September to April"
    },
    {
        "name": "Bengaluru",
        "country": "India",
        "state": "Karnataka",
        "city": "Bengaluru",
        "description": "Dynamic Garden City blending lush botanical parks, craft microbreweries, and modern innovation.",
        "image_url": "https://images.unsplash.com/photo-bengaluru",
        "latitude": 12.9716,
        "longitude": 77.5946,
        "tags": ["City", "Gardens", "Brewery", "Tech"],
        "best_time_to_visit": "Year round"
    }
]


async def seed_data(db: AsyncIOMotorDatabase) -> dict:
    """Idempotently seed demo tourism data."""
    now = datetime.now(timezone.utc)
    dest_map = {}

    # 1. Seed 10 Destinations
    dest_count = 0
    for d_data in SAMPLE_DESTINATIONS:
        filter_q = {"name": d_data["name"], "country": d_data["country"]}
        existing = await db["destinations"].find_one(filter_q)
        if existing:
            dest_map[d_data["name"]] = str(existing["_id"])
        else:
            doc = dict(d_data)
            doc["created_at"] = now
            doc["updated_at"] = now
            res = await db["destinations"].insert_one(doc)
            dest_map[d_data["name"]] = str(res.inserted_id)
            dest_count += 1

    # 2. Seed 20 Hotels (2 per destination)
    hotel_templates = [
        ("Amritsar", "Golden Sarovar Premiere", 4200.0, 4.6, ["WiFi", "Restaurant", "Temple Shuttle"], "Court Road"),
        ("Amritsar", "Heritage Inn Amritsar", 2200.0, 4.1, ["WiFi", "Breakfast", "AC"], "Town Hall"),
        ("Jaipur", "Royal Haveli Palace", 5500.0, 4.8, ["Pool", "Spa", "Rooftop Restaurant"], "Bani Park"),
        ("Jaipur", "Pink City Guest House", 1800.0, 4.2, ["WiFi", "Breakfast"], "MI Road"),
        ("Goa", "Sunset Sands Beach Resort", 6800.0, 4.7, ["Private Beach", "Pool", "Bar"], "Calangute"),
        ("Goa", "Casa Portuguese Heritage Villa", 3900.0, 4.5, ["Garden", "Kitchen", "WiFi"], "Fontainhas"),
        ("Manali", "Himalayan Cedar Pine Resort", 4500.0, 4.6, ["Mountain View", "Fireplace", "Buffet"], "Old Manali"),
        ("Manali", "Snowline Valley Hotel", 2400.0, 4.0, ["Heater", "Balcony", "Restaurant"], "Mall Road"),
        ("Varanasi", "Ganges View Heritage Stay", 3800.0, 4.6, ["Ghat View", "Rooftop Yoga", "WiFi"], "Assi Ghat"),
        ("Varanasi", "Kashi Pilgrims Inn", 1500.0, 4.1, ["AC", "Breakfast", "Pickup"], "Godowlia"),
        ("Udaipur", "Lake Pichola Palace Hotel", 7500.0, 4.9, ["Lake View", "Pool", "Fine Dining"], "Pichola"),
        ("Udaipur", "Mewar Boutique Suites", 3200.0, 4.4, ["Terrace", "WiFi", "Restaurant"], "Fateh Sagar"),
        ("Kochi", "Fort Spice Heritage Hotel", 4100.0, 4.5, ["Ayurveda Spa", "Pool", "Art Gallery"], "Fort Kochi"),
        ("Kochi", "Backwater Breeze Homestay", 2100.0, 4.3, ["Canoe Rental", "Breakfast"], "Kumbalangi"),
        ("Shillong", "Pine Crest Cloud Resort", 4800.0, 4.6, ["Valley View", "Garden Cafe", "Heater"], "Laitumkhrah"),
        ("Shillong", "Highland Eco Lodge", 2600.0, 4.2, ["Trek Guide", "Organic Food"], "Police Bazar"),
        ("Rishikesh", "Ganga Riverside Wellness Retreat", 5200.0, 4.7, ["Yoga Pavilion", "Spa", "River Beach"], "Tapovan"),
        ("Rishikesh", "Adventures Backpacker Haven", 1400.0, 4.2, ["Bunk Beds", "Cafe", "Rafting Desk"], "Laxman Jhula"),
        ("Bengaluru", "The Silicon Grand Hotel", 5900.0, 4.7, ["Pool", "Gym", "Business Center"], "MG Road"),
        ("Bengaluru", "Garden View Residency", 2800.0, 4.3, ["WiFi", "Breakfast", "Workspace"], "Indiranagar")
    ]

    hotel_count = 0
    for dest_name, name, price, rating, amenities, addr in hotel_templates:
        dest_id = dest_map.get(dest_name, "")
        existing = await db["hotels"].find_one({"name": name, "destination_id": dest_id})
        if not existing:
            await db["hotels"].insert_one({
                "destination_id": dest_id,
                "name": name,
                "description": f"Quality hospitality and comfortable stay in {dest_name}.",
                "address": addr,
                "rating": rating,
                "price_per_night": price,
                "currency": "INR",
                "amenities": amenities,
                "image_urls": ["https://images.unsplash.com/photo-demo-hotel"],
                "latitude": 20.0,
                "longitude": 75.0,
                "available_rooms": 15,
                "created_at": now,
                "updated_at": now
            })
            hotel_count += 1

    # 3. Seed 30 Activities (3 per destination)
    activity_templates = [
        ("Amritsar", "Golden Temple Sunrise Spiritual Walk", "Spiritual", 120, 0.0, 4.9),
        ("Amritsar", "Wagah Border Beating Retreat Ceremony", "Cultural", 240, 500.0, 4.8),
        ("Amritsar", "Old City Street Food & Kulcha Trail", "Culinary", 150, 650.0, 4.7),
        ("Jaipur", "Amber Fort & Palace Audio-Guided Tour", "Heritage", 180, 400.0, 4.7),
        ("Jaipur", "Hot Air Balloon Flight Over Pink City", "Adventure", 90, 8500.0, 4.9),
        ("Jaipur", "Block Printing Workshop with Local Artisans", "Cultural", 120, 1200.0, 4.6),
        ("Goa", "Scuba Diving & Snorkeling at Grande Island", "Adventure", 300, 3200.0, 4.6),
        ("Goa", "Mandovi River Sunset Luxury Cruise", "Leisure", 120, 950.0, 4.5),
        ("Goa", "Spice Plantation Tour & Authentic Goan Lunch", "Culinary", 180, 800.0, 4.6),
        ("Manali", "Solang Valley Paragliding & Zorbing", "Adventure", 180, 2500.0, 4.8),
        ("Manali", "Jogini Waterfall Hiking Trail", "Nature", 210, 300.0, 4.7),
        ("Manali", "Rohtang Pass High Altitude Snow Experience", "Adventure", 360, 3500.0, 4.9),
        ("Varanasi", "Early Morning Ganges Sunrise Boat Ride", "Spiritual", 90, 450.0, 4.9),
        ("Varanasi", "Dashashwamedh Ghat Grand Ganga Aarti Viewing", "Spiritual", 120, 250.0, 4.9),
        ("Varanasi", "Sarnath Buddhist Heritage & Stupa Excursion", "Heritage", 240, 700.0, 4.7),
        ("Udaipur", "Lake Pichola Sunset Heritage Boat Cruise", "Leisure", 60, 600.0, 4.8),
        ("Udaipur", "City Palace Museum & Courtyards Guided Tour", "Heritage", 150, 500.0, 4.7),
        ("Udaipur", "Bagore Ki Haveli Folk Dance Show", "Cultural", 90, 300.0, 4.8),
        ("Kochi", "Kerala Kathakali Live Dance Performance", "Cultural", 90, 450.0, 4.7),
        ("Kochi", "Alleppey Backwaters Private Houseboat Cruise", "Leisure", 360, 5500.0, 4.9),
        ("Kochi", "Fort Kochi Bicycle Heritage & Spice Trail", "Heritage", 120, 600.0, 4.6),
        ("Shillong", "Cherrapunjee Double Decker Root Bridge Trek", "Adventure", 480, 1800.0, 4.9),
        ("Shillong", "Elephant Falls & Shillong Peak Day Trip", "Nature", 240, 900.0, 4.6),
        ("Shillong", "Dawki River Crystal Clear Boating Experience", "Nature", 300, 1500.0, 4.8),
        ("Rishikesh", "Shivpuri White Water River Rafting (16km)", "Adventure", 180, 1200.0, 4.9),
        ("Rishikesh", "Sunrise Yoga & Guided Meditation on Ganga Beach", "Wellness", 90, 500.0, 4.8),
        ("Rishikesh", "Bungee Jumping from India's Highest Platform", "Adventure", 120, 3800.0, 4.9),
        ("Bengaluru", "Lalbagh Botanical Gardens Historical Walking Tour", "Nature", 120, 300.0, 4.6),
        ("Bengaluru", "Indiranagar Craft Microbrewery & Food Crawl", "Culinary", 180, 1800.0, 4.7),
        ("Bengaluru", "Nandi Hills Sunrise Excursion & Cloud Walk", "Nature", 240, 850.0, 4.8)
    ]

    activity_count = 0
    for dest_name, act_name, cat, dur, pr, rat in activity_templates:
        dest_id = dest_map.get(dest_name, "")
        existing = await db["activities"].find_one({"name": act_name, "destination_id": dest_id})
        if not existing:
            await db["activities"].insert_one({
                "destination_id": dest_id,
                "name": act_name,
                "description": f"Memorable {cat.lower()} experience exploring {dest_name}.",
                "category": cat,
                "duration_minutes": dur,
                "price": pr,
                "currency": "INR",
                "rating": rat,
                "image_url": "https://images.unsplash.com/photo-demo-activity",
                "location": dest_name,
                "created_at": now
            })
            activity_count += 1

    # 4. Seed 20 Demo Flights
    flight_data = [
        ("DEL", "ATQ", "IndiGo", "6E-401", 60, 2400.0, 0, 40),
        ("BOM", "ATQ", "Air India", "AI-612", 150, 5800.0, 0, 25),
        ("DEL", "JAI", "Alliance Air", "9I-702", 55, 2100.0, 0, 30),
        ("BOM", "JAI", "SpiceJet", "SG-304", 105, 3900.0, 0, 35),
        ("DEL", "GOI", "IndiGo", "6E-551", 145, 4600.0, 0, 50),
        ("BLR", "GOI", "Akasa Air", "QP-132", 70, 2900.0, 0, 45),
        ("DEL", "KUU", "Alliance Air", "9I-815", 80, 6200.0, 0, 18),
        ("DEL", "VNS", "IndiGo", "6E-208", 85, 3200.0, 0, 60),
        ("BOM", "VNS", "Air India", "AI-691", 130, 4900.0, 0, 30),
        ("DEL", "UDR", "Air India", "AI-471", 75, 3400.0, 0, 28),
        ("BOM", "UDR", "IndiGo", "6E-722", 85, 3100.0, 0, 32),
        ("DEL", "COK", "Vistara", "UK-883", 195, 6100.0, 0, 40),
        ("BLR", "COK", "IndiGo", "6E-311", 60, 2200.0, 0, 55),
        ("DEL", "SHL", "SpiceJet", "SG-288", 210, 7200.0, 1, 20),
        ("CCU", "SHL", "Alliance Air", "9I-741", 80, 3600.0, 0, 15),
        ("DEL", "DED", "IndiGo", "6E-902", 55, 2500.0, 0, 45),
        ("BOM", "DED", "Air India", "AI-809", 140, 5200.0, 0, 22),
        ("DEL", "BLR", "Vistara", "UK-819", 160, 5400.0, 0, 50),
        ("BOM", "BLR", "IndiGo", "6E-615", 95, 3300.0, 0, 70),
        ("HYD", "BLR", "Air India Express", "IX-931", 65, 2600.0, 0, 40)
    ]

    flight_count = 0
    for orig, dest, airline, f_no, dur, price, stops, seats in flight_data:
        existing = await db["flights"].find_one({"flight_number": f_no, "origin": orig, "destination": dest})
        if not existing:
            dep = now + timedelta(days=2)
            arr = dep + timedelta(minutes=dur)
            await db["flights"].insert_one({
                "origin": orig,
                "destination": dest,
                "airline": airline,
                "flight_number": f_no,
                "departure_time": dep,
                "arrival_time": arr,
                "duration_minutes": dur,
                "price": price,
                "currency": "INR",
                "stops": stops,
                "available_seats": seats,
                "created_at": now
            })
            flight_count += 1

    # 5. Seed 25 Demo Expenses (linked to demo trip_id 1, 2, 3)
    expense_templates = [
        (1, "Stay", "Royal Haveli Hotel Room Advance", 5500.0, date.today() - timedelta(days=5)),
        (1, "Food", "Dinner at Chokhi Dhani Traditional Village", 1850.0, date.today() - timedelta(days=4)),
        (1, "Travel", "Prepaid Taxi Airport to Bani Park", 750.0, date.today() - timedelta(days=5)),
        (1, "Activities", "Amber Fort Audio Guide & Entry Ticket", 400.0, date.today() - timedelta(days=3)),
        (1, "Shopping", "Jaipuri Blue Pottery Souvenirs", 1200.0, date.today() - timedelta(days=3)),
        (1, "Food", "Laxmi Misthan Bhandar Ghewar & Sweets", 650.0, date.today() - timedelta(days=2)),
        (1, "Travel", "Auto Rickshaw City Sightseeing", 500.0, date.today() - timedelta(days=2)),
        (1, "Activities", "City Palace Museum & Photography Pass", 600.0, date.today() - timedelta(days=2)),
        (1, "Food", "Rooftop Cafe Dinner at Nahargarh Fort", 1400.0, date.today() - timedelta(days=1)),
        (1, "Other", "Emergency Pharmacy Medicines", 220.0, date.today() - timedelta(days=1)),

        (2, "Stay", "Sunset Sands Resort 2-Night Stay", 13600.0, date.today() - timedelta(days=10)),
        (2, "Travel", "Goa Airport Dabolim Prepaid Cab", 1200.0, date.today() - timedelta(days=10)),
        (2, "Food", "Beach Shack Seafood Platter at Calangute", 2400.0, date.today() - timedelta(days=9)),
        (2, "Activities", "Scuba Diving & Watersports Package", 3200.0, date.today() - timedelta(days=9)),
        (2, "Travel", "Scooter Rental for 3 Days", 1500.0, date.today() - timedelta(days=8)),
        (2, "Food", "Cafe Bodega Panaji Brunch", 950.0, date.today() - timedelta(days=8)),
        (2, "Activities", "Mandovi River Sunset Cruise Tickets", 950.0, date.today() - timedelta(days=8)),
        (2, "Shopping", "Anjuna Flea Market Souvenirs", 1100.0, date.today() - timedelta(days=7)),

        (3, "Travel", "IndiGo Flight DEL to ATQ", 4800.0, date.today() - timedelta(days=15)),
        (3, "Stay", "Golden Sarovar Hotel", 4200.0, date.today() - timedelta(days=15)),
        (3, "Food", "Kesar Da Dhaba Thali & Lassi", 850.0, date.today() - timedelta(days=14)),
        (3, "Travel", "Cab to Wagah Border & Back", 1200.0, date.today() - timedelta(days=14)),
        (3, "Activities", "Jallianwala Bagh Memorial Audio Guide", 150.0, date.today() - timedelta(days=13)),
        (3, "Food", "Bhai Kulwant Singh Kulche Chhole", 320.0, date.today() - timedelta(days=13)),
        (3, "Shopping", "Traditional Phulkari Dupattas", 2200.0, date.today() - timedelta(days=13))
    ]

    expense_count = 0
    for trip_id, cat, title, amt, exp_date in expense_templates:
        existing = await db["expenses"].find_one({"trip_id": trip_id, "title": title})
        if not existing:
            await db["expenses"].insert_one({
                "trip_id": trip_id,
                "category": cat,
                "title": title,
                "amount": amt,
                "currency": "INR",
                "expense_date": exp_date.isoformat(),
                "notes": "Demo expense record",
                "created_at": now
            })
            expense_count += 1

    summary = {
        "destinations_inserted": dest_count,
        "hotels_inserted": hotel_count,
        "activities_inserted": activity_count,
        "flights_inserted": flight_count,
        "expenses_inserted": expense_count,
        "total_destinations": await db["destinations"].count_documents({}),
        "total_hotels": await db["hotels"].count_documents({}),
        "total_activities": await db["activities"].count_documents({}),
        "total_flights": await db["flights"].count_documents({}),
        "total_expenses": await db["expenses"].count_documents({})
    }

    logger.info(f"Seed complete: {summary}")
    return summary


async def main():
    db = get_database()
    try:
        res = await seed_data(db)
        print("Idempotent seed completed successfully:")
        for k, v in res.items():
            print(f"  {k}: {v}")
    finally:
        await close_mongo_connection()


if __name__ == "__main__":
    asyncio.run(main())
