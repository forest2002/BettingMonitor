# Betfair API Setup Guide

This guide will help you switch from web scraping to using the official Betfair API for more reliable, real-time data.

## Why Use the Betfair API?

**Advantages:**
- ✅ **Reliable**: No broken selectors when websites change
- ✅ **Real-time**: Near-instant updates (< 1 second)
- ✅ **Comprehensive**: Access to all markets and detailed data
- ✅ **Legal**: Official API, no terms of service violations
- ✅ **Faster**: Direct data feed vs web scraping

**Disadvantages:**
- ❌ **Paid**: Free delayed data, or £299 one-time for live app key
- ❌ **Setup**: Requires API credentials and some configuration

## Step 1: Create Betfair Developer Account

1. **Sign up for Betfair** (if you don't have an account):
   - Go to https://www.betfair.com
   - Create an account and verify your identity
   - You need a funded account (minimum deposit)

2. **Access Developer Program**:
   - Go to https://developer.betfair.com
   - Log in with your Betfair credentials
   - Accept the API terms and conditions

## Step 2: Generate App Key

1. **Navigate to My Account → API Access**:
   - https://myaccount.betfair.com/accountdetails/mysecurity?showAPI=1

2. **Generate an App Key**:
   - Click "Get an Application Key"
   - You'll get two types:
     - **Delayed App Key** (FREE): Data delayed by 1-60 seconds
     - **Live App Key** (£299 one-time): Real-time data

3. **For Testing**: Use the **Delayed App Key** first (it's free!)

4. **Copy your App Key** - you'll need it in Step 4

## Step 3: Get Your Credentials

You'll need three pieces of information:

1. **Username**: Your Betfair login username
2. **Password**: Your Betfair login password
3. **App Key**: The key you generated in Step 2

**Optional: Certificate-based Authentication** (more secure)
- Generate SSL certificates for production use
- See: https://developer.betfair.com/default/api-s-and-services/sports-api/sports-api-overview/#security

## Step 4: Configure Your Application

1. **Open the `.env` file** in the each-way-tracker directory

2. **Add your Betfair credentials**:

```bash
# Change mode from "scraper" to "api"
BETFAIR_MODE=api

# Add your Betfair API credentials
BETFAIR_APP_KEY=your_app_key_here
BETFAIR_USERNAME=your_betfair_username
BETFAIR_PASSWORD=your_betfair_password
BETFAIR_CERT_PATH=  # Leave empty unless using cert auth
```

3. **Save the file**

## Step 5: Rebuild and Restart

1. **Stop the current containers**:
```bash
cd /Users/bsslbj/Desktop/FirstUse/betting-monitor
docker-compose down
```

2. **Rebuild to install betfairlightweight library**:
```bash
docker-compose build scraper
```

3. **Start the services**:
```bash
docker-compose up -d
```

4. **Check the logs** to verify API connection:
```bash
docker-compose logs -f scraper
```

You should see:
```
INFO - Initializing Betfair client...
INFO - Successfully logged in to Betfair API
INFO - Betfair API client initialized successfully
```

## Step 6: Verify Data is Flowing

1. **Open the frontend**: http://localhost:3000

2. **Check the "Each-Way Opportunities" tab**:
   - You should see real data from Betfair API
   - Look for "source": "betfair_api" in the metadata

3. **Check the "All Races & Odds" tab**:
   - Should show live races from Betfair Exchange
   - Data updates every 30 seconds

## Troubleshooting

### Error: "Missing Betfair API credentials"
- Make sure you've set `BETFAIR_USERNAME`, `BETFAIR_PASSWORD`, and `BETFAIR_APP_KEY` in `.env`
- Rebuild the scraper container: `docker-compose build scraper`

### Error: "Invalid username or password"
- Double-check your Betfair login credentials
- Make sure your account is active and funded
- Try logging into https://www.betfair.com to verify

### Error: "Invalid application key"
- Verify your App Key from https://myaccount.betfair.com/accountdetails/mysecurity?showAPI=1
- Make sure there are no extra spaces in the `.env` file

### Error: "This account has been suspended from API usage"
- Check your account status on Betfair
- Contact Betfair support if needed

### No Data Appearing
- Check logs: `docker-compose logs scraper`
- Make sure there are live horse racing markets
- Try different times when UK/Ireland races are running

## Switching Back to Scraper Mode

If you want to go back to web scraping:

1. **Edit `.env`**:
```bash
BETFAIR_MODE=scraper
```

2. **Restart**:
```bash
docker-compose restart scraper
```

## API Rate Limits

Betfair API has rate limits:
- **Delayed App Key**: 1000 requests/hour
- **Live App Key**: Higher limits (contact Betfair for details)

Our current setup polls every 30 seconds, which is:
- **120 requests/hour** - well within limits ✅

## Cost Breakdown

| Option | Cost | Data Delay | Best For |
|--------|------|------------|----------|
| Web Scraping | Free | ~30-60s | Testing, personal use |
| Delayed API | Free | 1-60s | Development, testing |
| Live API | £299 one-time | < 1s | Production, serious betting |

## Next Steps

Once you have the API working:

1. **Monitor for a few days** with delayed data
2. **Verify opportunities** are being detected correctly
3. **Upgrade to Live API** if you want real-time data
4. **Add more bookmaker APIs** (if they have them)

## Support

- **Betfair API Docs**: https://developer.betfair.com
- **API Forum**: https://forum.developer.betfair.com
- **Our GitHub**: (add your repo link here)

---

**Current Mode**: Check your `.env` file - `BETFAIR_MODE=scraper` or `BETFAIR_MODE=api`
