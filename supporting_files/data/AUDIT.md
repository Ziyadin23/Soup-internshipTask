# Reference audit: review before training

Check query/tool compatibility, required values, ambiguity, and reference correctness. Record exclusions before freezing a new run; never repair labels after inspecting predictions.

## Source 38047

```json
{
  "id": "38047",
  "query": "I'm looking for the best match listings of condominiums and townhouses in Lake Worth with a maximum price of $450,000. I want to see the first 15 results.",
  "tools": [
    {
      "name": "getlistings",
      "description": "Retrieve a list of condominiums and townhouses in specified cities of Southwest Florida and the East Coast.",
      "parameters": {
        "sort": {
          "description": "Defines how the listings should be sorted. Supported values are 'RELEVANCE' (best match), 'NEWEST' (newest first), 'PRICE_LOW' (cheapest first), and 'PRICE_HIGH' (most expensive first). Default is 'RELEVANCE'.",
          "type": "str",
          "default": "RELEVANCE"
        },
        "offset": {
          "description": "For pagination. Specifies the starting point in the collection of listings. For example, to get the first set of items, set offset to 0. Default is 0.",
          "type": "int",
          "default": "0"
        },
        "price_max": {
          "description": "The maximum price in US dollars for the condos and townhouses. Default is 250,000.",
          "type": "int",
          "default": "250000"
        },
        "city": {
          "description": "The name of the city to search within. Supported cities include Cape Coral, Fort Myers, West Palm Beach, Lake Worth, Lantana, Boynton Beach, Delray Beach, Boca Raton, Pompano Beach, Fort Lauderdale, Naples, Tampa, and Saint Petersburg. Default is 'Cape Coral'.",
          "type": "str",
          "default": "Cape Coral"
        },
        "limit": {
          "description": "The maximum number of items to return. Default is 50.",
          "type": "int",
          "default": "50"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "getlistings",
      "arguments": {
        "sort": "RELEVANCE",
        "price_max": 450000,
        "city": "Lake Worth",
        "limit": 15
      }
    }
  ],
  "family": "getlistings",
  "rendered_tokens": 522,
  "supervised_tokens": 38
}
```

## Source 57030

```json
{
  "id": "57030",
  "query": "Obtain details for the pincode 920001, which is located in Faridabad.",
  "tools": [
    {
      "name": "findbypincode",
      "description": "Fetches information for a given Indian pincode using the Toolbench RapidAPI.",
      "parameters": {
        "pincode": {
          "description": "The pincode for which information needs to be fetched.",
          "type": "int",
          "default": 518345
        }
      }
    }
  ],
  "answers": [
    {
      "name": "findbypincode",
      "arguments": {
        "pincode": 920001
      }
    }
  ],
  "family": "findbypincode",
  "rendered_tokens": 223,
  "supervised_tokens": 24
}
```

## Source 30665

```json
{
  "id": "30665",
  "query": "Is the Riverside Hotel in Bangkok available for a stay from 2023-06-03 to 2023-06-10?",
  "tools": [
    {
      "name": "is_hotel_available",
      "description": "Checks the availability of a hotel for a given date range.",
      "parameters": {
        "hotel": {
          "description": "The name of the hotel.",
          "type": "str"
        },
        "city": {
          "description": "The city where the hotel is located.",
          "type": "str"
        },
        "checkin": {
          "description": "The check-in date in the format \"YYYY-MM-DD\".",
          "type": "str"
        },
        "checkout": {
          "description": "The check-out date in the format \"YYYY-MM-DD\".",
          "type": "str"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "is_hotel_available",
      "arguments": {
        "hotel": "Riverside Hotel",
        "city": "Bangkok",
        "checkin": "2023-06-03",
        "checkout": "2023-06-10"
      }
    }
  ],
  "family": "is_hotel_available",
  "rendered_tokens": 315,
  "supervised_tokens": 52
}
```

## Source 55783

```json
{
  "id": "55783",
  "query": "Who was the runner-up team in the NCAA Final Four in the year 2000?",
  "tools": [
    {
      "name": "runner_up",
      "description": "Fetches the runner-up team data for the given identifying parameter from the NCAA Final Four API.",
      "parameters": {
        "identifier": {
          "description": "The identifier (e.g., year) to fetch the runner-up team data for.",
          "type": "str",
          "default": "1959"
        }
      }
    },
    {
      "name": "basketball_search",
      "description": "Search for basketball players, teams, and tournaments using the provided term.",
      "parameters": {
        "term": {
          "description": "The search term used to look for players, teams, and tournaments.",
          "type": "str",
          "default": "kevin"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "runner_up",
      "arguments": {
        "identifier": "2000"
      }
    }
  ],
  "family": "runner_up",
  "rendered_tokens": 281,
  "supervised_tokens": 18
}
```

## Source 29212

```json
{
  "id": "29212",
  "query": "Fetch the spreadsheet with sales data for last month, located at /data/sales_data_august.xlsx.",
  "tools": [
    {
      "name": "retrieve_file",
      "description": "Retrieves a file from the server using the provided file path and API key.",
      "parameters": {
        "path": {
          "description": "The path of the file to be retrieved. This path is typically obtained by replacing the /p/ path in the /merge and /edit endpoint responses with /f/ or /d/.",
          "type": "str",
          "default": "ABCDEF"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "retrieve_file",
      "arguments": {
        "path": "/data/sales_data_august.xlsx"
      }
    }
  ],
  "family": "retrieve_file",
  "rendered_tokens": 239,
  "supervised_tokens": 21
}
```

## Source 45420

```json
{
  "id": "45420",
  "query": "Calculate the area of a circle with a radius of 7.5 units.",
  "tools": [
    {
      "name": "least_common_multiple",
      "description": "Computes the least common multiple (LCM) of two positive integers.",
      "parameters": {
        "a": {
          "description": "The first positive integer.",
          "type": "int"
        },
        "b": {
          "description": "The second positive integer.",
          "type": "int"
        }
      }
    },
    {
      "name": "circle_area",
      "description": "Computes the area of a circle given its radius.",
      "parameters": {
        "radius": {
          "description": "The radius of the circle.",
          "type": "float"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "circle_area",
      "arguments": {
        "radius": 7.5
      }
    }
  ],
  "family": "circle_area",
  "rendered_tokens": 251,
  "supervised_tokens": 17
}
```

## Source 53128

```json
{
  "id": "53128",
  "query": "What is the result of incrementing the number 100 by one?",
  "tools": [
    {
      "name": "get_plus_one",
      "description": "This function takes an integer `number` and uses the RapidAPI service to get the number incremented by one.",
      "parameters": {
        "number": {
          "description": "The integer to be incremented.",
          "type": "int",
          "default": "15"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "get_plus_one",
      "arguments": {
        "number": 100
      }
    }
  ],
  "family": "get_plus_one",
  "rendered_tokens": 204,
  "supervised_tokens": 18
}
```

## Source 22164

```json
{
  "id": "22164",
  "query": "How can I get a list of cat breeds ordered by their origin country in ascending order?",
  "tools": [
    {
      "name": "airplanes_by_brand",
      "description": "Fetches all airplanes by a specified brand from the airplanes database.",
      "parameters": {
        "brand": {
          "description": "The brand of airplanes to fetch information for.",
          "type": "str",
          "default": "Airbus"
        }
      }
    },
    {
      "name": "order_by_ascending",
      "description": "Fetches a list of all cats sorted in ascending order by a specified attribute.",
      "parameters": {
        "ordering": {
          "description": "The attribute by which to order the list of cats, e.g., 'name'.",
          "type": "str",
          "default": "breedName"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "order_by_ascending",
      "arguments": {
        "ordering": "origin"
      }
    }
  ],
  "family": "order_by_ascending",
  "rendered_tokens": 272,
  "supervised_tokens": 17
}
```

## Source 51602

```json
{
  "id": "51602",
  "query": "Does the following paragraph contain any profanity: 'This is a longer test. It should not contain any profanity, but let's see what the system says.'",
  "tools": [
    {
      "name": "dns",
      "description": "Fetches DNS records for a given domain using the RapidAPI domain checker service.",
      "parameters": {
        "domain": {
          "description": "The domain for which DNS records are to be retrieved.",
          "type": "str",
          "default": "rapidapi.com"
        }
      }
    },
    {
      "name": "check_if_text_contains_profanity",
      "description": "Check if a given text contains profanity using the Purgomalum API.",
      "parameters": {
        "text": {
          "description": "The text to be checked for profanity.",
          "type": "str",
          "default": "This is some test input"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "check_if_text_contains_profanity",
      "arguments": {
        "text": "This is a longer test. It should not contain any profanity, but let's see what the system says."
      }
    }
  ],
  "family": "check_if_text_contains_profanity",
  "rendered_tokens": 311,
  "supervised_tokens": 42
}
```

## Source 44119

```json
{
  "id": "44119",
  "query": "Get information about the Indian pincode 500001 in Hyderabad, including its taluk and circle.",
  "tools": [
    {
      "name": "findbypincode",
      "description": "Fetches information for a given Indian pincode using the Toolbench RapidAPI.",
      "parameters": {
        "pincode": {
          "description": "The pincode for which information needs to be fetched.",
          "type": "int",
          "default": 518345
        }
      }
    }
  ],
  "answers": [
    {
      "name": "findbypincode",
      "arguments": {
        "pincode": 500001
      }
    }
  ],
  "family": "findbypincode",
  "rendered_tokens": 224,
  "supervised_tokens": 24
}
```

## Source 46843

```json
{
  "id": "46843",
  "query": "Find out the WHOIS information for google.com.",
  "tools": [
    {
      "name": "v1_whois",
      "description": "Fetches the WHOIS information for a given domain using the API Ninjas Whois API.",
      "parameters": {
        "domain": {
          "description": "The domain to retrieve WHOIS information for.",
          "type": "str",
          "default": "example.com"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "v1_whois",
      "arguments": {
        "domain": "google.com"
      }
    }
  ],
  "family": "v1_whois",
  "rendered_tokens": 201,
  "supervised_tokens": 19
}
```

## Source 14004

```json
{
  "id": "14004",
  "query": "Is 54748 a number that can be expressed as the sum of the cubes of its digits?",
  "tools": [
    {
      "name": "is_sum_of_cubes",
      "description": "Checks if a number is the sum of the cubes of its digits.",
      "parameters": {
        "num": {
          "description": "The number to check.",
          "type": "int"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "is_sum_of_cubes",
      "arguments": {
        "num": 54748
      }
    }
  ],
  "family": "is_sum_of_cubes",
  "rendered_tokens": 201,
  "supervised_tokens": 22
}
```

## Source 39582

```json
{
  "id": "39582",
  "query": "Retrieve the monthly data and search count for the keyword 'climate change' from the Targeted Keyword Trend API.",
  "tools": [
    {
      "name": "keyword",
      "description": "Retrieves \u201cMonthly Data\u201d and \u201cSearch count\u201d for a given keyword from the Targeted Keyword Trend API.",
      "parameters": {
        "keyword": {
          "description": "The keyword to search data for.",
          "type": "str",
          "default": "digital marketing"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "keyword",
      "arguments": {
        "keyword": "climate change"
      }
    }
  ],
  "family": "keyword",
  "rendered_tokens": 208,
  "supervised_tokens": 15
}
```

## Source 5301

```json
{
  "id": "5301",
  "query": "Identify the car model and engine type for a vehicle with VIN 'ABC123DEF456GHI789'.",
  "tools": [
    {
      "name": "vin_decoder",
      "description": "Decodes a given VIN (Vehicle Identification Number) for a vehicle manufactured in Europe to retrieve information such as car model, maker, year, engine, and other relevant details.",
      "parameters": {
        "vin": {
          "description": "The VIN number to be decoded.",
          "type": "str",
          "default": "VF3CA5FU8DW062146"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "vin_decoder",
      "arguments": {
        "vin": "ABC123DEF456GHI789"
      }
    }
  ],
  "family": "vin_decoder",
  "rendered_tokens": 249,
  "supervised_tokens": 27
}
```

## Source 32778

```json
{
  "id": "32778",
  "query": "What is the quote with ID 13579 from the movie and TV shows quotes database?",
  "tools": [
    {
      "name": "get_individual_quotes_by_quote_id",
      "description": "Fetches individual quotes based on the given quote ID.",
      "parameters": {
        "is_id": {
          "description": "The ID of the quote to be retrieved.",
          "type": "int",
          "default": "4"
        }
      }
    },
    {
      "name": "get_one_anime_by_ranking",
      "description": "Fetches the details of an anime based on its ranking from the Anime DB API.",
      "parameters": {
        "rank": {
          "description": "The ranking position of the desired anime.",
          "type": "int",
          "default": "1"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "get_individual_quotes_by_quote_id",
      "arguments": {
        "is_id": 13579
      }
    }
  ],
  "family": "get_individual_quotes_by_quote_id",
  "rendered_tokens": 274,
  "supervised_tokens": 24
}
```

## Source 45599

```json
{
  "id": "45599",
  "query": "Retrieve crime data for the ZIP code 10001.",
  "tools": [
    {
      "name": "get_crime_rates_by_zip",
      "description": "Retrieve crime statistics for a given ZIP code using the Crime Data by Zipcode API.",
      "parameters": {
        "zip": {
          "description": "ZIP code to retrieve crime data for.",
          "type": "int",
          "default": "94109"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "get_crime_rates_by_zip",
      "arguments": {
        "zip": 10001
      }
    }
  ],
  "family": "get_crime_rates_by_zip",
  "rendered_tokens": 210,
  "supervised_tokens": 23
}
```

## Source 21959

```json
{
  "id": "21959",
  "query": "Provide information about the session 'GHI012' from the AI summit.",
  "tools": [
    {
      "name": "get_session_info",
      "description": "Fetches session information using the provided session ID and RapidAPI key.",
      "parameters": {
        "session_id": {
          "description": "The unique identifier for the session.",
          "type": "str",
          "default": "1685369452715x643061726475037300"
        }
      }
    },
    {
      "name": "dev_to",
      "description": "Checks the availability of a given username on Dev.to using the Toolbench RapidAPI service.",
      "parameters": {
        "username": {
          "description": "The username to check for availability on Dev.to.",
          "type": "str",
          "default": "username"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "get_session_info",
      "arguments": {
        "session_id": "GHI012"
      }
    }
  ],
  "family": "get_session_info",
  "rendered_tokens": 294,
  "supervised_tokens": 21
}
```

## Source 43128

```json
{
  "id": "43128",
  "query": "What is the frequency of each word in the long text 'Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed nec justo lacus. Sed in malesuada erat. Sed mollis, est et pellentesque gravida, dolor elit rhoncus justo, ut faucibus orci neque non ante. Sed id lectus lorem. Nulla facilisi.'?",
  "tools": [
    {
      "name": "calculate_age",
      "description": "Calculates the age based on the birthdate.",
      "parameters": {
        "birthdate": {
          "description": "The birthdate in the format 'YYYY-MM-DD'.",
          "type": "str"
        }
      }
    },
    {
      "name": "word_frequency",
      "description": "Calculates the frequency of each word in a text.",
      "parameters": {
        "text": {
          "description": "The input text.",
          "type": "str"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "word_frequency",
      "arguments": {
        "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed nec justo lacus. Sed in malesuada erat. Sed mollis, est et pellentesque gravida, dolor elit rhoncus justo, ut faucibus orci neque non ante. Sed id lectus lorem. Nulla facilisi."
      }
    }
  ],
  "family": "word_frequency",
  "rendered_tokens": 354,
  "supervised_tokens": 78
}
```

## Source 27187

```json
{
  "id": "27187",
  "query": "What are the details of the credit card associated with ID 24680?",
  "tools": [
    {
      "name": "random_credit_card_by_id",
      "description": "Retrieve fake credit card details by ID using the RapidAPI service.",
      "parameters": {
        "is_id": {
          "description": "The ID used to retrieve the fake credit card details.",
          "type": "int",
          "default": "1"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "random_credit_card_by_id",
      "arguments": {
        "is_id": 24680
      }
    }
  ],
  "family": "random_credit_card_by_id",
  "rendered_tokens": 209,
  "supervised_tokens": 23
}
```

## Source 22254

```json
{
  "id": "22254",
  "query": "Check if 'hello' is a rotation of 'lohel'.",
  "tools": [
    {
      "name": "is_rotation",
      "description": "Checks if one string is a rotation of another string.",
      "parameters": {
        "str1": {
          "description": "The first string.",
          "type": "str"
        },
        "str2": {
          "description": "The second string.",
          "type": "str"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "is_rotation",
      "arguments": {
        "str1": "hello",
        "str2": "lohel"
      }
    }
  ],
  "family": "is_rotation",
  "rendered_tokens": 203,
  "supervised_tokens": 22
}
```

## Source 24838

```json
{
  "id": "24838",
  "query": "Get information about the song at 'https://soundcloud.com/edsheeran/shape-of-you'",
  "tools": [
    {
      "name": "sign_info",
      "description": "Fetches and returns the sign information from the OnlyFans API using the provided user agent and RapidAPI key.",
      "parameters": {
        "useragent": {
          "description": "The user agent string to be used in the API request.",
          "type": "str",
          "default": ""
        }
      }
    },
    {
      "name": "song_info",
      "description": "Retrieve basic information about a song from a given track URL using the SoundCloud API.",
      "parameters": {
        "track_url": {
          "description": "The URL of the track for which the information is to be retrieved.",
          "type": "str",
          "default": "https://soundcloud.com/user-977421934/the-phoenix"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "song_info",
      "arguments": {
        "track_url": "https://soundcloud.com/edsheeran/shape-of-you"
      }
    }
  ],
  "family": "song_info",
  "rendered_tokens": 308,
  "supervised_tokens": 29
}
```

## Source 12998

```json
{
  "id": "12998",
  "query": "I need to find the least common multiple of 24 and 36 for my math homework, can you help?",
  "tools": [
    {
      "name": "least_common_multiple",
      "description": "Computes the least common multiple (LCM) of two positive integers.",
      "parameters": {
        "a": {
          "description": "The first positive integer.",
          "type": "int"
        },
        "b": {
          "description": "The second positive integer.",
          "type": "int"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "least_common_multiple",
      "arguments": {
        "a": 24,
        "b": 36
      }
    }
  ],
  "family": "least_common_multiple",
  "rendered_tokens": 220,
  "supervised_tokens": 22
}
```

## Source 38431

```json
{
  "id": "38431",
  "query": "Find TLE data for the satellite named 'NOAA 15'.",
  "tools": [
    {
      "name": "collection",
      "description": "Fetches TLE (Two-Line Element) data from the TLE API based on the specified search query.",
      "parameters": {
        "search": {
          "description": "The search term to query the API. Defaults to 'ISS'.",
          "type": "str",
          "default": "ISS"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "collection",
      "arguments": {
        "search": "NOAA 15"
      }
    }
  ],
  "family": "collection",
  "rendered_tokens": 208,
  "supervised_tokens": 18
}
```

## Source 39455

```json
{
  "id": "39455",
  "query": "Search for poems that contain the line 'Once upon a midnight dreary, while I pondered weak and weary.'",
  "tools": [
    {
      "name": "lines_line_abs",
      "description": "Fetches poems that contain a specific line using the Thundercomb Poetry DB API.",
      "parameters": {
        "line": {
          "description": "The exact line to search for in poems.",
          "type": "str",
          "default": ""
        }
      }
    }
  ],
  "answers": [
    {
      "name": "lines_line_abs",
      "arguments": {
        "line": "Once upon a midnight dreary, while I pondered weak and weary."
      }
    }
  ],
  "family": "lines_line_abs",
  "rendered_tokens": 217,
  "supervised_tokens": 30
}
```

## Source 56466

```json
{
  "id": "56466",
  "query": "Find cities in the United States and Canada with the name New York, excluding the first 2 results.",
  "tools": [
    {
      "name": "search_places",
      "description": "Fetches a list of places (either countries, cities, or administrative divisions) that match a query and can be filtered by various properties.",
      "parameters": {
        "type": {
          "description": "Filters places by `type`. Specifiable values are 'CITY', 'ADMIN_DIVISION_1', 'ADMIN_DIVISION_2', and 'COUNTRY'. Default is 'CITY'.",
          "type": "str",
          "default": "CITY"
        },
        "language": {
          "description": "Specifies the language (ISO 639-1) to get the localized name of the place. If translation is unavailable, the \"localizedName\" property will be null.",
          "type": "str",
          "default": ""
        },
        "skip": {
          "description": "Number of places to ignore before beginning to return results. Used with `limit` to paginate results. Defaults to 0.",
          "type": "int",
          "default": "0"
        },
        "country": {
          "description": "Filters places by their country `id`. Multiple values can be specified, separated by commas (e.g., 'US,CA'). Default is 'US,CA'.",
          "type": "str",
          "default": "US,CA"
        },
        "limit": {
          "description": "Maximum number of places to return. Used with `skip` to paginate results. Default is 10, maximum is 100.",
          "type": "int",
          "default": "10"
        },
        "admindivision1": {
          "description": "Filters places by their adminDivision1 `id`. Multiple values can be specified, separated by commas (e.g., 'US.CA,US.DE').",
          "type": "str",
          "default": ""
        },
        "admindivision2": {
          "description": "Filters places by their adminDivision2 `id`. Multiple values can be specified, separated by commas.",
          "type": "str",
          "default": ""
        },
        "accuracyradiuskm": {
          "description": "Maximum radius (in kilometers) from the point specified by `latitude` and `longitude` to filter places located within the area. Default is 100 km.",
          "type": "int",
          "default": ""
        },
        "latitude": {
          "description": "Latitude coordinate to filter places by location. Ignored if `longitude` is not specified.",
          "type": "int",
          "default": ""
        },
        "q": {
          "description": "Query string to find places with a similar name. Default is 'New York'.",
          "type": "str",
          "default": "New York"
        },
        "longitude": {
          "description": "Longitude coordinate to filter places by location. Ignored if `latitude` is not specified.",
          "type": "int",
          "default": ""
        }
      }
    }
  ],
  "answers": [
    {
      "name": "search_places",
      "arguments": {
        "type": "CITY",
        "country": "US,CA",
        "q": "New York",
        "skip": 2
      }
    }
  ],
  "family": "search_places",
  "rendered_tokens": 716,
  "supervised_tokens": 31
}
```

## Source 11515

```json
{
  "id": "11515",
  "query": "Fetch the top 10 discounted games in the US region starting from the 20th game.",
  "tools": [
    {
      "name": "gameslist",
      "description": "Retrieves a list of games on special discount offers from the specified region.",
      "parameters": {
        "region": {
          "description": "The region code to fetch the game offers from.",
          "type": "str",
          "default": "US"
        },
        "start": {
          "description": "The starting index for the list of games.",
          "type": "int",
          "default": "0"
        },
        "count": {
          "description": "The number of games to retrieve starting from the `start` index.",
          "type": "int",
          "default": "10"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "gameslist",
      "arguments": {
        "region": "US",
        "start": 20,
        "count": 10
      }
    }
  ],
  "family": "gameslist",
  "rendered_tokens": 274,
  "supervised_tokens": 25
}
```

## Source 30554

```json
{
  "id": "30554",
  "query": "Convert an HSL color with hue 60, saturation 80, and lightness 60 to other formats.",
  "tools": [
    {
      "name": "list_specific_qr_code",
      "description": "Fetches information about a specific registered QR code using the provided reference and RapidAPI key.",
      "parameters": {
        "ref": {
          "description": "The reference identifier for the specific QR code.",
          "type": "str",
          "default": ""
        }
      }
    },
    {
      "name": "convert_hsl",
      "description": "Converts an HSL color code to other color codes such as Hex, RGB, and CMYK using the Convexity API.",
      "parameters": {
        "s": {
          "description": "The saturation component of the HSL color code.",
          "type": "int",
          "default": "78"
        },
        "h": {
          "description": "The hue component of the HSL color code.",
          "type": "int",
          "default": "250"
        },
        "l": {
          "description": "The lightness component of the HSL color code.",
          "type": "int",
          "default": "45"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "convert_hsl",
      "arguments": {
        "s": 80,
        "h": 60,
        "l": 60
      }
    }
  ],
  "family": "convert_hsl",
  "rendered_tokens": 357,
  "supervised_tokens": 27
}
```

## Source 8678

```json
{
  "id": "8678",
  "query": "What are the conversions for an HSL color with hue 180, saturation 50, and lightness 75?",
  "tools": [
    {
      "name": "list_specific_qr_code",
      "description": "Fetches information about a specific registered QR code using the provided reference and RapidAPI key.",
      "parameters": {
        "ref": {
          "description": "The reference identifier for the specific QR code.",
          "type": "str",
          "default": ""
        }
      }
    },
    {
      "name": "convert_hsl",
      "description": "Converts an HSL color code to other color codes such as Hex, RGB, and CMYK using the Convexity API.",
      "parameters": {
        "s": {
          "description": "The saturation component of the HSL color code.",
          "type": "int",
          "default": "78"
        },
        "h": {
          "description": "The hue component of the HSL color code.",
          "type": "int",
          "default": "250"
        },
        "l": {
          "description": "The lightness component of the HSL color code.",
          "type": "int",
          "default": "45"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "convert_hsl",
      "arguments": {
        "s": 50,
        "h": 180,
        "l": 75
      }
    }
  ],
  "family": "convert_hsl",
  "rendered_tokens": 360,
  "supervised_tokens": 28
}
```

## Source 39030

```json
{
  "id": "39030",
  "query": "I need to fetch users from page 30. I'm not sure how to do it. Can you guide me?",
  "tools": [
    {
      "name": "get_all_users_paged_by_hundreds",
      "description": "Fetches a list of users from a specified page, with each page containing up to one hundred users, using the provided RapidAPI key.",
      "parameters": {
        "page": {
          "description": "The page number to retrieve the users from.",
          "type": "int",
          "default": "0"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "get_all_users_paged_by_hundreds",
      "arguments": {
        "page": 30
      }
    }
  ],
  "family": "get_all_users_paged_by_hundreds",
  "rendered_tokens": 230,
  "supervised_tokens": 22
}
```

## Source 36419

```json
{
  "id": "36419",
  "query": "Fetch the detailed information for the school with the encrypted ID '1234567890ABCDEF1234'.",
  "tools": [
    {
      "name": "school_detail",
      "description": "Fetch detailed information about a school using the encrypted school ID (sekolah_id_enkrip).",
      "parameters": {
        "sekolah_id_enkrip": {
          "description": "The encrypted ID of the school for which details are to be fetched. Default is '5DB43D89E6BFB0F76FBC'.",
          "type": "str",
          "default": "5DB43D89E6BFB0F76FBC"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "school_detail",
      "arguments": {
        "sekolah_id_enkrip": "1234567890ABCDEF1234"
      }
    }
  ],
  "family": "school_detail",
  "rendered_tokens": 284,
  "supervised_tokens": 36
}
```

## Source 14515

```json
{
  "id": "14515",
  "query": "Can you provide the details of the proxy test for request '67890'?",
  "tools": [
    {
      "name": "retrieve_proxy_information",
      "description": "Retrieves proxy test result information for a given user request ID.",
      "parameters": {
        "is_id": {
          "description": "The user request ID received from the response of sending a proxy for checking.",
          "type": "str",
          "default": "6416ab3d3c01efbe45e97675"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "retrieve_proxy_information",
      "arguments": {
        "is_id": "67890"
      }
    }
  ],
  "family": "retrieve_proxy_information",
  "rendered_tokens": 230,
  "supervised_tokens": 21
}
```

## Source 33354

```json
{
  "id": "33354",
  "query": "Fetch me some random user data, let's say 7 profiles, and see if there's any pattern in their emails or names.",
  "tools": [
    {
      "name": "getrandomuser",
      "description": "Fetches random user data such as name, e-mail, etc., from the specified API.",
      "parameters": {
        "count": {
          "description": "The number of user records to retrieve. Defaults to -2 if not specified.",
          "type": "int",
          "default": "-2"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "getrandomuser",
      "arguments": {
        "count": 7
      }
    }
  ],
  "family": "getrandomuser",
  "rendered_tokens": 219,
  "supervised_tokens": 16
}
```

## Source 9494

```json
{
  "id": "9494",
  "query": "Convert the HSL color with saturation 50, hue 180, and lightness 75 to RGB.",
  "tools": [
    {
      "name": "hsl_to_rgb",
      "description": "Converts HSL color values to RGB color values using an external API.",
      "parameters": {
        "s": {
          "description": "Saturation component of the HSL color value (0-100).",
          "type": "int",
          "default": "78"
        },
        "h": {
          "description": "Hue component of the HSL color value (0-360).",
          "type": "int",
          "default": "250"
        },
        "l": {
          "description": "Lightness component of the HSL color value (0-100).",
          "type": "int",
          "default": "45"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "hsl_to_rgb",
      "arguments": {
        "s": 50,
        "h": 180,
        "l": 75
      }
    }
  ],
  "family": "hsl_to_rgb",
  "rendered_tokens": 305,
  "supervised_tokens": 29
}
```

## Source 48997

```json
{
  "id": "48997",
  "query": "What is the block for the town 'East London'?",
  "tools": [
    {
      "name": "town",
      "description": "Retrieves information about a specified town, such as province and block, using the Mzansi Loadshedding API.",
      "parameters": {
        "town": {
          "description": "The name of the town for which information is being requested.",
          "type": "str",
          "default": "kagiso"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "town",
      "arguments": {
        "town": "East London"
      }
    }
  ],
  "family": "town",
  "rendered_tokens": 204,
  "supervised_tokens": 15
}
```

## Source 39829

```json
{
  "id": "39829",
  "query": "Attempt to sign in using the international number +447911123456 and password 'securePassword!'.",
  "tools": [
    {
      "name": "user_login",
      "description": "Logs in a user with the given username and password, and returns a JSON object containing the account's session key.",
      "parameters": {
        "username": {
          "description": "Username for the user account. For US domestic users, this should be a 10-digit number. For international users, use the full E.164 format (e.g., US: 5555555555, E.164: +1155555555555).",
          "type": "str",
          "default": ""
        },
        "password": {
          "description": "Password associated with the username.",
          "type": "str",
          "default": ""
        }
      }
    }
  ],
  "answers": [
    {
      "name": "user_login",
      "arguments": {
        "username": "+447911123456",
        "password": "securePassword!"
      }
    }
  ],
  "family": "user_login",
  "rendered_tokens": 318,
  "supervised_tokens": 32
}
```

## Source 31296

```json
{
  "id": "31296",
  "query": "What is the ZIP code for the IP address 55.55.55.55?",
  "tools": [
    {
      "name": "get_ip_zipcode",
      "description": "Retrieves the ZIP code of a given IP address using the ip-api.com API.",
      "parameters": {
        "ip": {
          "description": "The IP address to locate.",
          "type": "str"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "get_ip_zipcode",
      "arguments": {
        "ip": "55.55.55.55"
      }
    }
  ],
  "family": "get_ip_zipcode",
  "rendered_tokens": 209,
  "supervised_tokens": 27
}
```

## Source 48478

```json
{
  "id": "48478",
  "query": "Retrieve the 86th verse from the 29th chapter of the Quran.",
  "tools": [
    {
      "name": "get_specific_ayah_verse",
      "description": "Fetches a specific Ayah (verse) from a given chapter in the Quran, with details in JSON format.",
      "parameters": {
        "chapterid": {
          "description": "The chapter (Surah) number to fetch the verse from. Must be between 1 and 114.",
          "type": "int",
          "default": "38"
        },
        "verseid": {
          "description": "The verse (Ayah) number to fetch within the specified chapter. Must be a valid verse number within the chapter.",
          "type": "int",
          "default": "29"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "get_specific_ayah_verse",
      "arguments": {
        "chapterid": 29,
        "verseid": 86
      }
    }
  ],
  "family": "get_specific_ayah_verse",
  "rendered_tokens": 283,
  "supervised_tokens": 27
}
```

## Source 58728

```json
{
  "id": "58728",
  "query": "Please validate the email address: jane_doe123@company.co.uk. Thanks!",
  "tools": [
    {
      "name": "is_valid_email",
      "description": "Checks if an email address is valid.",
      "parameters": {
        "email": {
          "description": "The email address to validate.",
          "type": "str"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "is_valid_email",
      "arguments": {
        "email": "jane_doe123@company.co.uk"
      }
    }
  ],
  "family": "is_valid_email",
  "rendered_tokens": 194,
  "supervised_tokens": 26
}
```

## Source 3375

```json
{
  "id": "3375",
  "query": "What is the probability of Apple's stock (AAPL) price being above the current price?",
  "tools": [
    {
      "name": "price_probability",
      "description": "Fetch the probabilistic outcome of a stock's price based on over 1000 forecasts.",
      "parameters": {
        "symbol": {
          "description": "The stock symbol for which the probabilistic outcome is to be fetched.",
          "type": "str",
          "default": "AAPL"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "price_probability",
      "arguments": {
        "symbol": "AAPL"
      }
    }
  ],
  "family": "price_probability",
  "rendered_tokens": 210,
  "supervised_tokens": 16
}
```

## Source 560

```json
{
  "id": "560",
  "query": "Please provide the Piotroski F-Score for Alphabet Inc. (GOOGL).",
  "tools": [
    {
      "name": "getfscore",
      "description": "Fetches the Piotroski F-Score for a given stock ticker using the RapidAPI service.",
      "parameters": {
        "ticker": {
          "description": "The stock ticker symbol for which the F-Score is to be retrieved.",
          "type": "str",
          "default": "AAPL"
        }
      }
    }
  ],
  "answers": [
    {
      "name": "getfscore",
      "arguments": {
        "ticker": "GOOGL"
      }
    }
  ],
  "family": "getfscore",
  "rendered_tokens": 215,
  "supervised_tokens": 18
}
```

