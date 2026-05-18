#!/bin/bash

echo "============================================================"
echo "Instagram Token Setup - Interactive Script"
echo "============================================================"
echo ""
echo "This script will:"
echo "1. Convert your short-lived token to long-lived (60 days)"
echo "2. Add it to your local .env file"
echo "3. Show you what to add to Doppler"
echo ""
echo "============================================================"
echo ""

# Get App ID
echo "Step 1: Get your App ID"
echo "-----------------------------------------------------------"
echo "Go to: https://developers.facebook.com/apps"
echo "Select: 'Glycogrit Social' (or your app name)"
echo "Go to: Settings → Basic"
echo ""
read -p "Enter your App ID: " APP_ID
echo ""

# Get App Secret
echo "Step 2: Get your App Secret"
echo "-----------------------------------------------------------"
echo "On the same page, find 'App Secret'"
echo "Click 'Show' button"
echo ""
read -sp "Enter your App Secret (hidden): " APP_SECRET
echo ""
echo ""

# Short-lived token
echo "Step 3: Using your current token"
echo "-----------------------------------------------------------"
SHORT_TOKEN="EAAXffrHWGGQBRXI7RxZCcLIcoOk0BU2nix4VaS7VJjpZA4NzbaHDnzCHsvqEgPxvA1D6ZAwZCqmZCHI7L77Ft0XGzbS823TdPOvPZBNZBuCa9UMsfrzbjmOSlbu7hw47lEejfaOMXp6PPBj6WFKlg3UMZBiZAZAaaWDbPcybevddrZCgDh4w9LuZChtlVdLqbrc65BqF2al44ysrcVKZAa2ZCT4HvivWtmEfn8bEG4g1gB9aFu3DZBsMynW5DiDLhDcs3CWwhc3uDxyNmQDLuKaptZBHMKqpyVsJgUqWvBBpXAZDZD"
echo "Using token: ${SHORT_TOKEN:0:50}..."
echo ""

# Convert to long-lived token
echo "Step 4: Converting to long-lived token..."
echo "-----------------------------------------------------------"
RESPONSE=$(curl -s "https://graph.facebook.com/v18.0/oauth/access_token?grant_type=fb_exchange_token&client_id=$APP_ID&client_secret=$APP_SECRET&fb_exchange_token=$SHORT_TOKEN")

# Extract token
LONG_TOKEN=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('access_token', ''))" 2>/dev/null)

if [ -z "$LONG_TOKEN" ]; then
    echo "❌ Error converting token!"
    echo "Response: $RESPONSE"
    echo ""
    echo "Common issues:"
    echo "1. App ID or Secret is incorrect"
    echo "2. Token has expired (try generating a new one)"
    echo "3. Network/SSL issues"
    exit 1
fi

EXPIRES_IN=$(echo $RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('expires_in', 'unknown'))" 2>/dev/null)
DAYS=$((EXPIRES_IN / 86400))

echo "✅ Success! Token converted."
echo "   Expires in: $DAYS days ($EXPIRES_IN seconds)"
echo ""

# Show results
echo "============================================================"
echo "📋 YOUR LONG-LIVED TOKEN:"
echo "============================================================"
echo "$LONG_TOKEN"
echo "============================================================"
echo ""

# Add to .env
echo "Step 5: Adding to .env file"
echo "-----------------------------------------------------------"
read -p "Add to glycogrit-backend/.env? (y/n): " ADD_TO_ENV

if [ "$ADD_TO_ENV" = "y" ] || [ "$ADD_TO_ENV" = "Y" ]; then
    ENV_FILE=".env"

    # Backup existing .env
    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "$ENV_FILE.backup"
        echo "✅ Backed up existing .env to .env.backup"
    fi

    # Check if variables already exist
    if grep -q "INSTAGRAM_ACCESS_TOKEN" "$ENV_FILE" 2>/dev/null; then
        # Update existing
        sed -i.tmp "s|INSTAGRAM_ACCESS_TOKEN=.*|INSTAGRAM_ACCESS_TOKEN=$LONG_TOKEN|" "$ENV_FILE"
        rm -f "$ENV_FILE.tmp"
        echo "✅ Updated INSTAGRAM_ACCESS_TOKEN in .env"
    else
        # Add new
        echo "" >> "$ENV_FILE"
        echo "# Instagram API Configuration" >> "$ENV_FILE"
        echo "INSTAGRAM_ACCESS_TOKEN=$LONG_TOKEN" >> "$ENV_FILE"
        echo "✅ Added INSTAGRAM_ACCESS_TOKEN to .env"
    fi

    if grep -q "INSTAGRAM_ACCOUNT_ID" "$ENV_FILE" 2>/dev/null; then
        # Update existing
        sed -i.tmp "s|INSTAGRAM_ACCOUNT_ID=.*|INSTAGRAM_ACCOUNT_ID=26266167426339589|" "$ENV_FILE"
        rm -f "$ENV_FILE.tmp"
        echo "✅ Updated INSTAGRAM_ACCOUNT_ID in .env"
    else
        echo "INSTAGRAM_ACCOUNT_ID=26266167426339589" >> "$ENV_FILE"
        echo "✅ Added INSTAGRAM_ACCOUNT_ID to .env"
    fi

    echo ""
fi

# Show Doppler instructions
echo "============================================================"
echo "💾 ADD THESE TO DOPPLER:"
echo "============================================================"
echo "1. Go to: https://dashboard.doppler.com"
echo "2. Select: glycogrit project → production environment"
echo "3. Add these secrets:"
echo ""
echo "INSTAGRAM_ACCESS_TOKEN=$LONG_TOKEN"
echo "INSTAGRAM_ACCOUNT_ID=26266167426339589"
echo ""
echo "============================================================"
echo ""

# Verify permissions
echo "Step 6: Verifying token permissions..."
echo "-----------------------------------------------------------"
PERMS=$(curl -s "https://graph.facebook.com/v18.0/me/permissions?access_token=$LONG_TOKEN")
echo "$PERMS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    perms = {p['permission']: p['status'] for p in data.get('data', [])}
    required = ['instagram_basic', 'instagram_content_publish', 'pages_manage_posts', 'pages_show_list']

    print('\nToken Permissions:')
    all_granted = True
    for perm in required:
        status = perms.get(perm, 'not_granted')
        icon = '✅' if status == 'granted' else '❌'
        print(f'  {icon} {perm}: {status}')
        if status != 'granted':
            all_granted = False

    if all_granted:
        print('\n✅ All required permissions verified!')
    else:
        print('\n⚠️  Some permissions are missing.')
except:
    print('Could not verify permissions')
"
echo ""

# Next steps
echo "============================================================"
echo "🚀 NEXT STEPS:"
echo "============================================================"
echo "1. ✅ Token converted and saved"
echo "2. ⏭️  Add token to Doppler (see above)"
echo "3. ⏭️  Deploy backend: git add . && git commit -m 'feat: Add gallery submission' && git push"
echo "4. ⏭️  Deploy frontend: (in glycogrit-frontend) git add . && git commit && git push"
echo "5. ⏭️  Test at: https://glycogrit.com/gallery"
echo "6. ⏭️  Set reminder to refresh token in $DAYS days"
echo ""
echo "⚠️  Token expires in $DAYS days - set a calendar reminder!"
echo "============================================================"
