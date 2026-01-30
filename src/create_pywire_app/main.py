import time
import sys
import shutil
import subprocess
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
import questionary

console = Console()

LOGO = r"""
 [bold cyan]
██████╗ ██╗   ██╗██╗    ██╗██╗██████╗ ███████╗
██╔══██╗╚██╗ ██╔╝██║    ██║██║██╔══██╗██╔════╝
██████╔╝ ╚████╔╝ ██║ █╗ ██║██║██████╔╝█████╗  
██╔═══╝   ╚██╔╝  ██║███╗██║██║██╔══██╗██╔══╝  
██║        ██║   ╚███╔███╔╝██║██║  ██║███████╗
╚═╝        ╚═╝    ╚══╝╚══╝ ╚═╝╚═╝  ╚═╝╚══════╝
 [/bold cyan]
"""

# --- Templates ---

PYPROJECT_TOML = """[project]
name = "{project_name}"
version = "0.1.0"
description = "A new pywire application"
requires-python = ">=3.12"
dependencies = [
    "{dependency}",
]
"""

MAIN_PY_PATH_BASED = """from pathlib import Path
from pywire import PyWire

# Create application instance
app = PyWire(
    pages_dir="pages",
    enable_pjax=True,
    debug=True
)
"""

MAIN_PY_DICT_BASED = """from pathlib import Path
from pywire import PyWire

# Create application instance
app = PyWire(
    path_based_routing=False,
    pages_dir="pages",
    enable_pjax=True,
    debug=True
)
"""

LAYOUT_WIRE_PATH_BASED = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>My pywire App</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
</head>
<body>
    <header class="container">
        <nav>
            <ul>
                <li><strong>{project_name}</strong></li>
            </ul>
        </nav>
    </header>
    <main class="container">
        <slot />
    </main>
</body>
</html>
"""

INDEX_WIRE_PATH_BASED = """<div class="container">
    <h1>Welcome to pywire</h1>
    <p>Edit <code>pages/index.wire</code> to allow hot reload to do its magic!</p>
    <p>Count is: {count}</p>
    <button @click={count += 1}>Increment</button>
</div>

---
count = 0
"""

LAYOUT_WIRE_DICT_BASED = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>My pywire App</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css">
</head>
<body>
    <header class="container">
        <nav>
            <ul>
                <li><strong>{project_name}</strong></li>
            </ul>
        </nav>
    </header>
    <main class="container">
        <slot />
    </main>
</body>
</html>
"""

HOME_WIRE_DICT_BASED = """!path "/"
!layout "layout.wire"

<div class="container">
    <h1>Welcome to pywire (Dict/Attr Routing)</h1>
    <p>This page uses explicit routing via <code>!path</code> attributes.</p>
    <p>Count is: {count}</p>
    <button @click={count += 1}>Increment</button>
</div>

---
count = 0
"""

DOCKERFILE = """FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install uv && uv sync

COPY . .

CMD ["uv", "run", "pywire", "dev"]
"""

WRANGLER_TOML = """name = "{project_name}"
main = "src/worker.py"
compatibility_date = "2024-01-01"

[site]
bucket = "./public"
"""


def main():
    console.clear()
    
    # Check for local override for testing
    use_local = os.environ.get("USE_LOCAL_PYWIRE") == "1"
    pywire_dep = "pywire"
    if use_local:
        # User requested local testing
        pywire_dep = "pywire @ /Users/rholmdahl/projects/pywire-workspace/pywire"
        console.print("[yellow]WARNING: Using local pywire dependency[/yellow]")

    console.print(LOGO) # Original line
    console.print("[dim]v0.1.0 • The Python Web Framework[/dim]\n")

    try:
        # 2. Project Location
        # Use questionary.path for autocomplete
        project_location = questionary.path(
            "Where should we initialize the system?",
            default="./my-pywire-app",
            style=questionary.Style([
                ('qmark', 'fg:#00ffff bold'),
                ('question', 'bold'),
                ('answer', 'fg:#00ffff'),
            ])
        ).unsafe_ask()
        
        project_path = Path(project_location).expanduser().resolve()
        project_name = project_path.name

        # 3. Project Template
        template = questionary.select(
            "Select a starting template:",
            choices=[
                "Empty (Bare bones)", 
                # "Blog (Markdown + SQLite)", 
                # "SaaS (Stripe + Postgres + Auth)", 
                # "Documentation Site"
            ],
            pointer=">"
        ).unsafe_ask()

        # 4. Routing Strategy
        routing_strategy = questionary.select(
            "Choose a routing architecture:",
            choices=[
                questionary.Choice(
                    "Path-based (Svelte-like)", 
                    value="path",
                    checked=True,
                    shortcut_key="p"
                ),
                questionary.Choice(
                    "Path-Dict / Attribute (Doors.dev-like)", 
                    value="dict", 
                    shortcut_key="d"
                ),
            ],
            qmark="?",
            pointer=">"
        ).unsafe_ask()

        # 5. Project Structure (Src vs Root)
        use_src = questionary.confirm(
            "Use 'src/' directory layout?",
            default=True,
            auto_enter=False,
            instruction=" (Y/n) Recommended for larger projects " # Added leading/trailing space
        ).unsafe_ask()

        # 6. Deployment / Adapters
        adapters = questionary.checkbox(
            "Select deployment adapters to configure:",
            choices=[
                "Docker (Dockerfile)",
                "Cloudflare Pages",
            ],
        ).unsafe_ask()

        # --- The Build Animation ---
        console.print()
        
        # We start with the structure synthesis
        with console.status("[bold cyan]Synthesizing project structure...", spinner="simpleDots"):
            time.sleep(1.0)
            
            # --- Generation Logic ---
            if project_path.exists():
                if any(project_path.iterdir()):
                     pass 

            project_path.mkdir(parents=True, exist_ok=True)
            
            # 1. pyproject.toml
            (project_path / "pyproject.toml").write_text(PYPROJECT_TOML.format(
                project_name=project_name, 
                dependency=pywire_dep
            ))
            
            # 2. Source Directory
            if use_src:
                app_root = project_path / "src"
            else:
                app_root = project_path
            
            app_root.mkdir(exist_ok=True)
            
            # 3. Pages Directory
            pages_dir = app_root / "pages"
            pages_dir.mkdir(exist_ok=True)
            
            # 4. Main & Pages
            if routing_strategy == "path":
                (app_root / "main.py").write_text(MAIN_PY_PATH_BASED)
                (pages_dir / "__layout__.wire").write_text(LAYOUT_WIRE_PATH_BASED.format(project_name=project_name))
                (pages_dir / "index.wire").write_text(INDEX_WIRE_PATH_BASED)
            else:
                (app_root / "main.py").write_text(MAIN_PY_DICT_BASED)
                (pages_dir / "layout.wire").write_text(LAYOUT_WIRE_DICT_BASED.format(project_name=project_name))
                (pages_dir / "home.wire").write_text(HOME_WIRE_DICT_BASED)

            # 5. Adapters
            if "Docker (Dockerfile)" in adapters:
                (project_path / "Dockerfile").write_text(DOCKERFILE)
                
            if "Cloudflare Pages" in adapters:
                (project_path / "wrangler.toml").write_text(WRANGLER_TOML.format(project_name=project_name))
                
            # Create a simple .gitignore
            (project_path / ".gitignore").write_text(".venv/\n__pycache__/\n*.pyc\n")
            
            # Use console.print instead of log to avoid file/line clutter
            console.print("[green]✓[/green] Project structure created")

        # --- UV SYNC with Live Progress ---
        sync_success = False
        with console.status("[bold cyan]Initializing environment (uv sync)...", spinner="bouncingBar"):
            try:
                # Capture output to avoid it polluting expectations, or use text=True for cleaner errors
                # We assume uv is in path since they are running this via uv usually
                # Strip VIRTUAL_ENV to avoid warning about nested environments and ensure clean creation
                env = os.environ.copy()
                env.pop("VIRTUAL_ENV", None)
                
                result = subprocess.run(
                    ["uv", "sync"], 
                    cwd=project_path, 
                    check=True, 
                    capture_output=True, 
                    text=True,
                    env=env
                )
                console.print("[green]✓[/green] Environment optimized")
                sync_success = True
            except subprocess.CalledProcessError as e:
                console.print("[red]✗[/red] Failed to sync environment")
                # Optional: print part of the error if verbose, but user screenshot shows full error output is desired if failed?
                # The previous implementations let it spill. 
                # Let's clean it up: only show error if it fails?
                # User screenshot shows the error output below the ✗.
                console.print(e.stderr)
            except FileNotFoundError:
                console.print("[yellow]![/yellow] uv not found, skipping sync")

        # --- Success ---
        console.print()
        
        commands = [f"cd {project_location}"]
        if not sync_success:
             commands.append("uv sync")
        
        # We assume 'pywire dev' is the goal. 
        # If sync succeeded, 'uv run pywire dev' works.
        # If sync failed, they need to sync first.
        commands.append("pywire dev")
        
        cmd_text = "\n    ".join(commands)

        console.print(Panel(
            Markdown(f"""
# System Online 🟢

Run the following commands to enter the environment:

    {cmd_text}
            """),
            border_style="cyan",
            title="Initialization Complete",
            title_align="left"
        ))
    except KeyboardInterrupt:
        console.print("\n[bold red]System Aborted.[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()
