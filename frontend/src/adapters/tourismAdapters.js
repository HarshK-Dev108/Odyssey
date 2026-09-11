/**
 * Data contract adapters between backend Tourism Data Layer and frontend UI models.
 */

const DEFAULT_DESTINATION_IMAGES = [
  "https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=900&h=650&fit=crop", // Goa
  "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=900&h=650&fit=crop", // Manali
  "https://images.unsplash.com/photo-1477587458883-47145ed94245?w=900&h=650&fit=crop", // Jaipur
  "https://images.unsplash.com/photo-1602216056096-3b40cc0c9944?w=900&h=650&fit=crop", // Kerala
  "https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=900&h=650&fit=crop", // Amritsar / Luxury
  "https://images.unsplash.com/photo-1570168007204-dfb528c6958f?w=900&h=650&fit=crop", // Varanasi
];

/**
 * Normalizes a backend DestinationResponse into the frontend Discover card format.
 * @param {Object} item - DestinationResponse from backend
 * @param {number} index
 * @returns {Object}
 */
export function adaptDestination(item, index = 0) {
  const fallbackPrices = [8900, 7400, 6200, 9800, 5400, 4900];
  const fallbackRatings = [4.8, 4.9, 4.8, 4.9, 4.7, 4.8];
  
  return {
    id: item.id || `dest-${index}`,
    name: item.name || 'Featured Destination',
    country: item.country || 'India',
    state: item.state || '',
    city: item.city || '',
    tag: (Array.isArray(item.tags) && item.tags.length > 0)
      ? item.tags.slice(0, 2).join(' · ')
      : (item.city || item.country || 'Scenic escape'),
    tags: item.tags || [],
    price: item.starting_price || fallbackPrices[index % fallbackPrices.length],
    rating: item.rating || fallbackRatings[index % fallbackRatings.length],
    image: item.image_url && !item.image_url.includes('example') && item.image_url.startsWith('http') && !item.image_url.endsWith('photo-jaipur') && !item.image_url.endsWith('photo-amritsar') && !item.image_url.endsWith('photo-goa') && !item.image_url.endsWith('photo-manali')
      ? item.image_url
      : DEFAULT_DESTINATION_IMAGES[index % DEFAULT_DESTINATION_IMAGES.length],
    latitude: item.latitude || 26.9124,
    longitude: item.longitude || 75.7873,
    description: item.description || '',
    bestTimeToVisit: item.best_time_to_visit || 'Year-round',
  };
}

/**
 * Normalizes a backend HotelResponse into the frontend Hotel card format.
 * @param {Object} item - HotelResponse from backend
 * @param {number} [nights=7]
 * @returns {Object}
 */
export function adaptHotel(item, nights = 7) {
  const perNight = item.price_per_night || 3800;
  return {
    id: item.id,
    destinationId: item.destination_id,
    name: item.name || 'Featured Hotel',
    description: item.description || '',
    address: item.address || 'Prime City Location',
    rating: item.rating || 4.7,
    pricePerNight: perNight,
    totalPrice: Math.round(perNight * nights),
    currency: item.currency || 'INR',
    amenities: item.amenities || ['WiFi', 'Breakfast', 'Air Conditioning'],
    image: (Array.isArray(item.image_urls) && item.image_urls.length > 0 && !item.image_urls[0].includes('photo-hotel'))
      ? item.image_urls[0]
      : 'https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=600&h=450&fit=crop',
    availableRooms: item.available_rooms || 5,
  };
}

/**
 * Normalizes a backend ActivityResponse into the frontend experience / timeline format.
 * @param {Object} item - ActivityResponse from backend
 * @param {number} [day=2]
 * @param {string} [time='10:00']
 * @returns {Object}
 */
export function adaptActivity(item, day = 2, time = '10:00') {
  const indoorCategories = ['Food', 'Heritage', 'Culture', 'Wellness', 'Shopping', 'Cooking'];
  const isRainSafe = indoorCategories.some(cat => 
    (item.category || '').toLowerCase().includes(cat.toLowerCase())
  );

  return {
    id: item.id,
    destinationId: item.destination_id,
    day,
    time,
    title: item.name || 'Curated Experience',
    place: item.location || 'City Center',
    cost: Math.round(item.price || 1200),
    currency: item.currency || 'INR',
    category: item.category || 'Sightseeing',
    rating: item.rating || 4.8,
    durationMinutes: item.duration_minutes || 120,
    rainSafe: isRainSafe,
    icon: isRainSafe ? '👩‍🍳' : (item.category?.includes('Adventure') ? '🌊' : '🏛️'),
    image: item.image_url || '',
  };
}

/**
 * Normalizes a backend FlightResponse into the frontend flight schedule format.
 * @param {Object} item - FlightResponse from backend
 * @returns {Object}
 */
export function adaptFlight(item) {
  const formatTime = (isoString, defaultTime) => {
    if (!isoString) return defaultTime;
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', hour12: false });
    } catch {
      return defaultTime;
    }
  };

  return {
    id: item.id,
    origin: item.origin || 'DEL',
    destination: item.destination || 'JAI',
    airline: item.airline || 'IndiGo',
    flightNumber: item.flight_number || '6E-101',
    departureTime: formatTime(item.departure_time, '08:20'),
    arrivalTime: formatTime(item.arrival_time, '10:00'),
    durationMinutes: item.duration_minutes || 100,
    price: Math.round(item.price || 3500),
    currency: item.currency || 'INR',
    stops: item.stops || 0,
    availableSeats: item.available_seats || 12,
  };
}

/**
 * Normalizes a backend WeatherResponse into the frontend weather format.
 * @param {Object} item - WeatherResponse from backend
 * @returns {Object}
 */
export function adaptWeather(item) {
  const temp = Math.round(item.temperature || 28);
  const condition = item.condition || 'Sunny';
  const humidity = item.humidity || 45;
  const isRain = (item.weather_code && item.weather_code >= 50) || condition.toLowerCase().includes('rain');
  
  return {
    temperature: temp,
    condition,
    humidity,
    windSpeed: Math.round(item.wind_speed || 10),
    unit: item.unit || 'Celsius',
    rainChance: isRain ? '75%' : `${Math.min(Math.round(humidity * 0.4), 30)}%`,
    crowd: 'Moderate',
    displayString: `${temp}°C · ${condition}`,
  };
}

/**
 * Maps category names between backend conventions (Stay, Travel, Food, etc.) and UI names.
 * @param {Record<string, number>} byCategory
 * @returns {Array<{ name: string, value: number, key: string }>}
 */
export function adaptExpenseBreakdown(byCategory = {}) {
  const categoryMap = [
    { key: 'Travel', name: 'Flights', defaultValue: 37000 },
    { key: 'Stay', name: 'Hotels', defaultValue: 27000 },
    { key: 'Transport', name: 'Transport', defaultValue: 8000 },
    { key: 'Activities', name: 'Activities', defaultValue: 12000 },
    { key: 'Food', name: 'Food', defaultValue: 8000 },
  ];

  return categoryMap.map(cat => {
    const val = byCategory[cat.key] !== undefined 
      ? Math.round(byCategory[cat.key]) 
      : cat.defaultValue;
    return {
      key: cat.key,
      name: cat.name,
      value: val,
    };
  });
}

/**
 * Aggregates a list of expense records into 7 daily spending buckets for Recharts.
 * @param {Array} expenseItems
 * @param {number} [totalDays=7]
 * @returns {Array<{ day: string, spend: number }>}
 */
export function adaptDailyExpenses(expenseItems = [], totalDays = 7) {
  if (!Array.isArray(expenseItems) || expenseItems.length === 0) {
    // Default fallback curve matching planned budget
    return [
      { day: "D1", spend: 21700 },
      { day: "D2", spend: 3400 },
      { day: "D3", spend: 5200 },
      { day: "D4", spend: 3500 },
      { day: "D5", spend: 2100 },
      { day: "D6", spend: 2800 },
      { day: "D7", spend: 18500 },
    ];
  }

  const buckets = Array.from({ length: totalDays }, (_, i) => ({
    day: `D${i + 1}`,
    spend: 0,
  }));

  expenseItems.forEach(exp => {
    const expDate = new Date(exp.expense_date);
    const dayIndex = isNaN(expDate.getTime()) ? 0 : (expDate.getDate() % totalDays);
    buckets[dayIndex].spend += Math.round(exp.amount || 0);
  });

  return buckets;
}
