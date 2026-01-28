"""
Drupal Manager - Fully Automated Version
Handles the creation of Drupal 11 sites with AI modules.
"""
import argparse
import os
import sys
import subprocess
import time
from pathlib import Path


class DrupalManager:
    def __init__(self, apache_htdocs="C:/APACHE24/htdocs", php_manager=None):
        self.htdocs_path = Path(apache_htdocs)
        # In the future, this could be integrated with PHPManager to get the correct php.exe
        self.php_manager = php_manager
        self.php_exe_path = None
        self.composer_path = None
        self._find_php_installation()

    def _find_php_installation(self):
        """Finds a suitable PHP installation managed by php_manager.py."""
        self.log("Searching for a valid PHP installation...")
        # Check in common locations managed by php_manager.py, starting with newest
        for version in ["8.4", "8.3", "8.2", "8.1", "8.0", "7.4"]:
            php_path = Path(f"C:/php{version}")
            php_exe = php_path / "php.exe"
            composer_phar = php_path / "composer.phar"
            if php_exe.exists() and composer_phar.exists():
                self.log(f"Found PHP {version} at {php_path}", "INFO")
                self.php_exe_path = str(php_exe)
                self.composer_path = str(composer_phar)
                return

        self.log("No suitable PHP installation with Composer found. Please ensure PHP is installed via php_manager.py.",
                 "ERROR")
        raise EnvironmentError("Could not find a valid PHP installation with composer.phar.")

    def log(self, message, level="INFO"):
        """Log messages with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")

    def create_site(self, project_name, drupal_version="11.x-dev"):
        """
        Main method to create a new Drupal site.
        """
        self.log(f"Starting creation of Drupal site: {project_name}")
        project_path = self.htdocs_path / project_name

        if project_path.exists():
            self.log(f"Project path {project_path} already exists. Aborting.", "ERROR")
            return False

        # Step 1: Create project with Composer
        if not self._create_drupal_project(project_path, drupal_version):
            return False

        # Step 2: Add AI and Key modules
        if not self._add_modules(project_path):
            return False

        # Step 3: Install Drupal using Drush
        if not self._install_site(project_path):
            return False

        # Step 4: Enable modules
        if not self._enable_modules(project_path):
            return False

        # Step 5: Create .env.example
        self._create_env_example(project_path)

        self.log(f"Successfully created Drupal site: {project_name}", "INFO")
        self.log(f"Site located at: {project_path}", "INFO")
        self.log(f"Next steps: Configure your API keys in the Drupal admin or using the .env file.", "INFO")

        return True

    def _run_command(self, command, cwd):
        """Helper to run a command and log its output."""
        self.log(f"Running command: {' '.join(command)} in {cwd}", "DEBUG")
        try:
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace'
            )

            # Stream output for better feedback
            for line in process.stdout:
                self.log(line.strip(), "CMD")

            process.wait()

            if process.returncode != 0:
                self.log(f"Command failed with exit code {process.returncode}", "ERROR")
                stderr_output = process.stderr.read()
                self.log(stderr_output, "ERROR")
                return False

            return True
        except FileNotFoundError:
            self.log(f"Command not found: {command[0]}", "ERROR")
            return False
        except Exception as e:
            self.log(f"An exception occurred: {e}", "ERROR")
            return False

    def _create_drupal_project(self, project_path, drupal_version):
        """Creates a new Drupal project using Composer."""
        self.log("Creating Drupal project with Composer...")
        command = [
            self.php_exe_path,
            self.composer_path,
            "create-project",
            f"drupal/recommended-project:{drupal_version}",
            str(project_path)
        ]
        return self._run_command(command, self.htdocs_path)

    def _add_modules(self, project_path):
        """Adds Drupal AI and requested modules via Composer."""
        self.log("Adding AI modules and dependencies...")

        modules = [
            "drupal/ai:^1.3@beta",
            "drupal/key",
            "drupal/ai_agents",
            "drupal/ai_simple_pdf_to_text:^1.0@alpha",
            "drupal/tool:^1.0@alpha",
            "drupal/ai_provider_openai",
            "drupal/ai_provider_ollama",
            "drupal/gemini_provider",
            "drupal/ai_provider_anthropic"
        ]

        for module in modules:
            self.log(f"Requiring module: {module}")
            command = [self.php_exe_path, self.composer_path, "require", module]
            if not self._run_command(command, project_path):
                self.log(f"Failed to add module {module}.", "ERROR")
                return False

        return True

    def _install_site(self, project_path):
        """Installs the Drupal site using Drush."""
        self.log("Installing Drupal site using Drush...")

        drush_path = project_path / "vendor" / "bin" / "drush"
        db_config = "mysql://drupal_user:drupal_pass_123@localhost/drupal_db"  # Assumes mysql_manager created this

        command = [
            self.php_exe_path,
            str(drush_path),
            "site:install",
            "--db-url=" + db_config,
            "--account-name=admin",
            "--account-pass=admin",
            "--site-name=DrupalAI Site",
            "-y"  # Assume yes for all prompts
        ]
        return self._run_command(command, project_path / "web")  # Drush commands run from the web root

    def _enable_modules(self, project_path):
        """Enables the newly added modules."""
        self.log("Enabling AI modules...")
        drush_path = project_path / "vendor" / "bin" / "drush"

        modules = [
            "ai",
            "key",
            "ai_agents",
            "ai_simple_pdf_to_text",
            "tool",
            "ai_provider_openai",
            "ai_provider_ollama",
            "gemini_provider",
            "ai_provider_anthropic"
        ]

        command = [
            self.php_exe_path,
            str(drush_path),
            "en"
        ] + modules + ["-y"]

        return self._run_command(command, project_path / "web")

    def _create_env_example(self, project_path):
        """Creates a .env.example file with API key placeholders."""
        self.log("Creating .env.example file...")
        env_content = """# AI API Keys configuration
# Rename this file to .env and fill in your keys
# These can be used by the Key module if configured to read from environment variables

OPENAI_API_KEY=your_openai_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here
GEMINI_API_KEY=your_gemini_key_here
OLLAMA_HOST=http://localhost:11434
"""
        try:
            with open(project_path / ".env.example", "w") as f:
                f.write(env_content)
            return True
        except Exception as e:
            self.log(f"Failed to create .env.example: {e}", "ERROR")
            return False


def main():
    parser = argparse.ArgumentParser(description="Drupal Manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_parser = subparsers.add_parser("create", help="Create a new Drupal site.")
    create_parser.add_argument("project_name", help="The name of the project folder to be created.")
    create_parser.add_argument("--drupal-version", default="11.x-dev", help="The version of Drupal to install.")

    args = parser.parse_args()
    manager = DrupalManager()

    if args.command == "create":
        manager.create_site(args.project_name, args.drupal_version)


if __name__ == "__main__":
    main()
