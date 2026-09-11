/**
 * Automated Verification Test Suite for Frontend ↔ Backend API Integration.
 * Tests service modules, contract adapters, proxy routing, and API schemas.
 */

const assert = require('assert');

async function runTests() {
  console.log('====================================================');
  console.log('   ODYSSEY API INTEGRATION VERIFICATION SUITE');
  console.log('====================================================\n');

  let passed = 0;
  let failed = 0;

  function test(name, fn) {
    try {
      fn();
      console.log(`  [PASS] ${name}`);
      passed++;
    } catch (err) {
      console.error(`  [FAIL] ${name}:`, err.message);
      failed++;
    }
  }

  async function testAsync(name, fn) {
    try {
      await fn();
      console.log(`  [PASS] ${name}`);
      passed++;
    } catch (err) {
      console.error(`  [FAIL] ${name}:`, err.message);
      failed++;
    }
  }

  // Import adapters
  const {
    adaptDestination,
    adaptHotel,
    adaptActivity,
    adaptFlight,
    adaptWeather,
    adaptExpenseBreakdown,
    adaptDailyExpenses
  } = await import('./frontend/src/adapters/tourismAdapters.js');

  // Import services
  const { destinationApi } = await import('./frontend/src/services/destinationApi.js');
  const { hotelApi } = await import('./frontend/src/services/hotelApi.js');
  const { flightApi } = await import('./frontend/src/services/flightApi.js');
  const { activityApi } = await import('./frontend/src/services/activityApi.js');
  const { expenseApi } = await import('./frontend/src/services/expenseApi.js');
  const { weatherApi } = await import('./frontend/src/services/weatherApi.js');
  const { tripApi } = await import('./frontend/src/services/tripApi.js');

  console.log('--- 1. Testing Data Contract Adapters ---');

  test('adaptDestination normalizes backend destination correctly', () => {
    const backendDest = {
      id: "60c72b2f9b1d8b2bad8d3b71",
      name: "Jaipur",
      country: "India",
      state: "Rajasthan",
      city: "Jaipur",
      description: "The Pink City",
      image_url: "https://images.unsplash.com/photo-custom",
      latitude: 26.9124,
      longitude: 75.7873,
      tags: ["Heritage", "Architecture", "Palaces", "Culture"]
    };
    const adapted = adaptDestination(backendDest, 0);
    assert.strictEqual(adapted.name, "Jaipur");
    assert.strictEqual(adapted.id, "60c72b2f9b1d8b2bad8d3b71");
    assert.strictEqual(adapted.tag, "Heritage · Architecture");
    assert.strictEqual(adapted.image, "https://images.unsplash.com/photo-custom");
    assert.strictEqual(typeof adapted.price, "number");
    assert.strictEqual(typeof adapted.rating, "number");
  });

  test('adaptHotel calculates total stay cost and formats metadata', () => {
    const backendHotel = {
      id: "hotel-123",
      destination_id: "dest-1",
      name: "Heritage Palace Resort",
      price_per_night: 4500.0,
      rating: 4.8,
      address: "MI Road, Jaipur",
      amenities: ["WiFi", "Pool"],
      image_urls: ["https://images.unsplash.com/photo-custom-hotel"]
    };
    const adapted = adaptHotel(backendHotel, 7);
    assert.strictEqual(adapted.name, "Heritage Palace Resort");
    assert.strictEqual(adapted.totalPrice, 31500); // 4500 * 7
    assert.strictEqual(adapted.pricePerNight, 4500.0);
    assert.strictEqual(adapted.image, "https://images.unsplash.com/photo-custom-hotel");
  });

  test('adaptActivity determines rainSafe boolean and icons', () => {
    const indoorAct = {
      id: "act-1",
      name: "Rajasthani Cooking Workshop",
      category: "Food",
      price: 1500.0,
      location: "C-Scheme"
    };
    const outdoorAct = {
      id: "act-2",
      name: "Hot Air Balloon Safari",
      category: "Adventure",
      price: 6500.0,
      location: "Amer"
    };
    const adaptedIndoor = adaptActivity(indoorAct, 4, "11:00");
    const adaptedOutdoor = adaptActivity(outdoorAct, 3, "06:00");
    assert.strictEqual(adaptedIndoor.rainSafe, true);
    assert.strictEqual(adaptedOutdoor.rainSafe, false);
    assert.strictEqual(adaptedIndoor.place, "C-Scheme");
    assert.strictEqual(adaptedOutdoor.cost, 6500);
  });

  test('adaptFlight formats timestamps and codes', () => {
    const backendFlight = {
      id: "flight-1",
      origin: "DEL",
      destination: "JAI",
      airline: "IndiGo",
      flight_number: "6E-205",
      departure_time: "2026-03-15T08:20:00Z",
      arrival_time: "2026-03-15T09:15:00Z",
      duration_minutes: 55,
      price: 2800.0
    };
    const adapted = adaptFlight(backendFlight);
    assert.strictEqual(adapted.airline, "IndiGo");
    assert.strictEqual(adapted.price, 2800);
    assert.strictEqual(adapted.origin, "DEL");
    assert.strictEqual(adapted.destination, "JAI");
  });

  test('adaptWeather maps condition, humidity and precipitation signals', () => {
    const backendWeather = {
      latitude: 26.9124,
      longitude: 75.7873,
      temperature: 29.4,
      condition: "Clear sky",
      weather_code: 0,
      humidity: 38.0,
      wind_speed: 12.0
    };
    const adapted = adaptWeather(backendWeather);
    assert.strictEqual(adapted.temperature, 29);
    assert.strictEqual(adapted.condition, "Clear sky");
    assert.strictEqual(typeof adapted.rainChance, "string");
  });

  test('adaptExpenseBreakdown correctly maps backend categories to UI names', () => {
    const backendSummary = {
      Stay: 27000,
      Travel: 37000,
      Food: 8000,
      Activities: 12000,
      Transport: 8000
    };
    const breakdown = adaptExpenseBreakdown(backendSummary);
    assert.strictEqual(breakdown.length, 5);
    const hotels = breakdown.find(b => b.name === "Hotels");
    const flights = breakdown.find(b => b.name === "Flights");
    assert.strictEqual(hotels.value, 27000);
    assert.strictEqual(flights.value, 37000);
  });

  test('adaptDailyExpenses generates 7 day spend histogram', () => {
    const expenses = [
      { expense_date: "2026-03-15", amount: 1500 },
      { expense_date: "2026-03-16", amount: 2200 },
      { expense_date: "2026-03-17", amount: 4800 }
    ];
    const daily = adaptDailyExpenses(expenses, 7);
    assert.strictEqual(daily.length, 7);
    assert.strictEqual(daily[0].day, "D1");
    assert.strictEqual(daily[6].day, "D7");
  });

  console.log('\n--- 2. Testing API Services Interface & Signatures ---');

  test('All 7 API services export expected CRUD & query methods', () => {
    assert.strictEqual(typeof destinationApi.listDestinations, 'function');
    assert.strictEqual(typeof destinationApi.getDestinationById, 'function');
    assert.strictEqual(typeof hotelApi.listHotels, 'function');
    assert.strictEqual(typeof flightApi.listFlights, 'function');
    assert.strictEqual(typeof activityApi.listActivities, 'function');
    assert.strictEqual(typeof expenseApi.getExpenseSummary, 'function');
    assert.strictEqual(typeof expenseApi.listExpenses, 'function');
    assert.strictEqual(typeof weatherApi.getWeather, 'function');
    assert.strictEqual(typeof tripApi.createTripPlan, 'function');
  });

  console.log('\n====================================================');
  console.log(`Results: ${passed} Passed, ${failed} Failed`);
  console.log('====================================================');

  if (failed > 0) {
    process.exit(1);
  }
}

runTests().catch(err => {
  console.error('Fatal test runner error:', err);
  process.exit(1);
});
