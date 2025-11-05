# American Airlines CPP Calculator

A scraper that fetches both award and cash pricing from American Airlines and calculates the Cents Per Point (CPP) value for each flight.

## Features

- Fetches award pricing (points + taxes) for economy/MAIN class only
- Fetches cash pricing (USD) for economy/MAIN class only
- Calculates CPP: `(Cash Price - Taxes) / Points × 100`
- Strict filtering: Only includes flights with MAIN product type
- Supports proxy configuration
- Outputs structured JSON data (to file or stdout)
- Docker support for easy deployment

## Installation

### Local Installation

```bash
pip install -r requirements.txt
```

### Docker

Build the image:

```bash
docker build -t aa-scraper:latest .
```

## Usage

### Local Usage

Basic usage (prints to stdout):

```bash
python scrape.py \
  --origin LAX \
  --destination JFK \
  --date 2025-12-15 \
  --passengers 1 \
  --class economy
```

Save to file:

```bash
python scrape.py \
  --origin LAX \
  --destination JFK \
  --date 2025-12-15 \
  --passengers 1 \
  --class economy \
  --output results.json
```

Another example:

```bash
python scrape.py \
  --origin SFO \
  --destination BOS \
  --date 2025-12-20 \
  --passengers 1 \
  --class economy \
  --output sfo-bos.json
```

With proxy:

```bash
python scrape.py \
  --origin LAX \
  --destination JFK \
  --date 2025-12-15 \
  --passengers 1 \
  --class economy \
  --proxy http://user:pass@proxy.com:8080 \
  --output results.json
```

Debug mode (save raw API responses):

```bash
python scrape.py \
  --origin LAX \
  --destination JFK \
  --date 2025-12-15 \
  --passengers 1 \
  --class economy \
  --save-responses
```

This will save `award_response.json` and `revenue_response.json` to the current directory for debugging purposes.

### Docker Usage

Basic usage (prints to stdout):

```bash
docker run --rm aa-scraper:latest \
  --origin LAX \
  --destination JFK \
  --date 2025-12-15 \
  --passengers 1 \
  --class economy
```

Save to file:

```bash
docker run --rm -v $(pwd)/output:/output aa-scraper:latest \
  --origin LAX \
  --destination JFK \
  --date 2025-12-15 \
  --passengers 1 \
  --class economy \
  --output /output/results.json
```

With proxy:

```bash
docker run --rm -v $(pwd)/output:/output aa-scraper:latest \
  --origin LAX \
  --destination JFK \
  --date 2025-12-15 \
  --passengers 1 \
  --class economy \
  --proxy http://proxy:8080 \
  --output /output/results.json
```

## Command Line Arguments

| Argument           | Required | Description                                                      |
| ------------------ | -------- | ---------------------------------------------------------------- |
| `--origin`         | **Yes**  | Origin airport code (e.g., LAX, SFO, ORD)                        |
| `--destination`    | **Yes**  | Destination airport code (e.g., JFK, BOS, MIA)                   |
| `--date`           | **Yes**  | Departure date in YYYY-MM-DD format                              |
| `--passengers`     | **Yes**  | Number of passengers                                             |
| `--class`          | **Yes**  | Cabin class (must be "economy")                                  |
| `--output`         | No       | Output file path - if not provided, prints to stdout             |
| `--proxy`          | No       | Proxy URL (e.g., http://user:pass@host:port)                     |
| `--save-responses` | No       | Save raw API responses (award_response.json, revenue_response.json) for debugging |

**Notes:**

- The `--class` parameter must be set to "economy". Only economy class (MAIN) flights are supported.
- If `--output` is not provided, the JSON result will be printed to stdout (useful for piping to other commands)

## Output Format

```json
{
  "search_metadata": {
    "origin": "LAX",
    "destination": "JFK",
    "date": "2025-12-15",
    "passengers": 1,
    "cabin_class": "economy"
  },
  "flights": [
    {
      "is_nonstop": true,
      "segments": [
        {
          "flight_number": "AA123",
          "departure_time": "08:00",
          "arrival_time": "16:30"
        }
      ],
      "total_duration": "5h 30m",
      "points_required": 12500,
      "cash_price_usd": 289.0,
      "taxes_fees_usd": 5.6,
      "cpp": 2.27
    }
  ],
  "total_results": 1
}
```

## CPP Calculation

The Cents Per Point (CPP) is calculated using the formula:

```
CPP = (Cash Price - Taxes & Fees) / Points Required × 100
```

**Example:**

- Cash Price: $289.00
- Taxes & Fees: $5.60
- Points Required: 12,500

```
CPP = ($289.00 - $5.60) / 12,500 × 100 = 2.27
```

This means each point is worth 2.27 cents when booking this flight.

## Proxy Support

The scraper supports proxy configuration via command line argument:

```bash
python scrape.py \
  --origin LAX \
  --destination JFK \
  --date 2025-12-15 \
  --passengers 1 \
  --class economy \
  --proxy http://proxy:8080
```

## Docker Compose

Run with docker-compose:

```bash
docker-compose up
```

To use a proxy, edit the `command` section in `docker-compose.yml` and add:

```yaml
command: >
  --origin LAX
  --destination JFK
  --date 2025-12-15
  --passengers 1
  --class economy
  --proxy http://proxy:8080
```

## Notes

- **Economy/MAIN Only**: This scraper only retrieves and processes economy class (MAIN product type) flights
- The scraper matches flights between award and revenue searches by flight number and departure time
- Only flights that appear in both searches (with valid pricing) are included in the output
- Flights must have both MAIN product type AND MAIN cabin type to be included
- CPP values help determine if booking with points provides good value compared to cash
- Generally, a CPP of 1.5+ is considered good value for economy class
