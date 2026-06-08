#!/usr/bin/env python3
"""
Shiprocket CLI - Interactive command-line interface for Shiprocket API

Usage:
    shiprocket login           # Login to Shiprocket
    shiprocket logout          # Logout from Shiprocket
    shiprocket status          # Show authentication status
    shiprocket test            # Test API connection
    shiprocket track <awb>     # Track shipment by AWB number
    shiprocket pincode <code>  # Check pincode serviceability
"""

import asyncio
import sys
from typing import Optional

import click
import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from cli.auth_manager import AuthManager

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Shiprocket CLI - Manage your Shiprocket shipping operations"""
    pass


@cli.command()
@click.option("--email", prompt="Email", help="Shiprocket account email")
@click.option("--password", prompt="Password", hide_input=True, help="Shiprocket password")
def login(email: str, password: str):
    """Login to Shiprocket

    This will authenticate with Shiprocket API and store your credentials
    securely in ~/.shiprocket/credentials.json
    """
    console.print("\n[bold cyan]🔐 Logging in to Shiprocket...[/bold cyan]\n")

    auth = AuthManager()

    async def do_login():
        success, message = await auth.login(email, password)
        return success, message

    success, message = asyncio.run(do_login())

    if success:
        console.print(Panel.fit(
            f"[bold green]✅ {message}[/bold green]\n\n"
            f"Email: [cyan]{email}[/cyan]\n"
            f"Config: [dim]{auth.config_file}[/dim]\n\n"
            "You can now use other Shiprocket CLI commands.",
            title="Login Successful",
            border_style="green",
        ))
    else:
        console.print(Panel.fit(
            f"[bold red]❌ {message}[/bold red]\n\n"
            "Please check your credentials and try again.",
            title="Login Failed",
            border_style="red",
        ))
        sys.exit(1)


@cli.command()
def logout():
    """Logout from Shiprocket

    This will remove stored credentials from your system.
    """
    auth = AuthManager()

    if not auth.is_authenticated():
        console.print("[yellow]⚠️  You are not logged in[/yellow]")
        return

    user_info = auth.get_user_info()
    email = user_info.get("email", "Unknown") if user_info else "Unknown"

    auth.logout()

    console.print(Panel.fit(
        f"[bold green]✅ Successfully logged out[/bold green]\n\n"
        f"Email: [dim]{email}[/dim]\n\n"
        "Your credentials have been removed.",
        title="Logout Successful",
        border_style="green",
    ))


@cli.command()
def status():
    """Show authentication status

    Display information about your current Shiprocket authentication,
    including email, token expiry, and configuration location.
    """
    auth = AuthManager()

    if not auth.is_authenticated():
        console.print(Panel.fit(
            "[yellow]⚠️  Not authenticated[/yellow]\n\n"
            "Run [cyan]shiprocket login[/cyan] to get started.",
            title="Authentication Status",
            border_style="yellow",
        ))
        return

    user_info = auth.get_user_info()
    if not user_info:
        console.print("[red]Error loading user information[/red]")
        return

    has_valid_token = auth.has_valid_token()

    # Create status table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="cyan")
    table.add_column("Value")

    table.add_row("Email", user_info.get("email", "N/A"))
    table.add_row("Status", "[green]✅ Authenticated[/green]" if has_valid_token else "[yellow]⚠️  Token expired[/yellow]")
    table.add_row("Logged in", user_info.get("logged_in_at", "N/A"))
    table.add_row("Token expires", user_info.get("token_expires_at", "N/A"))
    table.add_row("Config file", str(auth.config_file))

    console.print("\n")
    console.print(Panel(
        table,
        title="[bold]Shiprocket Authentication Status[/bold]",
        border_style="green" if has_valid_token else "yellow",
    ))
    console.print("\n")


@cli.command()
def test():
    """Test API connection

    Verify that your Shiprocket credentials work and the API is accessible.
    This will attempt to refresh your access token.
    """
    auth = AuthManager()

    if not auth.is_authenticated():
        console.print("[red]❌ Not authenticated. Run: shiprocket login[/red]")
        sys.exit(1)

    console.print("\n[bold cyan]🔍 Testing Shiprocket API connection...[/bold cyan]\n")

    async def do_test():
        token = await auth.get_token()
        return token

    token = asyncio.run(do_test())

    if token:
        console.print(Panel.fit(
            "[bold green]✅ Connection successful![/bold green]\n\n"
            f"Token: [dim]{token[:50]}...[/dim]\n"
            f"Length: [cyan]{len(token)}[/cyan] characters\n\n"
            "Your Shiprocket API integration is working correctly.",
            title="API Test Result",
            border_style="green",
        ))
    else:
        console.print(Panel.fit(
            "[bold red]❌ Connection failed[/bold red]\n\n"
            "Could not authenticate with Shiprocket API.\n"
            "Try logging in again: [cyan]shiprocket login[/cyan]",
            title="API Test Result",
            border_style="red",
        ))
        sys.exit(1)


@cli.command()
@click.argument("awb")
def track(awb: str):
    """Track shipment by AWB number

    Args:
        awb: Air Waybill (tracking) number
    """
    auth = AuthManager()

    if not auth.is_authenticated():
        console.print("[red]❌ Not authenticated. Run: shiprocket login[/red]")
        sys.exit(1)

    console.print(f"\n[bold cyan]📦 Tracking shipment: {awb}[/bold cyan]\n")

    async def do_track():
        token = await auth.get_token()
        if not token:
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                response = await client.get(
                    f"{auth.BASE_URL}/courier/track/awb/{awb}",
                    headers={"Authorization": f"Bearer {token}"},
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    console.print(f"[red]Error: {response.status_code} - {response.text}[/red]")
                    return None

        except httpx.RequestError as e:
            console.print(f"[red]Network error: {str(e)}[/red]")
            return None

    result = asyncio.run(do_track())

    if result:
        tracking_data = result.get("tracking_data", {})

        # Create tracking info table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="cyan bold")
        table.add_column("Value")

        table.add_row("AWB Code", tracking_data.get("awb_code", awb))
        table.add_row("Status", tracking_data.get("shipment_status", "Unknown"))
        table.add_row("Current Location", tracking_data.get("current_location", "N/A"))
        table.add_row("Courier", tracking_data.get("courier_name", "N/A"))
        table.add_row("ETD", tracking_data.get("etd", "N/A"))
        table.add_row("Track URL", tracking_data.get("track_url", "N/A"))

        console.print(Panel(
            table,
            title=f"[bold]Shipment Tracking - {awb}[/bold]",
            border_style="green",
        ))

        # Show tracking history
        history = tracking_data.get("shipment_track", [])
        if history:
            console.print("\n[bold cyan]📍 Tracking History:[/bold cyan]\n")
            history_table = Table(show_header=True, box=None)
            history_table.add_column("Date", style="cyan")
            history_table.add_column("Status", style="green")
            history_table.add_column("Location")

            for event in history:
                history_table.add_row(
                    event.get("date", "N/A"),
                    event.get("status", "N/A"),
                    event.get("location", "N/A"),
                )

            console.print(history_table)
        console.print("\n")
    else:
        console.print(f"[red]❌ Could not track shipment {awb}[/red]")
        sys.exit(1)


@cli.command()
@click.argument("pincode")
def pincode(pincode: str):
    """Check pincode serviceability

    Args:
        pincode: Postal code to check
    """
    auth = AuthManager()

    if not auth.is_authenticated():
        console.print("[red]❌ Not authenticated. Run: shiprocket login[/red]")
        sys.exit(1)

    console.print(f"\n[bold cyan]📍 Checking pincode: {pincode}[/bold cyan]\n")

    async def do_check():
        token = await auth.get_token()
        if not token:
            return None

        try:
            async with httpx.AsyncClient(timeout=30.0, verify=False) as client:
                response = await client.get(
                    f"{auth.BASE_URL}/courier/serviceability/",
                    headers={"Authorization": f"Bearer {token}"},
                    params={
                        "delivery_postcode": pincode,
                        "pickup_pincode": "110001",  # Default pickup
                        "weight": 0.5,
                        "cod": 0,
                    },
                )

                if response.status_code == 200:
                    return response.json()
                else:
                    console.print(f"[red]Error: {response.status_code} - {response.text}[/red]")
                    return None

        except httpx.RequestError as e:
            console.print(f"[red]Network error: {str(e)}[/red]")
            return None

    result = asyncio.run(do_check())

    if result and result.get("data"):
        data = result["data"]

        # Create info table
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Key", style="cyan bold")
        table.add_column("Value")

        table.add_row("Pincode", data.get("delivery_postcode", pincode))
        table.add_row("City", data.get("city", "N/A"))
        table.add_row("State", data.get("state", "N/A"))
        table.add_row("State Code", data.get("state_code", "N/A"))

        serviceable = data.get("is_serviceable", False)
        status_text = "[green]✅ Serviceable[/green]" if serviceable else "[red]❌ Not Serviceable[/red]"
        table.add_row("Status", status_text)

        console.print(Panel(
            table,
            title=f"[bold]Pincode Information - {pincode}[/bold]",
            border_style="green" if serviceable else "yellow",
        ))

        # Show available couriers
        couriers = data.get("available_courier_companies", [])
        if couriers:
            console.print("\n[bold cyan]🚚 Available Couriers:[/bold cyan]\n")
            courier_table = Table(show_header=True, box=None)
            courier_table.add_column("Courier", style="cyan")
            courier_table.add_column("ID")
            courier_table.add_column("ETD")

            for courier in couriers[:10]:  # Show first 10
                courier_table.add_row(
                    courier.get("courier_name", "N/A"),
                    str(courier.get("courier_company_id", "N/A")),
                    courier.get("etd", "N/A"),
                )

            console.print(courier_table)
        console.print("\n")
    else:
        console.print(f"[red]❌ Could not check pincode {pincode}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    cli()
