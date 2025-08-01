"""Command-line interface for openapi2locust."""

import sys
import logging
from pathlib import Path
from typing import Optional

import click

from .generator import LocustGenerator, LocustGeneratorError, InvalidFilenameError
from .config import ConfigurationManager, ConfigError
from . import __version__


@click.command()
@click.argument('spec_file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '-o', '--output',
    type=click.Path(path_type=Path),
    help='Output directory for generated Locust file (default: current directory)'
)
@click.option(
    '-f', '--filename',
    type=str,
    help='Name of the output file (default: locustfile_<spec_name>.py)'
)
@click.option(
    '--validate-only',
    is_flag=True,
    help='Only validate the OpenAPI spec without generating Locust file'
)
@click.option(
    '-v', '--verbose',
    is_flag=True,
    help='Enable verbose logging'
)
@click.option(
    '-c', '--config',
    type=click.Path(exists=True, path_type=Path),
    help='Path to configuration file (YAML or JSON)'
)
@click.version_option(version=__version__)
def main(
    spec_file: Path,
    output: Optional[Path] = None,
    filename: Optional[str] = None,
    validate_only: bool = False,
    verbose: bool = False,
    config: Optional[Path] = None
) -> None:
    """Generate Locust test scripts from OpenAPI specifications.
    
    SPEC_FILE: Path to the OpenAPI specification file (JSON or YAML)
    
    Examples:
    
        # Generate from a local OpenAPI spec
        openapi2locust api-spec.yaml
        
        # Generate with custom output directory and filename
        openapi2locust api-spec.yaml -o ./tests -f my_loadtest.py
        
        # Only validate the OpenAPI spec
        openapi2locust api-spec.yaml --validate-only
    """
    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s' if verbose else '%(message)s'
    )
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration if provided
        config_manager = None
        if config:
            try:
                config_manager = ConfigurationManager(config)
                config_manager.validate_config()
                logger.info(f"Loaded configuration from {config}")
            except ConfigError as e:
                raise click.ClickException(f"Configuration error: {e}")
        
        # Validate inputs
        if not spec_file.exists():
            raise click.ClickException(f"Specification file not found: {spec_file}")
        
        # Validate filename if provided
        if filename and not _is_valid_filename(filename):
            raise click.ClickException(f"Invalid filename: {filename}")
        
        # Set default output directory (use config if available)
        if output is None:
            if config_manager:
                output = Path(config_manager.get_output_dir())
            else:
                output = Path.cwd()
        
        # Ensure output directory exists
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            raise click.ClickException(f"Cannot create output directory {output}: {e}")
        
        # Create generator with configuration
        logger.info(f"Initializing generator for {spec_file}")
        generator = LocustGenerator(str(spec_file), str(output), config_manager)
        
        if validate_only:
            click.echo(f"Validating OpenAPI specification: {spec_file}")
            # This will raise an exception if invalid
            generator.parser.parse()
            click.echo("✓ OpenAPI specification is valid!")
            return
        
        # Generate Locust script
        click.echo(f"Generating Locust script from: {spec_file}")
        
        output_file = generator.generate(filename)
        
        click.echo(f"✓ Locust script generated: {output_file}")
        click.echo("")
        click.echo("Next steps:")
        click.echo(f"1. Review the generated file: {output_file}")
        click.echo("2. Set up any required environment variables for authentication")
        click.echo(f"3. Run the load test: locust -f {output_file}")
        
    except InvalidFilenameError as e:
        click.echo(f"Invalid filename: {e}", err=True)
        sys.exit(1)
    except LocustGeneratorError as e:
        click.echo(f"Generation error: {e}", err=True)
        sys.exit(1)
    except click.ClickException:
        raise  # Let Click handle these
    except FileNotFoundError as e:
        click.echo(f"File not found: {e}", err=True)
        sys.exit(1)
    except PermissionError as e:
        click.echo(f"Permission denied: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=verbose)
        click.echo(f"Unexpected error: {e}", err=True)
        sys.exit(1)


@click.group()
def cli() -> None:
    """OpenAPI to Locust converter tools."""
    pass


@cli.command()
@click.argument('spec_file', type=click.Path(exists=True, path_type=Path))
def info(spec_file: Path) -> None:
    """Show information about an OpenAPI specification."""
    try:
        from .parser import OpenAPIParser
        
        parser = OpenAPIParser(spec_file)
        spec = parser.parse()
        
        info_data = spec.get("info", {})
        
        click.echo(f"OpenAPI Specification Info:")
        click.echo(f"  Title: {info_data.get('title', 'N/A')}")
        click.echo(f"  Version: {info_data.get('version', 'N/A')}")
        click.echo(f"  Description: {info_data.get('description', 'N/A')}")
        
        click.echo(f"\nServers:")
        for i, server in enumerate(parser.servers, 1):
            click.echo(f"  {i}. {server.get('url', 'N/A')}")
            if server.get('description'):
                click.echo(f"     {server['description']}")
        
        endpoints = parser.get_endpoints()
        click.echo(f"\nEndpoints: {len(endpoints)}")
        
        method_counts = {}
        for endpoint in endpoints:
            method = endpoint['method']
            method_counts[method] = method_counts.get(method, 0) + 1
        
        for method, count in sorted(method_counts.items()):
            click.echo(f"  {method}: {count}")
        
        security_schemes = parser.security_schemes
        if security_schemes:
            click.echo(f"\nSecurity Schemes:")
            for name, scheme in security_schemes.items():
                click.echo(f"  {name}: {scheme.get('type', 'unknown')}")
        
    except FileNotFoundError as e:
        click.echo(f"File not found: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _is_valid_filename(filename: str) -> bool:
    """Validate filename input."""
    import re
    if not filename or not isinstance(filename, str):
        return False
    # Basic validation - no path separators, reasonable length, no hidden files
    if len(filename) > 255 or '..' in filename or '/' in filename or '\\' in filename or filename.startswith('.'):
        return False
    return bool(re.match(r'^[a-zA-Z0-9._-]+$', filename))


@cli.command()
@click.argument('spec_file', type=click.Path(exists=True, path_type=Path))
def endpoints(spec_file: Path) -> None:
    """List all endpoints in an OpenAPI specification."""
    try:
        from .parser import OpenAPIParser
        
        parser = OpenAPIParser(spec_file)
        parser.parse()
        endpoints = parser.get_endpoints()
        
        click.echo(f"Endpoints ({len(endpoints)}):")
        click.echo("")
        
        for endpoint in endpoints:
            click.echo(f"{endpoint['method']:8} {endpoint['path']}")
            if endpoint.get('summary'):
                click.echo(f"         {endpoint['summary']}")
            click.echo("")
        
    except FileNotFoundError as e:
        click.echo(f"File not found: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# Add subcommands to the main CLI
cli.add_command(info)
cli.add_command(endpoints)


if __name__ == "__main__":
    main()