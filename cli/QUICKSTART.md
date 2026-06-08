# Shiprocket CLI - Quick Start

## Installation

No installation needed! Just use the wrapper script:

```bash
cd glycogrit-backend
./shiprocket --help
```

## First Time Setup

### Step 1: Login

```bash
./shiprocket login
```

**Credentials:**
- Email: `admin@glycogrit.com`
- Password: `V56$%zynS8M$FNB0@6ml^u6zHPXopv^I`

### Step 2: Verify

```bash
./shiprocket status
./shiprocket test
```

## Common Commands

```bash
# Authentication
./shiprocket login                    # Login to Shiprocket
./shiprocket logout                   # Logout
./shiprocket status                   # Check auth status
./shiprocket test                     # Test API connection

# Shipping Operations
./shiprocket track <AWB>              # Track shipment
./shiprocket pincode <CODE>           # Check serviceability

# Help
./shiprocket --help                   # Show all commands
./shiprocket <command> --help         # Command-specific help
```

## Examples

### Track a Shipment
```bash
./shiprocket track 1234567890
```

### Check Delivery to Delhi
```bash
./shiprocket pincode 110001
```

## Features

- 🔐 **Secure Login** - Like `gcloud auth login`
- 💾 **Credential Storage** - Stored in `~/.shiprocket/`
- 🔄 **Auto Token Refresh** - Tokens valid 10 days
- 🎨 **Beautiful UI** - Rich terminal output
- ⚡ **Fast** - Cached tokens for quick access

## File Structure

```
glycogrit-backend/
├── shiprocket              # Main CLI wrapper script
└── cli/
    ├── __init__.py
    ├── auth_manager.py     # Authentication logic
    ├── shiprocket.py       # CLI commands
    ├── README.md           # Full documentation
    ├── DEMO.md             # Live demo results
    └── QUICKSTART.md       # This file
```

## Credentials Storage

Your credentials are stored securely:

```
~/.shiprocket/credentials.json (chmod 600)
```

To view:
```bash
cat ~/.shiprocket/credentials.json | python3 -m json.tool
```

To remove:
```bash
./shiprocket logout
# or
rm -rf ~/.shiprocket
```

## Troubleshooting

### Not Authenticated?
```bash
./shiprocket login
```

### Token Expired?
CLI auto-refreshes, but you can manually refresh:
```bash
./shiprocket test
```

### Want to start fresh?
```bash
./shiprocket logout
./shiprocket login
```

## Next: Full Documentation

See [README.md](README.md) for:
- Complete API reference
- Architecture details
- Extending the CLI
- Integration examples

See [DEMO.md](DEMO.md) for:
- Live test results
- Expected outputs
- Troubleshooting tips
