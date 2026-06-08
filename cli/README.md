# Shiprocket CLI

A modern, interactive command-line interface for Shiprocket API - inspired by `gcloud`, `doppler`, and other modern CLI tools.

## Features

- 🔐 **Interactive Authentication** - Login flow similar to modern CLI tools
- 💾 **Secure Credential Storage** - Credentials stored locally in `~/.shiprocket/`
- 🔄 **Automatic Token Refresh** - Tokens refresh automatically (valid for 10 days)
- 📦 **Track Shipments** - Track shipments by AWB number
- 📍 **Check Serviceability** - Verify pincode serviceability
- 🎨 **Rich UI** - Beautiful terminal output with colors and tables

## Installation

### Install Dependencies

```bash
cd glycogrit-backend
pip install click rich httpx
```

### Make CLI Executable

```bash
chmod +x cli/shiprocket.py
```

### Optional: Create System-wide Alias

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
alias shiprocket="python /path/to/glycogrit-backend/cli/shiprocket.py"
```

Or create a symlink:

```bash
ln -s /path/to/glycogrit-backend/cli/shiprocket.py /usr/local/bin/shiprocket
```

## Usage

### Login (First Time)

```bash
python cli/shiprocket.py login
```

You'll be prompted for:
- **Email**: teamglycogrit@gmail.com
- **Password**: (your Shiprocket password)

Credentials are stored in `~/.shiprocket/credentials.json` with restrictive permissions (600).

### Check Authentication Status

```bash
python cli/shiprocket.py status
```

Shows:
- Email
- Authentication status
- Token expiry
- Config file location

### Test API Connection

```bash
python cli/shiprocket.py test
```

Verifies your credentials work and the API is accessible.

### Track Shipment

```bash
python cli/shiprocket.py track <AWB_NUMBER>
```

Example:
```bash
python cli/shiprocket.py track 1234567890
```

Shows:
- Current status
- Current location
- Courier name
- ETD (Estimated Time of Delivery)
- Full tracking history
- Tracking URL

### Check Pincode Serviceability

```bash
python cli/shiprocket.py pincode <PINCODE>
```

Example:
```bash
python cli/shiprocket.py pincode 110001
```

Shows:
- City and state information
- Serviceability status
- Available courier partners
- Estimated delivery times

### Logout

```bash
python cli/shiprocket.py logout
```

Removes stored credentials from your system.

### Help

```bash
python cli/shiprocket.py --help
```

## Quick Start Example

```bash
# 1. Login
python cli/shiprocket.py login
# Enter: teamglycogrit@gmail.com
# Enter: <your-password>

# 2. Check status
python cli/shiprocket.py status

# 3. Test connection
python cli/shiprocket.py test

# 4. Track a shipment
python cli/shiprocket.py track 1234567890

# 5. Check if delivery is available
python cli/shiprocket.py pincode 110001
```

## Authentication Flow

Similar to `gcloud auth login` or `doppler login`:

1. **Interactive Login**: CLI prompts for email and password
2. **API Validation**: Authenticates with Shiprocket API
3. **Secure Storage**: Stores credentials in `~/.shiprocket/credentials.json`
4. **Token Caching**: Caches access token (valid for 10 days)
5. **Auto Refresh**: Automatically refreshes token when needed

## Security

- Credentials stored in `~/.shiprocket/` with `700` permissions
- Config file has `600` permissions (owner read/write only)
- Tokens auto-refresh 1 hour before expiry
- No credentials stored in git or database

## Architecture

```
cli/
├── __init__.py          # Package initialization
├── auth_manager.py      # Authentication & credential storage
├── shiprocket.py        # Main CLI commands
└── README.md            # This file
```

### AuthManager Class

Handles:
- Credential storage in `~/.shiprocket/credentials.json`
- Token management and auto-refresh
- Login/logout operations
- Authentication status checks

### CLI Commands

Built with [Click](https://click.palletsprojects.com/):
- `login` - Interactive authentication
- `logout` - Remove credentials
- `status` - Show auth status
- `test` - Test API connection
- `track` - Track shipments
- `pincode` - Check serviceability

### Rich UI

Uses [Rich](https://rich.readthedocs.io/) for:
- Colored output
- Tables and panels
- Progress indicators
- Beautiful formatting

## Configuration File Format

`~/.shiprocket/credentials.json`:

```json
{
  "email": "teamglycogrit@gmail.com",
  "password": "encrypted_password",
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_expires_at": "2026-06-18T10:30:00",
  "logged_in_at": "2026-06-08T10:30:00"
}
```

## Comparison with Other CLIs

| Feature | Shiprocket CLI | gcloud | doppler | gh |
|---------|---------------|--------|---------|-----|
| Interactive Login | ✅ | ✅ | ✅ | ✅ |
| OAuth Flow | ❌* | ✅ | ✅ | ✅ |
| Local Config | ✅ | ✅ | ✅ | ✅ |
| Token Caching | ✅ | ✅ | ✅ | ✅ |
| Auto Refresh | ✅ | ✅ | ✅ | ✅ |
| Rich UI | ✅ | ✅ | ✅ | ✅ |

*Shiprocket API only supports email/password authentication, not OAuth2

## Extending the CLI

### Add New Commands

```python
@cli.command()
@click.argument("order_id")
def create_order(order_id: str):
    """Create a new order"""
    auth = AuthManager()
    # ... implementation
```

### Add API Methods

```python
# In auth_manager.py or new shiprocket_api.py
async def get_orders(token: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BASE_URL}/orders",
            headers={"Authorization": f"Bearer {token}"}
        )
        return response.json()
```

## Troubleshooting

### "Not authenticated" Error

```bash
python cli/shiprocket.py login
```

### Token Expired

The CLI will automatically refresh. If issues persist:

```bash
python cli/shiprocket.py logout
python cli/shiprocket.py login
```

### Network Errors

Check your internet connection and Shiprocket API status.

### Permission Errors

Ensure `~/.shiprocket/` has correct permissions:

```bash
chmod 700 ~/.shiprocket
chmod 600 ~/.shiprocket/credentials.json
```

## Development

### Requirements

- Python 3.10+
- click
- rich
- httpx

### Running Tests

```bash
# Test authentication
python cli/shiprocket.py test

# Test with real data
python cli/shiprocket.py track <real-awb>
python cli/shiprocket.py pincode 110001
```

## Future Enhancements

- [ ] Add order creation command
- [ ] Add bulk tracking
- [ ] Add webhook management
- [ ] Export tracking data to CSV
- [ ] Add shell completion (bash/zsh)
- [ ] Add verbose/debug mode
- [ ] Add config file for defaults
- [ ] Add integration with backend database

## License

MIT

## Support

For issues or questions:
- Check Shiprocket API docs: https://apidocs.shiprocket.in/
- File an issue in the repository
