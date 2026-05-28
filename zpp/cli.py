import click
import os
import webbrowser
import threading
import time
from flask import Flask, render_template, jsonify, request
from .webui import create_app
from .config import ConfigManager

@click.group()
@click.version_option(version="0.1.0")
def cli():
    """zpp - A CLI tool with webui for LLM interactions"""
    pass

@cli.command()
@click.option('--port', default=5000, help='Port to run the webui server on')
@click.option('--host', default='127.0.0.1', help='Host to bind the server to')
@click.option('--no-browser', is_flag=True, help='Do not open browser automatically')
def webui(port, host, no_browser):
    """Start the webui server and open the web page"""
    app = create_app()
    
    if not no_browser:
        # Open browser in a separate thread after a short delay
        def open_browser():
            time.sleep(1.5)
            webbrowser.open(f'http://{host}:{port}')
        threading.Thread(target=open_browser, daemon=True).start()
    
    print(f"Starting zpp webui at http://{host}:{port}")
    print("Press Ctrl+C to stop the server")
    app.run(host=host, port=port, debug=False, use_reloader=False)

@cli.command()
def config():
    """Show or manage configuration"""
    config_manager = ConfigManager()
    current_config = config_manager.get_config()
    click.echo("Current configuration:")
    click.echo(f"  API Key: {'*' * 8 if current_config.get('api_key') else 'Not set'}")
    click.echo(f"  Model: {current_config.get('model', 'Not set')}")
    click.echo(f"  API URL: {current_config.get('api_url', 'Not set')}")

def main():
    cli()

if __name__ == '__main__':
    main()
