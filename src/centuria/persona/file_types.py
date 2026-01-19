"""File type definitions for synthetic persona generation.

Each file type represents a type of online data that could be legally acquired
about a person. These are used to generate realistic synthetic data files.
"""

# The {identity} placeholder in prompts will be replaced with formatted identity text

FILE_TYPES = {
    # ==========================================================================
    # PROFESSIONAL / CAREER
    # ==========================================================================
    "cv": {
        "filename": "cv.txt",
        "description": "CV/Resume",
        "prompt": """Generate a realistic CV/resume for this person as plain text.

{identity}

Write a CV that includes:
- Contact header (name, location - invent a plausible email)
- Professional summary (2-3 sentences)
- Work experience (2-4 positions with dates, company names, bullet points)
- Education
- Skills

Keep it factual and realistic. No flattery or puffery - write like a real CV.
Output only the CV text, no preamble."""
    },
    "linkedin_summary": {
        "filename": "linkedin_summary.txt",
        "description": "LinkedIn about section",
        "prompt": """Generate a LinkedIn "About" section for this person.

{identity}

Write 2-3 paragraphs that:
- Summarize their professional focus
- Mention what they're interested in
- Reflect their communication style

Keep it professional but authentic to their personality. Avoid corporate buzzwords.
Output only the summary text, no preamble."""
    },
    "work_calendar": {
        "filename": "work_calendar.txt",
        "description": "Typical weekly work schedule",
        "prompt": """Generate a typical weekly calendar/schedule for this person.

{identity}

Show a realistic week including:
- Work hours and commute patterns
- Regular meetings or appointments
- Lunch breaks and personal time
- Evening activities
- Weekend plans

Format as a simple schedule (Mon-Sun) with time blocks.
Make it realistic for their occupation and lifestyle.
Output only the schedule, no preamble."""
    },
    "email_signature": {
        "filename": "email_signature.txt",
        "description": "Professional email signature",
        "prompt": """Generate an email signature for this person.

{identity}

Include what's appropriate for their role:
- Name and title
- Contact information (invent plausible phone/email)
- Company/organization if employed
- Any relevant credentials or certifications
- Optional: a brief quote or tagline if it fits their personality

Keep it realistic - not everyone has elaborate signatures.
Output only the signature, no preamble."""
    },

    # ==========================================================================
    # SOCIAL MEDIA PROFILES
    # ==========================================================================
    "twitter_bio": {
        "filename": "twitter_bio.txt",
        "description": "Twitter/X profile bio and interests",
        "prompt": """Generate a Twitter/X profile for this person.

{identity}

Include:
- Bio (max 160 characters)
- Location as displayed
- 5-10 topics they frequently tweet/post about
- Their general posting style (lurker, occasional, frequent)

The profile should reflect their personality and views authentically.
Output as plain text with labeled sections, no preamble."""
    },
    "instagram_bio": {
        "filename": "instagram_bio.txt",
        "description": "Instagram profile and content themes",
        "prompt": """Generate an Instagram profile for this person.

{identity}

Include:
- Bio (max 150 characters)
- Link in bio (if any - could be linktree, personal site, nothing)
- Type of content they post (photos of food, family, travel, work, pets, hobbies, rarely posts, etc.)
- Estimated follower count (be realistic - most people have 200-500 followers)
- Posting frequency

Not everyone is active on Instagram - reflect their likely engagement level.
Output as plain text with labeled sections, no preamble."""
    },
    "facebook_about": {
        "filename": "facebook_about.txt",
        "description": "Facebook profile information",
        "prompt": """Generate Facebook profile information for this person.

{identity}

Include:
- About/intro text
- Work and education listed
- Relationship status (if they'd share it)
- Places lived
- Life events they might have shared
- Groups they might belong to (local community, hobby groups, alumni, etc.)
- Typical content they share (family photos, news articles, memes, rarely posts, etc.)

Facebook skews older - reflect realistic usage patterns for their age.
Output as plain text with labeled sections, no preamble."""
    },
    "reddit_profile": {
        "filename": "reddit_profile.txt",
        "description": "Reddit activity and subreddits",
        "prompt": """Generate a Reddit profile summary for this person.

{identity}

Include:
- Username style (not their real name)
- Subreddits they subscribe to (8-15, mix of interests)
- Type of participation (lurker, commenter, occasional poster)
- Topics they engage with most
- Karma level estimate (most users have low karma)

IMPORTANT: Subreddits should reflect VARIED interests - hobbies, local area, entertainment, advice, not just politics.
Many people lurk without posting.
Output as plain text with labeled sections, no preamble."""
    },
    "tiktok_profile": {
        "filename": "tiktok_profile.txt",
        "description": "TikTok usage and interests",
        "prompt": """Generate TikTok usage profile for this person.

{identity}

Include:
- Whether they have an account (younger people more likely)
- Bio if they have one
- Content they watch (For You page interests)
- Whether they create content or just consume
- Favorite creators/topics
- Usage frequency

TikTok skews younger - older users may not use it at all.
Output as plain text with labeled sections, no preamble."""
    },
    "nextdoor_activity": {
        "filename": "nextdoor_activity.txt",
        "description": "Neighbourhood social network activity",
        "prompt": """Generate Nextdoor activity profile for this person.

{identity}

Include:
- Whether they use the app
- Types of posts they engage with (lost pets, recommendations, safety alerts, selling items, events)
- Their posting style (helpful neighbor, complainer, lurker, active community member)
- Local businesses they've recommended
- Neighbourhood concerns they've raised or engaged with

Nextdoor usage varies - some people love it, many ignore it.
Output as plain text with labeled sections, no preamble."""
    },

    # ==========================================================================
    # MEDIA CONSUMPTION
    # ==========================================================================
    "reading_list": {
        "filename": "recent_reads.txt",
        "description": "Recent books read",
        "prompt": """Generate a list of 5-8 books this person has recently read.

{identity}

IMPORTANT - Avoid overfitting to demographics:
- Most of what people read is NOT political or directly related to their job
- Include genre fiction (thrillers, romance, sci-fi), hobby books, self-help, popular non-fiction
- Only 1-2 books (if any) should relate to their political views

The books should:
- Be real books that actually exist
- Reflect VARIED interests, not just politics/work
- Include popular mainstream titles that many people read

Format: One book per line as "Title - Author"
Output only the list, no preamble."""
    },
    "subscriptions": {
        "filename": "subscriptions.txt",
        "description": "Media subscriptions (publications, podcasts)",
        "prompt": """Generate a list of media subscriptions for this person.

{identity}

IMPORTANT - Avoid overfitting to demographics:
- Most media consumption is entertainment, not politics
- Include: true crime podcasts, sports, comedy, hobby-related content, mainstream entertainment
- Only 1-2 items (if any) should be explicitly political

Include a mix of:
- Podcasts (true crime, comedy, sports, storytelling, interview shows)
- Entertainment (streaming, YouTube channels, sports)
- Maybe 1-2 news sources or political content at most

Format: One item per line
Output only the list, no preamble."""
    },
    "spotify_favorites": {
        "filename": "spotify_favorites.txt",
        "description": "Music streaming favorites",
        "prompt": """Generate a Spotify/music streaming favorites list for this person.

{identity}

Include:
- 8-12 favorite artists
- 2-3 favorite genres
- 2-3 favorite playlists they might have

The music taste should feel authentic to their age, background, and personality.

Format as a simple text list with sections for Artists, Genres, Playlists.
Output only the list, no preamble."""
    },
    "netflix_history": {
        "filename": "netflix_history.txt",
        "description": "Recently watched shows and movies",
        "prompt": """Generate a Netflix/streaming watch history for this person.

{identity}

Include:
- 10-15 recently watched titles (mix of shows and movies)
- Genres they gravitate toward
- Whether they binge-watch or watch casually
- Shows they've rewatched

Use real show/movie titles. Reflect their personality but include mainstream entertainment.
Most people watch a mix of quality TV and guilty pleasures.
Output as plain text list with brief notes, no preamble."""
    },
    "youtube_subscriptions": {
        "filename": "youtube_subscriptions.txt",
        "description": "YouTube channel subscriptions",
        "prompt": """Generate YouTube subscription list for this person.

{identity}

Include 10-20 channels across categories:
- Entertainment (comedy, music, gaming if relevant)
- Educational/informational
- Hobby-related
- News/commentary (if any)
- Local or niche interests

IMPORTANT: Most YouTube consumption is entertainment, tutorials, and hobby content.
Include mainstream creators and smaller niche channels.
Format: Channel name - brief description of content
Output only the list, no preamble."""
    },
    "podcast_subscriptions": {
        "filename": "podcast_subscriptions.txt",
        "description": "Podcast subscriptions",
        "prompt": """Generate a podcast subscription list for this person.

{identity}

Include 5-10 podcasts they listen to:
- True crime, comedy, or storytelling (very popular)
- Industry/professional podcasts if relevant
- Interview shows
- News/commentary (1-2 max)
- Hobby-related

Use real podcast names. Most podcast listening is entertainment, not politics.
Output as a list with podcast name and brief description.
Output only the list, no preamble."""
    },

    # ==========================================================================
    # SHOPPING & CONSUMER BEHAVIOR
    # ==========================================================================
    "amazon_wishlist": {
        "filename": "amazon_wishlist.txt",
        "description": "Amazon wishlist items",
        "prompt": """Generate an Amazon wishlist for this person.

{identity}

Include 10-15 items they might have saved:
- Practical items they need
- Hobby-related purchases
- Gift ideas for themselves
- Books or media
- Home/lifestyle items

Reflect their income level and interests realistically.
Format: Item name - approximate price - why they want it
Output only the list, no preamble."""
    },
    "shopping_history": {
        "filename": "shopping_history.txt",
        "description": "Recent online purchases",
        "prompt": """Generate recent online shopping history for this person.

{identity}

Include 8-12 recent purchases from various retailers:
- Amazon, eBay, or equivalent
- Clothing/fashion sites
- Specialty stores for hobbies
- Grocery delivery if they use it
- Subscriptions (boxes, refills, etc.)

Reflect their income level, lifestyle, and practical needs.
Format: Item - Retailer - approximate price
Output only the list, no preamble."""
    },
    "grocery_list": {
        "filename": "grocery_list.txt",
        "description": "Typical grocery shopping list",
        "prompt": """Generate a typical weekly grocery list for this person.

{identity}

Include items that reflect:
- Their dietary preferences/restrictions
- Cooking habits (cook from scratch vs. ready meals)
- Household size
- Budget level
- Cultural food preferences based on ethnicity
- Health consciousness

Format as a simple shopping list grouped by category.
Output only the list, no preamble."""
    },
    "loyalty_programs": {
        "filename": "loyalty_programs.txt",
        "description": "Store loyalty cards and memberships",
        "prompt": """Generate loyalty program memberships for this person.

{identity}

Include memberships they likely have:
- Supermarket loyalty cards
- Coffee shop rewards
- Airline/hotel points (if they travel)
- Retail store cards
- Gym membership
- Professional memberships
- Subscription boxes

Reflect their lifestyle and spending patterns.
Format: Program name - usage frequency - rough points/status level
Output only the list, no preamble."""
    },

    # ==========================================================================
    # REVIEWS & OPINIONS
    # ==========================================================================
    "google_reviews": {
        "filename": "google_reviews.txt",
        "description": "Google Maps local reviews",
        "prompt": """Generate Google Maps reviews this person has written.

{identity}

Include 5-8 reviews of local places:
- Restaurants they frequent
- Shops or services they use
- Their local area spots
- Occasional travel reviews

Write realistic reviews - mix of lengths, some detailed, some brief.
Include star ratings (1-5). Most reviews are 4-5 stars (people review places they like).
Output as a series of reviews with place name, rating, and review text.
No preamble."""
    },
    "product_reviews": {
        "filename": "product_reviews.txt",
        "description": "Product reviews written",
        "prompt": """Generate product reviews this person has written on various sites.

{identity}

Include 4-6 product reviews:
- Items they've bought on Amazon or similar
- Apps they use
- Services they subscribe to

Write realistic reviews - varying lengths, mostly positive (people review things they feel strongly about).
Include ratings where applicable.
Output as a series of reviews with product, platform, rating, and review text.
No preamble."""
    },
    "yelp_reviews": {
        "filename": "yelp_reviews.txt",
        "description": "Restaurant and business reviews",
        "prompt": """Generate Yelp-style reviews this person has written.

{identity}

Include 4-6 reviews:
- Restaurants matching their taste and budget
- Local services (hair salon, mechanic, etc.)
- Occasional businesses from trips

Write realistic reviews reflecting their personality and communication style.
Some people write detailed reviews, others are brief.
Output as reviews with business name, type, rating, and review text.
No preamble."""
    },

    # ==========================================================================
    # PERSONAL NOTES & COMMUNICATION
    # ==========================================================================
    "notes_snippet": {
        "filename": "notes.txt",
        "description": "Personal notes or journal snippets",
        "prompt": """Generate a few personal notes or journal snippets for this person.

{identity}

Write 3-5 short notes (1-3 sentences each) that might be from their notes app:
- A thought about something they're working on
- A reminder or goal
- A reaction to something they read/watched
- A personal reflection
- Mundane life stuff (groceries, appointments, gift ideas)

IMPORTANT: Most personal notes are mundane, not political or philosophical.
Include things like "pick up milk", "call mom", "look into that show Sarah mentioned", "dentist Tuesday 3pm".
These should feel authentic and unpolished - real notes, not a manifesto.

Output only the notes, no preamble."""
    },
    "bookmarks": {
        "filename": "bookmarks.txt",
        "description": "Saved articles and links",
        "prompt": """Generate a list of saved bookmarks/articles for this person.

{identity}

IMPORTANT - Avoid overfitting to demographics:
- People bookmark practical stuff: recipes, how-to guides, travel ideas, product reviews, health tips
- Include entertainment: articles about TV shows, sports, celebrities, viral stories
- Only 1-2 (if any) should be explicitly political

List 8-12 articles/links they might have saved:
- Practical/how-to content
- Entertainment and lifestyle
- Hobby-related
- Maybe 1-2 news/opinion pieces at most

Format: "Article Title - Publication/Website" (one per line)
Use real publications but you can invent plausible article titles.
Output only the list, no preamble."""
    },
    "text_messages": {
        "filename": "text_messages.txt",
        "description": "Sample text message conversations",
        "prompt": """Generate sample text message snippets for this person.

{identity}

Include 3-4 short conversation snippets with different people:
- Family member (parent, sibling, child, spouse)
- Friend
- Work colleague
- Service provider (plumber, delivery, etc.)

Keep messages realistic and brief - real texts are short and casual.
Show their communication style and relationships.
Format as labeled conversations with back-and-forth messages.
No preamble."""
    },
    "voicemail_greeting": {
        "filename": "voicemail_greeting.txt",
        "description": "Voicemail greeting message",
        "prompt": """Generate a voicemail greeting for this person.

{identity}

Write a realistic voicemail greeting that reflects:
- Their personality (formal, casual, brief, friendly)
- Whether it's a personal or work phone
- Their communication style

Most people have very simple greetings. Some have none (default carrier message).
Output only the greeting text, no preamble."""
    },

    # ==========================================================================
    # HEALTH & FITNESS
    # ==========================================================================
    "fitness_tracker": {
        "filename": "fitness_tracker.txt",
        "description": "Fitness app/tracker summary",
        "prompt": """Generate fitness tracker data summary for this person.

{identity}

Include:
- Average daily steps
- Exercise activities and frequency
- Sleep patterns (if tracked)
- Any fitness goals
- Apps/devices they use (Fitbit, Apple Watch, Strava, none, etc.)

Be realistic - most people don't hit 10,000 steps. Many don't track at all.
Reflect their lifestyle, age, and health consciousness.
Output as a summary with relevant metrics, no preamble."""
    },
    "health_goals": {
        "filename": "health_goals.txt",
        "description": "Health and wellness goals",
        "prompt": """Generate health/wellness goals or notes for this person.

{identity}

Include things they might track or think about:
- Diet goals or restrictions
- Exercise intentions
- Health concerns for their age
- Medications or supplements (general categories, not specific)
- Doctor appointment notes

Be realistic for their age and lifestyle. Not everyone is health-focused.
Output as informal notes/goals, no preamble."""
    },

    # ==========================================================================
    # TRAVEL & LOCATION
    # ==========================================================================
    "travel_history": {
        "filename": "travel_history.txt",
        "description": "Recent trips and travel style",
        "prompt": """Generate travel history for this person.

{identity}

Include:
- Trips in the past 2-3 years (or lack thereof)
- Travel style (budget, luxury, adventure, family, business)
- Destinations they've visited
- How they typically book (apps, agents, package deals)
- Bucket list destinations

Be realistic for their income, job, and family situation.
Many people don't travel much. Business travel differs from leisure.
Output as a summary with trip details, no preamble."""
    },
    "location_history": {
        "filename": "location_history.txt",
        "description": "Frequent locations and routines",
        "prompt": """Generate a location history pattern for this person.

{identity}

Include their typical weekly location patterns:
- Home location (general area)
- Work/commute patterns
- Regular stops (gym, coffee shop, school pickup, etc.)
- Weekend patterns
- Frequent establishments

This represents what Google Maps timeline might show.
Output as a weekly pattern summary, no preamble."""
    },

    # ==========================================================================
    # FINANCIAL (Self-reported or inferred)
    # ==========================================================================
    "bank_categories": {
        "filename": "bank_categories.txt",
        "description": "Spending category breakdown",
        "prompt": """Generate a monthly spending breakdown for this person.

{identity}

Include typical monthly spending categories:
- Housing (rent/mortgage)
- Utilities
- Groceries
- Transport (car, public transit)
- Entertainment/dining
- Subscriptions
- Shopping
- Savings (if any)

Be realistic for their income and lifestyle. Many people live paycheck to paycheck.
Format as categories with approximate monthly amounts.
Output only the breakdown, no preamble."""
    },
    "charity_donations": {
        "filename": "charity_donations.txt",
        "description": "Charitable giving history",
        "prompt": """Generate charitable donation history for this person.

{identity}

Include:
- Causes they support (if any)
- Donation frequency and amounts
- Whether they volunteer
- Fundraising participation (runs, bake sales, etc.)

Be realistic - many people donate little or nothing.
Donations often reflect personal connections, not just political alignment.
Output as a summary of giving patterns, no preamble."""
    },

    # ==========================================================================
    # HOME & LIFESTYLE
    # ==========================================================================
    "home_description": {
        "filename": "home_description.txt",
        "description": "Home and living situation",
        "prompt": """Generate a description of this person's home/living situation.

{identity}

Include:
- Type of dwelling (flat, house, room in shared house, etc.)
- Ownership status (rent, own, live with family)
- General description of the space
- Decor style (or lack thereof)
- Notable features or items
- State of tidiness

Be realistic for their income, age, and location.
Output as a descriptive paragraph, no preamble."""
    },
    "pet_profile": {
        "filename": "pet_profile.txt",
        "description": "Pet ownership details",
        "prompt": """Generate pet information for this person (if they have pets).

{identity}

Include (if they have pets):
- Type of pet(s) and names
- Breed and age
- Where they got the pet
- Pet-related expenses
- Vet and care routines

Many people don't have pets - consider their lifestyle, housing, and time.
If no pets, briefly explain why (allergies, landlord rules, lifestyle, etc.).
Output as a pet profile or explanation, no preamble."""
    },
    "vehicle_info": {
        "filename": "vehicle_info.txt",
        "description": "Car/vehicle ownership",
        "prompt": """Generate vehicle information for this person.

{identity}

Include:
- Whether they own/lease a car (or don't have one)
- Make, model, year, condition
- Why they chose this vehicle
- Driving habits
- Public transport usage

Be realistic for their location (urban vs suburban), income, and needs.
Many urban dwellers don't have cars.
Output as a vehicle profile, no preamble."""
    },
    "recipe_collection": {
        "filename": "recipe_collection.txt",
        "description": "Saved recipes and cooking habits",
        "prompt": """Generate a saved recipe collection for this person.

{identity}

Include 6-10 recipes they've saved or frequently make:
- Reflect their cooking skill level
- Cultural/ethnic food preferences
- Health considerations
- Time constraints (quick meals vs elaborate dishes)
- Whether they actually cook or mostly order in

Format as recipe names with brief notes about each.
Output only the collection, no preamble."""
    },

    # ==========================================================================
    # DATING & RELATIONSHIPS
    # ==========================================================================
    "dating_profile": {
        "filename": "dating_profile.txt",
        "description": "Dating app profile (if single)",
        "prompt": """Generate a dating app profile for this person (if applicable).

{identity}

If they would be on dating apps, include:
- Bio text
- Photos they'd use (described)
- What they're looking for
- Deal-breakers
- Prompts/answers

If they wouldn't use dating apps (in relationship, not interested, age, etc.), explain briefly.
Be realistic about how people present themselves - some are earnest, some use humor, some are low-effort.
Output as a profile or explanation, no preamble."""
    },

    # ==========================================================================
    # COMMUNITY & LOCAL
    # ==========================================================================
    "forum_posts": {
        "filename": "forum_posts.txt",
        "description": "Forum/community participation",
        "prompt": """Generate forum or online community participation for this person.

{identity}

Include:
- What forums/communities they participate in (if any)
- Topics they engage with
- Whether they post or just read
- Sample posts or comments they might write

Many people don't participate in forums. Consider their interests and tech comfort.
Include hobby forums, parenting groups, local community boards, professional forums, etc.
Output as a summary with sample posts, no preamble."""
    },
    "event_attendance": {
        "filename": "event_attendance.txt",
        "description": "Events and activities attended",
        "prompt": """Generate recent event attendance for this person.

{identity}

Include events from the past year:
- Concerts, shows, sports events
- Community events, fairs, markets
- Professional events or conferences
- Religious or cultural events
- Family gatherings
- Classes or workshops

Reflect their interests, budget, and social patterns.
Many people don't attend many events.
Output as a list with dates and brief descriptions, no preamble."""
    },
}


def get_file_type(file_type: str) -> dict:
    """Get a file type configuration by key."""
    if file_type not in FILE_TYPES:
        raise ValueError(f"Unknown file type: {file_type}")
    return FILE_TYPES[file_type]


def list_file_types() -> dict[str, str]:
    """List available file types and their descriptions."""
    return {k: v["description"] for k, v in FILE_TYPES.items()}


def get_all_file_type_keys() -> list[str]:
    """Get all available file type keys."""
    return list(FILE_TYPES.keys())
