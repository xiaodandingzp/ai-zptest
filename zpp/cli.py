import click
import os
import webbrowser
import threading
import time
from flask import Flask, render_template, jsonify, request
from .webui import create_app
from .config import ConfigManager
from .knowledge import KnowledgeManager


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
@click.option('--dir', 'knowledge_dir', default=None, help='Knowledge directory path')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed output')
def init(knowledge_dir, verbose):
    """
    Initialize the knowledge base.
    
    Scans files in the knowledge directory, creates embeddings, 
    and stores them in a vector database for RAG (Retrieval Augmented Generation).
    """
    click.echo("Initializing knowledge base...")
    
    # 创建知识库管理器
    manager = KnowledgeManager(knowledge_dir)
    
    if knowledge_dir:
        click.echo(f"Knowledge directory: {knowledge_dir}")
    else:
        click.echo(f"Knowledge directory: {manager.knowledge_dir}")
    
    # 检查目录是否存在
    if not manager.knowledge_dir.exists():
        click.echo(f"\nWarning: Knowledge directory does not exist.")
        click.echo(f"Creating directory: {manager.knowledge_dir}")
        manager.knowledge_dir.mkdir(parents=True, exist_ok=True)
        click.echo("\nPlease add files to the knowledge directory and run 'zpp init' again.")
        click.echo("Supported file types: .txt, .md, .json, .py, .js, .html, .css")
        return
    
    # 初始化知识库
    result = manager.init_knowledge_base(verbose=verbose)
    
    if result.get("success"):
        click.echo(click.style("\nKnowledge base initialized successfully!", fg="green"))
        click.echo(f"  Files processed: {result.get('file_count', 0)}")
        click.echo(f"  Text chunks created: {result.get('chunk_count', 0)}")
    else:
        click.echo(click.style("\nFailed to initialize knowledge base:", fg="red"))
        click.echo(f"  Error: {result.get('error', 'Unknown error')}")
        click.echo("\nTips:")
        click.echo("  1. Make sure you have configured a model with API key")
        click.echo("  2. Install required dependencies: pip install langchain langchain-community langchain-openai chromadb")


@cli.command()
@click.argument('query')
@click.option('--k', default=4, help='Number of results to return')
def search(query, k):
    """Search the knowledge base for relevant content."""
    manager = KnowledgeManager()
    
    click.echo(f"Searching for: {query}")
    click.echo("-" * 50)
    
    results = manager.search(query, k=k)
    
    if not results:
        click.echo("No results found.")
        click.echo("\nMake sure you have run 'zpp init' to initialize the knowledge base.")
        return
    
    for i, item in enumerate(results, 1):
        source = item.get("metadata", {}).get("filename", "Unknown")
        content = item.get("content", "")
        click.echo(f"\n[Result {i}] Source: {source}")
        click.echo("-" * 40)
        # 截断过长的内容
        if len(content) > 500:
            click.echo(content[:500] + "...")
        else:
            click.echo(content)


@cli.command()
def config():
    """Show or manage configuration"""
    config_manager = ConfigManager()
    current_model = config_manager.get_current_model_name()
    models = config_manager.list_models()
    
    click.echo("Current configuration:")
    click.echo(f"  Current model: {current_model or 'Not set'}")
    click.echo(f"\nAvailable models:")
    
    for model_id, model_config in models.items():
        marker = " (current)" if model_id == current_model else ""
        click.echo(f"  - {model_config.get('display_name', model_id)}{marker}")
        click.echo(f"    Provider: {model_config.get('provider', 'unknown')}")
        click.echo(f"    Model: {model_config.get('model', 'unknown')}")


@cli.command()
def clear():
    """Clear the knowledge base."""
    if click.confirm("Are you sure you want to clear the knowledge base?"):
        manager = KnowledgeManager()
        manager.clear_knowledge_base()
        click.echo("Knowledge base cleared.")


def main():
    cli()


if __name__ == '__main__':
    main()
