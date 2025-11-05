import curl_cffi
import json
import argparse
import sys
import time
from concurrent.futures import ThreadPoolExecutor


def get_pricing_response(origin, destination, departure_date, search_type, proxy=None, max_retries=3):
    """Fetch pricing data from American Airlines API with retry logic"""
    if search_type == "award":
        udo = {}
        search_type_api = "Award"
        version = ""
    else:
        udo = {"search_method": "Lowest"}
        search_type_api = "Revenue"
        version = "cfr"

    json_data = {
        "metadata": {
            "selectedProducts": [],
            "tripType": "OneWay",
            "udo": udo,
        },
        "passengers": [
            {
                "type": "adult",
                "count": 1,
            },
        ],
        "requestHeader": {
            "clientId": "AAcom",
        },
        "slices": [
            {
                "allCarriers": True,
                "cabin": "",
                "departureDate": departure_date,
                "destination": destination,
                "destinationNearbyAirports": False,
                "maxStops": None,
                "origin": origin,
                "originNearbyAirports": False,
            },
        ],
        "tripOptions": {
            "corporateBooking": False,
            "fareType": "Lowest",
            "locale": "en_US",
            "pointOfSale": None,
            "searchType": search_type_api,
        },
        "loyaltyInfo": None,
        "version": version,
        "queryParams": {
            "sliceIndex": 0,
            "sessionId": "",
            "solutionSet": "",
            "solutionId": "",
            "sort": "CARRIER",
        },
    }

    kwargs = {
        "json": json_data,
        "impersonate": "chrome",
    }

    if proxy:
        kwargs["proxies"] = {"http": proxy, "https": proxy}

    for attempt in range(max_retries):
        try:
            response = curl_cffi.post(
                "https://www.aa.com/booking/api/search/itinerary", **kwargs
            )

            # Check for bot detection via status code or HTML response
            if response.status_code == 403 or response.text.strip().startswith("<"):
                print(f"{search_type.upper()} API blocked request - bot detection (attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                print(f"Status code: {response.status_code}", file=sys.stderr)
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Waiting {wait_time} seconds before retry...", file=sys.stderr)
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"{search_type.upper()} API continues to block after {max_retries} attempts", file=sys.stderr)
                    return {"error": "access blocked. try use proxy"}

            # Try to parse JSON
            try:
                response_json = response.json()
            except json.JSONDecodeError as e:
                print(f"{search_type.upper()} API returned non-JSON response (attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                print(f"Status code: {response.status_code}", file=sys.stderr)
                print(f"Response preview: {response.text[:200]}", file=sys.stderr)
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"Waiting {wait_time} seconds before retry...", file=sys.stderr)
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"{search_type.upper()} API continues to return non-JSON after {max_retries} attempts", file=sys.stderr)
                    return {"error": "access blocked. try use proxy"}

            # Check if response is a challenge (bot detection)
            if response_json.get("cpr_chlge") == "true":
                print(f"{search_type.upper()} API returned challenge response (attempt {attempt + 1}/{max_retries})", file=sys.stderr)
                if attempt < max_retries - 1:
                    # Wait before retrying (exponential backoff)
                    wait_time = 2 ** attempt
                    print(f"Waiting {wait_time} seconds before retry...", file=sys.stderr)
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"{search_type.upper()} API challenge persists after {max_retries} attempts", file=sys.stderr)
                    return {"error": "access blocked. try use proxy"}

            # Success - return the response
            return response_json

        except Exception as e:
            # Catch any other errors (network issues, connection errors, etc.)
            print(f"Error on attempt {attempt + 1}/{max_retries}: {str(e)}", file=sys.stderr)
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Waiting {wait_time} seconds before retry...", file=sys.stderr)
                time.sleep(wait_time)
                continue
            else:
                print(f"All retry attempts failed with error: {str(e)}", file=sys.stderr)
                return {"error": "access blocked. try use proxy"}


def parse_segment(segment):
    """Parse a flight segment to extract key information"""
    flight = segment.get("flight", {})
    legs = segment.get("legs", [])

    if not legs:
        return None

    first_leg = legs[0]
    last_leg = legs[-1]

    return {
        "flight_number": f"{flight.get('carrierCode', '')}{flight.get('flightNumber', '')}",
        "departure_time": (
            first_leg.get("departureDateTime", "").split("T")[1][:5]
            if "T" in first_leg.get("departureDateTime", "")
            else ""
        ),
        "arrival_time": (
            last_leg.get("arrivalDateTime", "").split("T")[1][:5]
            if "T" in last_leg.get("arrivalDateTime", "")
            else ""
        ),
    }


def format_duration(minutes):
    """Convert minutes to human-readable format"""
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m"


def parse_slice(slice_data):
    """Parse a slice (flight option) from the API response"""
    segments_data = slice_data.get("segments", [])
    pricing_detail = slice_data.get("pricingDetail", [])

    # Only accept COACH product type (economy class)
    cabin_pricing = None
    for pricing in pricing_detail:
        if pricing.get("productType") == "COACH":
            cabin_pricing = pricing
            break

    if not cabin_pricing:
        return None

    # Verify all segments are economy (COACH cabin)
    for seg in segments_data:
        legs = seg.get("legs", [])
        for leg in legs:
            product_details = leg.get("productDetails", [])
            # Check if any product detail has COACH cabin type
            has_coach_cabin = False
            for product in product_details:
                if (
                    product.get("cabinType") == "COACH"
                    and product.get("productType") == "COACH"
                ):
                    has_coach_cabin = True
                    break
            if not has_coach_cabin:
                return None

    # Parse segments
    segments = []
    for seg in segments_data:
        parsed_seg = parse_segment(seg)
        if parsed_seg:
            segments.append(parsed_seg)

    if not segments:
        return None

    is_nonstop = len(segments) == 1
    duration = slice_data.get("durationInMinutes", 0)

    return {
        "is_nonstop": is_nonstop,
        "segments": segments,
        "total_duration": format_duration(duration),
        "pricing": cabin_pricing,
        "slice_data": slice_data,
    }


def create_flight_key(segments):
    """Create a unique key for matching flights across award and revenue pricing"""
    return "_".join([f"{s['flight_number']}_{s['departure_time']}" for s in segments])


def calculate_cpp(cash_price, taxes_fees, points):
    """Calculate cents per point (CPP)"""
    if points == 0:
        return 0.0
    return round((cash_price - taxes_fees) / points * 100, 2)


def merge_pricing_data(award_response, revenue_response):
    """Merge award and revenue pricing data to calculate CPP (COACH economy only)"""
    # Check for errors in responses
    if "error" in award_response:
        return {"error": award_response["error"]}
    if "error" in revenue_response:
        return {"error": revenue_response["error"]}

    flights_map = {}

    # Process award pricing (COACH economy only)
    award_slices = award_response.get("slices", [])
    for slice_data in award_slices:
        parsed = parse_slice(slice_data)
        if not parsed:
            continue

        key = create_flight_key(parsed["segments"])

        pricing = parsed["pricing"]
        points = pricing.get("perPassengerAwardPoints", 0)
        taxes_fees = pricing.get("perPassengerTaxesAndFees", {}).get("amount", 0)

        flights_map[key] = {
            "is_nonstop": parsed["is_nonstop"],
            "segments": parsed["segments"],
            "total_duration": parsed["total_duration"],
            "points_required": points,
            "taxes_fees_usd": taxes_fees,
            "cash_price_usd": None,
        }

    # Process revenue pricing and merge (COACH economy only)
    revenue_slices = revenue_response.get("slices", [])
    for slice_data in revenue_slices:
        parsed = parse_slice(slice_data)
        if not parsed:
            continue

        key = create_flight_key(parsed["segments"])

        pricing = parsed["pricing"]
        cash_price = pricing.get("allPassengerDisplayTotal", {}).get("amount", 0)

        if key in flights_map:
            flights_map[key]["cash_price_usd"] = cash_price

    # Calculate CPP and filter flights with both prices
    results = []
    for flight in flights_map.values():
        if flight["cash_price_usd"] is not None and flight["points_required"] > 0:
            flight["cpp"] = calculate_cpp(
                flight["cash_price_usd"],
                flight["taxes_fees_usd"],
                flight["points_required"],
            )
            results.append(flight)

    return results


def generate_output(origin, destination, date, passengers, flights):
    """Generate the final JSON output"""
    # Check if flights contains an error
    if isinstance(flights, dict) and "error" in flights:
        return {
            "search_metadata": {
                "origin": origin,
                "destination": destination,
                "date": date,
                "passengers": passengers,
                "cabin_class": "economy",
            },
            "error": flights["error"],
            "flights": [],
            "total_results": 0,
        }

    return {
        "search_metadata": {
            "origin": origin,
            "destination": destination,
            "date": date,
            "passengers": passengers,
            "cabin_class": "economy",
        },
        "flights": flights,
        "total_results": len(flights),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Scrape American Airlines flight pricing and calculate CPP (Economy/COACH only)"
    )
    parser.add_argument(
        "--origin", required=True, help="Origin airport code (e.g., LAX, SFO, ORD)"
    )
    parser.add_argument(
        "--destination",
        required=True,
        help="Destination airport code (e.g., JFK, BOS, MIA)",
    )
    parser.add_argument(
        "--date", required=True, help="Departure date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--passengers", type=int, required=True, help="Number of passengers"
    )
    parser.add_argument(
        "--class",
        dest="cabin_class",
        required=True,
        choices=["economy"],
        help="Cabin class (only 'economy' is supported)",
    )
    parser.add_argument(
        "--output",
        help="Output file path (optional - if not provided, prints to stdout)",
    )
    parser.add_argument("--proxy", help="Proxy URL (e.g., http://user:pass@host:port)")
    parser.add_argument(
        "--save-responses",
        action="store_true",
        help="Save raw API responses to files (award_response.json and revenue_response.json)",
    )

    args = parser.parse_args()

    # Run both API requests in parallel (like Promise.all in JavaScript)
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Submit both requests
        award_future = executor.submit(
            get_pricing_response,
            args.origin,
            args.destination,
            args.date,
            "award",
            args.proxy,
            5,
        )
        revenue_future = executor.submit(
            get_pricing_response,
            args.origin,
            args.destination,
            args.date,
            "revenue",
            args.proxy,
            5,
        )

        # Wait for both to complete
        award_response = award_future.result()
        revenue_response = revenue_future.result()

    # Save API responses if requested
    if args.save_responses:
        with open("award_response.json", "w") as f:
            json.dump(award_response, f, indent=2)
        with open("revenue_response.json", "w") as f:
            json.dump(revenue_response, f, indent=2)
        print(
            "API responses saved to award_response.json and revenue_response.json",
            file=sys.stderr,
        )

    # Merge and calculate CPP (COACH economy only)
    flights = merge_pricing_data(award_response, revenue_response)

    # Generate output
    output = generate_output(
        args.origin, args.destination, args.date, args.passengers, flights
    )

    # Save or print output
    if args.output:
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"Results saved to {args.output}")
    else:
        # Print JSON to stdout
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
